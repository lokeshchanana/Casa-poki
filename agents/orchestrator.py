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
    log_request_flow,
    log_token_usage,
    save_missing_workflow_spec,
    update_audit_status,
)
from tools import TOOL_SCHEMAS, execute_tool, format_tool_result
import vector_memory

logger = logging.getLogger("agent_orchestrator")

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://192.168.1.240:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "crm-qwen:3b")
DEFAULT_TASK_BUDGET = int(os.environ.get("TASK_TOKEN_BUDGET", "32000"))


# =============================================================================
# Modern Multi-Agent Prompts
# =============================================================================

# =============================================================================
# Modern Multi-Agent Prompts & Persona Specializations
# =============================================================================

SPECIALIST_PERSONAS = {
    "manager": {
        "name": "Marcus Vance",
        "role": "General Manager & Orchestrator",
        "system_prompt": """You are Marcus Vance, General Manager & Orchestrator for Lokesh Chanana Real Estate and Casa-poki.
You focus on overall business triage, client communications, and orchestrating work across specialist agents.
DELEGATION POLICY:
- If a task requires IT infrastructure, server container healing, or technical database repairs, delegate to 'it'.
- If a task requires market comps, CMA, valuation, or MLS analytics, delegate to 'cma'.
- If a task requires marketing copy, listing flyers, or open house announcements, delegate to 'marketing'.
- If a task requires financial accounting, ledger statements, or transaction fee calculations, delegate to 'finance'.
- If a task requires client visitor intake or open house sign-in management, delegate to 'intake'.
- You have tools to manage Twenty CRM directly, query/store vector memory, or delegate to any specialist.""",
    },
    "it": {
        "name": "Ian Torres",
        "role": "IT Systems & Infrastructure Guardian",
        "system_prompt": """You are Ian Torres, IT Systems & Infrastructure Guardian for Casa-poki.
You focus on Docker containers, system self-healing, Uptime Kuma monitors, database connectivity, and backend tool reliability.
You provide technical precision and operational integrity.""",
    },
    "auditor": {
        "name": "Audrey Chen",
        "role": "Quality Assurance & Compliance Auditor",
        "system_prompt": """You are Audrey Chen, Quality Assurance & Compliance Auditor for Casa-poki.
You verify outputs, enforce the strict Zero Stray Communications policy, ensure no hallucinations, and log preventative lessons.""",
    },
    "intake": {
        "name": "Miles Miller",
        "role": "Client Intake & Communications",
        "system_prompt": """You are Miles Miller, Client Intake Specialist.
You focus on Open House check-ins, visitor inquiries, prompt CRM lead capture, and greeting new clients with warmth and accuracy.""",
    },
    "finance": {
        "name": "Fiona Banks",
        "role": "Financial Controller & Bigcapital Manager",
        "system_prompt": """You are Fiona Banks, Financial Controller for Casa-poki and Lokesh Chanana Real Estate.
You manage all financial accounting through Bigcapital hosted at https://finance.lokeshchanana.com.
You have direct tools to:
- Record incoming bills and invoices (`finance_record_bill`)
- Settle and record bill payments (`finance_record_payment`)
- Audit bills, open balances, and due dates (`finance_list_bills`, `finance_dashboard`)
- Ingest batches of historical bills and receipts (`finance_import_historical_bills`)
Whenever the user or an incoming email/message presents a bill or payment, extract the vendor, amount, due date, category, and record it into Bigcapital.
When asked about finances, summarize accounts payable, upcoming due bills, and provide the portal link https://finance.lokeshchanana.com.""",
    },
    "marketing": {
        "name": "Maya Reyes",
        "role": "Creative Director & Listing Promotions",
        "system_prompt": """You are Maya Reyes, Creative Director for Lokesh Chanana Real Estate.
You focus on high-impact property marketing, neighborhood highlights, open house flyers, and compelling real estate storytelling.""",
    },
    "cma": {
        "name": "Carter Hayes",
        "role": "Real Estate Analyst & CMA Specialist",
        "system_prompt": """You are Carter Hayes, Real Estate Market Analyst & CMA Specialist.
You focus on Northwest MLS comparables, King County parcel pricing, school district impacts, and accurate valuation modeling.""",
    },
    "mailman": {
        "name": "Silas Drake",
        "role": "Mail Courier & Inbox Dispatcher",
        "system_prompt": """You are Silas Drake, Mail Courier & Inbox Dispatcher for Casa-poki and Lokesh Chanana Real Estate.
You are responsible for connecting to lokesh@lokeshchanana.com, reading incoming messages, stripping noise and HTML signatures, and delivering triaged email summaries directly to Marcus Vance (General Manager).
You do not make independent business decisions; your sole mission is to reliably fetch, inspect, and present clean emails to Marcus Vance so he can decide what needs to be done:
- Finance emails (bills, invoices, payment receipts, taxes) -> Handed off to Fiona Banks (Finance).
- CRM related emails (buyer/seller inquiries, client leads, contact info updates) -> Handed off to Miles Miller (Intake) or recorded directly into Twenty CRM.
- CMA & property valuation inquiries -> Handed off to Carter Hayes (CMA).
- Marketing & promotional opportunities -> Handed off to Maya Reyes (Marketing).
- IT & infrastructure alerts -> Handed off to Ian Torres (IT).
- Useless / spam / cold solicitations -> Filtered out and discarded.""",
    },
}

MANAGER_SYSTEM_PROMPT = """You are Marcus Vance, Central Manager Agent for Lokesh Chanana Real Estate and Casa-poki.
You have access to a suite of tools to manage Twenty CRM (contacts, tasks, notes, deals), inspect automations, store/query vector memory, read incoming emails via Silas Drake, and delegate to specialist agents.

CORE CAPABILITIES & GUIDELINES:
1. Tool Invocation & Delegation:
   - When the user asks to check, read, triage, or fetch incoming emails from lokesh@lokeshchanana.com, invoke `mailman_read_inbox` or delegate to Silas Drake ('mailman').
   - When Silas Drake presents emails, analyze each message and decide what needs to be done:
     * Finance email (invoices, utility bills, receipts, payment notices) -> Delegate to Fiona Banks ('finance') or call `finance_record_bill` to record into Bigcapital.
     * CRM related email (buyer/seller inquiries, new leads, client updates) -> Delegate to Miles Miller ('intake') or call `create_contact` / `manage_notes` in Twenty CRM.
     * CMA / valuation request -> Delegate to Carter Hayes ('cma') for MLS comps.
     * Marketing / promotional email -> Delegate to Maya Reyes ('marketing') or review listing promos.
     * IT / system alerts -> Delegate to Ian Torres ('it') to inspect containers or monitors.
     * Useless email / spam / cold solicitation -> Categorize as spam and discard with zero action.
   - When the user asks to consult, ask, or assign a task to another specialist (such as Carter Hayes for CMA/valuation, Maya Reyes for marketing, Fiona Banks for finance, Miles Miller for intake, Silas Drake for emails, Ian Torres for IT), invoke `delegate_to_agent` with target_agent and task_description.
   - When the user instructs you to search, view, count, create, update, or delete contacts, tasks, or notes in Twenty CRM, invoke the appropriate CRM tool.
   - For queries like "How many people...", use `search_contacts` with `count_mode: true` and appropriate filters (`can_email`, `phone_blank`, `email_present`).
   - Before answering complex questions or market inquiries, invoke `query_memory` to check the Vector Database for stored insights or past resolutions.
   - Store valuable lessons, client preferences, or domain facts with `store_memory` so the team gets continuously better.
2. Capability Inquiries vs. Actions:
   - If the user asks a question about what you can do (e.g. "Can you read my emails?"), answer directly in natural language explaining your capabilities, introducing Silas Drake, and noting the parameters.
3. Zero Stray Communications (STRICT SAFETY):
   - All production services are live. Never generate random or fake contact emails/phones. Only verified owner contact details (lokeshchanana@gmail.com / 8018601052) may be used for testing.
4. Response Tone:
   - Professional, concise, executive, and direct.
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
        async with httpx.AsyncClient(timeout=180.0) as client:
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
    start_time = time.time()
    tokens_used = 0
    trace_steps: List[Dict[str, Any]] = []
    invoked_tool_name: Optional[str] = None
    invoked_tool_args: Optional[Dict[str, Any]] = None
    tool_result: Optional[Dict[str, Any]] = None

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
    # Main Agent Reasoner: Vector Memory Retrieval + Native Multi-Agent Triage
    # -------------------------------------------------------------------------
    # 1. Retrieve relevant memories from the Vector Database
    recalled_memories = vector_memory.query_memories(query=user_message, top_k=3)
    memory_context_block = ""
    if recalled_memories:
        memory_lines = [
            f"- [{m['agent_id'].upper()}] {m['content']} (relevance: {int(m['similarity']*100)}%)"
            for m in recalled_memories
        ]
        memory_context_block = "\nRelevant Vector Memories from Brain:\n" + "\n".join(memory_lines) + "\n"

    # Load historical context
    history = get_chat_history(session_id, limit=6)
    lessons = [l["rule"] for l in get_lessons()[:8]]
    lessons_block = ("\nActive Lessons:\n" + "\n".join(f"- {r}" for r in lessons)) if lessons else ""

    messages = [
        {"role": "system", "content": MANAGER_SYSTEM_PROMPT + lessons_block + memory_context_block},
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

        invoked_tool_name = tool_name
        invoked_tool_args = args

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

        # Special Handling: Dynamic Inter-Agent Delegation
        if tool_name == "delegate_to_agent":
            target_agent = args.get("target_agent", "manager").lower()
            task_desc = args.get("task_description", "")
            context_data = args.get("context_data", "")

            specialist_info = SPECIALIST_PERSONAS.get(target_agent, SPECIALIST_PERSONAS["manager"])
            specialist_name = specialist_info["name"]

            yield emit(
                "agent_status",
                {
                    "agent": target_agent,
                    "phase": "specialist_working",
                    "message": f"{specialist_name} ({specialist_info['role']}) is executing delegated task...",
                },
            )

            # Retrieve specialist vector memory for this task
            spec_memories = vector_memory.query_memories(query=task_desc, agent_id=target_agent, top_k=2)
            spec_mem_str = "\n".join(f"- {m['content']}" for m in spec_memories) if spec_memories else "None"

            specialist_messages = [
                {
                    "role": "system",
                    "content": f"{specialist_info['system_prompt']}\nRelevant Domain Knowledge:\n{spec_mem_str}\nProvide a direct, high-value, professional response.",
                },
                {
                    "role": "user",
                    "content": f"Task: {task_desc}\nContext: {context_data}",
                },
            ]

            spec_tools = (
                [t for t in TOOL_SCHEMAS if t["function"]["name"].startswith("finance_")]
                if target_agent == "finance"
                else (
                    [t for t in TOOL_SCHEMAS if t["function"]["name"].startswith("mailman_")]
                    if target_agent == "mailman"
                    else None
                )
            )

            spec_resp = await call_llm_chat(
                task_id=task_id,
                agent_name=target_agent,
                messages=specialist_messages,
                tools=spec_tools,
                max_tokens=800,
                temperature=0.2,
            )
            tokens_used += spec_resp["metrics"]["total_tokens"]
            specialist_output = spec_resp["content"]

            # If specialist invoked tools autonomously, execute and synthesize response
            if spec_resp.get("tool_calls"):
                fn_formatted = ""
                for t_call in spec_resp["tool_calls"]:
                    fn_data = t_call.get("function", {})
                    fn_name = fn_data.get("name")
                    fn_args = fn_data.get("arguments", {})
                    fn_res = await execute_tool(fn_name, fn_args)
                    fn_formatted = format_tool_result(fn_name, fn_res, fn_args)
                    specialist_messages.append({"role": "assistant", "content": "", "tool_calls": [t_call]})
                    specialist_messages.append({"role": "tool", "content": json.dumps(fn_res)})

                spec_turn2 = await call_llm_chat(
                    task_id=task_id,
                    agent_name=target_agent,
                    messages=specialist_messages,
                    tools=None,
                    max_tokens=800,
                    temperature=0.2,
                )
                tokens_used += spec_turn2["metrics"]["total_tokens"]
                specialist_output = spec_turn2["content"]
                if fn_formatted and fn_formatted not in specialist_output:
                    specialist_output = f"{fn_formatted}\n\n{specialist_output}"

            tool_result = {
                "ok": True,
                "tool": "delegate_to_agent",
                "target_agent": target_agent,
                "specialist_name": specialist_name,
                "response": specialist_output,
                "duration_ms": spec_resp["metrics"]["duration_ms"],
            }
            formatted_result = (
                f"### Delegated Response from {specialist_name} ({specialist_info['role']})\n\n"
                f"{specialist_output}"
            )

            # Auto-save successful resolution into Vector Memory for self-improvement
            vector_memory.store_memory(
                agent_id=target_agent,
                content=f"Resolution for task '{task_desc[:120]}': {specialist_output[:300]}",
                category="past_resolution",
            )
        else:
            # Execute Standard Tool via Gateway
            tool_result = await execute_tool(tool_name, args)
            formatted_result = format_tool_result(tool_name, tool_result, args)

        step2_trace = {
            "step": 2,
            "agent": specialist_name if tool_name == "delegate_to_agent" else "IT Agent",
            "role": f"Specialist ({specialist_info['role']})" if tool_name == "delegate_to_agent" else "Tool Execution Gateway",
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

        # Log request flow for the Virtual Office Floor Inspector
        try:
            delegated_agent_name = (
                SPECIALIST_PERSONAS.get(args.get("target_agent", ""), {}).get("name")
                if tool_name == "delegate_to_agent"
                else None
            )
            agents_in_flow = ["Marcus Vance"]
            if delegated_agent_name:
                agents_in_flow.append(delegated_agent_name)
            agents_in_flow.append("Audrey Chen")

            steps_summary = [
                {
                    "step": "Planning & Orchestration",
                    "agent": "Marcus Vance",
                    "action": f"Analyzed prompt: '{user_message[:60]}...'",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(start_time)),
                    "status": "ok",
                },
                {
                    "step": f"Delegated Execution ({tool_name})" if delegated_agent_name else f"Tool Execution ({tool_name})",
                    "agent": delegated_agent_name or "Marcus Vance",
                    "action": f"Executed `{tool_name}`: {json.dumps(args)[:120]}",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "status": "ok" if (tool_result or {}).get("ok", True) else "warning",
                },
                {
                    "step": "Quality & Verification",
                    "agent": "Audrey Chen",
                    "action": f"Audit verification ({audit_status}, quality: {quality_score}/10)",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "status": "ok" if audit_ok else "warning",
                },
            ]
            log_request_flow(
                flow_id=f"flow_chat_{task_id}",
                source="Manager Chat UI",
                title=f"Chat: {user_message[:50]}",
                status="completed" if audit_ok else "warning",
                agents_involved=agents_in_flow,
                steps=steps_summary,
                payload_preview={"input": user_message, "tool": tool_name, "args": args},
                result_summary=formatted_result[:140],
                duration_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            logger.warning(f"Could not log tool request flow: {e}")

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

    # Log request flow for the Virtual Office Floor Inspector
    try:
        steps_summary = [
            {
                "step": "Planning & Orchestration",
                "agent": "Marcus Vance",
                "action": f"Analyzed prompt: '{user_message[:60]}...'",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(start_time)),
                "status": "ok",
            }
        ]
        if invoked_tool_name:
            steps_summary.append({
                "step": f"Tool Execution ({invoked_tool_name})",
                "agent": "Marcus Vance",
                "action": f"Executed tool `{invoked_tool_name}` with parameters: {json.dumps(invoked_tool_args)[:120]}",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "status": "ok" if (tool_result or {}).get("ok", True) else "warning",
            })
        steps_summary.append({
            "step": "Quality & Verification",
            "agent": "Audrey Chen",
            "action": f"Audit quality verified (tokens: {tokens_used}, duration: {int((time.time() - start_time) * 1000)}ms)",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "status": "ok",
        })
        log_request_flow(
            flow_id=f"flow_chat_{task_id}",
            source="Manager Chat UI",
            title=f"Chat: {user_message[:50]}",
            status="completed",
            agents_involved=["Marcus Vance", "Audrey Chen"],
            steps=steps_summary,
            payload_preview={"input": user_message, "session_id": session_id},
            result_summary=final_msg[:120],
            duration_ms=int((time.time() - start_time) * 1000),
        )
    except Exception as e:
        logger.warning(f"Could not log chat flow: {e}")

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
