import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional

from context_manager import store_or_inline_tool_output
from hooks import pre_tool_use_hook
from llm_gateway import call_llm_chat, select_model_tier
from state_store import create_pending_approval, get_lessons
from tools import TOOL_SCHEMAS, execute_tool, format_tool_result
import vector_memory

CORE_META_TOOLS = {
    "delegate_to_agent",
    "delegate_parallel",
    "manage_plan",
    "inspect_artifact",
    "store_memory",
    "query_memory",
    "web_search",
    "deep_search",
    "fetch_webpage",
}

SPECIALIST_TOOL_MAP: Dict[str, List[str]] = {
    "it": [
        "infra_list_containers",
        "infra_check_monitors",
        "infra_container_logs",
        "infra_restart_container",
        "inspect_artifact",
        "query_memory",
        "store_memory",
    ],
    "intake": [
        "search_contacts",
        "create_contact",
        "update_contact",
        "delete_contact",
        "manage_notes",
        "manage_tasks",
        "manage_opportunities",
        "crm_entity_operation",
        "inspect_artifact",
        "query_memory",
        "store_memory",
    ],
    "finance": [
        "finance_record_bill",
        "finance_update_bill",
        "finance_manage_vendors",
        "finance_manage_bill_payments",
        "finance_entity_operation",
        "finance_record_payment",
        "finance_list_bills",
        "finance_dashboard",
        "finance_import_historical_bills",
        "finance_scan_email_bills",
        "finance_scan_drive_bills",
        "finance_tax_audit",
        "inspect_artifact",
        "query_memory",
        "store_memory",
    ],
    "tax_auditor": [
        "finance_tax_audit",
        "finance_list_bills",
        "finance_dashboard",
        "finance_manage_bill_payments",
        "inspect_artifact",
        "query_memory",
        "store_memory",
    ],
    "marketing": [
        "enroll_buyer_post_close",
        "list_post_close_drips",
        "process_post_close_drips",
        "social_list_research_briefs",
        "social_list_media_assets",
        "social_render_content",
        "web_search",
        "inspect_artifact",
        "query_memory",
        "store_memory",
    ],
    "social_scout": [
        "social_research_market_and_trends",
        "social_list_research_briefs",
        "web_search",
        "deep_search",
        "fetch_webpage",
        "inspect_artifact",
        "query_memory",
        "store_memory",
    ],
    "avatar_artist": [
        "social_list_media_assets",
        "query_memory",
        "store_memory",
    ],
    "content_producer": [
        "social_render_content",
        "social_list_media_assets",
        "social_list_research_briefs",
        "inspect_artifact",
        "query_memory",
    ],
    "social_ops": [
        "social_sync_analytics",
        "social_compute_cadence",
        "social_list_approval_queue",
        "social_approve_and_schedule",
        "inspect_artifact",
        "query_memory",
    ],
    "cma": [
        "web_search",
        "deep_search",
        "fetch_webpage",
        "search_contacts",
        "inspect_artifact",
        "query_memory",
        "store_memory",
    ],
    "mailman": [
        "mailman_read_inbox",
        "search_contacts",
        "inspect_artifact",
        "query_memory",
    ],
    "homeassistant": [
        "ha_health_check",
        "ha_fix_issues",
        "ha_call_service",
        "inspect_artifact",
        "query_memory",
        "store_memory",
    ],
}

DOMAIN_TO_SPECIALIST = {
    "INFRA_TELEMETRY": ["it"],
    "CRM_CONTACTS": ["intake"],
    "FINANCE_ACCOUNTING": ["finance", "tax_auditor"],
    "EMAIL_INBOX": ["mailman", "intake"],
    "SOCIAL_MEDIA": ["marketing", "social_scout", "avatar_artist", "content_producer", "social_ops"],
    "REAL_ESTATE_CMA": ["cma", "marketing"],
    "HOME_ASSISTANT": ["homeassistant"],
}


def get_tools_for_agent(agent_id: str, schemas: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    all_s = schemas or TOOL_SCHEMAS
    allowed = set(SPECIALIST_TOOL_MAP.get(agent_id, []))
    if not allowed:
        return all_s
    return [t for t in all_s if t.get("function", {}).get("name") in allowed]


def get_domain_tools_for_manager(domain: str, schemas: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    all_s = schemas or TOOL_SCHEMAS
    if not domain or domain == "GENERAL_CONVERSATION":
        return all_s
    allowed = set(CORE_META_TOOLS)
    for spec in DOMAIN_TO_SPECIALIST.get(domain, []):
        allowed.update(SPECIALIST_TOOL_MAP.get(spec, []))
    return [t for t in all_s if t.get("function", {}).get("name") in allowed]


async def run_specialist_subagent(
    task_id: str,
    session_id: str,
    target_agent: str,
    task_desc: str,
    context_data: str,
    personas: Dict[str, Dict[str, str]],
    max_turns: int = 6,
) -> Dict[str, Any]:
    """
    Runs an isolated multi-turn ReAct loop (up to 6 turns) for any specialist subagent
    with its own domain toolset, PreToolUse guardrails, and artifact-backed outputs.
    """
    start_ts = time.time()
    info = personas.get(target_agent, personas["manager"])
    spec_name = info["name"]
    spec_tools = get_tools_for_agent(target_agent)
    spec_memories = vector_memory.query_memories(query=task_desc, agent_id=target_agent, top_k=3)
    spec_mem_str = "\n".join(f"- {m['content']}" for m in spec_memories) if spec_memories else "None"

    scoped_lessons = [
        l["rule"]
        for l in get_lessons()
        if l.get("agent_name") in (target_agent, "global", "all")
    ][:5]
    lessons_str = ("\nScoped Rules:\n" + "\n".join(f"- {r}" for r in scoped_lessons)) if scoped_lessons else ""

    messages: List[Dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                f"{info['system_prompt']}{lessons_str}\n"
                f"Relevant Domain Knowledge:\n{spec_mem_str}\n"
                "You can execute multiple tool turns if needed. When done, provide a crisp, evidence-backed Markdown answer."
            ),
        },
        {
            "role": "user",
            "content": f"Task: {task_desc}\nContext: {context_data}",
        },
    ]

    total_tokens = 0
    citations: List[Dict[str, Any]] = []
    pending_approvals: List[Dict[str, Any]] = []
    formatted_outputs: List[str] = []
    final_output = ""
    seen_calls = set()
    model_name = select_model_tier(agent_name=target_agent, user_message=task_desc)

    for _ in range(max_turns):
        resp = await call_llm_chat(
            task_id=task_id,
            agent_name=target_agent,
            messages=messages,
            tools=spec_tools,
            max_tokens=1200,
            temperature=0.15,
            model_tier=model_name,
        )
        total_tokens += int(resp["metrics"].get("total_tokens") or 0)
        t_calls = resp.get("tool_calls") or []
        if not t_calls:
            final_output = (resp.get("content") or "").strip()
            break

        # Filter duplicate loop calls
        exec_batch = []
        for tc in t_calls:
            fn_data = tc.get("function") or {}
            fn_name = fn_data.get("name") or ""
            fn_args = fn_data.get("arguments") or {}
            if isinstance(fn_args, str):
                try:
                    fn_args = json.loads(fn_args)
                except Exception:
                    fn_args = {}
            sig = f"{fn_name}:{json.dumps(fn_args, sort_keys=True)}"
            if sig in seen_calls:
                continue
            seen_calls.add(sig)
            exec_batch.append((tc, fn_name, fn_args))

        if not exec_batch:
            final_output = (resp.get("content") or "").strip() or "\n\n".join(formatted_outputs)
            break

        async def _run_one(tc_obj, fn_name: str, fn_args: Dict[str, Any]):
            hook_res = pre_tool_use_hook(fn_name, fn_args, session_id)
            if hook_res["decision"] == "BLOCK":
                return tc_obj, fn_name, fn_args, {"ok": False, "blocked": True, "error": hook_res["reason"]}
            if hook_res["decision"] == "REQUIRE_APPROVAL":
                app_id = f"appr_{uuid.uuid4().hex[:10]}"
                appr = create_pending_approval(
                    approval_id=app_id,
                    session_id=session_id,
                    task_id=task_id,
                    agent_name=target_agent,
                    tool_name=fn_name,
                    arguments=fn_args,
                    summary=hook_res["summary"],
                )
                pending_approvals.append(appr)
                return tc_obj, fn_name, fn_args, {
                    "ok": False,
                    "approval_required": True,
                    "approval": appr,
                    "message": f"Paused for owner approval: {hook_res['summary']}",
                }
            res = await execute_tool(fn_name, fn_args)
            return tc_obj, fn_name, fn_args, res

        batch_results = await asyncio.gather(*[_run_one(tc, n, a) for tc, n, a in exec_batch])

        messages.append({"role": "assistant", "content": "", "tool_calls": [b[0] for b in batch_results]})
        for _, fn_name, fn_args, fn_res in batch_results:
            if isinstance(fn_res, dict) and fn_res.get("citations"):
                citations.extend(fn_res["citations"])
            if fn_res.get("ok", True) and not fn_res.get("approval_required"):
                formatted_outputs.append(format_tool_result(fn_name, fn_res, fn_args))
            safe_payload = store_or_inline_tool_output(session_id, fn_name, fn_res)
            messages.append({"role": "tool", "content": safe_payload})

        if pending_approvals:
            final_output = f"Action paused for owner approval ({pending_approvals[0]['summary']})."
            break

    if not final_output and formatted_outputs:
        final_output = "\n\n".join(formatted_outputs)

    if final_output and not pending_approvals:
        vector_memory.store_memory(
            agent_id=target_agent,
            content=f"Resolution for '{task_desc[:120]}': {final_output[:300]}",
            category="past_resolution",
        )

    return {
        "ok": True,
        "tool": "delegate_to_agent",
        "target_agent": target_agent,
        "specialist_name": spec_name,
        "role": info["role"],
        "response": final_output,
        "tokens_used": total_tokens,
        "duration_ms": int((time.time() - start_ts) * 1000),
        "citations": citations,
        "pending_approvals": pending_approvals,
    }


async def run_parallel_subagents(
    task_id: str,
    session_id: str,
    tasks: List[Dict[str, Any]],
    personas: Dict[str, Dict[str, str]],
) -> Dict[str, Any]:
    """
    Runs multiple independent specialists concurrently via asyncio.gather.
    """
    coros = [
        run_specialist_subagent(
            task_id=task_id,
            session_id=session_id,
            target_agent=str(t.get("target_agent") or "manager").lower(),
            task_desc=str(t.get("task_description") or ""),
            context_data=str(t.get("context_data") or ""),
            personas=personas,
        )
        for t in (tasks or [])[:5]
    ]
    results = await asyncio.gather(*coros) if coros else []
    combined_citations: List[Dict[str, Any]] = []
    combined_approvals: List[Dict[str, Any]] = []
    for r in results:
        combined_citations.extend(r.get("citations") or [])
        combined_approvals.extend(r.get("pending_approvals") or [])
    return {
        "ok": True,
        "tool": "delegate_parallel",
        "count": len(results),
        "reports": results,
        "citations": combined_citations,
        "pending_approvals": combined_approvals,
        "tokens_used": sum(int(r.get("tokens_used") or 0) for r in results),
    }
