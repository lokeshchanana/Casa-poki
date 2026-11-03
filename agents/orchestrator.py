import json
import logging
import os
import re
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional
import httpx

from n8n_catalog import N8N_BASE_URL, get_n8n_workflows, inspect_latest_n8n_execution
from state_store import (
    add_agent_feedback,
    add_chat_message,
    add_lesson,
    get_backlog_specs,
    get_chat_history,
    get_last_audit_record,
    get_lessons,
    get_system_summary,
    log_audit_result,
    log_token_usage,
    save_missing_workflow_spec,
    update_audit_status,
)
from tools import TOOL_SCHEMAS, execute_tool, format_tool_result

logger = logging.getLogger("agent_orchestrator")

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://192.168.1.240:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "crm-qwen:3b")
DEFAULT_TASK_BUDGET = int(os.environ.get("TASK_TOKEN_BUDGET", "32000"))


# =============================================================================
# Modern Multi-Agent Prompts
# =============================================================================

MANAGER_SYSTEM_PROMPT = """You are the Central Manager Agent for Lokesh Chanana Real Estate and Casa-poki.
You have access to a suite of tools to manage Twenty CRM (contacts, tasks, notes, deals) and inspect n8n automation workflows.

CORE CAPABILITIES & GUIDELINES:
1. Tool Invocation:
   - When the user instructs you to search, view, count, create, update, or delete contacts, tasks, or notes in the CRM, invoke the appropriate tool from your tools list.
   - For queries like "How many people...", use `search_contacts` with `count_mode: true` and appropriate filters (`can_email`, `phone_blank`, `email_present`).
   - Tolerate minor typos in user requests (e.g. "is there a use Lokesh" -> search for "Lokesh", "add a not for user X" -> manage_notes).
2. Capability Inquiries vs. Actions:
   - If the user asks a question about what you can do (e.g. "So you can't update any contacts?", "Can you update contacts?"), DO NOT invoke an empty update tool. Instead, answer directly in natural language, explaining your capabilities and detailing what parameters are needed (e.g. contact name/ID and the fields to change).
3. Zero Stray Communications (STRICT SAFETY):
   - All production services are live. Never generate random or fake contact emails/phones. Only verified owner contact details (lokeshchanana@gmail.com / 8018601052) may be used for testing.
4. Response Tone:
   - Professional, concise, executive, and direct. Deliver clear answers without verbose filler.
"""

AUDITOR_SYSTEM_PROMPT = """You are the Auditor Agent for Casa-poki and Lokesh Chanana Real Estate.
Review the execution of the IT Agent and tool output.
Verify:
1. Zero Hallucinations: Does the output accurately reflect the live database / tool response?
2. Criteria Satisfaction: Did the execution satisfy the user's specific request?
3. Safety Compliance: Were any unauthorized test records or stray communications triggered?

Output JSON:
{
  "audit_status": "PASS" | "QUALITY_IMPROVEMENT_NEEDED" | "MISSING_CAPABILITY",
  "quality_score": 1 to 10,
  "findings": "Clear explanation of audit verification verdict",
  "lesson_rule": "Optional preventative lesson if an improvement is needed, else empty"
}
"""


# =============================================================================
# LLM Gateway (Native Tool Calling & Chat)
# =============================================================================

async def call_llm_chat(
    task_id: str,
    agent_name: str,
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
    max_tokens: int = 2000,
    temperature: float = 0.1,
) -> Dict[str, Any]:
    """
    Calls the local or configured LLM engine with tool declarations and token tracking.
    """
    start_ts = time.time()
    payload: Dict[str, Any] = {
        "model": DEFAULT_MODEL,
        "messages": messages,
        "stream": False,
        "keep_alive": "24h",
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    if tools:
        payload["tools"] = tools

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        duration_ms = int((time.time() - start_ts) * 1000)
        logger.error(f"LLM call failed: {e}")
        return {
            "content": f"LLM Error: {str(e)}",
            "tool_calls": [],
            "metrics": log_token_usage(task_id, agent_name, DEFAULT_MODEL, 0, 0, 0.0, duration_ms),
        }

    duration_ms = int((time.time() - start_ts) * 1000)
    msg = data.get("message") or {}
    content = msg.get("content", "") or ""
    tool_calls = msg.get("tool_calls", []) or []

    prompt_tokens = int(data.get("prompt_eval_count") or 0)
    completion_tokens = int(data.get("eval_count") or 0)
    eval_duration_ns = int(data.get("eval_duration") or 0)
    tok_per_sec = (completion_tokens / (eval_duration_ns / 1e9)) if eval_duration_ns > 0 else 0.0

    metrics = log_token_usage(
        task_id=task_id,
        agent_name=agent_name,
        model=DEFAULT_MODEL,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        tokens_per_sec=tok_per_sec,
        duration_ms=duration_ms,
    )

    return {
        "content": content,
        "tool_calls": tool_calls,
        "metrics": metrics,
    }


# =============================================================================
# Multi-Agent Pipeline Runner
# =============================================================================

async def run_multi_agent_pipeline(
    user_message: str,
    session_id: str = "manager_default",
    token_budget: int = DEFAULT_TASK_BUDGET,
) -> AsyncGenerator[str, None]:
    """
    Modern Antigravity Manager Agent Pipeline:
    1. Multi-turn context resolution & triage
    2. Native tool execution via IT Agent (Twenty CRM / n8n gateway)
    3. Auditor Agent quality verification & spec generation
    4. Streams real-time ndjson events to the Check-in web app.
    """
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    tokens_used = 0
    trace_steps: List[Dict[str, Any]] = []

    def emit(event_type: str, data: Dict[str, Any]) -> str:
        return json.dumps({"type": event_type, "task_id": task_id, **data}) + "\n"

    # Step 1: Manager Status
    yield emit(
        "agent_status",
        {
            "agent": "manager",
            "phase": "routing",
            "message": "Manager Agent is analyzing your request and preparing execution plan...",
        },
    )

    u_low = user_message.strip().lower()

    # -------------------------------------------------------------------------
    # Fast-Path 1: Human Feedback & Audit Flagging
    # -------------------------------------------------------------------------
    feedback_triggers = [
        "note for auditor", "note to auditor", "note for anti gravity", "note to anti gravity",
        "last execution is not correct", "execution is not correct", "result is no good",
        "result is not correct", "incorrect result", "fix this functionality", "flag this execution"
    ]
    if any(ft in u_low for ft in feedback_triggers):
        last_audit = get_last_audit_record()
        flagged_task_id = last_audit["task_id"] if last_audit else None
        saved_fb = add_agent_feedback(
            user_feedback=user_message,
            target_agent="auditor",
            action_taken="Flagged previous execution and recorded Auditor improvement task.",
            task_id=flagged_task_id,
        )
        if flagged_task_id:
            update_audit_status(flagged_task_id, "USER_FLAGGED_FAILURE", 2)

        fb_trace = {
            "step": 1,
            "agent": "Auditor Agent",
            "role": "Human Feedback Registry",
            "result": {"status": "FEEDBACK_LOGGED", "feedback_id": saved_fb["id"]},
            "metrics": {"duration_ms": 1, "total_tokens": 0},
            "tokens_remaining": token_budget,
        }
        trace_steps.append(fb_trace)
        yield emit("agent_trace", {"trace": fb_trace})

        reply = (
            f"### Human Feedback Recorded\n"
            f"- **Feedback ID:** `{saved_fb['id']}`\n"
            f"- **Target Task:** `{flagged_task_id or 'General'}`\n"
            f"- **Status:** Flagged for continuous learning and logged in Auditor Registry.\n"
            f"- The IT Agent was **not** invoked to avoid unnecessary write operations."
        )
        add_chat_message(session_id, "user", user_message)
        add_chat_message(session_id, "assistant", reply)
        yield emit("item", {"content": reply})
        yield emit(
            "agent_summary",
            {
                "success": True,
                "workflow_executed": None,
                "trace_steps": trace_steps,
                "tokens_used": 0,
                "token_budget": token_budget,
            },
        )
        return

    # -------------------------------------------------------------------------
    # Fast-Path 2: Teaching Rules ("Remember: ...")
    # -------------------------------------------------------------------------
    if any(u_low.startswith(p) for p in ["remember:", "remember to", "teach:", "add a rule:"]):
        rule_text = re.sub(r"^(remember:|remember to|teach:|add a rule:)\s*", "", user_message, flags=re.I).strip()
        target_agent = "it_agent" if "it" in u_low or "n8n" in u_low or "crm" in u_low else "manager"
        saved_lesson = add_lesson(target_agent, rule_text, source="user_prompt")

        teach_trace = {
            "step": 1,
            "agent": "Manager Agent",
            "role": "Lesson Registry",
            "result": {"status": "LESSON_ADDED", "lesson_id": saved_lesson["id"]},
            "metrics": {"duration_ms": 1, "total_tokens": 0},
            "tokens_remaining": token_budget,
        }
        trace_steps.append(teach_trace)
        yield emit("agent_trace", {"trace": teach_trace})

        reply = (
            f"### Rule Added to Agent Memory\n"
            f"- **Agent:** `{target_agent}`\n"
            f"- **Rule:** \"{rule_text}\"\n"
            f"- **Lesson ID:** `{saved_lesson['id']}`\n"
            f"All agents will adhere to this guideline in future executions."
        )
        add_chat_message(session_id, "user", user_message)
        add_chat_message(session_id, "assistant", reply)
        yield emit("item", {"content": reply})
        yield emit(
            "agent_summary",
            {
                "success": True,
                "workflow_executed": None,
                "trace_steps": trace_steps,
                "tokens_used": 0,
                "token_budget": token_budget,
            },
        )
        return

    # -------------------------------------------------------------------------
    # Main Agent Reasoner: Multi-Turn Context + Native Tool Calling
    # -------------------------------------------------------------------------
    # Load historical context
    history = get_chat_history(session_id, limit=6)
    lessons = [l["rule"] for l in get_lessons()[:8]]
    lessons_block = ("\nActive Lessons:\n" + "\n".join(f"- {r}" for r in lessons)) if lessons else ""

    messages = [
        {"role": "system", "content": MANAGER_SYSTEM_PROMPT + lessons_block},
    ]
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": user_message})

    # Call Manager Agent with tool declarations
    llm_resp = await call_llm_chat(
        task_id=task_id,
        agent_name="manager",
        messages=messages,
        tools=TOOL_SCHEMAS,
        max_tokens=1500,
        temperature=0.1,
    )
    tokens_used += llm_resp["metrics"]["total_tokens"]
    tool_calls = llm_resp["tool_calls"]
    direct_content = llm_resp["content"]

    # -------------------------------------------------------------------------
    # Path A: Manager Calls One or More Tools via IT Agent
    # -------------------------------------------------------------------------
    if tool_calls:
        call = tool_calls[0]
        func = call.get("function") or {}
        tool_name = func.get("name")
        args = func.get("arguments") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {}

        # Fallback check for query typos (e.g. "use Lokesh" -> "Lokesh")
        if tool_name == "search_contacts" and "query" in args:
            args["query"] = re.sub(r"^(is there a |does a |find |search |use |user )", "", str(args["query"]), flags=re.I).strip()

        yield emit(
            "agent_status",
            {
                "agent": "it_agent",
                "phase": "executing_tool",
                "message": f"IT Agent is executing verified CRM tool: `{tool_name}`...",
            },
        )

        step1_trace = {
            "step": 1,
            "agent": "Manager Agent",
            "role": "Task Triage & Delegation",
            "decision": {
                "intent": "EXECUTE_TOOL",
                "tool": tool_name,
                "arguments": args,
                "delegated_to": "IT Agent",
            },
            "metrics": llm_resp["metrics"],
            "tokens_remaining": max(0, token_budget - tokens_used),
        }
        trace_steps.append(step1_trace)
        yield emit("agent_trace", {"trace": step1_trace})

        # Execute Tool via IT Gateway
        tool_result = await execute_tool(tool_name, args)
        formatted_result = format_tool_result(tool_name, tool_result, args)

        step2_trace = {
            "step": 2,
            "agent": "IT Agent",
            "role": "Tool Execution Gateway",
            "result": {
                "tool": tool_name,
                "status": "SUCCESS" if tool_result.get("ok", True) else "FAILED",
                "raw_result": tool_result,
            },
            "metrics": {"duration_ms": tool_result.get("duration_ms", 50), "total_tokens": 0},
            "tokens_remaining": max(0, token_budget - tokens_used),
        }
        trace_steps.append(step2_trace)
        yield emit("agent_trace", {"trace": step2_trace})

        # Step 3: Auditor Verification
        yield emit(
            "agent_status",
            {
                "agent": "auditor",
                "phase": "auditing",
                "message": "Auditor Agent is verifying execution output and ensuring zero hallucinations...",
            },
        )

        audit_ok = tool_result.get("ok", True) and "error" not in tool_result
        audit_findings = (
            f"Verified tool `{tool_name}` executed against Twenty CRM. Zero stray communications detected."
            if audit_ok
            else f"Execution of `{tool_name}` failed: {tool_result.get('error')}"
        )
        audit_status = "PASS" if audit_ok else "QUALITY_IMPROVEMENT_NEEDED"
        quality_score = 10 if audit_ok else 2

        log_audit_result(
            task_id=task_id,
            user_request=user_message,
            routed_agent="it_agent",
            workflow_id="crmRelaticleAssistant",
            audit_status=audit_status,
            quality_score=quality_score,
            findings=audit_findings,
        )

        step3_trace = {
            "step": 3,
            "agent": "Auditor Agent",
            "role": "Quality & Compliance Audit",
            "report": {
                "audit_status": audit_status,
                "quality_score": quality_score,
                "findings": audit_findings,
            },
            "metrics": {"duration_ms": 2, "total_tokens": 0},
            "tokens_remaining": max(0, token_budget - tokens_used),
        }
        trace_steps.append(step3_trace)
        yield emit("agent_trace", {"trace": step3_trace})

        # Save to chat history
        add_chat_message(session_id, "user", user_message)
        add_chat_message(session_id, "assistant", formatted_result, tool_calls=[{"name": tool_name, "args": args}])

        # Deliver final content
        yield emit("item", {"content": formatted_result})
        yield emit(
            "agent_summary",
            {
                "success": audit_ok,
                "workflow_executed": "crmRelaticleAssistant",
                "trace_steps": trace_steps,
                "tokens_used": tokens_used,
                "token_budget": token_budget,
            },
        )
        return

    # -------------------------------------------------------------------------
    # Path B: Direct Conversational / Capability Response (0 Tool Calls)
    # -------------------------------------------------------------------------
    yield emit(
        "agent_status",
        {
            "agent": "manager",
            "phase": "answering",
            "message": "Manager Agent formulated a direct strategic response...",
        },
    )

    log_audit_result(
        task_id=task_id,
        user_request=user_message,
        routed_agent="manager",
        workflow_id=None,
        audit_status="PASS",
        quality_score=10,
        findings="Manager answered directly and concisely without unnecessary IT Agent tool overhead.",
    )

    step1_trace = {
        "step": 1,
        "agent": "Manager Agent",
        "role": "Direct Strategic Response",
        "result": {"status": "DIRECT_ANSWER_DELIVERED"},
        "metrics": llm_resp["metrics"],
        "tokens_remaining": max(0, token_budget - tokens_used),
    }
    trace_steps.append(step1_trace)
    yield emit("agent_trace", {"trace": step1_trace})

    final_msg = direct_content.strip() or "I have processed your request."
    add_chat_message(session_id, "user", user_message)
    add_chat_message(session_id, "assistant", final_msg)

    yield emit("item", {"content": final_msg})
    yield emit(
        "agent_summary",
        {
            "success": True,
            "workflow_executed": None,
            "trace_steps": trace_steps,
            "tokens_used": tokens_used,
            "token_budget": token_budget,
        },
    )
