import json
import logging
import re
import time
from typing import Any, Dict, List, Optional
import httpx

from n8n_catalog import N8N_BASE_URL, get_n8n_workflows, execute_n8n_workflow, inspect_latest_n8n_execution

logger = logging.getLogger("agent_tools")
CRM_GATEWAY_URL = f"{N8N_BASE_URL}/webhook/relaticle-crm-action"


# =============================================================================
# Tool Schema Declarations (OpenAI / Gemini function calling format)
# =============================================================================

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_contacts",
            "description": "Search contacts in Twenty CRM with semantic keywords or compound criteria (can_email, missing phone, role, market). Also used for counting matching contacts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keyword, contact name, email, phone, or 'all'. Defaults to 'all'.",
                    },
                    "can_email": {
                        "type": "boolean",
                        "description": "Filter by email permission: true if contact can be emailed, false if cannot be emailed.",
                    },
                    "phone_blank": {
                        "type": "boolean",
                        "description": "True to only return contacts with NO phone number (blank/empty).",
                    },
                    "email_present": {
                        "type": "boolean",
                        "description": "True to only return contacts that have a non-empty email address.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of contacts to return (default 50, use up to 500 for counts).",
                    },
                    "count_mode": {
                        "type": "boolean",
                        "description": "Set to true if user is asking 'how many' or count inquiries.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_contact",
            "description": "Create a new contact/lead in Twenty CRM. Requires at least a valid full name. Live service: only test with verified owner details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Full name of the contact"},
                    "email": {"type": "string", "description": "Email address"},
                    "phone_number": {"type": "string", "description": "Phone number"},
                    "role": {
                        "type": "string",
                        "description": "Role: Customer, Buyer, Seller, Real estate agent, etc.",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_contact",
            "description": "Update an existing contact in Twenty CRM. Requires either contact_id or target_name to identify the contact, plus at least one field to change.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_id": {
                        "type": "string",
                        "description": "Twenty CRM contact UUID (e.g. 0001f8ad-6f16-4074-9329-1b6c31a860c6)",
                    },
                    "target_name": {
                        "type": "string",
                        "description": "Full name of the contact to update if ID is unknown",
                    },
                    "phone_number": {"type": "string", "description": "New phone number"},
                    "email": {"type": "string", "description": "New email address"},
                    "can_email": {
                        "type": "string",
                        "description": "'True' or 'False' to update email permission",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_contact",
            "description": "Delete a contact from Twenty CRM by UUID or full name. Use with caution. Only delete verified test records.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_id": {"type": "string", "description": "Twenty CRM contact UUID"},
                    "name": {"type": "string", "description": "Contact name if UUID unknown"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_notes",
            "description": "List or add client interaction notes in Twenty CRM.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "create"],
                        "description": "'list' to view notes, 'create' to add a new note",
                    },
                    "target_name": {
                        "type": "string",
                        "description": "Contact name the note belongs to",
                    },
                    "contact_id": {"type": "string", "description": "Contact UUID"},
                    "title": {"type": "string", "description": "Note title / subject"},
                    "content": {"type": "string", "description": "Body / details of the note"},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_tasks",
            "description": "List or create follow-up tasks in Twenty CRM.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "create"],
                        "description": "'list' to view tasks, 'create' to add a new task",
                    },
                    "title": {"type": "string", "description": "Task description/title"},
                    "priority": {
                        "type": "string",
                        "enum": ["LOW", "MEDIUM", "HIGH"],
                        "description": "Task priority",
                    },
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_opportunities",
            "description": "List active real estate deals / pipeline opportunities in Twenty CRM.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "create"],
                        "description": "'list' to view deals",
                    },
                    "name": {"type": "string", "description": "Deal / property name"},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_n8n_workflows",
            "description": "Inspect active automation workflows in n8n to check system capabilities.",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Optional domain filter (e.g. 'crm', 'marketing', 'finance')",
                    }
                },
                "required": [],
            },
        },
    },
]


# =============================================================================
# Tool Execution Dispatcher
# =============================================================================

async def execute_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes a typed tool call against Casa-poki services (n8n, Twenty CRM)
    and returns a structured execution payload.
    """
    start_ts = time.time()

    if name == "inspect_n8n_workflows":
        wfs = get_n8n_workflows()
        domain = args.get("domain")
        if domain:
            wfs = [w for w in wfs if w.get("domain") == domain]
        active = [w for w in wfs if w.get("active")]
        inactive = [w for w in wfs if not w.get("active")]
        return {
            "ok": True,
            "tool": name,
            "active_workflows": [{"id": w["id"], "name": w["name"], "domain": w.get("domain")} for w in active],
            "inactive_workflows": [{"id": w["id"], "name": w["name"], "domain": w.get("domain")} for w in inactive],
            "duration_ms": int((time.time() - start_ts) * 1000),
        }

    # All CRM tools route to the verified Relaticle CRM gateway in n8n
    payload: Dict[str, Any] = {"tool": name}

    if name == "search_contacts":
        query = args.get("query") or "all"
        filters: Dict[str, Any] = {}
        if args.get("can_email") is not None:
            filters["can_email"] = bool(args["can_email"])
        if args.get("phone_blank"):
            filters["phone_blank"] = True
        if args.get("email_present"):
            filters["email_present"] = True

        limit = args.get("limit") or (500 if args.get("count_mode") else 50)
        payload = {
            "operation": "search_contacts",
            "query": query,
            "filters": filters,
            "limit": limit,
            "count_mode": bool(args.get("count_mode")),
        }

    elif name == "create_contact":
        payload = {
            "tool": "create_contact",
            "name": args.get("name"),
            "email": args.get("email"),
            "phone_number": args.get("phone_number"),
            "role": args.get("role", "Customer"),
        }

    elif name == "update_contact":
        if not args.get("contact_id") and not args.get("target_name"):
            return {
                "ok": False,
                "tool": name,
                "error": "Missing parameter: Either 'contact_id' or 'target_name' must be provided to update a contact.",
                "duration_ms": int((time.time() - start_ts) * 1000),
            }
        payload = {
            "tool": "update_contact",
            "id": args.get("contact_id"),
            "target_name": args.get("target_name"),
            "phone_number": args.get("phone_number"),
            "email": args.get("email"),
            "can_email": args.get("can_email"),
        }

    elif name == "delete_contact":
        if not args.get("contact_id") and not args.get("name"):
            return {
                "ok": False,
                "tool": name,
                "error": "Missing parameter: Either 'contact_id' or 'name' must be provided to delete a contact.",
                "duration_ms": int((time.time() - start_ts) * 1000),
            }
        payload = {
            "tool": "delete_contact",
            "id": args.get("contact_id"),
            "name": args.get("name"),
        }

    elif name == "manage_notes":
        payload = {
            "tool": "manage_notes",
            "action": args.get("action", "list"),
            "target_name": args.get("target_name"),
            "contact_id": args.get("contact_id"),
            "title": args.get("title"),
            "content": args.get("content"),
        }

    elif name == "manage_tasks":
        payload = {
            "tool": "manage_tasks",
            "action": args.get("action", "list"),
            "title": args.get("title"),
            "priority": args.get("priority", "MEDIUM"),
        }

    elif name == "manage_opportunities":
        payload = {
            "tool": "manage_opportunities",
            "action": args.get("action", "list"),
            "name": args.get("name"),
        }

    # Dispatch to n8n CRM gateway
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(CRM_GATEWAY_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
            data["duration_ms"] = int((time.time() - start_ts) * 1000)
            data["raw_payload_sent"] = payload
            return data
    except Exception as e:
        return {
            "ok": False,
            "tool": name,
            "error": str(e),
            "raw_payload_sent": payload,
            "duration_ms": int((time.time() - start_ts) * 1000),
        }


def format_tool_result(tool_name: str, result: Dict[str, Any], args: Dict[str, Any]) -> str:
    """
    Formats the tool output into clean, structured Markdown for the user.
    """
    if not result.get("ok", True) and "error" in result:
        return f"⚠️ **Operation Error (`{tool_name}`):** {result.get('error')}"

    if tool_name == "search_contacts":
        contacts = result.get("contacts") or []
        filters = (result.get("raw_payload_sent") or {}).get("filters") or {}

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
            if filters.get("email_present"):
                contacts = [
                    c for c in contacts
                    if c.get("email") and str(c.get("email")).strip() not in ("", "N/A", "None")
                ]

        total = len(contacts)
        is_count = args.get("count_mode") or (result.get("raw_payload_sent") or {}).get("count_mode")

        filter_parts = []
        if filters.get("can_email") is not None:
            filter_parts.append(f"can_email={filters['can_email']}")
        if filters.get("phone_blank"):
            filter_parts.append("phone=blank")
        if filters.get("email_present"):
            filter_parts.append("email=present")
        filter_str = f" [Filters: {', '.join(filter_parts)}]" if filter_parts else ""

        if total == 0:
            count_line = "### CRM Contact Count: **0 matching contacts found**\n" if is_count else ""
            return f"{count_line}### CRM Contact Search\nNo matching contacts found in Twenty CRM{filter_str}."

        title = f"### CRM Contact Count: **{total} matching contacts found**{filter_str}" if is_count else f"### CRM Contacts (`{total}` verified records{filter_str})"
        lines = [f"{title}\n"]
        for c in contacts[:50]:
            lines.append(
                f"- **{c.get('name')}** (ID: `{c.get('id')}`)\n"
                f"  - Phone: `{c.get('phone') or 'N/A'}` | Email: `{c.get('email') or 'N/A'}`\n"
                f"  - Role: `{c.get('role') or 'Customer'}` | Can Email: `{c.get('can_email')}` | Market: `{c.get('market') or 'N/A'}`"
            )
        if total > 50:
            lines.append(f"\n*...and {total - 50} more records.*")
        return "\n".join(lines)

    if tool_name == "create_contact":
        return (
            f"### Contact Created in Twenty CRM\n"
            f"- **Name:** **{result.get('name') or args.get('name')}**\n"
            f"- **ID:** `{result.get('id')}`\n"
            f"- **Status:** {result.get('message', 'Created successfully')}"
        )

    if tool_name == "update_contact":
        return (
            f"### Contact Updated in Twenty CRM\n"
            f"- **Name / ID:** `{result.get('updated_id') or args.get('contact_id') or args.get('target_name')}`\n"
            f"- **Status:** {result.get('message', 'Updated successfully')}"
        )

    if tool_name == "delete_contact":
        return (
            f"### Contact Deleted from Twenty CRM\n"
            f"- **Deleted ID:** `{result.get('deleted_id') or args.get('contact_id')}`\n"
            f"- **Status:** {result.get('message', 'Deleted successfully')}"
        )

    if tool_name == "manage_notes":
        notes = result.get("notes") or []
        if args.get("action") == "create" or "message" in result:
            return f"### CRM Note Added\n- **Status:** {result.get('message', 'Note saved successfully')}"
        if not notes:
            return "### Twenty CRM Notes\nNo client notes found."
        lines = [f"### Twenty CRM Notes (`{len(notes)}` total)\n"]
        for n in notes[:10]:
            lines.append(f"- **{n.get('title')}** (`{n.get('id')}`) — Added: `{str(n.get('created_at'))[:10]}`")
        return "\n".join(lines)

    if tool_name == "manage_tasks":
        tasks = result.get("tasks") or []
        if not tasks:
            return "### Twenty CRM Tasks\nNo tasks found."
        lines = [f"### Twenty CRM Tasks (`{len(tasks)}` total)\n"]
        for t in tasks[:15]:
            lines.append(f"- **{t.get('title')}** — Status: **{t.get('status')}** | Priority: `{t.get('priority')}`")
        return "\n".join(lines)

    if tool_name == "manage_opportunities":
        opps = result.get("opportunities") or []
        if not opps:
            return "### Twenty CRM Opportunities\nNo active deals found."
        lines = [f"### Twenty CRM Opportunities (`{len(opps)}` total)\n"]
        for o in opps[:15]:
            lines.append(f"- **{o.get('name')}** — Stage: **{o.get('stage') or 'N/A'}**")
        return "\n".join(lines)

    if tool_name == "inspect_n8n_workflows":
        active = result.get("active_workflows", [])
        lines = [f"### n8n Active Workflows (`{len(active)}` active)\n"]
        for w in active:
            lines.append(f"- **{w['name']}** (`{w['id']}`) [Domain: `{w.get('domain')}`]")
        return "\n".join(lines)

    return f"```json\n{json.dumps(result, indent=2)}\n```"
