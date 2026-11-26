import json
import re
from typing import Any, Dict

STRAY_EMAIL_RE = re.compile(r"@(example\.com|test\.com|fake\.com|dummy\.com)\b", re.I)
STRAY_PHONE_RE = re.compile(r"\b555[-.\s]?\d{4}\b")

# Tools that ALWAYS require interactive human approval before execution:
# - All deletions (contacts, CRM entities, finance entities)
# - Container restarts & HA core restarts
# - External social publishing & batch drip sends
# Note: All ADD/CREATE and UPDATE operations remain automated per owner directive.
APPROVAL_GATED_TOOLS = {
    "delete_contact",
    "infra_restart_container",
    "social_approve_and_schedule",
    "process_post_close_drips",
}


def _contains_stray_contact_info(args: Dict[str, Any]) -> str:
    raw = json.dumps(args or {})
    if STRAY_EMAIL_RE.search(raw):
        return "Stray placeholder email domain (@example.com / @test.com) detected — blocked by Zero Stray Communications policy."
    if STRAY_PHONE_RE.search(raw):
        return "Stray placeholder 555-xxxx phone number detected — blocked by Zero Stray Communications policy."
    return ""


def pre_tool_use_hook(tool_name: str, args: Dict[str, Any], session_id: str = "") -> Dict[str, Any]:
    """
    Deterministic PreToolUse guardrail (Claude Code pattern):
    Returns:
      - {"decision": "BLOCK", "reason": "..."}
      - {"decision": "REQUIRE_APPROVAL", "summary": "..."}
      - {"decision": "ALLOW"}
    """
    args = args or {}

    # 1. Hard Policy Block: Zero Stray Communications
    if tool_name in (
        "create_contact",
        "update_contact",
        "crm_entity_operation",
        "enroll_buyer_post_close",
        "manage_notes",
    ):
        stray_err = _contains_stray_contact_info(args)
        if stray_err:
            return {"decision": "BLOCK", "reason": stray_err}

    # 2. Hard Policy Block: Never touch production real-estate container
    if tool_name == "infra_restart_container":
        cname = str(args.get("container_name") or "").strip().lower()
        if cname == "real-estate":
            return {
                "decision": "BLOCK",
                "reason": "Production 'real-estate' container cannot be restarted without explicit CLI override.",
            }

    # 3. Hard Policy Block: Missing required IDs on destructive delete calls
    if tool_name == "delete_contact" and not (args.get("contact_id") or args.get("target_name")):
        return {
            "decision": "BLOCK",
            "reason": "delete_contact requires either contact_id or target_name.",
        }

    # 4. Interactive HITL Approval Gate: Deletions, restarts, and external sends
    if tool_name in APPROVAL_GATED_TOOLS:
        return {
            "decision": "REQUIRE_APPROVAL",
            "summary": _build_approval_summary(tool_name, args),
        }

    if tool_name in ("crm_entity_operation", "finance_entity_operation"):
        if str(args.get("action") or "").lower() == "delete":
            return {
                "decision": "REQUIRE_APPROVAL",
                "summary": _build_approval_summary(tool_name, args),
            }

    if tool_name == "ha_fix_issues" and bool(args.get("allow_restart")):
        return {
            "decision": "REQUIRE_APPROVAL",
            "summary": "Restart Home Assistant Core (validated configuration.yaml)",
        }

    return {"decision": "ALLOW"}


def _build_approval_summary(tool_name: str, args: Dict[str, Any]) -> str:
    if tool_name == "delete_contact":
        target = args.get("target_name") or args.get("contact_id") or "contact"
        return f"Permanently delete Twenty CRM contact: {target}"
    if tool_name == "crm_entity_operation":
        return f"Delete Twenty CRM {args.get('entity', 'record')} (ID: {args.get('id', 'unknown')})"
    if tool_name == "finance_entity_operation":
        return f"Delete Bigcapital {args.get('entity', 'record')} (ID: {args.get('id', 'unknown')})"
    if tool_name == "infra_restart_container":
        return f"Restart Docker container: {args.get('container_name', 'unknown')}"
    if tool_name == "social_approve_and_schedule":
        return f"Approve & schedule social post {args.get('post_id', '')} to live Postiz channels"
    if tool_name == "process_post_close_drips":
        return "Trigger Brevo batch processing for due Buyer Post-Close drip emails"
    return f"Execute gated action `{tool_name}`"
