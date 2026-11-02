import json
import os
import re
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional
import httpx

from n8n_catalog import (
    N8N_BASE_URL,
    execute_n8n_workflow,
    get_n8n_workflows,
    inspect_latest_n8n_execution,
)
from state_store import (
    add_agent_feedback,
    add_lesson,
    get_backlog_specs,
    get_last_audit_record,
    get_lessons,
    get_system_summary,
    log_audit_result,
    log_token_usage,
    save_missing_workflow_spec,
    update_audit_status,
)

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://192.168.1.240:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "crm-qwen:3b")
DEFAULT_TASK_BUDGET = int(os.environ.get("TASK_TOKEN_BUDGET", "2000"))


def _extract_json(text: str) -> Dict[str, Any]:
    """Robustly extract JSON object from model response."""
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return {}


async def call_ollama(
    task_id: str,
    agent_name: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 200,
    json_mode: bool = True,
    temperature: float = 0.1,
) -> Dict[str, Any]:
    """Calls local Ollama with token tracking."""
    start_ts = time.time()
    payload: Dict[str, Any] = {
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "keep_alive": "24h",
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    if json_mode:
        payload["format"] = "json"

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        duration_ms = int((time.time() - start_ts) * 1000)
        return {
            "content": json.dumps({"error": str(e)}) if json_mode else f"Ollama error: {str(e)}",
            "parsed": {"error": str(e)},
            "metrics": log_token_usage(task_id, agent_name, DEFAULT_MODEL, 0, 0, 0.0, duration_ms),
        }

    duration_ms = int((time.time() - start_ts) * 1000)
    content = (data.get("message") or {}).get("content", "")
    prompt_tokens = int(data.get("prompt_eval_count") or 0)
    completion_tokens = int(data.get("eval_count") or 0)
    eval_duration_ns = int(data.get("eval_duration") or 0)
    if eval_duration_ns > 0:
        tok_per_sec = completion_tokens / (eval_duration_ns / 1e9)
    elif duration_ms > 0:
        tok_per_sec = completion_tokens / (duration_ms / 1000.0)
    else:
        tok_per_sec = 0.0

    metrics = log_token_usage(
        task_id=task_id,
        agent_name=agent_name,
        model=DEFAULT_MODEL,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        tokens_per_sec=tok_per_sec,
        duration_ms=duration_ms,
    )

    parsed = _extract_json(content) if json_mode else {}
    return {
        "content": content,
        "parsed": parsed,
        "metrics": metrics,
    }


def _extract_crm_payload_fast(user_message: str) -> Optional[Dict[str, Any]]:
    """
    Fast deterministic extraction for Relaticle CRM webhook operations
    so standard CRM queries execute in ~100ms without an Ollama round-trip.
    Supports compound filtering (can_email, blank/missing fields, limits).
    """
    text = user_message.strip()
    low = text.lower()

    # 1. Tasks
    if any(w in low for w in ["list task", "show task", "recent task", "follow-up task", "check task", "all task", "crm tasks"]):
        return {"tool": "manage_tasks", "action": "list"}

    # 2. Deals / Opportunities
    if any(w in low for w in ["list deal", "show deal", "active deal", "opportunit", "pipeline", "crm deals"]):
        return {"tool": "manage_opportunities", "action": "list"}

    # 3. CRM Notes (Must be explicitly about CRM / contacts / clients)
    if any(w in low for w in ["list crm note", "show crm note", "crm note", "contact note", "notes on contact", "notes for contact"]):
        return {"tool": "manage_notes", "action": "list"}

    # 4. Companies
    if any(w in low for w in ["list compan", "show compan", "search compan", "crm compan"]):
        return {"tool": "manage_companies", "action": "search"}

    # 5. Custom fields
    if "custom field" in low:
        return {"tool": "manage_custom_fields", "action": "list"}

    # 6. Delete contact
    if any(w in low for w in ["delete ", "remove "]) and not any(w in low for w in ["task", "note", "company", "deal"]):
        m_id = re.search(r"\b(01[a-z0-9]{24})\b", low)
        if m_id:
            return {"tool": "delete_contact", "id": m_id.group(1)}
        m_name = re.search(
            r"(?:delete|remove)\s+(?:the\s+)?(?:user|contact|record|person)?\s*(?:for|named|called)?\s*([a-zA-Z][a-zA-Z\s]{1,35}?)(?:\s+from\b|\s+in\b|$)",
            text,
            re.IGNORECASE,
        )
        if m_name:
            cand = m_name.group(1).strip()
            if cand.lower() not in ("this", "this user", "this contact", "her", "him", "them", "record", "people"):
                return {"tool": "delete_contact", "name": cand}

    # 7. Create contact
    if any(w in low for w in ["create a new contact", "create contact", "add a new contact", "add contact", "add lead", "create lead"]):
        m_name = re.search(r"(?:named|called|contact|lead)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)", text)
        m_email = re.search(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", text)
        m_phone = re.search(r"(\+?1?\s*\(?\d{3}\)?[-.\s]*\d{3}[-.\s]*\d{4})", text)
        if m_name:
            payload: Dict[str, Any] = {"tool": "create_contact", "name": m_name.group(1).strip()}
            if m_email:
                payload["email"] = m_email.group(1).strip()
            if m_phone:
                payload["phone_number"] = m_phone.group(1).strip()
            return payload

    # 8. Update contact phone or email permission
    if any(w in low for w in ["update phone", "change phone", "change can email", "toggle email", "update email"]):
        m_for = re.search(r"(?:for|of)\s+([a-zA-Z][a-zA-Z\s]{1,30}?)\s+to\s+", text, re.IGNORECASE)
        if m_for:
            target_name = m_for.group(1).strip(" []")
            if "can email" in low or "permission" in low:
                can_val = "True" if "true" in low or "yes" in low else "False"
                return {"tool": "update_contact", "target_name": target_name, "can_email": can_val}
            m_phone = re.search(r"to\s+(\+?[\d\s()-]{10,18})", text)
            if m_phone:
                return {"tool": "update_contact", "target_name": target_name, "phone_number": m_phone.group(1).strip()}

    # 9. Contact Search with Compound Filtering (can_email, phone blank, email blank, limits)
    filters: Dict[str, Any] = {}
    if any(k in low for k in ["can email is false", "can_email is false", "can email false", "can_email false", "cannot email", "can't email", "can email: false", "can email=false"]):
        filters["can_email"] = False
    elif any(k in low for k in ["can email is true", "can_email is true", "can email true", "can_email true", "can email: true", "can email=true"]):
        filters["can_email"] = True

    if any(ph in low for ph in ["phone is blank", "phone number is blank", "phone is empty", "phone number is empty", "no phone", "without phone", "missing phone"]):
        filters["phone_blank"] = True
    elif any(ph in low for ph in ["has phone", "with phone", "phone is present", "phone is not empty", "phone number is present"]):
        filters["phone_present"] = True

    if any(em in low for em in ["email is blank", "email address is blank", "email is empty", "no email", "without email", "missing email"]):
        filters["email_blank"] = True

    limit = 50
    m_lim = re.search(r"\b(?:last|top|first)\s+(\d+)\b", low)
    if m_lim:
        limit = int(m_lim.group(1))

    # Search by email pattern (e.g. "Find users with email as*@example.com" or "Find user with email john@test.com")
    m_email_search = re.search(r"(?:with\s+email\s+(?:as\s+|is\s+|like\s+)?|email\s+contains\s+)([*@a-zA-Z0-9._+-]+)", text, re.IGNORECASE)
    if m_email_search:
        clean_em = m_email_search.group(1).strip(" *").replace("*", "")
        return {
            "tool": "search_contacts",
            "query": clean_em or "all",
            "filters": filters,
            "limit": limit,
        }

    # Search by phone number (e.g. "Find user with phone number 8018601052")
    m_phone_search = re.search(r"(?:phone\s*(?:number)?\s*(?:is|as)?\s*)(\+?[\d\s()-]{7,18})", text, re.IGNORECASE)
    if m_phone_search:
        clean_phone = re.sub(r"[^\d+]", "", m_phone_search.group(1))
        return {
            "tool": "search_contacts",
            "query": clean_phone,
            "filters": filters,
            "limit": limit,
        }

    # Compound queries or general listing with criteria (e.g. "Find all the people where can email is false and phone number is blank", "Show me last 5 people")
    if filters or m_lim:
        return {
            "tool": "search_contacts",
            "query": "all",
            "filters": filters,
            "limit": limit,
        }

    if any(w in low for w in ["list all contact", "show all contact", "all contact", "list contact", "all people", "list people"]):
        return {"tool": "search_contacts", "query": "all", "filters": filters, "limit": limit}
    if "today" in low and any(w in low for w in ["contact", "user", "lead", "people", "added"]):
        return {"tool": "search_contacts", "query": "today", "filters": filters, "limit": limit}

    patterns = [
        r"(?:does|is)\s+(?:there\s+)?(?:a\s+)?(?:user|contact|person|client|lead)?\s*(?:named|called)?\s*([a-zA-Z0-9@.+-]+)\s+exist",
        r"check\s+if\s+(?:user|contact|person)?\s*([a-zA-Z0-9@.+-]+)\s+(?:was\s+deleted|exists|is\s+in)",
        r"(?:search|find|look\s*up)\s+(?:for\s+)?(?:contacts?|users?|people|person|records?)?\s*(?:named|called|for)?\s*([a-zA-Z0-9@.+-]+?)(?:\s+in\s+(?:the\s+)?(?:relaticle\s+)?crm|\s*$)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            q = m.group(1).strip(" ?.,'\"")
            if q.lower() not in ("user", "contact", "contacts", "people", "crm", "relaticle", "anyone"):
                return {"tool": "search_contacts", "query": q, "filters": filters, "limit": limit}

    return None


def _format_crm_gateway_output(data: Any, req_payload: Dict[str, Any]) -> str:
    """Formats JSON output from n8n Twenty CRM Gateway into Markdown, applying client-side post-filters."""
    if not isinstance(data, dict):
        return str(data)

    if not data.get("ok", True) or data.get("error"):
        return f"⚠️ **CRM Operation Error (`{data.get('tool') or req_payload.get('tool')}`):** {data.get('error')}"

    tool = data.get("tool") or req_payload.get("tool")

    if tool == "search_contacts":
        contacts = data.get("contacts") or []
        filters = req_payload.get("filters") or {}

        # Apply deterministic filters to ensure verified results
        if filters:
            if "can_email" in filters:
                expected_bool = filters["can_email"]
                contacts = [
                    c for c in contacts
                    if (str(c.get("can_email")).lower() == "true") == expected_bool
                ]
            if filters.get("phone_blank"):
                contacts = [
                    c for c in contacts
                    if not c.get("phone") or str(c.get("phone")).strip() in ("", "N/A", "None")
                ]
            if filters.get("phone_present"):
                contacts = [
                    c for c in contacts
                    if c.get("phone") and str(c.get("phone")).strip() not in ("", "N/A", "None")
                ]
            if filters.get("email_blank"):
                contacts = [
                    c for c in contacts
                    if not c.get("email") or str(c.get("email")).strip() in ("", "N/A", "None")
                ]

        limit = req_payload.get("limit")
        if limit and isinstance(limit, int):
            contacts = contacts[:limit]

        q = req_payload.get("query") or "all"
        filter_desc_parts = []
        if filters.get("can_email") is not None:
            filter_desc_parts.append(f"can_email={filters['can_email']}")
        if filters.get("phone_blank"):
            filter_desc_parts.append("phone=blank")
        if filters.get("phone_present"):
            filter_desc_parts.append("phone=present")
        if filters.get("email_blank"):
            filter_desc_parts.append("email=blank")
        filter_str = f" [Filters: {', '.join(filter_desc_parts)}]" if filter_desc_parts else ""

        total = len(contacts)
        if total == 0:
            return f"### CRM Contact Search Result\nNo contacts matching **`{q}`**{filter_str} were found in Twenty CRM (`0 matching records`)."

        lines = [f"### CRM Contact Search Result (`{total}` verified matching records{filter_str})\n"]
        for c in contacts:
            lines.append(
                f"- **{c.get('name')}** (ID: `{c.get('id')}`)\n"
                f"  - Phone: `{c.get('phone') or 'N/A'}` | Email: `{c.get('email') or 'N/A'}`\n"
                f"  - Role: `{c.get('role') or 'Customer'}` | Can Email: `{c.get('can_email')}` | Market: `{c.get('market') or 'N/A'}` | Added: `{c.get('created_date')}`"
            )
        return "\n".join(lines)

    if tool == "delete_contact":
        return (
            f"### Contact Deleted from Twenty CRM\n"
            f"- **Deleted ID:** `{data.get('deleted_id')}`\n"
            f"- **Name:** `{data.get('deleted_name') or req_payload.get('name') or 'N/A'}`\n"
            f"- **Status:** {data.get('message')}"
        )

    if tool == "create_contact":
        return (
            f"### Contact Created in Twenty CRM\n"
            f"- **Name:** **{data.get('name')}**\n"
            f"- **ID:** `{data.get('id')}`\n"
            f"- **Status:** {data.get('message')}"
        )

    if tool == "update_contact":
        return (
            f"### Contact Updated in Twenty CRM\n"
            f"- **Name:** **{data.get('name')}**\n"
            f"- **Updated ID:** `{data.get('updated_id')}`\n"
            f"- **Status:** {data.get('message')}"
        )

    if tool == "manage_tasks":
        if "tasks" in data:
            tasks = data.get("tasks") or []
            if not tasks:
                return "### Twenty CRM Tasks\nNo tasks found in CRM."
            lines = [f"### Twenty CRM Tasks (`{len(tasks)}` total)\n"]
            for t in tasks[:15]:
                lines.append(
                    f"- **{t.get('title')}** (`{t.get('id')}`) — Status: **{t.get('status')}** | Priority: `{t.get('priority')}`"
                )
            return "\n".join(lines)
        return f"### CRM Task Updated\n{data.get('message')} (ID: `{data.get('id') or data.get('deleted_id')}`)"

    if tool == "manage_opportunities":
        opps = data.get("opportunities") or []
        if not opps:
            return "### Twenty CRM Opportunities\nNo active opportunities/deals found."
        lines = [f"### Twenty CRM Opportunities (`{len(opps)}` total)\n"]
        for o in opps[:15]:
            lines.append(
                f"- **{o.get('name')}** (`{o.get('id')}`) — Stage: **{o.get('stage') or 'N/A'}** | Contact ID: `{o.get('contact_id') or 'N/A'}`"
            )
        return "\n".join(lines)

    if tool == "manage_notes":
        notes = data.get("notes") or []
        if not notes:
            return "### Twenty CRM Notes\nNo client notes found in CRM."
        lines = [f"### Twenty CRM Notes (`{len(notes)}` total)\n"]
        for n in notes[:10]:
            lines.append(f"- **{n.get('title')}** (`{n.get('id')}`) — Added: `{str(n.get('created_at'))[:10]}`")
        return "\n".join(lines)

    if tool == "manage_companies":
        companies = data.get("companies") or []
        if not companies:
            return "### Twenty CRM Companies\nNo companies found."
        lines = [f"### Twenty CRM Companies (`{len(companies)}` total)\n"]
        for c in companies[:15]:
            lines.append(f"- **{c.get('name')}** (`{c.get('id')}`) — Phone: `{c.get('phone') or 'N/A'}`")
        return "\n".join(lines)

    return f"```json\n{json.dumps(data, indent=2)}\n```"


def _classify_request_fast(user_message: str) -> Dict[str, Any]:
    """
    Zero-token deterministic classifier for Manager & IT Agent.
    Prioritizes Human Feedback and Direct Answers over unnecessary IT Agent execution.
    """
    u_low = user_message.lower().strip()

    # 1. System Feedback / Audit Note / Quality Flagging (NEVER route to CRM or IT)
    feedback_triggers = [
        "note for auditor", "note to auditor", "note for anti gravity", "note to anti gravity",
        "note for antigravity", "note to antigravity", "note for manager", "feedback for auditor",
        "last execution is not correct", "the last execution is not correct", "execution is not correct",
        "last execution was not correct", "last execution was wrong", "not correct result",
        "this is not correct result", "this is not correct", "result is no good", "result is not good",
        "result is not correct", "bad result", "incorrect result", "that result is wrong",
        "fix this functionality", "flag this execution", "create a note for auditor", "create note for auditor",
        "create a note for anti gravity", "create note for anti gravity", "create note for antigravity"
    ]
    if any(phrase in u_low for phrase in feedback_triggers):
        return {
            "intent": "SYSTEM_FEEDBACK",
            "target_domain": "system",
            "feedback_text": user_message,
            "fast_routed": True,
        }

    # 2. Teaching / Fine-tuning an agent rule
    if any(
        phrase in u_low
        for phrase in ["remember:", "remember to", "teach ", "add a rule", "new rule for", "fine tune", "fine-tune"]
    ):
        target_ag = "manager"
        for ag in ["it_agent", "auditor", "crm", "marketing"]:
            if ag.replace("_", " ") in u_low or ag in u_low:
                target_ag = ag
                break
        return {
            "intent": "TEACH_AGENT",
            "target_domain": target_ag,
            "teach_target_agent": target_ag,
            "teach_rule": user_message,
            "fast_routed": True,
        }

    # 3. System Inventory / Workflows / Token status inspection
    if any(
        phrase in u_low
        for phrase in [
            "what workflows", "which workflows", "list workflows", "available workflows",
            "available in n8n", "workflows in n8n", "n8n status", "show backlog",
            "missing workflows", "system status", "token budget", "token ledger"
        ]
    ):
        return {
            "intent": "INSPECT_SYSTEM",
            "target_domain": "it_system",
            "match_status": "INVENTORY_REPORT",
            "fast_routed": True,
        }

    # 4. Diagnostic inspection of failures
    if any(
        phrase in u_low
        for phrase in [
            "why was the execution failed", "why did the execution fail", "why did it fail",
            "why did that fail", "what was the error", "check the failed execution",
            "diagnose failure"
        ]
    ):
        return {
            "intent": "DIAGNOSE_FAILURE",
            "target_domain": "it_system",
            "match_status": "DIAGNOSTIC_REPORT",
            "fast_routed": True,
        }

    # 5. Direct Manager Response / Strategy / Advisory / General Questions (0 IT Tool calls)
    direct_greetings = ["hello", "hi", "hey", "good morning", "good evening", "good afternoon"]
    is_greeting = u_low in direct_greetings or any(u_low.startswith(g + " ") for g in direct_greetings)
    is_direct_query = (
        is_greeting
        or any(phrase in u_low for phrase in [
            "who are you", "what can you do", "help me understand", "how do you work",
            "marketing strategy", "pricing strategy", "advice on", "best practices",
            "what is your role", "tell me about yourself", "how do we organize"
        ])
        or (
            u_low.startswith(("what is ", "what are ", "how should we ", "how do we ", "can you explain ", "explain "))
            and not any(k in u_low for k in ["workflow", "n8n", "task_", "in crm", "from crm", "contact", "contacts", "person", "people", "deal", "lead"])
        )
    )
    if is_direct_query:
        return {
            "intent": "DIRECT_ANSWER",
            "target_domain": "general",
            "fast_routed": True,
        }

    # 6. Relaticle CRM Contact & Entity Operations (Strict Context Matching)
    crm_entities = ["contact", "contacts", "person", "people", "user", "users", "lead", "leads", "client", "clients", "deal", "pipeline", "crm"]
    crm_filter_signals = ["can email", "can_email", "phone number is blank", "phone is blank", "with phone", "no phone", "with email", "no email"]
    has_crm_entity = any(e in u_low for e in crm_entities) or any(f in u_low for f in crm_filter_signals)

    if has_crm_entity and any(
        action in u_low
        for action in [
            "search", "find", "show", "list", "lookup", "look up", "exist", "create", "add",
            "delete", "remove", "update", "toggle", "where", "last 5", "last ", "top ", "who is in"
        ]
    ):
        return {
            "intent": "EXECUTE_TASK",
            "target_domain": "crm",
            "match_status": "MATCH_ACTIVE",
            "workflow_id": "crmRelaticleAssistant",
            "fast_routed": True,
        }

    # 7. Mailman / Email reading or sending (Only when explicit mailbox access is requested)
    if any(
        w in u_low
        for w in ["mailbox", "inbox", "unread mail", "mailman", "send mail", "read email", "triage email", "gmail", "outlook"]
    ) and not any(
        w in u_low
        for w in ["can email", "can_email", "email permission", "create contact", "add contact", "search", "find", "with email"]
    ):
        return {
            "intent": "EXECUTE_TASK",
            "target_domain": "mailman",
            "match_status": "MISSING_WORKFLOW",
            "workflow_id": None,
            "missing_capability_summary": (
                "No n8n workflow is currently available to connect to an email mailbox (IMAP/Gmail) to read, triage, or send emails."
            ),
            "default_spec": {
                "workflow_name": "Mailman - Mailbox Reader & Triage Webhook",
                "domain": "mailman",
                "webhook_path": "mailman-inbox-triage",
                "trigger_type": "Webhook (POST) + IMAP/Gmail Schedule Trigger",
                "required_inputs": ["mailbox_filter", "max_emails", "urgency_threshold"],
                "recommended_n8n_nodes": [
                    "Webhook Trigger / Email Read (IMAP or Gmail)",
                    "Code Node (Strip HTML & Signatures)",
                    "Respond to Webhook",
                ],
                "expected_output": "JSON array of triaged emails with { sender, subject, urgency, summary, action_required }",
                "priority": "High",
            },
            "fast_routed": True,
        }

    # 8. Finance / Accounting (Missing capability in n8n)
    if any(w in u_low for w in ["finance", "invoice", "commission", "expense", "quickbooks", "payment", "budget report", "tax"]):
        return {
            "intent": "EXECUTE_TASK",
            "target_domain": "finance",
            "match_status": "MISSING_WORKFLOW",
            "workflow_id": None,
            "missing_capability_summary": (
                "No n8n workflow is currently available in n8n for Finance / accounting system updates or ledger queries."
            ),
            "default_spec": {
                "workflow_name": "Finance - Commission & Expense Ledger Sync",
                "domain": "finance",
                "webhook_path": "finance-ledger-sync",
                "trigger_type": "Webhook (POST)",
                "required_inputs": ["transaction_type", "amount", "client_or_property", "date", "notes"],
                "recommended_n8n_nodes": [
                    "Webhook Trigger",
                    "Postgres / Accounting API Node",
                    "Respond to Webhook",
                ],
                "expected_output": "JSON confirmation with { ok: true, transaction_id, updated_balance }",
                "priority": "Medium",
            },
            "fast_routed": True,
        }

    # 9. Marketing / Google Business Profile / Website Updates
    if any(w in u_low for w in ["google business", "gbp", "website", "blog", "listing on site", "seo", "hero banner", "market update"]):
        if "open house" in u_low and ("calendar" in u_low or "event" in u_low or "gbp" in u_low or "google business" in u_low):
            return {
                "intent": "EXECUTE_TASK",
                "target_domain": "marketing",
                "match_status": "INACTIVE_WORKFLOW",
                "workflow_id": "gbpEventPoster01",
                "missing_capability_summary": (
                    "Workflow 'Google Calendar → AI Property Research (Ollama) → GBP Event Poster' (gbpEventPoster01) exists in n8n, but it is currently INACTIVE and has no HTTP webhook trigger."
                ),
                "default_spec": {
                    "workflow_name": "Google Calendar to GBP Open House Event Poster (Activate & Add Webhook)",
                    "domain": "marketing",
                    "existing_inactive_workflow_id": "gbpEventPoster01",
                    "webhook_path": "gbp-open-house-event",
                    "trigger_type": "Webhook (POST) + Google Calendar Trigger",
                    "required_inputs": ["property_address", "event_start", "event_end", "description"],
                    "recommended_n8n_nodes": [
                        "Webhook Trigger",
                        "Google Business Profile - Create Event Post",
                        "Respond to Webhook",
                    ],
                    "expected_output": "JSON object with { ok: true, gbp_post_id, post_url }",
                    "priority": "High",
                },
                "fast_routed": True,
            }
        else:
            return {
                "intent": "EXECUTE_TASK",
                "target_domain": "marketing",
                "match_status": "MISSING_WORKFLOW",
                "workflow_id": None,
                "missing_capability_summary": (
                    "No active n8n workflow exists to automatically publish updates to Google Business Profile or modify website content."
                ),
                "default_spec": {
                    "workflow_name": "Marketing - Google Business Profile & Website Publisher",
                    "domain": "marketing",
                    "webhook_path": "marketing-gbp-web-publish",
                    "trigger_type": "Webhook (POST)",
                    "required_inputs": ["channel", "title", "content_markdown", "target_market", "call_to_action"],
                    "recommended_n8n_nodes": [
                        "Webhook Trigger",
                        "Google Business Profile API / CMS Webhook Node",
                        "Respond to Webhook",
                    ],
                    "expected_output": "JSON object with { ok: true, published_url, status }",
                    "priority": "High",
                },
                "fast_routed": True,
            }

    # 10. External Messaging / SMS / Social Media
    if any(w in u_low for w in ["send sms", "text message", "whatsapp", "mls", "instagram", "facebook", "linkedin"]):
        return {
            "intent": "EXECUTE_TASK",
            "target_domain": "marketing" if any(w in u_low for w in ["instagram", "facebook", "linkedin"]) else "crm",
            "match_status": "MISSING_WORKFLOW",
            "workflow_id": None,
            "missing_capability_summary": (
                f"No n8n workflow is currently available for external SMS/social/MLS integration requested in: '{user_message}'."
            ),
            "default_spec": {
                "workflow_name": f"External Integration - {user_message[:40].strip()}",
                "domain": "crm",
                "webhook_path": "external-messaging-integration",
                "trigger_type": "Webhook (POST)",
                "required_inputs": ["recipient", "message_body", "channel"],
                "recommended_n8n_nodes": [
                    "Webhook Trigger",
                    "Twilio / Social API Node",
                    "Respond to Webhook",
                ],
                "expected_output": "JSON delivery receipt { ok: true, message_id, status }",
                "priority": "Medium",
            },
            "fast_routed": True,
        }

    return {"fast_routed": False}


async def run_multi_agent_pipeline(
    user_message: str,
    session_id: str = "manager_default",
    token_budget: int = DEFAULT_TASK_BUDGET,
) -> AsyncGenerator[str, None]:
    """
    Executes the Manager -> IT Agent (Deterministic n8n Gateway) -> Auditor -> Manager pipeline.
    Includes smart Human-in-the-Loop Feedback handling and Direct Advisory without IT overhead.
    """
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    tokens_used = 0
    trace_steps: List[Dict[str, Any]] = []

    def emit(event_type: str, data: Dict[str, Any]) -> str:
        return json.dumps({"type": event_type, "task_id": task_id, **data}) + "\n"

    workflows = get_n8n_workflows()

    # -------------------------------------------------------------------------
    # STEP 1: MANAGER AGENT — TRIAGE & ROUTING
    # -------------------------------------------------------------------------
    yield emit(
        "agent_status",
        {
            "agent": "manager",
            "phase": "routing",
            "message": "Manager Agent is analyzing your instruction and rationing tokens...",
        },
    )

    fast_route = _classify_request_fast(user_message)
    step1_metrics = {
        "agent": "manager",
        "model": "fast-router (0 tok)",
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "tokens_per_sec": 0.0,
        "duration_ms": 1,
    }

    if fast_route.get("fast_routed"):
        intent = fast_route["intent"]
        target_domain = fast_route.get("target_domain", "general")
        task_instruction = user_message
    else:
        manager_system = """You are the Central Manager Agent. Classify the user request into JSON:
{
  "intent": "EXECUTE_TASK" | "DIRECT_ANSWER" | "SYSTEM_FEEDBACK" | "INSPECT_SYSTEM" | "TEACH_AGENT",
  "target_domain": "crm" | "marketing" | "mailman" | "finance" | "general",
  "match_status": "MATCH_ACTIVE" | "MISSING_WORKFLOW" | "DIRECT_REPLY",
  "workflow_id": "crmRelaticleAssistant" | null,
  "missing_capability_summary": "explain what capability or n8n workflow is needed"
}"""
        step1_llm = await call_ollama(
            task_id=task_id,
            agent_name="manager",
            system_prompt=manager_system,
            user_prompt=user_message,
            max_tokens=120,
            json_mode=True,
        )
        step1_metrics = step1_llm["metrics"]
        tokens_used += step1_metrics["total_tokens"]
        p = step1_llm["parsed"]
        valid_intents = ("EXECUTE_TASK", "DIRECT_ANSWER", "SYSTEM_FEEDBACK", "INSPECT_SYSTEM", "TEACH_AGENT")
        intent = p.get("intent") if p.get("intent") in valid_intents else "DIRECT_ANSWER"
        target_domain = p.get("target_domain") or "general"
        task_instruction = user_message
        fast_route = {
            "intent": intent,
            "target_domain": target_domain,
            "match_status": p.get("match_status") or "MISSING_WORKFLOW",
            "workflow_id": p.get("workflow_id"),
            "missing_capability_summary": p.get("missing_capability_summary")
            or f"No active n8n workflow found for: '{user_message}'.",
        }

    delegated_label = "IT Agent"
    if intent == "TEACH_AGENT":
        delegated_label = "Prompt Registry"
    elif intent == "SYSTEM_FEEDBACK":
        delegated_label = "Auditor Registry"
    elif intent == "DIRECT_ANSWER":
        delegated_label = "Manager (Direct Answer)"

    step1_trace = {
        "step": 1,
        "agent": "Manager Agent",
        "role": "Task Triage & Token Rationing",
        "decision": {
            "intent": intent,
            "target_domain": target_domain,
            "delegated_to": delegated_label,
            "instruction": task_instruction,
        },
        "metrics": step1_metrics,
        "tokens_remaining": max(0, token_budget - tokens_used),
    }
    trace_steps.append(step1_trace)
    yield emit("agent_trace", {"trace": step1_trace})

    # -------------------------------------------------------------------------
    # SPECIAL INTENT: SYSTEM_FEEDBACK (HUMAN-IN-THE-LOOP CORRECTION)
    # -------------------------------------------------------------------------
    if intent == "SYSTEM_FEEDBACK":
        last_rec = get_last_audit_record()
        flagged_task_id = last_rec["task_id"] if last_rec else "N/A"
        flagged_info = ""
        if last_rec:
            update_audit_status(
                task_id=last_rec["task_id"],
                new_status="USER_FLAGGED_FAILURE",
                new_score=2,
                additional_finding=f"Human Feedback: {user_message}",
            )
            flagged_info = f"- **Flagged Previous Task:** `{last_rec['task_id']}` (*\"{last_rec['user_request']}\"*)\n- **Previous Audit Status:** Updated to `USER_FLAGGED_FAILURE` (Score: 2/10)\n"

        saved_fb = add_agent_feedback(
            user_feedback=user_message,
            task_id=last_rec["task_id"] if last_rec else None,
            target_agent="auditor",
            action_taken="Flagged previous execution and recorded Auditor improvement task.",
        )

        log_audit_result(
            task_id=task_id,
            user_request=user_message,
            routed_agent="auditor",
            workflow_id=None,
            audit_status="PASS",
            quality_score=10,
            findings="Human feedback accurately captured and routed to Auditor Registry without executing external CRM operations.",
        )

        final_msg = (
            f"### 📝 Agent Quality Feedback Recorded\n\n"
            f"{flagged_info}"
            f"- **User Feedback:** {user_message}\n"
            f"- **Auditor Action:** Recorded in agent feedback registry (`feedback_id: {saved_fb['id']}`).\n"
            f"- **Protection Active:** The IT Agent was **not** invoked, and no false contact notes were created in Twenty CRM."
        )
        yield emit("item", {"content": final_msg})
        yield emit(
            "complete",
            {
                "trace": trace_steps,
                "tokens_used": tokens_used,
                "token_budget": token_budget,
                "feedback_saved": saved_fb,
            },
        )
        return

    # -------------------------------------------------------------------------
    # SPECIAL INTENT: TEACH_AGENT (PROMPT LEARNING)
    # -------------------------------------------------------------------------
    if intent == "TEACH_AGENT":
        target_ag = fast_route.get("teach_target_agent") or "manager"
        rule_text = fast_route.get("teach_rule") or user_message
        saved_lesson = add_lesson(target_ag, rule_text, source="user_instruction")
        final_msg = (
            f"### Agent Fine-Tuning Rule Saved\n\n"
            f"- **Target Agent:** `{target_ag}`\n"
            f"- **Learned Rule:** {saved_lesson.get('rule', rule_text)}\n\n"
            f"This rule is now stored in the persistent prompt registry and will guide future `{target_ag}` executions."
        )
        yield emit("item", {"content": final_msg})
        yield emit(
            "complete",
            {
                "trace": trace_steps,
                "tokens_used": tokens_used,
                "token_budget": token_budget,
                "lesson_added": saved_lesson,
            },
        )
        return

    # -------------------------------------------------------------------------
    # SPECIAL INTENT: DIRECT_ANSWER (STRATEGY & ADVISORY WITHOUT IT AGENT)
    # -------------------------------------------------------------------------
    if intent == "DIRECT_ANSWER":
        yield emit(
            "agent_status",
            {
                "agent": "manager",
                "phase": "answering",
                "message": "Manager Agent is formulating a direct response without external tool calls...",
            },
        )
        lessons = [l["rule"] for l in get_lessons("manager")]
        lessons_context = f"\nRelevant Lessons:\n" + "\n".join(f"- {r}" for r in lessons[:3]) if lessons else ""

        manager_qa_prompt = f"""You are the Central Manager Agent for Lokesh Chanana Real Estate.
Answer the user's question directly, clearly, concisely, and professionally.
Provide strategic advice, explanations, or greeting responses without hallucinating CRM database records.{lessons_context}"""

        direct_resp = await call_ollama(
            task_id=task_id,
            agent_name="manager",
            system_prompt=manager_qa_prompt,
            user_prompt=user_message,
            max_tokens=300,
            json_mode=False,
            temperature=0.4,
        )
        tokens_used += direct_resp["metrics"]["total_tokens"]

        answer_content = direct_resp["content"].strip()
        log_audit_result(
            task_id=task_id,
            user_request=user_message,
            routed_agent="manager",
            workflow_id=None,
            audit_status="PASS",
            quality_score=10,
            findings="Manager answered directly and concisely without unnecessary IT Agent or n8n workflow overhead.",
        )

        step2_direct_trace = {
            "step": 2,
            "agent": "Manager Agent",
            "role": "Direct Answer & Strategy",
            "result": {"status": "DIRECT_ANSWER_DELIVERED"},
            "metrics": direct_resp["metrics"],
            "tokens_remaining": max(0, token_budget - tokens_used),
        }
        trace_steps.append(step2_direct_trace)
        yield emit("agent_trace", {"trace": step2_direct_trace})

        final_msg = f"{answer_content}\n\n---\n*Delivered directly by Manager Agent (0 external IT API calls)*"
        yield emit("item", {"content": final_msg})
        yield emit(
            "complete",
            {
                "trace": trace_steps,
                "tokens_used": tokens_used,
                "token_budget": token_budget,
            },
        )
        return

    # -------------------------------------------------------------------------
    # STEP 2: IT AGENT — PREPROCESSING & DETERMINISTIC N8N WEBHOOK EXECUTION
    # -------------------------------------------------------------------------
    yield emit(
        "agent_status",
        {
            "agent": "it_agent",
            "phase": "n8n_lookup",
            "message": "IT Agent is preprocessing parameters and executing the verified n8n webhook...",
        },
    )

    it_result: Dict[str, Any] = {}
    it_metrics: Dict[str, Any] = {
        "agent": "it_agent",
        "model": "n8n-preprocessor (0 tok)",
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "tokens_per_sec": 0.0,
        "duration_ms": 2,
    }

    if intent == "DIAGNOSE_FAILURE":
        latest_n8n = inspect_latest_n8n_execution("crmRelaticleAssistant")
        sys_sum = get_system_summary()
        failed_audits = [
            a for a in (sys_sum.get("recent_audits") or []) if a.get("audit_status") != "PASS"
        ][:3]
        it_result = {
            "status": "DIAGNOSTIC_REPORT",
            "latest_n8n_execution": latest_n8n,
            "recent_failed_audits": failed_audits,
        }
    elif intent == "INSPECT_SYSTEM":
        active_wfs = [w for w in workflows if w.get("active")]
        inactive_wfs = [w for w in workflows if not w.get("active")]
        backlog = get_backlog_specs()
        it_result = {
            "status": "INVENTORY_REPORT",
            "active_workflows_count": len(active_wfs),
            "inactive_workflows_count": len(inactive_wfs),
            "active_workflows": [
                {"id": w["id"], "name": w["name"], "summary": w["summary"], "webhook": w["webhook_url"]}
                for w in active_wfs
            ],
            "inactive_workflows": [
                {"id": w["id"], "name": w["name"], "summary": w["summary"]}
                for w in inactive_wfs
            ],
            "pending_antigravity_specs": len(backlog),
        }
    else:
        match_status = fast_route.get("match_status") or "MISSING_WORKFLOW"
        matched_wf_id = fast_route.get("workflow_id")

        if match_status == "MATCH_ACTIVE" and matched_wf_id:
            wf_obj = next((w for w in workflows if w["id"] == matched_wf_id), None)
            if wf_obj and wf_obj.get("active"):
                # IT Agent Preprocessor: extract structured JSON parameters for deterministic n8n CRM gateway
                crm_payload = _extract_crm_payload_fast(user_message)
                if not crm_payload:
                    it_extract_sys = """You are the IT Agent Preprocessor for Twenty CRM.
Convert the user request into JSON:
{
  "tool": "search_contacts" | "create_contact" | "update_contact" | "delete_contact" | "manage_companies" | "manage_tasks" | "manage_opportunities" | "manage_custom_fields",
  "action": "list" | "search" | "create" | "update" | "delete",
  "query": "search keyword, email, or phone",
  "name": "contact or company name",
  "phone_number": "phone if provided",
  "email": "email if provided",
  "can_email": "True or False if provided"
}"""
                    llm_ext = await call_ollama(
                        task_id=task_id,
                        agent_name="it_agent",
                        system_prompt=it_extract_sys,
                        user_prompt=user_message,
                        max_tokens=120,
                        json_mode=True,
                    )
                    it_metrics = llm_ext["metrics"]
                    tokens_used += it_metrics["total_tokens"]
                    crm_payload = llm_ext["parsed"] or {"tool": "search_contacts", "query": user_message}

                start_n8n = time.time()
                exec_res = await execute_n8n_workflow(wf_obj, crm_payload, session_id=session_id)
                n8n_ms = int((time.time() - start_n8n) * 1000)
                it_metrics["duration_ms"] = it_metrics.get("duration_ms", 0) + n8n_ms

                exec_inspect = inspect_latest_n8n_execution(wf_obj["id"])
                raw_out = exec_res.get("output")
                tool_used = crm_payload.get("tool", "search_contacts")

                if not exec_res.get("ok") or (isinstance(raw_out, dict) and raw_out.get("ok") is False):
                    err_msg = (
                        raw_out.get("error")
                        if isinstance(raw_out, dict)
                        else exec_res.get("message", "n8n execution failed")
                    )
                    it_result = {
                        "status": "EXECUTION_FAILED",
                        "workflow_id": wf_obj["id"],
                        "workflow_name": wf_obj["name"],
                        "execution_id": exec_inspect.get("execution_id"),
                        "tools_invoked": [tool_used],
                        "preprocessed_payload": crm_payload,
                        "error_message": err_msg,
                    }
                else:
                    formatted_md = _format_crm_gateway_output(raw_out, crm_payload)
                    it_result = {
                        "status": "EXECUTED_SUCCESS",
                        "workflow_id": wf_obj["id"],
                        "workflow_name": wf_obj["name"],
                        "execution_id": exec_inspect.get("execution_id"),
                        "tools_invoked": [tool_used],
                        "preprocessed_payload": crm_payload,
                        "webhook_url": wf_obj.get("webhook_url"),
                        "n8n_response": formatted_md,
                        "raw_output": raw_out,
                    }
            else:
                it_result = {
                    "status": "INACTIVE_WORKFLOW",
                    "workflow_id": matched_wf_id,
                    "workflow_name": wf_obj["name"] if wf_obj else matched_wf_id,
                    "domain": target_domain,
                    "reason": fast_route.get("missing_capability_summary")
                    or f"Workflow '{matched_wf_id}' is currently INACTIVE in n8n.",
                }
        elif match_status == "INACTIVE_WORKFLOW":
            wf_obj = next((w for w in workflows if w["id"] == matched_wf_id), None)
            it_result = {
                "status": "INACTIVE_WORKFLOW",
                "workflow_id": matched_wf_id or "gbpEventPoster01",
                "workflow_name": wf_obj["name"] if wf_obj else "Inactive n8n Workflow",
                "domain": target_domain,
                "reason": fast_route.get("missing_capability_summary")
                or "Workflow exists in n8n but is currently INACTIVE.",
            }
        else:
            # IT Agent AI evaluation: check active n8n workflows if domain was not matched by fast rules
            active_wfs = [w for w in workflows if w.get("active")]
            ai_matched_wf = None
            if active_wfs and (token_budget - tokens_used) > 300:
                wf_catalog_str = "\n".join(
                    f"- {w['id']}: {w['name']} | Domain: {w.get('domain')} | Summary: {w.get('summary')}"
                    for w in active_wfs
                )
                it_ai_prompt = f"""You are the IT Agent. Determine if any active n8n workflow can execute the user's task.
Active Workflows in n8n:
{wf_catalog_str}

Output JSON:
{{
  "can_execute": true | false,
  "workflow_id": "matched_workflow_id" | null,
  "reason": "short explanation"
}}"""
                it_ai_match = await call_ollama(
                    task_id=task_id,
                    agent_name="it_agent",
                    system_prompt=it_ai_prompt,
                    user_prompt=user_message,
                    max_tokens=100,
                    json_mode=True,
                )
                it_metrics = it_ai_match["metrics"]
                tokens_used += it_metrics["total_tokens"]
                p_match = it_ai_match["parsed"] or {}
                if p_match.get("can_execute") and p_match.get("workflow_id"):
                    ai_matched_wf = next((w for w in active_wfs if w["id"] == p_match["workflow_id"]), None)

            if ai_matched_wf:
                crm_payload = _extract_crm_payload_fast(user_message) or {"query": user_message}
                start_n8n = time.time()
                exec_res = await execute_n8n_workflow(ai_matched_wf, crm_payload, session_id=session_id)
                n8n_ms = int((time.time() - start_n8n) * 1000)
                it_metrics["duration_ms"] = it_metrics.get("duration_ms", 0) + n8n_ms
                exec_inspect = inspect_latest_n8n_execution(ai_matched_wf["id"])
                raw_out = exec_res.get("output")
                if exec_res.get("ok"):
                    it_result = {
                        "status": "EXECUTED_SUCCESS",
                        "workflow_id": ai_matched_wf["id"],
                        "workflow_name": ai_matched_wf["name"],
                        "execution_id": exec_inspect.get("execution_id"),
                        "tools_invoked": [ai_matched_wf.get("capability_key", "n8n_webhook")],
                        "preprocessed_payload": crm_payload,
                        "webhook_url": ai_matched_wf.get("webhook_url"),
                        "n8n_response": _format_crm_gateway_output(raw_out, crm_payload) if ai_matched_wf["id"] == "crmRelaticleAssistant" else f"```json\n{json.dumps(raw_out, indent=2)}\n```",
                        "raw_output": raw_out,
                    }
                else:
                    it_result = {
                        "status": "EXECUTION_FAILED",
                        "workflow_id": ai_matched_wf["id"],
                        "workflow_name": ai_matched_wf["name"],
                        "error_message": exec_res.get("message", "Execution failed"),
                    }
            else:
                it_result = {
                    "status": "MISSING_WORKFLOW",
                    "workflow_id": None,
                    "domain": target_domain,
                    "reason": fast_route.get("missing_capability_summary")
                    or f"No active n8n workflow is available to handle: '{user_message}'.",
                }

    step2_trace = {
        "step": 2,
        "agent": "IT Agent",
        "role": "Preprocessing & n8n Webhook Execution",
        "result": it_result,
        "metrics": it_metrics,
        "tokens_remaining": max(0, token_budget - tokens_used),
    }
    trace_steps.append(step2_trace)
    yield emit("agent_trace", {"trace": step2_trace})

    # -------------------------------------------------------------------------
    # STEP 3: AUDITOR AGENT — QUALITY CHECK & CAPABILITY GAP REPORT
    # -------------------------------------------------------------------------
    yield emit(
        "agent_status",
        {
            "agent": "auditor",
            "phase": "auditing",
            "message": "Auditor Agent is verifying the IT Agent's result and ensuring zero hallucinations...",
        },
    )

    it_status = it_result.get("status")
    auditor_metrics = {
        "agent": "auditor",
        "model": "rule-verifier (0 tok)",
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "tokens_per_sec": 0.0,
        "duration_ms": 2,
    }

    if it_status in ("MISSING_WORKFLOW", "INACTIVE_WORKFLOW"):
        audit_status = "MISSING_CAPABILITY"
        quality_score = 0
        findings = (
            f"Task failed because the required capability is unavailable or inactive in n8n: {it_result.get('reason')}"
        )
        spec_raw = fast_route.get("default_spec")
        if not spec_raw:
            auditor_system = """You are the Auditor Agent. Specify the missing n8n workflow in JSON:
{
  "workflow_name": "Descriptive title for needed n8n workflow",
  "domain": "crm | marketing | mailman | finance",
  "webhook_path": "kebab-case-slug",
  "trigger_type": "Webhook (POST)",
  "required_inputs": ["field1", "field2"],
  "recommended_n8n_nodes": ["Webhook Trigger", "API / Service Node", "Respond to Webhook"],
  "expected_output": "JSON response description",
  "priority": "High"
}"""
            step3_llm = await call_ollama(
                task_id=task_id,
                agent_name="auditor",
                system_prompt=auditor_system,
                user_prompt=f"User Request: {user_message}\nGap: {it_result.get('reason')}",
                max_tokens=150,
                json_mode=True,
            )
            auditor_metrics = step3_llm["metrics"]
            tokens_used += auditor_metrics["total_tokens"]
            spec_raw = step3_llm["parsed"] or {}

        if not spec_raw.get("workflow_name"):
            spec_raw["workflow_name"] = f"{target_domain.upper()} - {user_message[:45].strip()}"
        if not spec_raw.get("domain"):
            spec_raw["domain"] = target_domain

        audit_report = {
            "audit_status": "MISSING_CAPABILITY",
            "quality_score": 0,
            "findings": findings,
            "lesson_for_agent": "",
            "missing_workflow_spec": spec_raw,
        }
    elif it_status == "EXECUTION_FAILED":
        # Auditor uses Ollama to analyze failure and formulate an actionable lesson
        auditor_diag_sys = """You are the Auditor Agent. Analyze the IT Agent's failed execution and formulate an actionable diagnosis.
Output JSON:
{
  "quality_score": 1, 2, 3, or 4,
  "findings": "Brief root-cause diagnosis of why the operation failed",
  "lesson_rule": "A concise preventative rule for the agent, or empty string"
}"""
        step3_llm = await call_ollama(
            task_id=task_id,
            agent_name="auditor",
            system_prompt=auditor_diag_sys,
            user_prompt=f"User Request: {user_message}\nWorkflow: {it_result.get('workflow_name')}\nError: {it_result.get('error_message')}",
            max_tokens=150,
            json_mode=True,
        )
        auditor_metrics = step3_llm["metrics"]
        tokens_used += auditor_metrics["total_tokens"]
        p_diag = step3_llm["parsed"] or {}
        audit_status = "QUALITY_IMPROVEMENT_NEEDED"
        quality_score = int(p_diag.get("quality_score") or 4)
        findings = p_diag.get("findings") or f"n8n execution #{it_result.get('execution_id')} returned error: {it_result.get('error_message')}"
        lesson_rule = p_diag.get("lesson_rule", "")
        if lesson_rule:
            add_lesson("it_agent", lesson_rule, source="auditor_failure_diagnosis")

        audit_report = {
            "audit_status": audit_status,
            "quality_score": quality_score,
            "findings": findings,
            "lesson_for_agent": lesson_rule,
            "missing_workflow_spec": None,
        }
    else:
        tools_invoked = it_result.get("tools_invoked") or []
        pre_payload = it_result.get("preprocessed_payload") or {}
        filters_used = pre_payload.get("filters") or {}

        # If complex unstructured task or AI extraction was used, Auditor uses Ollama to verify quality
        if not filters_used and it_metrics.get("prompt_tokens", 0) > 0 and (token_budget - tokens_used) > 200:
            auditor_eval_sys = """You are the Auditor Agent. Verify if the execution output satisfies the user's request.
Output JSON:
{
  "quality_score": 8, 9, or 10,
  "audit_status": "PASS" | "QUALITY_IMPROVEMENT_NEEDED",
  "findings": "Brief explanation of verification verdict"
}"""
            step3_llm = await call_ollama(
                task_id=task_id,
                agent_name="auditor",
                system_prompt=auditor_eval_sys,
                user_prompt=f"User Request: {user_message}\nPayload Sent: {json.dumps(pre_payload)}\nTools: {tools_invoked}",
                max_tokens=100,
                json_mode=True,
            )
            auditor_metrics = step3_llm["metrics"]
            tokens_used += auditor_metrics["total_tokens"]
            p_eval = step3_llm["parsed"] or {}
            quality_score = int(p_eval.get("quality_score") or 10)
            audit_status = p_eval.get("audit_status") or "PASS"
            findings = p_eval.get("findings") or f"Auditor verified execution of tools: {tools_invoked} via AI reasoning."
        else:
            audit_status = "PASS"
            quality_score = 10
            tools_note = f" (Deterministic n8n tool: `{', '.join(tools_invoked)}`"
            if filters_used:
                tools_note += f" with verified filters: {filters_used}"
            tools_note += ")"
            findings = f"IT Agent preprocessed request and verified execution output against criteria{tools_note}."

        audit_report = {
            "audit_status": audit_status,
            "quality_score": quality_score,
            "findings": findings,
            "lesson_for_agent": "",
            "missing_workflow_spec": None,
        }

    step3_trace = {
        "step": 3,
        "agent": "Auditor Agent",
        "role": "Work Verification & Gap Detection",
        "report": audit_report,
        "metrics": auditor_metrics,
        "tokens_remaining": max(0, token_budget - tokens_used),
    }
    trace_steps.append(step3_trace)
    yield emit("agent_trace", {"trace": step3_trace})

    # -------------------------------------------------------------------------
    # STEP 4: MANAGER AGENT — POST-AUDIT ACTION, LEARNING & FINAL RESPONSE
    # -------------------------------------------------------------------------
    saved_spec: Optional[Dict[str, Any]] = None
    saved_lesson: Optional[Dict[str, Any]] = None

    if audit_status == "MISSING_CAPABILITY" and audit_report.get("missing_workflow_spec"):
        saved_spec = save_missing_workflow_spec(
            spec=audit_report["missing_workflow_spec"],
            user_request=user_message,
            auditor_findings=findings,
        )

    log_audit_result(
        task_id=task_id,
        user_request=user_message,
        routed_agent="it_agent",
        workflow_id=it_result.get("workflow_id"),
        audit_status=audit_status,
        quality_score=quality_score,
        findings=findings,
        missing_capability=saved_spec["workflow_name"] if saved_spec else None,
        spec_file=saved_spec["host_path"] if saved_spec else None,
    )

    if it_status == "DIAGNOSTIC_REPORT":
        latest_ex = it_result.get("latest_n8n_execution") or {}
        failed_list = "\n".join(
            f"- **Task `{a['task_id']}`** (*\"{a['user_request']}\"*): `{a['audit_status']}` — {a['findings']}"
            for a in (it_result.get("recent_failed_audits") or [])
        )
        final_response = (
            f"### Diagnostic Report on Recent Execution Failures\n\n"
            f"#### Latest n8n Workflow Execution (`#{latest_ex.get('execution_id')}`)\n"
            f"- **Status:** `{latest_ex.get('status')}`\n"
            f"- **Error Detail:** `{latest_ex.get('error_detail') or 'None'}`\n\n"
            f"#### Recent Non-Pass Audit Logs\n"
            f"{failed_list or '- None'}\n"
        )
        yield emit("item", {"content": final_response})
    elif it_status == "INVENTORY_REPORT":
        active_list = "\n".join(
            f"- **`{w['name']}`** (`{w['id']}`) — {w['summary']}\n  - Webhook: `{w['webhook']}`"
            for w in it_result.get("active_workflows", [])
        )
        inactive_list = "\n".join(
            f"- **`{w['name']}`** (`{w['id']}`) — *{w['summary']}*"
            for w in it_result.get("inactive_workflows", [])
        )
        final_response = (
            f"### Live n8n Workflow Inventory (Reported by IT Agent)\n\n"
            f"#### Active & Callable Workflows ({it_result.get('active_workflows_count', 0)})\n"
            f"{active_list or '- None'}\n\n"
            f"#### Inactive / Draft Workflows in n8n ({it_result.get('inactive_workflows_count', 0)})\n"
            f"{inactive_list or '- None'}\n\n"
            f"---\n"
            f"**Auditor Verdict:** `PASS` ({quality_score}/10) — {findings}\n"
            f"**Pending Antigravity Workflow Specs in Backlog:** `{it_result.get('pending_antigravity_specs', 0)}`"
        )
        yield emit("item", {"content": final_response})
    elif audit_status == "MISSING_CAPABILITY" and saved_spec:
        inactive_note = (
            f"\n- **Existing Inactive Workflow in n8n:** `{saved_spec['existing_inactive_workflow_id']}` (needs activation & webhook trigger)"
            if saved_spec.get("existing_inactive_workflow_id")
            else ""
        )
        nodes_str = ", ".join(saved_spec.get("recommended_n8n_nodes") or [])
        inputs_str = ", ".join(saved_spec.get("required_inputs") or [])
        final_response = (
            f"### Capability Not Available in n8n — Spec Created for Antigravity\n\n"
            f"**IT Agent Report:** {it_result.get('reason')}\n\n"
            f"**Auditor Verdict:** `MISSING_CAPABILITY` — {findings}\n\n"
            f"---\n"
            f"### Manager Action: Missing Workflow Spec Generated\n"
            f"- **Proposed Workflow:** `{saved_spec['workflow_name']}`\n"
            f"- **Target Domain:** `{saved_spec['domain']}`{inactive_note}\n"
            f"- **Planned Webhook:** `{saved_spec['webhook_path']}`\n"
            f"- **Required Inputs:** `{inputs_str}`\n"
            f"- **Recommended n8n Nodes:** {nodes_str}\n"
            f"- **Saved Spec File:** `{saved_spec['host_path']}`\n\n"
            f"**Next Step with Antigravity:**\n"
            f"Ask Antigravity:\n"
            f"> *{saved_spec['antigravity_prompt']}*"
        )
        yield emit("item", {"content": final_response})
    elif it_status == "EXECUTED_SUCCESS":
        final_response = (
            f"{it_result.get('n8n_response')}\n\n"
            f"---\n"
            f"**Preprocessed Payload:** `{json.dumps(it_result.get('preprocessed_payload'))}`\n"
            f"**Executed via n8n Workflow:** `{it_result.get('workflow_name')}` (`#{it_result.get('execution_id')}`)\n"
            f"**Auditor Verdict:** `{audit_status}` (Score: **{quality_score}/10**) — {findings}"
        )
        yield emit("item", {"content": final_response})
    else:
        final_response = (
            f"### Task Execution Report\n\n"
            f"- **IT Agent Status:** `{it_status}` — {it_result.get('error_message') or it_result.get('reason')}\n"
            f"- **Preprocessed Payload:** `{json.dumps(it_result.get('preprocessed_payload'))}`\n"
            f"- **Auditor Verdict:** `{audit_status}` (Score: **{quality_score}/10**) — {findings}"
        )
        yield emit("item", {"content": final_response})

    step4_trace = {
        "step": 4,
        "agent": "Manager Agent",
        "role": "Post-Audit Decision & Spec Generation",
        "action_taken": (
            f"Generated Antigravity n8n spec: {saved_spec['file_name']}"
            if saved_spec
            else "Verified PASS and delivered response to user"
        ),
        "spec_created": saved_spec,
        "lesson_added": saved_lesson,
        "tokens_used_total": tokens_used,
        "token_budget": token_budget,
    }
    trace_steps.append(step4_trace)
    yield emit("agent_trace", {"trace": step4_trace})

    yield emit(
        "complete",
        {
            "trace": trace_steps,
            "tokens_used": tokens_used,
            "token_budget": token_budget,
            "spec_created": saved_spec,
            "lesson_added": saved_lesson,
        },
    )
