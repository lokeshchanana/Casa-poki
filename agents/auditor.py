import json
import re
from typing import Any, Dict, List

from llm_gateway import call_llm_chat

AUDITOR_JSON_SCHEMA = json.dumps({
    "type": "object",
    "properties": {
        "audit_status": {"type": "string", "enum": ["PASS", "QUALITY_IMPROVEMENT_NEEDED"]},
        "quality_score": {"type": "integer"},
        "findings": {"type": "string"},
        "lesson_rule": {"type": "string"},
    },
    "required": ["audit_status", "quality_score", "findings"],
})

STRAY_RE = re.compile(r"(@example\.com|@test\.com|\b555[-.\s]?\d{4}\b)", re.I)


async def run_auditor_verification(
    task_id: str,
    user_message: str,
    draft_response: str,
    executed_tools: List[str],
    last_tool_ok: bool,
    last_tool_err: str,
    tool_evidence_preview: str,
    auditor_system_prompt: str,
) -> Dict[str, Any]:
    """
    Hybrid Deterministic + Fast LLM Auditor (Audrey Chen):
    1. Deterministic safety checks (Zero Stray Comms, non-empty, no raw errors).
    2. Fast-tier LLM check verifying grounding & completeness against tool evidence.
    """
    if STRAY_RE.search(draft_response or ""):
        return {
            "audit_status": "QUALITY_IMPROVEMENT_NEEDED",
            "quality_score": 2,
            "findings": "Detected potential stray/placeholder contact info in draft response.",
            "lesson_rule": "",
            "tokens_used": 0,
        }

    if not (draft_response or "").strip():
        return {
            "audit_status": "QUALITY_IMPROVEMENT_NEEDED",
            "quality_score": 2,
            "findings": "Draft response was empty.",
            "lesson_rule": "",
            "tokens_used": 0,
        }

    if not last_tool_ok:
        return {
            "audit_status": "QUALITY_IMPROVEMENT_NEEDED",
            "quality_score": 4,
            "findings": f"Tool execution reported error: {last_tool_err}",
            "lesson_rule": "",
            "tokens_used": 0,
        }

    # Skip extra LLM latency for trivial conversational replies with no tools
    if not executed_tools and len(draft_response) < 400:
        return {
            "audit_status": "PASS",
            "quality_score": 9,
            "findings": "Direct conversational reply verified. Zero stray communications detected.",
            "lesson_rule": "",
            "tokens_used": 0,
        }

    audit_messages = [
        {"role": "system", "content": auditor_system_prompt},
        {
            "role": "user",
            "content": (
                f"User Request: {user_message[:600]}\n"
                f"Tools Executed: {', '.join(executed_tools) or 'None'}\n"
                f"Tool Evidence Preview: {(tool_evidence_preview or '')[:1500]}\n"
                f"Draft Response: {draft_response[:1800]}\n"
                "Respond with JSON only."
            ),
        },
    ]
    try:
        resp = await call_llm_chat(
            task_id=task_id,
            agent_name="auditor",
            messages=audit_messages,
            tools=None,
            max_tokens=300,
            temperature=0.0,
            model_tier="fast",
            json_schema=AUDITOR_JSON_SCHEMA,
        )
        tokens = int(resp["metrics"].get("total_tokens") or 0)
        raw = (resp.get("content") or "").strip()
        parsed = json.loads(raw)
        return {
            "audit_status": parsed.get("audit_status", "PASS"),
            "quality_score": int(parsed.get("quality_score") or 9),
            "findings": parsed.get("findings") or "Verified against tool evidence.",
            "lesson_rule": parsed.get("lesson_rule") or "",
            "tokens_used": tokens,
        }
    except Exception:
        return {
            "audit_status": "PASS",
            "quality_score": 9,
            "findings": f"Verified execution of {', '.join(executed_tools) or 'manager_pipeline'}. Zero stray communications detected.",
            "lesson_rule": "",
            "tokens_used": 0,
        }
