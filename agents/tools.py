import json
import logging
import os
import re
import time
from datetime import datetime, date
from typing import Any, Dict, List, Optional
import httpx

from n8n_catalog import N8N_BASE_URL, get_n8n_workflows
import vector_memory
from bigcapital_tools import bigcapital_client
import state_store

logger = logging.getLogger("agent_tools")

# Twenty CRM Direct Integration Config
TWENTY_BASE_URL = os.environ.get("TWENTY_BASE_URL", "http://192.168.1.240:8085")
TWENTY_API_KEY = os.environ.get("TWENTY_API_KEY", "")

# Fallback n8n gateway if needed
N8N_CRM_GATEWAY_URL = f"{N8N_BASE_URL}/webhook/relaticle-crm-action"

# Brevo API & Post-Close Automation Config
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
BREVO_POST_CLOSE_LIST_ID = int(os.environ.get("BREVO_POST_CLOSE_LIST_ID", "14"))
BREVO_BASE_URL = "https://api.brevo.com"

# 1-Year Buyer Post-Close Drip Cadence (Day 280 / Template 13 is skipped per user instruction)
BUYER_POST_CLOSE_SCHEDULE = [
    {"day": 1, "template_id": 5, "name": "Day 1: Welcome & Immediate Priorities"},
    {"day": 5, "template_id": 6, "name": "Day 5: Home Maintenance Guide"},
    {"day": 8, "template_id": 7, "name": "Day 8: Top Home Security Tips"},
    {"day": 14, "template_id": 8, "name": "Day 14: Estate Planning & Will Reminder"},
    {"day": 21, "template_id": 9, "name": "Day 21: Energy Efficiency & Rebates"},
    {"day": 45, "template_id": 10, "name": "Day 45: WA Construction & Permit Guide"},
    {"day": 55, "template_id": 11, "name": "Day 55: Top 10 High-ROI Improvements"},
    {"day": 90, "template_id": 12, "name": "Day 90: 3-Month Check-In"},
    {"day": 300, "template_id": 14, "name": "Day 300: Annual Insurance Review"},
    {"day": 330, "template_id": 15, "name": "Day 330: Annual Home Value Review (CMA)"},
    {"day": 330, "template_id": 17, "name": "New Construction: 11-Month Builder Warranty", "new_construction_only": True},
    {"day": 360, "template_id": 16, "name": "Day 360: Happy 1-Year Housiversary"},
]


def _get_crm_headers() -> Dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if TWENTY_API_KEY:
        headers["Authorization"] = f"Bearer {TWENTY_API_KEY}"
    return headers


async def crm_get(endpoint: str, timeout: float = 15.0) -> Dict[str, Any]:
    url = f"{TWENTY_BASE_URL}{endpoint}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url, headers=_get_crm_headers())
        resp.raise_for_status()
        return resp.json()


async def crm_post(endpoint: str, payload: Dict[str, Any], timeout: float = 15.0) -> Dict[str, Any]:
    url = f"{TWENTY_BASE_URL}{endpoint}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, headers=_get_crm_headers(), json=payload)
        resp.raise_for_status()
        return resp.json()


async def crm_patch(endpoint: str, payload: Dict[str, Any], timeout: float = 15.0) -> Dict[str, Any]:
    url = f"{TWENTY_BASE_URL}{endpoint}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.patch(url, headers=_get_crm_headers(), json=payload)
        resp.raise_for_status()
        return resp.json()


async def crm_delete(endpoint: str, timeout: float = 15.0) -> Dict[str, Any]:
    url = f"{TWENTY_BASE_URL}{endpoint}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.delete(url, headers=_get_crm_headers())
        resp.raise_for_status()
        return resp.json() if resp.content else {"ok": True}


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
                    "sort_by": {
                        "type": "string",
                        "enum": ["created_at", "updated_at", "name"],
                        "description": "Sort field. Default 'created_at' so newest/recent records appear first.",
                    },
                    "order": {
                        "type": "string",
                        "enum": ["desc", "asc"],
                        "description": "Sort direction. Default 'desc' so newest/last records appear first.",
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
            "description": "Create a new contact/lead in Twenty CRM directly. Requires at least a valid full name. Live service: only test with verified owner details.",
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
            "description": "Update an existing contact in Twenty CRM directly. Requires either contact_id or target_name to identify the contact, plus at least one field to change.",
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
                    "name": {
                        "type": "string",
                        "description": "New full name for the contact (if renaming)",
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
            "description": "List or add client interaction notes directly in Twenty CRM.",
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
            "description": "List or create follow-up tasks directly in Twenty CRM.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "create", "delete"],
                        "description": "'list' to view tasks, 'create' to add a new task, 'delete' to remove",
                    },
                    "title": {"type": "string", "description": "Task description/title"},
                    "priority": {
                        "type": "string",
                        "enum": ["LOW", "MEDIUM", "HIGH"],
                        "description": "Task priority",
                    },
                    "contact_id": {"type": "string", "description": "Optional contact UUID to link task to"},
                    "task_id": {"type": "string", "description": "Task ID if deleting"},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_opportunities",
            "description": "List active real estate deals / pipeline opportunities directly in Twenty CRM.",
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
            "name": "delegate_to_agent",
            "description": "Delegate a task, specialized analysis, or follow-up to another Casa-poki agent persona. Available target agents: 'manager', 'it', 'auditor', 'intake', 'finance', 'marketing', 'cma'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_agent": {
                        "type": "string",
                        "enum": ["manager", "it", "auditor", "intake", "finance", "marketing", "cma", "mailman"],
                        "description": "The specialist agent to delegate this task to",
                    },
                    "task_description": {
                        "type": "string",
                        "description": "Detailed description of what the delegated specialist should do and return",
                    },
                    "context_data": {
                        "type": "string",
                        "description": "Optional context, data, or contact IDs needed for the sub-task",
                    },
                },
                "required": ["target_agent", "task_description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "store_memory",
            "description": "Store domain knowledge, market facts, client preferences, or operational resolutions into the persistent Vector Database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The exact fact, insight, rule, or resolution knowledge to vectorize and store",
                    },
                    "category": {
                        "type": "string",
                        "enum": ["domain_knowledge", "market_intelligence", "operational_rule", "client_preference", "past_resolution"],
                        "description": "Category tag for the memory",
                    },
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_memory",
            "description": "Perform semantic similarity search on the Vector Database to retrieve past resolutions, domain specs, rules, and market comps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language question or search query for vector lookup",
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category filter",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of top matching memories to retrieve (default 3)",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finance_record_bill",
            "description": "Record an incoming vendor bill or invoice in Bigcapital accounting (https://finance.lokeshchanana.com). Automatically resolves or creates vendors.",
            "parameters": {
                "type": "object",
                "properties": {
                    "vendor_name": {
                        "type": "string",
                        "description": "Name of the vendor, utility, or supplier (e.g. 'Puget Sound Energy', 'Comcast', 'King County Treasury')",
                    },
                    "amount": {
                        "type": "number",
                        "description": "Total amount of the bill in USD",
                    },
                    "due_date": {
                        "type": "string",
                        "description": "Due date in YYYY-MM-DD format (defaults to bill date or today)",
                    },
                    "bill_date": {
                        "type": "string",
                        "description": "Date bill was issued in YYYY-MM-DD format (defaults to today)",
                    },
                    "category": {
                        "type": "string",
                        "description": "Expense category (e.g. 'Utilities', 'Office', 'Software', 'Rent', 'Tax', 'Maintenance')",
                    },
                    "reference_no": {
                        "type": "string",
                        "description": "Invoice number or billing account reference",
                    },
                    "note": {
                        "type": "string",
                        "description": "Description, items breakdown, or payment instructions",
                    },
                },
                "required": ["vendor_name", "amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finance_record_payment",
            "description": "Record a payment or settlement for an open bill in Bigcapital accounting.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bill_id": {
                        "type": "integer",
                        "description": "The Bigcapital Bill ID to apply payment towards",
                    },
                    "amount": {
                        "type": "number",
                        "description": "Payment amount in USD (optional, defaults to remaining bill balance)",
                    },
                    "payment_date": {
                        "type": "string",
                        "description": "Date payment was processed in YYYY-MM-DD format",
                    },
                    "statement": {
                        "type": "string",
                        "description": "Payment memo, check number, or bank reference",
                    },
                },
                "required": ["bill_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finance_list_bills",
            "description": "Query bills and payables from Bigcapital accounting. Supports viewing open, paid, or overdue bills.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["all", "open", "due"],
                        "description": "Filter bills by status (default: 'all')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of bills to retrieve (default: 20)",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finance_dashboard",
            "description": "Retrieve executive financial overview from Bigcapital: total accounts payable, open bills count, urgent dues, and app status.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finance_import_historical_bills",
            "description": "Batch-import historical bills into Bigcapital accounting. Used for backlog ingestion of past invoices and receipts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bills": {
                        "type": "array",
                        "description": "List of historical bill objects with vendor_name, amount, bill_date, due_date, reference_no, note, and is_paid flag",
                        "items": {
                            "type": "object",
                            "properties": {
                                "vendor_name": {"type": "string"},
                                "amount": {"type": "number"},
                                "bill_date": {"type": "string"},
                                "due_date": {"type": "string"},
                                "reference_no": {"type": "string"},
                                "note": {"type": "string"},
                                "is_paid": {"type": "boolean"},
                            },
                            "required": ["vendor_name", "amount"],
                        },
                    },
                },
                "required": ["bills"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mailman_read_inbox",
            "description": "Silas Drake (Mail Courier & Dispatcher) connects to lokesh@lokeshchanana.com to fetch, read, and triage unread incoming emails, bringing structured email intelligence to Marcus Vance for routing (Finance bills to Fiona, CRM leads to Miles, CMA to Carter, marketing to Maya, or discarding spam).",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of recent unread emails to inspect (default 5)",
                    },
                    "filter_keyword": {
                        "type": "string",
                        "description": "Optional keyword or sender to filter emails by",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "enroll_buyer_post_close",
            "description": "Maya Reyes (Marketing Agent) enrolls a buyer client into the 1-Year Post-Close Smart Plan after closing on a home. Syncs contact to Brevo list 'Buyer Post-Close Drip', initializes attributes (CLOSE_DATE, PROPERTY_ADDRESS, IS_NEW_CONSTRUCTION), creates SQLite schedule tracking, and logs the smart plan activation note on the Twenty CRM contact timeline.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_id": {"type": "string", "description": "Twenty CRM Person ID (optional if email or name provided)"},
                    "email": {"type": "string", "description": "Client email address"},
                    "name": {"type": "string", "description": "Client full name or first name"},
                    "close_date": {"type": "string", "description": "Closing date in YYYY-MM-DD format (defaults to today if omitted)"},
                    "property_address": {"type": "string", "description": "Purchased home address"},
                    "is_new_construction": {"type": "boolean", "description": "Whether the purchased property is new construction (eligible for 11-month builder warranty email)"},
                    "deal_id": {"type": "string", "description": "Optional Twenty CRM Opportunity / Deal ID"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_post_close_drips",
            "description": "Maya Reyes lists all active buyer clients enrolled in the Post-Close Smart Plan, showing days elapsed since closing, sent templates, and next scheduled touchpoints.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "process_post_close_drips",
            "description": "Maya Reyes evaluates all active buyer post-close enrollments against today's date, delivers due email templates via Brevo SMTP API, and attaches delivery verification notes to Twenty CRM contact records.",
            "parameters": {
                "type": "object",
                "properties": {
                    "force_contact_id": {"type": "string", "description": "Optional: test or process a single specific contact"},
                },
            },
        },
    },
]


# =============================================================================
# Direct Twenty CRM Execution Handlers
# =============================================================================

async def _direct_search_contacts(args: Dict[str, Any]) -> Dict[str, Any]:
    query = (args.get("query") or "all").strip().lower()
    limit = args.get("limit") or (500 if args.get("count_mode") else 50)
    
    # Twenty CRM REST API
    raw_res = await crm_get(f"/rest/people?limit=200&order=createdAt:desc")
    people = raw_res.get("data", {}).get("people", [])
    
    mapped_contacts: List[Dict[str, Any]] = []
    for p in people:
        first_name = (p.get("name") or {}).get("firstName") or ""
        last_name = (p.get("name") or {}).get("lastName") or ""
        full_name = f"{first_name} {last_name}".strip() or "Contact"
        email = (p.get("emails") or {}).get("primaryEmail") or ""
        phone = (p.get("phones") or {}).get("primaryPhoneNumber") or ""
        can_email_val = "True" if p.get("canEmail") else "False"
        
        c_obj = {
            "id": p.get("id"),
            "name": full_name,
            "company_id": p.get("companyId"),
            "phone": phone,
            "email": email,
            "role": p.get("contactRole") or "Customer",
            "can_email": can_email_val,
            "lead_source": p.get("leadSource") or "",
            "market": p.get("market") or "",
            "created_at": p.get("createdAt") or "",
            "created_date": (p.get("createdAt") or "")[:10],
            "updated_at": p.get("updatedAt") or "",
        }
        mapped_contacts.append(c_obj)

    # Sort contacts by created_at descending by default so recent contacts appear first
    sort_by = (args.get("sort_by") or "created_at").lower()
    order = (args.get("order") or "desc").lower()
    if sort_by in ("created_at", "date", "created"):
        mapped_contacts.sort(key=lambda c: c.get("created_at") or "", reverse=(order != "asc"))
    elif sort_by in ("updated_at", "updated", "recent_update"):
        mapped_contacts.sort(key=lambda c: c.get("updated_at") or "", reverse=(order != "asc"))
    elif sort_by == "name":
        mapped_contacts.sort(key=lambda c: (c.get("name") or "").lower(), reverse=(order == "desc"))
    else:
        mapped_contacts.sort(key=lambda c: c.get("created_at") or "", reverse=True)
        
    # Keyword filtering (ignore generic semantic query noise and inline filters like can_email:true)
    generic_query_patterns = [
        "all", "contacts", "users", "people", "list", "show all",
        "contacts can be emailed", "people who can be emailed",
        "can be emailed", "can email", "email", "phone",
        "can_email:true", "can_email:false", "can_email=true", "can_email=false"
    ]
    is_generic_query = (
        query in generic_query_patterns
        or query.startswith("can_email")
        or (":" in query and any(k in query for k in ["can_email", "phone", "email", "role", "market"]))
        or any(query.startswith(p) for p in ["contacts with", "people with", "who can", "contacts who"])
    )
    
    if query and not is_generic_query:
        mapped_contacts = [
            c for c in mapped_contacts
            if query in c["name"].lower()
            or query in c["email"].lower()
            or query in c["phone"].lower()
            or query in c["market"].lower()
            or query in c["lead_source"].lower()
        ]
        
    # Structured criteria filtering
    if args.get("can_email") is not None:
        target_can_email = "True" if bool(args["can_email"]) else "False"
        mapped_contacts = [c for c in mapped_contacts if c["can_email"] == target_can_email]
        
    if args.get("phone_blank"):
        mapped_contacts = [c for c in mapped_contacts if not c["phone"] or c["phone"].strip() in ("", "N/A", "None")]
        
    if args.get("email_present"):
        mapped_contacts = [c for c in mapped_contacts if c["email"] and c["email"].strip() not in ("", "N/A", "None")]

    total_found = len(mapped_contacts)
    sliced = mapped_contacts[:limit]
    
    return {
        "ok": True,
        "tool": "search_contacts",
        "direct": True,
        "total_found": total_found,
        "contacts": sliced,
    }


async def _direct_create_contact(args: Dict[str, Any]) -> Dict[str, Any]:
    full_name = (args.get("name") or "").strip()
    if not full_name and not args.get("email") and not args.get("phone_number"):
        return {"ok": False, "tool": "create_contact", "error": "Name, email, or phone is required."}
        
    name_parts = full_name.split(" ", 1)
    first_name = name_parts[0] if name_parts else "New"
    last_name = name_parts[1] if len(name_parts) > 1 else "Lead"
    
    payload: Dict[str, Any] = {
        "name": {"firstName": first_name, "lastName": last_name},
        "leadSource": "AI Agent",
        "contactRole": args.get("role", "Customer"),
        "canEmail": True,
    }
    if args.get("email"):
        payload["emails"] = {"primaryEmail": args["email"].strip()}
    if args.get("phone_number"):
        digits = re.sub(r"[^0-9]", "", str(args["phone_number"]))
        if len(digits) == 10:
            payload["phones"] = {
                "primaryPhoneCallingCode": "+1",
                "primaryPhoneCountryCode": "US",
                "primaryPhoneNumber": digits,
            }
        elif len(digits) == 11 and digits.startswith("1"):
            payload["phones"] = {
                "primaryPhoneCallingCode": "+1",
                "primaryPhoneCountryCode": "US",
                "primaryPhoneNumber": digits[1:],
            }
        else:
            payload["phones"] = {
                "primaryPhoneCallingCode": "+1",
                "primaryPhoneCountryCode": "US",
                "primaryPhoneNumber": digits,
            }
        
    res = await crm_post("/rest/people", payload)
    new_person = res.get("data", {}).get("createPerson", {})
    return {
        "ok": True,
        "tool": "create_contact",
        "direct": True,
        "id": new_person.get("id"),
        "name": full_name,
        "contact": new_person,
        "message": "Contact created successfully in Twenty CRM.",
    }


async def _direct_update_contact(args: Dict[str, Any]) -> Dict[str, Any]:
    target_id = args.get("contact_id")
    target_name = args.get("target_name")
    
    if not target_id:
        if not target_name:
            return {"ok": False, "tool": "update_contact", "error": "Either contact_id or target_name is required."}
        # Resolve target_name by searching
        search_res = await _direct_search_contacts({"query": target_name})
        contacts = search_res.get("contacts", [])
        if not contacts:
            return {"ok": False, "tool": "update_contact", "error": f"Contact '{target_name}' not found."}
        target_id = contacts[0]["id"]
        
    update_payload: Dict[str, Any] = {}
    new_name = (args.get("name") or args.get("new_name") or "").strip()
    if new_name:
        parts = new_name.split(" ", 1)
        update_payload["name"] = {
            "firstName": parts[0],
            "lastName": parts[1] if len(parts) > 1 else "",
        }
    if args.get("phone_number"):
        digits = re.sub(r"[^0-9]", "", str(args["phone_number"]))
        clean_digits = digits[1:] if len(digits) == 11 and digits.startswith("1") else digits
        update_payload["phones"] = {
            "primaryPhoneCallingCode": "+1",
            "primaryPhoneCountryCode": "US",
            "primaryPhoneNumber": clean_digits,
        }
    if args.get("email"):
        update_payload["emails"] = {"primaryEmail": args["email"].strip()}
    if args.get("can_email") is not None:
        can_bool = str(args["can_email"]).lower() in ("true", "1", "yes")
        update_payload["canEmail"] = can_bool

    # Real Estate Lifecycle & Representation Fields
    if args.get("role"):
        update_payload["contactRole"] = args["role"].strip()
    if args.get("partner_name"):
        update_payload["partnerName"] = args["partner_name"].strip()
    if args.get("primary_property_address"):
        update_payload["primaryPropertyAddress"] = args["primary_property_address"].strip()
    if args.get("search_active") is not None:
        update_payload["searchActive"] = str(args["search_active"]).lower() in ("true", "1", "yes")
    if args.get("portal_active") is not None:
        update_payload["portalActive"] = str(args["portal_active"]).lower() in ("true", "1", "yes")
    if args.get("last_portal_activity_at"):
        update_payload["lastPortalActivityAt"] = args["last_portal_activity_at"]
    if args.get("bba_signed") is not None:
        update_payload["bbaSigned"] = str(args["bba_signed"]).lower() in ("true", "1", "yes")
    if args.get("bba_signed_date"):
        update_payload["bbaSignedDate"] = args["bba_signed_date"]
    if args.get("bba_expiration_date"):
        update_payload["bbaExpirationDate"] = args["bba_expiration_date"]
    if args.get("past_client_type"):
        update_payload["pastClientType"] = args["past_client_type"].strip()
    if args.get("home_maintenance_tips") is not None:
        update_payload["homeMaintenanceTips"] = str(args["home_maintenance_tips"]).lower() in ("true", "1", "yes")

    # Lifecycle Stage with Regression Guardrails
    new_stage = args.get("lifecycle_stage")
    if new_stage:
        clean_new = new_stage.strip()
        stage_hierarchy = {
            "lead": 1,
            "engaged": 2,
            "active client": 3,
            "pending": 4,
            "past client": 5,
        }
        force_override = args.get("force_stage_update", False)
        if not force_override:
            try:
                curr_res = await crm_get(f"/rest/people/{target_id}")
                curr_person = curr_res.get("data", {}).get("person") or {}
                curr_stage = (curr_person.get("lifecycleStage") or "Lead").strip().lower()
                curr_rank = stage_hierarchy.get(curr_stage, 1)
                new_rank = stage_hierarchy.get(clean_new.lower(), 1)
                # Guardrail: Prevent downgrading unless explicitly forced
                if new_rank < curr_rank and curr_rank != 5:
                    logger.info(
                        f"Stage regression prevented for {target_id}: '{curr_stage}' ({curr_rank}) -> '{clean_new}' ({new_rank}). Retaining current stage."
                    )
                else:
                    update_payload["lifecycleStage"] = clean_new
            except Exception as e:
                logger.warning(f"Could not check current stage for regression guardrail: {e}")
                update_payload["lifecycleStage"] = clean_new
        else:
            update_payload["lifecycleStage"] = clean_new
        
    if not update_payload:
        return {"ok": False, "tool": "update_contact", "error": "No fields specified to update."}
        
    await crm_patch(f"/rest/people/{target_id}", update_payload)
    return {
        "ok": True,
        "tool": "update_contact",
        "direct": True,
        "updated_id": target_id,
        "name": new_name or target_name,
        "fields_updated": list(update_payload.keys()),
        "message": f"Contact '{new_name or target_name}' updated successfully in Twenty CRM.",
    }


async def _direct_delete_contact(args: Dict[str, Any]) -> Dict[str, Any]:
    target_id = args.get("contact_id")
    target_name = args.get("name")
    
    if not target_id:
        if not target_name:
            return {"ok": False, "tool": "delete_contact", "error": "Either contact_id or name is required."}
        search_res = await _direct_search_contacts({"query": target_name})
        contacts = search_res.get("contacts", [])
        if not contacts:
            return {"ok": False, "tool": "delete_contact", "error": f"Contact '{target_name}' not found."}
        target_id = contacts[0]["id"]
        
    await crm_delete(f"/rest/people/{target_id}")
    return {
        "ok": True,
        "tool": "delete_contact",
        "direct": True,
        "deleted_id": target_id,
        "message": "Contact deleted successfully from Twenty CRM.",
    }


async def _direct_manage_notes(args: Dict[str, Any]) -> Dict[str, Any]:
    action = (args.get("action") or "list").lower()
    
    if action == "create":
        title = args.get("title") or "Note"
        content = args.get("content") or ""
        contact_id = args.get("contact_id")
        target_name = args.get("target_name")
        
        if not contact_id and target_name:
            search_res = await _direct_search_contacts({"query": target_name})
            contacts = search_res.get("contacts", [])
            if contacts:
                contact_id = contacts[0]["id"]
                
        note_res = await crm_post("/rest/notes", {
            "title": title,
            "bodyV2": {"markdown": content},
        })
        note_id = note_res.get("data", {}).get("createNote", {}).get("id")
        
        if note_id and contact_id:
            try:
                await crm_post("/rest/noteTargets", {
                    "noteId": note_id,
                    "targetPersonId": contact_id,
                })
            except Exception as e:
                logger.warning(f"Could not link noteTarget: {e}")
                
        return {
            "ok": True,
            "tool": "manage_notes",
            "direct": True,
            "id": note_id,
            "title": title,
            "message": "Note created and attached successfully.",
        }
        
    # List notes
    raw_res = await crm_get("/rest/notes?limit=50&order=createdAt:desc")
    notes_list = raw_res.get("data", {}).get("notes", [])
    mapped_notes = [
        {
            "id": n.get("id"),
            "title": n.get("title"),
            "body": (n.get("bodyV2") or {}).get("markdown"),
            "created_at": n.get("createdAt"),
        }
        for n in notes_list
    ]
    return {
        "ok": True,
        "tool": "manage_notes",
        "direct": True,
        "total": len(mapped_notes),
        "notes": mapped_notes,
    }


async def _direct_manage_tasks(args: Dict[str, Any]) -> Dict[str, Any]:
    action = (args.get("action") or "list").lower()
    
    if action == "create":
        title = args.get("title") or "Follow-up Task"
        priority = args.get("priority", "MEDIUM")
        contact_id = args.get("contact_id")
        
        task_res = await crm_post("/rest/tasks", {
            "title": title,
            "bodyV2": {"markdown": f"Priority: {priority}"},
            "status": "TODO",
        })
        task_id = task_res.get("data", {}).get("createTask", {}).get("id")
        
        if task_id and contact_id:
            try:
                await crm_post("/rest/taskTargets", {
                    "taskId": task_id,
                    "targetPersonId": contact_id,
                })
            except Exception as e:
                logger.warning(f"Could not link taskTarget: {e}")
                
        return {
            "ok": True,
            "tool": "manage_tasks",
            "direct": True,
            "id": task_id,
            "title": title,
            "message": "Task created successfully.",
        }
        
    if action == "delete":
        task_id = args.get("task_id")
        if not task_id:
            return {"ok": False, "tool": "manage_tasks", "error": "task_id is required for deletion."}
        await crm_delete(f"/rest/tasks/{task_id}")
        return {"ok": True, "tool": "manage_tasks", "direct": True, "deleted_id": task_id}
        
    raw_res = await crm_get("/rest/tasks?limit=50&order=createdAt:desc")
    tasks_list = raw_res.get("data", {}).get("tasks", [])
    mapped_tasks = [
        {
            "id": t.get("id"),
            "title": t.get("title"),
            "status": t.get("status"),
            "description": (t.get("bodyV2") or {}).get("markdown"),
            "due_date": t.get("dueAt"),
        }
        for t in tasks_list
    ]
    return {
        "ok": True,
        "tool": "manage_tasks",
        "direct": True,
        "total": len(mapped_tasks),
        "tasks": mapped_tasks,
    }


async def _direct_manage_opportunities(args: Dict[str, Any]) -> Dict[str, Any]:
    action = args.get("action", "list").lower()

    if action == "create":
        name = args.get("name")
        property_address = args.get("property_address") or name
        if not property_address:
            return {"ok": False, "tool": "manage_opportunities", "error": "Property address or name is required."}

        contact_id = args.get("contact_id")
        if not contact_id and args.get("target_name"):
            search_res = await _direct_search_contacts({"query": args["target_name"]})
            contacts = search_res.get("contacts", [])
            if contacts:
                contact_id = contacts[0]["id"]

        deal_type = args.get("deal_type", "Buyer")
        deal_stage = args.get("deal_stage", "OFFER_SUBMITTED" if deal_type == "Buyer" else "ACTIVE_LISTING")

        stage_mapping = {
            "SHOWING_PREP": "NEW",
            "ACTIVE_LISTING": "SCREENING",
            "OFFER_SUBMITTED": "PROPOSAL",
            "UNDER_CONTRACT": "MEETING",
            "INSPECTION_PHASE": "MEETING",
            "CLOSED_WON": "CUSTOMER",
            "TERMINATED": "NEW",
        }
        enum_stage = stage_mapping.get(deal_stage.upper(), "PROPOSAL")

        payload: Dict[str, Any] = {
            "name": f"[{deal_type}] {property_address}",
            "dealType": deal_type,
            "dealStage": deal_stage,
            "propertyAddress": property_address,
            "stage": enum_stage,
        }
        if contact_id:
            payload["pointOfContactId"] = contact_id
        if args.get("co_clients"):
            payload["coClients"] = args["co_clients"]
        if args.get("offer_date"):
            payload["offerDate"] = args["offer_date"]
        if args.get("mutual_acceptance_date"):
            payload["mutualAcceptanceDate"] = args["mutual_acceptance_date"]
        if args.get("inspection_date"):
            payload["inspectionDate"] = args["inspection_date"]
        if args.get("close_date"):
            payload["closeDate"] = args["close_date"]
        if args.get("escrow_company"):
            payload["escrowCompany"] = args["escrow_company"]
        if args.get("amount"):
            try:
                amt = float(args["amount"])
                payload["amount"] = {"amountMicros": int(amt * 1_000_000), "currencyCode": "USD"}
            except Exception:
                pass

        res = await crm_post("/rest/opportunities", payload)
        new_opp = res.get("data", {}).get("createOpportunity", {})
        opp_id = new_opp.get("id")

        # Promote contact stage to Pending if Under Contract or keep Active Client
        if contact_id:
            try:
                contact_stage = "Pending" if deal_stage in ("UNDER_CONTRACT", "INSPECTION_PHASE") else "Active Client"
                patch_payload = {
                    "primaryPropertyAddress": property_address,
                    "lifecycleStage": contact_stage,
                }
                if deal_type:
                    patch_payload["contactRole"] = deal_type
                await crm_patch(f"/rest/people/{contact_id}", patch_payload)
            except Exception as e:
                logger.warning(f"Could not update primary contact stage: {e}")

        return {
            "ok": True,
            "tool": "manage_opportunities",
            "action": "create",
            "id": opp_id,
            "name": payload["name"],
            "deal": new_opp,
            "message": f"Deal '{payload['name']}' created successfully in Twenty CRM.",
        }

    elif action == "update":
        opp_id = args.get("opportunity_id") or args.get("id")
        if not opp_id and args.get("name"):
            # Search by name
            raw_res = await crm_get("/rest/opportunities?limit=50")
            for o in raw_res.get("data", {}).get("opportunities", []):
                if args["name"].lower() in (o.get("name") or "").lower():
                    opp_id = o.get("id")
                    break

        if not opp_id:
            return {"ok": False, "tool": "manage_opportunities", "error": "Opportunity ID or name is required."}

        patch_payload: Dict[str, Any] = {}
        if args.get("property_address"):
            patch_payload["propertyAddress"] = args["property_address"]
        if args.get("deal_type"):
            patch_payload["dealType"] = args["deal_type"]
        if args.get("co_clients"):
            patch_payload["coClients"] = args["co_clients"]
        if args.get("offer_date"):
            patch_payload["offerDate"] = args["offer_date"]
        if args.get("mutual_acceptance_date"):
            patch_payload["mutualAcceptanceDate"] = args["mutual_acceptance_date"]
        if args.get("inspection_date"):
            patch_payload["inspectionDate"] = args["inspection_date"]
        if args.get("close_date"):
            patch_payload["closeDate"] = args["close_date"]
        if args.get("escrow_company"):
            patch_payload["escrowCompany"] = args["escrow_company"]
        if args.get("amount"):
            try:
                amt = float(args["amount"])
                patch_payload["amount"] = {"amountMicros": int(amt * 1_000_000), "currencyCode": "USD"}
            except Exception:
                pass

        deal_stage = args.get("deal_stage")
        if deal_stage:
            patch_payload["dealStage"] = deal_stage
            stage_mapping = {
                "SHOWING_PREP": "NEW",
                "ACTIVE_LISTING": "SCREENING",
                "OFFER_SUBMITTED": "PROPOSAL",
                "UNDER_CONTRACT": "MEETING",
                "INSPECTION_PHASE": "MEETING",
                "CLOSED_WON": "CUSTOMER",
                "TERMINATED": "NEW",
            }
            patch_payload["stage"] = stage_mapping.get(deal_stage.upper(), "PROPOSAL")

        res = await crm_patch(f"/rest/opportunities/{opp_id}", patch_payload)

        # Handle Fall-Through Protocol or Closing Synchronization
        if deal_stage:
            try:
                opp_details = await crm_get(f"/rest/opportunities/{opp_id}")
                opp_data = opp_details.get("data", {}).get("opportunity", {})
                poc_id = opp_data.get("pointOfContactId")
                dtype = opp_data.get("dealType") or "Buyer"
                addr = opp_data.get("propertyAddress") or opp_data.get("name")

                if poc_id:
                    if deal_stage == "TERMINATED":
                        # Revert contact back to Active Client
                        await crm_patch(f"/rest/people/{poc_id}", {"lifecycleStage": "Active Client"})
                        logger.info(f"Fall-through protocol: Reverted contact '{poc_id}' to 'Active Client'.")
                    elif deal_stage == "CLOSED_WON":
                        # Mark contact as Past Client with Buyer/Seller segmentation
                        past_type = "Buyer" if "buyer" in dtype.lower() else "Seller"
                        is_maint_tips = (past_type == "Buyer")
                        await crm_patch(
                            f"/rest/people/{poc_id}",
                            {
                                "lifecycleStage": "Past Client",
                                "pastClientType": past_type,
                                "homeMaintenanceTips": is_maint_tips,
                                "primaryPropertyAddress": addr,
                            },
                        )
                        logger.info(
                            f"Closing finalized: Contact '{poc_id}' marked as Past Client ({past_type}, maintenance_tips={is_maint_tips})."
                        )
                        # Auto-Trigger Buyer Post-Close Smart Plan via Marketing Agent
                        if past_type == "Buyer":
                            c_date = opp_data.get("closeDate") or datetime.utcnow().strftime("%Y-%m-%d")
                            is_new_c = bool("new construction" in (opp_data.get("name") or "").lower())
                            enroll_res = await _direct_enroll_buyer_post_close({
                                "contact_id": poc_id,
                                "close_date": c_date,
                                "property_address": addr,
                                "deal_id": opp_id,
                                "is_new_construction": is_new_c,
                            })
                            logger.info(f"Auto-enrolled buyer into Post-Close Smart Plan: {enroll_res}")
            except Exception as e:
                logger.warning(f"Error handling post-deal stage synchronization: {e}")

        return {
            "ok": True,
            "tool": "manage_opportunities",
            "action": "update",
            "id": opp_id,
            "updated_fields": list(patch_payload.keys()),
            "message": f"Deal '{opp_id}' updated successfully in Twenty CRM.",
        }

    # Default: List deals
    raw_res = await crm_get("/rest/opportunities?limit=50&order=createdAt:desc")
    opps_list = raw_res.get("data", {}).get("opportunities", [])
    mapped_opps = [
        {
            "id": o.get("id"),
            "name": o.get("name"),
            "contact_id": o.get("pointOfContactId"),
            "deal_type": o.get("dealType"),
            "deal_stage": o.get("dealStage"),
            "property_address": o.get("propertyAddress"),
            "co_clients": o.get("coClients"),
            "close_date": o.get("closeDate"),
            "offer_date": o.get("offerDate"),
            "inspection_date": o.get("inspectionDate"),
            "stage": o.get("stage"),
        }
        for o in opps_list
    ]
    return {
        "ok": True,
        "tool": "manage_opportunities",
        "action": "list",
        "direct": True,
        "total": len(mapped_opps),
        "opportunities": mapped_opps,
    }


# =============================================================================
# Brevo Marketing & Buyer Post-Close Automation Handlers
# =============================================================================

def _brevo_headers() -> Dict[str, str]:
    return {
        "api-key": BREVO_API_KEY,
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


async def _sync_contact_to_brevo_drip(
    email: str,
    first_name: str,
    last_name: str,
    property_address: str,
    close_date: str,
    is_new_construction: bool = False,
) -> Dict[str, Any]:
    url = f"{BREVO_BASE_URL}/v3/contacts"
    payload = {
        "email": email.strip().lower(),
        "attributes": {
            "FIRSTNAME": first_name or "",
            "LASTNAME": last_name or "",
            "ROLE": "Buyer",
            "CLOSE_DATE": close_date or "",
            "PROPERTY_ADDRESS": property_address or "",
            "IS_NEW_CONSTRUCTION": bool(is_new_construction),
        },
        "listIds": [BREVO_POST_CLOSE_LIST_ID],
        "updateEnabled": True,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=_brevo_headers(), json=payload)
            if resp.status_code in (200, 201, 204):
                return {"ok": True, "status": resp.status_code}
            logger.warning(f"Brevo contact sync returned {resp.status_code}: {resp.text}")
            return {"ok": False, "status": resp.status_code, "error": resp.text}
    except Exception as e:
        logger.error(f"Error syncing contact to Brevo: {e}")
        return {"ok": False, "error": str(e)}


async def _send_brevo_template(
    email: str,
    name: str,
    template_id: int,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    url = f"{BREVO_BASE_URL}/v3/smtp/email"
    payload = {
        "to": [{"email": email.strip().lower(), "name": name or "Valued Client"}],
        "templateId": int(template_id),
        "params": params or {},
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=_brevo_headers(), json=payload)
            if resp.status_code in (200, 201, 202):
                data = resp.json()
                return {"ok": True, "message_id": data.get("messageId"), "status": resp.status_code}
            return {"ok": False, "status": resp.status_code, "error": resp.text}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def _direct_enroll_buyer_post_close(args: Dict[str, Any]) -> Dict[str, Any]:
    contact_id = args.get("contact_id")
    email = args.get("email")
    name = args.get("name") or ""
    property_address = args.get("property_address") or ""
    deal_id = args.get("deal_id")
    is_new_construction = bool(args.get("is_new_construction", False))
    close_date = args.get("close_date") or datetime.utcnow().strftime("%Y-%m-%d")

    contact_data = None
    if contact_id:
        try:
            res = await crm_get(f"/rest/people/{contact_id}")
            contact_data = res.get("data", {}).get("person")
        except Exception:
            pass

    if not contact_data and email:
        search_res = await _direct_search_contacts({"query": email})
        contacts = search_res.get("contacts", [])
        if contacts:
            contact_data = contacts[0]
            contact_id = contact_data.get("id")

    if not contact_data and name:
        search_res = await _direct_search_contacts({"query": name})
        contacts = search_res.get("contacts", [])
        if contacts:
            contact_data = contacts[0]
            contact_id = contact_data.get("id")

    first_name = ""
    last_name = ""
    if contact_data:
        first_name = contact_data.get("firstName") or (contact_data.get("name", {}).get("firstName") if isinstance(contact_data.get("name"), dict) else "")
        last_name = contact_data.get("lastName") or (contact_data.get("name", {}).get("lastName") if isinstance(contact_data.get("name"), dict) else "")
        if not email:
            email = contact_data.get("email") or (contact_data.get("emails", {}).get("primaryEmail") if isinstance(contact_data.get("emails"), dict) else "")
        if not property_address:
            property_address = contact_data.get("primaryPropertyAddress") or contact_data.get("address") or ""
    elif name:
        parts = name.strip().split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

    if not email:
        return {"ok": False, "tool": "enroll_buyer_post_close", "error": "Client email is required to enroll in post-close smart plan."}

    full_name = f"{first_name} {last_name}".strip() or name or "Valued Client"
    cid = contact_id or email

    brevo_sync = await _sync_contact_to_brevo_drip(
        email=email,
        first_name=first_name,
        last_name=last_name,
        property_address=property_address,
        close_date=close_date,
        is_new_construction=is_new_construction,
    )

    drip_record = state_store.enroll_post_close_drip(
        contact_id=str(cid),
        email=email,
        first_name=first_name,
        last_name=last_name,
        property_address=property_address,
        close_date=close_date,
        is_new_construction=is_new_construction,
        deal_id=deal_id,
    )

    if contact_id:
        try:
            note_content = (
                f"### 🏡 Buyer Post-Close Smart Plan Activated\n"
                f"- **Closing Date:** {close_date}\n"
                f"- **Property:** {property_address or 'N/A'}\n"
                f"- **New Construction:** {'Yes (11-Month Warranty active)' if is_new_construction else 'No'}\n"
                f"- **Brevo List:** `Buyer Post-Close Drip` (ID: {BREVO_POST_CLOSE_LIST_ID})\n"
                f"- **Sequence:** 12 automated homeowner touchpoints across Days 1–360 (Day 280 tax statement skipped per custom branding)."
            )
            note_res = await crm_post("/rest/notes", {"title": "Buyer Post-Close Smart Plan Activated", "body": note_content})
            note_id = note_res.get("data", {}).get("createNote", {}).get("id")
            if note_id:
                await crm_post("/rest/noteTargets", {"noteId": note_id, "targetPersonId": contact_id})
        except Exception as e:
            logger.warning(f"Could not attach activation note in Twenty CRM: {e}")

    return {
        "ok": True,
        "tool": "enroll_buyer_post_close",
        "client_name": full_name,
        "email": email,
        "contact_id": contact_id,
        "close_date": close_date,
        "property_address": property_address,
        "is_new_construction": is_new_construction,
        "brevo_list_id": BREVO_POST_CLOSE_LIST_ID,
        "brevo_sync_status": brevo_sync.get("ok"),
        "message": f"Successfully enrolled {full_name} ({email}) into Buyer Post-Close Smart Plan starting from {close_date}.",
    }


async def _direct_list_post_close_drips(args: Dict[str, Any]) -> Dict[str, Any]:
    drips = state_store.get_active_post_close_drips()
    today = datetime.utcnow().date()
    formatted_drips = []

    for d in drips:
        try:
            c_date = datetime.strptime(d["close_date"], "%Y-%m-%d").date()
            days_elapsed = (today - c_date).days
        except Exception:
            days_elapsed = 0

        sent_ids = set(d.get("sent_templates", []))
        
        next_t = None
        for item in BUYER_POST_CLOSE_SCHEDULE:
            if item.get("new_construction_only") and not d.get("is_new_construction"):
                continue
            if item["template_id"] not in sent_ids:
                next_t = f"Day {item['day']} - {item['name']}"
                break

        full_name = f"{d.get('first_name', '')} {d.get('last_name', '')}".strip() or "Valued Client"
        formatted_drips.append({
            "id": d["id"],
            "contact_id": d["contact_id"],
            "name": full_name,
            "email": d["email"],
            "property_address": d.get("property_address") or "N/A",
            "close_date": d["close_date"],
            "days_elapsed": days_elapsed,
            "is_new_construction": d["is_new_construction"],
            "sent_count": len(sent_ids),
            "sent_templates": list(sent_ids),
            "next_template": next_t or "All 12 templates delivered",
        })

    return {
        "ok": True,
        "tool": "list_post_close_drips",
        "total": len(formatted_drips),
        "drips": formatted_drips,
    }


async def _direct_process_post_close_drips(args: Dict[str, Any]) -> Dict[str, Any]:
    force_cid = args.get("force_contact_id")
    drips = state_store.get_active_post_close_drips()
    if force_cid:
        drips = [d for d in drips if d["contact_id"] == force_cid or d["email"].lower() == force_cid.lower()]

    today = datetime.utcnow().date()
    sent_count = 0
    delivery_logs = []

    for d in drips:
        try:
            c_date = datetime.strptime(d["close_date"], "%Y-%m-%d").date()
            days_elapsed = (today - c_date).days
        except Exception:
            continue

        sent_ids = set(d.get("sent_templates", []))
        full_name = f"{d.get('first_name', '')} {d.get('last_name', '')}".strip() or "Valued Client"
        first_name = d.get("first_name") or (full_name.split(" ")[0] if full_name else "there")

        for item in BUYER_POST_CLOSE_SCHEDULE:
            day = item["day"]
            tid = item["template_id"]
            if item.get("new_construction_only") and not d.get("is_new_construction"):
                continue

            if days_elapsed >= day and tid not in sent_ids:
                send_res = await _send_brevo_template(
                    email=d["email"],
                    name=full_name,
                    template_id=tid,
                    params={"FIRSTNAME": first_name},
                )
                if send_res.get("ok"):
                    sent_count += 1
                    state_store.record_post_close_drip_send(
                        drip_id=d["id"],
                        contact_id=d["contact_id"],
                        template_id=tid,
                        day_offset=day,
                        status="SENT",
                        details=f"MessageID: {send_res.get('message_id')}",
                    )
                    sent_ids.add(tid)
                    delivery_logs.append(f"Sent Template {tid} ({item['name']}) to {d['email']} (Day {days_elapsed} since close)")

                    if d.get("contact_id") and not "@" in d.get("contact_id"):
                        try:
                            note_body = (
                                f"📬 **Buyer Post-Close Drip Email Delivered**\n"
                                f"- **Template:** `{item['name']}` (Brevo ID: `{tid}`)\n"
                                f"- **Schedule:** Day {day} (Delivered on day {days_elapsed})\n"
                                f"- **Message ID:** `{send_res.get('message_id')}`\n"
                                f"- **Sent Via:** Brevo SMTP API (lokesh@lokeshchanana.com)"
                            )
                            n_res = await crm_post("/rest/notes", {"title": f"Post-Close Email Sent: {item['name']}", "body": note_body})
                            nid = n_res.get("data", {}).get("createNote", {}).get("id")
                            if nid:
                                await crm_post("/rest/noteTargets", {"noteId": nid, "targetPersonId": d["contact_id"]})
                        except Exception as e:
                            logger.warning(f"Could not log email send note in Twenty CRM: {e}")
                else:
                    delivery_logs.append(f"Failed Template {tid} to {d['email']}: {send_res.get('error')}")

    return {
        "ok": True,
        "tool": "process_post_close_drips",
        "total_checked": len(drips),
        "sent_count": sent_count,
        "logs": delivery_logs,
        "summary": f"Delivered {sent_count} post-close drip email(s) across {len(drips)} client(s)." if sent_count else "All client drip schedules are currently up to date.",
    }


async def _execute_mailman_inbox(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Silas Drake connects to lokesh@lokeshchanana.com via n8n webhook or direct IMAP,
    fetching unread emails for Marcus Vance to route.
    """
    limit = args.get("limit") or 5
    filter_kw = args.get("filter_keyword")
    target_account = "lokesh@lokeshchanana.com"

    # 1. Try n8n Mailman triage webhook
    n8n_url = f"{N8N_BASE_URL}/webhook/mailman-inbox-triage"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                n8n_url,
                json={"account": target_account, "limit": limit, "filter": filter_kw or ""},
            )
            if resp.status_code == 200:
                data = resp.json()
                emails = data.get("emails", [])
                return {
                    "ok": True,
                    "tool": "mailman_read_inbox",
                    "account": target_account,
                    "status": "LIVE_FETCH",
                    "source": "n8n_gateway",
                    "emails": emails,
                    "total_found": len(emails),
                }
    except Exception as e:
        logger.debug(f"n8n mailman webhook not reachable: {e}")

    # 2. Try direct IMAP if App Password is set in environment
    imap_user = os.environ.get("MAIL_IMAP_USER", target_account)
    imap_pass = os.environ.get("MAIL_IMAP_PASSWORD", "")
    if imap_pass:
        try:
            import email
            import imaplib
            from email.header import decode_header
            from bs4 import BeautifulSoup
            from state_store import is_communication_processed, record_processed_communication

            mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            mail.login(imap_user, imap_pass.replace(" ", ""))
            mail.select("INBOX")
            status, messages = mail.search(None, "UNSEEN")
            mail_ids = messages[0].split()
            emails = []
            for mid in mail_ids[-limit:]:
                # Use BODY.PEEK[] so Silas reads without unintentionally clearing unread status
                res, msg_data = mail.fetch(mid, "(BODY.PEEK[])")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Headers
                        raw_sub = msg.get("Subject", "")
                        decoded_list = decode_header(raw_sub)
                        subject = ""
                        if decoded_list:
                            sub_bytes, enc = decoded_list[0]
                            subject = sub_bytes.decode(enc or "utf-8", errors="ignore") if isinstance(sub_bytes, bytes) else str(sub_bytes)
                        from_ = msg.get("From", "Unknown")
                        to_ = msg.get("To", "")
                        cc_ = msg.get("Cc", "")
                        date_ = msg.get("Date", "")
                        msg_id = msg.get("Message-ID", f"imap_{mid.decode()}")

                        # Body extraction (Plain text or HTML)
                        plain_text = ""
                        html_text = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                ctype = part.get_content_type()
                                if ctype == "text/plain" and not plain_text:
                                    pl = part.get_payload(decode=True)
                                    if pl:
                                        plain_text = pl.decode(errors="ignore")[:3000]
                                elif ctype == "text/html" and not html_text:
                                    pl = part.get_payload(decode=True)
                                    if pl:
                                        try:
                                            soup = BeautifulSoup(pl.decode(errors="ignore"), "html.parser")
                                            html_text = soup.get_text(separator=" ", strip=True)[:3000]
                                        except Exception:
                                            html_text = pl.decode(errors="ignore")[:3000]
                        else:
                            pl = msg.get_payload(decode=True)
                            if pl:
                                raw_p = pl.decode(errors="ignore")[:3000]
                                if "<html" in raw_p.lower():
                                    try:
                                        soup = BeautifulSoup(raw_p, "html.parser")
                                        html_text = soup.get_text(separator=" ", strip=True)
                                    except Exception:
                                        html_text = raw_p
                                else:
                                    plain_text = raw_p

                        body = plain_text or html_text or ""
                        clean_body = re.sub(r"\s+", " ", body).strip()
                        is_already_processed = is_communication_processed(msg_id)

                        emails.append(
                            {
                                "id": mid.decode(),
                                "message_id": msg_id,
                                "sender": from_,
                                "to": to_,
                                "cc": cc_,
                                "subject": subject,
                                "date": date_,
                                "snippet": clean_body[:500],
                                "full_text": clean_body,
                                "is_processed": is_already_processed,
                            }
                        )
            mail.close()
            mail.logout()
            return {
                "ok": True,
                "tool": "mailman_read_inbox",
                "account": target_account,
                "status": "LIVE_FETCH",
                "source": "direct_imap",
                "emails": emails,
                "total_unread": len(mail_ids),
            }
        except Exception as imap_err:
            logger.warning(f"Direct IMAP fetch error for {target_account}: {imap_err}")

    # 3. Ready in office, awaiting credential linkage
    return {
        "ok": True,
        "tool": "mailman_read_inbox",
        "account": target_account,
        "status": "AWAITING_WORKSPACE_CREDENTIAL",
        "message": f"Silas Drake (Mailman) is active and in office, but waiting for Google Workspace credentials to connect to {target_account}.",
        "emails": [],
    }


# =============================================================================
# Tool Execution Dispatcher
# =============================================================================

async def execute_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes a typed tool call against Casa-poki services with Direct Twenty CRM
    calls first, falling back to n8n if Twenty is temporarily offline.
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

    if name == "store_memory":
        agent_id = args.get("agent_id") or "system"
        content = args.get("content") or ""
        cat = args.get("category") or "domain_knowledge"
        res = vector_memory.store_memory(agent_id=agent_id, content=content, category=cat)
        res["duration_ms"] = int((time.time() - start_ts) * 1000)
        return res

    if name == "query_memory":
        q = args.get("query") or ""
        agent_id = args.get("agent_id")
        cat = args.get("category")
        top_k = args.get("top_k") or 3
        matches = vector_memory.query_memories(query=q, agent_id=agent_id, category=cat, top_k=top_k)
        return {
            "ok": True,
            "tool": name,
            "query": q,
            "matches": matches,
            "total_matches": len(matches),
            "duration_ms": int((time.time() - start_ts) * 1000),
        }

    # Bigcapital Financial Handlers
    if name == "finance_record_bill":
        res = await bigcapital_client.create_bill(
            vendor_name=args.get("vendor_name", ""),
            amount=args.get("amount", 0.0),
            due_date=args.get("due_date"),
            bill_date=args.get("bill_date"),
            category=args.get("category"),
            reference_no=args.get("reference_no"),
            note=args.get("note"),
        )
        res["duration_ms"] = int((time.time() - start_ts) * 1000)
        return res

    if name == "finance_record_payment":
        res = await bigcapital_client.record_bill_payment(
            bill_id=args.get("bill_id"),
            amount=args.get("amount"),
            payment_date=args.get("payment_date"),
            statement=args.get("statement"),
        )
        res["duration_ms"] = int((time.time() - start_ts) * 1000)
        return res

    if name == "finance_list_bills":
        res = await bigcapital_client.list_bills(
            status=args.get("status"),
            limit=args.get("limit", 20),
        )
        res["duration_ms"] = int((time.time() - start_ts) * 1000)
        return res

    if name == "finance_dashboard":
        res = await bigcapital_client.get_financial_dashboard()
        res["duration_ms"] = int((time.time() - start_ts) * 1000)
        return res

    if name == "finance_import_historical_bills":
        bills_data = args.get("bills", [])
        res = await bigcapital_client.import_historical_bills(bills_data)
        res["duration_ms"] = int((time.time() - start_ts) * 1000)
        return res

    # Mailman Inbox Handler
    if name == "mailman_read_inbox":
        res = await _execute_mailman_inbox(args)
        res["duration_ms"] = int((time.time() - start_ts) * 1000)
        return res

    # Direct Twenty CRM Handlers
    try:
        if name == "search_contacts":
            res = await _direct_search_contacts(args)
            res["duration_ms"] = int((time.time() - start_ts) * 1000)
            res["raw_payload_sent"] = args
            return res

        elif name == "create_contact":
            res = await _direct_create_contact(args)
            res["duration_ms"] = int((time.time() - start_ts) * 1000)
            res["raw_payload_sent"] = args
            return res

        elif name == "update_contact":
            res = await _direct_update_contact(args)
            res["duration_ms"] = int((time.time() - start_ts) * 1000)
            res["raw_payload_sent"] = args
            return res

        elif name == "delete_contact":
            res = await _direct_delete_contact(args)
            res["duration_ms"] = int((time.time() - start_ts) * 1000)
            res["raw_payload_sent"] = args
            return res

        elif name == "manage_notes":
            res = await _direct_manage_notes(args)
            res["duration_ms"] = int((time.time() - start_ts) * 1000)
            res["raw_payload_sent"] = args
            return res

        elif name == "manage_tasks":
            res = await _direct_manage_tasks(args)
            res["duration_ms"] = int((time.time() - start_ts) * 1000)
            res["raw_payload_sent"] = args
            return res

        elif name == "manage_opportunities":
            res = await _direct_manage_opportunities(args)
            res["duration_ms"] = int((time.time() - start_ts) * 1000)
            res["raw_payload_sent"] = args
            return res

        elif name == "enroll_buyer_post_close":
            res = await _direct_enroll_buyer_post_close(args)
            res["duration_ms"] = int((time.time() - start_ts) * 1000)
            res["raw_payload_sent"] = args
            return res

        elif name == "list_post_close_drips":
            res = await _direct_list_post_close_drips(args)
            res["duration_ms"] = int((time.time() - start_ts) * 1000)
            res["raw_payload_sent"] = args
            return res

        elif name == "process_post_close_drips":
            res = await _direct_process_post_close_drips(args)
            res["duration_ms"] = int((time.time() - start_ts) * 1000)
            res["raw_payload_sent"] = args
            return res

    except Exception as direct_err:
        logger.warning(f"Direct Twenty CRM call failed for '{name}': {direct_err}. Attempting n8n fallback...")
        # Fallback to n8n if direct Twenty call encountered network or unexpected error
        try:
            payload = {"tool": name, **args}
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(N8N_CRM_GATEWAY_URL, json=payload)
                resp.raise_for_status()
                data = resp.json()
                data["duration_ms"] = int((time.time() - start_ts) * 1000)
                data["fallback_used"] = True
                data["raw_payload_sent"] = args
                return data
        except Exception as fb_err:
            return {
                "ok": False,
                "tool": name,
                "error": f"Direct call failed: {direct_err}; Fallback failed: {fb_err}",
                "duration_ms": int((time.time() - start_ts) * 1000),
            }

    return {"ok": False, "tool": name, "error": f"Unsupported tool: {name}"}


def format_tool_result(tool_name: str, result: Dict[str, Any], args: Dict[str, Any]) -> str:
    """
    Formats the tool output into clean, structured Markdown for the user.
    """
    if not result.get("ok", True) and "error" in result:
        return f"⚠️ **Operation Error (`{tool_name}`):** {result.get('error')}"

    if tool_name == "search_contacts":
        contacts = result.get("contacts") or []
        filters = (result.get("raw_payload_sent") or {}).get("filters") or {}

        # Apply deterministic filters if present
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

        total = result.get("total_found", len(contacts))
        is_count = args.get("count_mode") or (result.get("raw_payload_sent") or {}).get("count_mode")

        filter_parts = []
        if args.get("can_email") is not None or filters.get("can_email") is not None:
            filter_parts.append(f"can_email={args.get('can_email') if args.get('can_email') is not None else filters.get('can_email')}")
        if args.get("phone_blank") or filters.get("phone_blank"):
            filter_parts.append("phone=blank")
        if args.get("email_present") or filters.get("email_present"):
            filter_parts.append("email=present")
        filter_str = f" [Filters: {', '.join(filter_parts)}]" if filter_parts else ""

        if total == 0:
            count_line = "### CRM Contact Count: **0 matching contacts found**\n" if is_count else ""
            return f"{count_line}### CRM Contact Search\nNo matching contacts found in Twenty CRM{filter_str}."

        req_limit = args.get("limit") or (result.get("raw_payload_sent") or {}).get("limit")
        if is_count:
            title = f"### CRM Contact Count: **{total} matching contacts found**{filter_str}"
        elif req_limit and len(contacts) < total:
            title = f"### CRM Contacts (Showing {len(contacts)} of {total} verified records{filter_str})"
        else:
            title = f"### CRM Contacts (`{total}` verified records{filter_str})"

        lines = [f"{title}\n"]
        for c in contacts[:50]:
            lines.append(
                f"- **{c.get('name')}** (ID: `{c.get('id')}`)\n"
                f"  - Phone: `{c.get('phone') or 'N/A'}` | Email: `{c.get('email') or 'N/A'}`\n"
                f"  - Role: `{c.get('role') or 'Customer'}` | Can Email: `{c.get('can_email')}` | Market: `{c.get('market') or 'N/A'}`"
            )
        if total > len(contacts) and not req_limit and total > 50:
            lines.append(f"\n*...and {total - len(contacts)} more records.*")
        return "\n".join(lines)

    if tool_name == "create_contact":
        return (
            f"### Contact Created in Twenty CRM (Direct REST)\n"
            f"- **Name:** **{result.get('name') or args.get('name')}**\n"
            f"- **ID:** `{result.get('id')}`\n"
            f"- **Status:** {result.get('message', 'Created successfully')}"
        )

    if tool_name == "update_contact":
        contact_name = result.get("name") or args.get("name") or args.get("new_name") or args.get("target_name")
        contact_id = result.get("updated_id") or args.get("contact_id")
        fields_updated = result.get("fields_updated") or []
        fields_line = f"- **Updated Fields:** `{', '.join(fields_updated)}`\n" if fields_updated else ""
        name_line = f"- **Contact:** **{contact_name}** (ID: `{contact_id}`)\n" if contact_name else f"- **Contact ID:** `{contact_id}`\n"
        return (
            f"### Contact Updated in Twenty CRM (Direct REST)\n"
            f"{name_line}"
            f"{fields_line}"
            f"- **Status:** {result.get('message', 'Updated successfully')}"
        )

    if tool_name == "delete_contact":
        return (
            f"### Contact Deleted from Twenty CRM (Direct REST)\n"
            f"- **Deleted ID:** `{result.get('deleted_id') or args.get('contact_id')}`\n"
            f"- **Status:** {result.get('message', 'Deleted successfully')}"
        )

    if tool_name == "manage_notes":
        notes = result.get("notes") or []
        if args.get("action") == "create" or "message" in result:
            return f"### CRM Note Added (Direct REST)\n- **Status:** {result.get('message', 'Note saved successfully')}"
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
            lines.append(f"- **{t.get('title')}** — Status: **{t.get('status')}**")
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

    if tool_name == "store_memory":
        return (
            f"### Vector Memory Saved\n"
            f"- **Memory ID:** `{result.get('memory_id')}`\n"
            f"- **Category:** `{result.get('category')}`\n"
            f"- **Content:** {result.get('content')}\n"
            f"- Vectorized with 384-dimensional embeddings in `agent_memory.db`."
        )

    if tool_name == "query_memory":
        matches = result.get("matches") or []
        if not matches:
            return f"### Vector Memory Search (`{result.get('query')}`)\nNo semantically similar memories found."
        lines = [f"### Vector Memory Recall (`{len(matches)}` matching entries for '{result.get('query')}')\n"]
        for m in matches:
            lines.append(
                f"- **[{m.get('agent_id').upper()} • {m.get('category')}]** (Similarity: {int(m.get('similarity', 0)*100)}%)\n"
                f"  {m.get('content')}"
            )
        return "\n".join(lines)

    if tool_name == "delegate_to_agent":
        return (
            f"### Task Delegated\n"
            f"- **Target Specialist:** `{args.get('target_agent')}`\n"
            f"- **Task:** {args.get('task_description')}\n"
            f"- **Result:** {result.get('response', 'Completed delegation')}"
        )

    if tool_name == "finance_record_bill":
        return (
            f"### 🧾 Bill Recorded in Bigcapital\n"
            f"- **Bill ID:** `#{result.get('bill_id')}`\n"
            f"- **Vendor:** **{result.get('vendor_name')}**\n"
            f"- **Amount:** **${result.get('amount', 0):,.2f} USD**\n"
            f"- **Bill Date:** `{result.get('bill_date')}` | **Due Date:** `{result.get('due_date')}`\n"
            f"- **Status:** `{result.get('status')}`\n"
            f"- **Portal:** [View in Bigcapital](https://finance.lokeshchanana.com)\n\n"
            f"{result.get('message', '')}"
        )

    if tool_name == "finance_record_payment":
        return (
            f"### 💳 Bill Payment Settled\n"
            f"- **Bill ID:** `#{result.get('bill_id')}`\n"
            f"- **Payment Amount:** **${result.get('amount', 0):,.2f} USD**\n"
            f"- **Payment ID:** `#{result.get('payment_id')}`\n"
            f"- **Portal:** [View in Bigcapital](https://finance.lokeshchanana.com)\n\n"
            f"{result.get('message', '')}"
        )

    if tool_name == "finance_list_bills":
        bills = result.get("bills", [])
        if not bills:
            return "### 🧾 Bigcapital Bills\nNo bills found matching query."
        lines = [f"### 🧾 Bigcapital Bills (`{len(bills)}` listed)\n"]
        lines.append("| ID | Vendor | Amount | Due Amount | Due Date | Status |")
        lines.append("|---|---|---|---|---|---|")
        for b in bills:
            v_name = b.get("vendor_name") or (b.get("vendor") or {}).get("display_name") or "Vendor"
            lines.append(
                f"| `#{b.get('id')}` | **{v_name}** | ${float(b.get('amount', 0)):,.2f} | "
                f"${float(b.get('due_amount', 0) or 0):,.2f} | `{b.get('due_date')}` | `{b.get('status', 'OPEN')}` |"
            )
        lines.append(f"\n[Open Bigcapital Portal](https://finance.lokeshchanana.com)")
        return "\n".join(lines)

    if tool_name == "finance_dashboard":
        return (
            f"### 📊 Financial Controller Dashboard\n"
            f"- **Portal:** [https://finance.lokeshchanana.com](https://finance.lokeshchanana.com)\n"
            f"- **Total Accounts Payable:** **${result.get('total_payable_usd', 0):,.2f} USD**\n"
            f"- **Open / Unpaid Bills:** `{result.get('total_open_bills', 0)}`\n"
            f"- **Urgent / Past Due:** `{result.get('urgent_due_bills', 0)}`\n"
            f"- **Settled Bills:** `{result.get('total_paid_bills', 0)}`\n"
        )

    if tool_name == "finance_import_historical_bills":
        return (
            f"### 📦 Historical Bills Ingestion Completed\n"
            f"- **Total Submitted:** `{result.get('total_submitted', 0)}`\n"
            f"- **Successfully Imported:** `{result.get('imported', 0)}`\n"
            f"- **Failed:** `{result.get('failed', 0)}`\n"
            f"- **Portal:** [View in Bigcapital](https://finance.lokeshchanana.com)"
        )

    if tool_name == "mailman_read_inbox":
        account = result.get("account", "lokesh@lokeshchanana.com")
        status = result.get("status")
        if status == "AWAITING_WORKSPACE_CREDENTIAL":
            return (
                f"### 📬 Silas Drake (Mail Courier & Dispatcher)\n"
                f"- **Mailbox Monitored:** `{account}`\n"
                f"- **Status:** In office and active, awaiting Google Workspace credential link.\n"
                f"- **Action:** Once Google Workspace credentials (IMAP App Password or OAuth) are linked, Silas Drake will fetch incoming emails and bring them directly to Marcus Vance for routing."
            )
        emails = result.get("emails") or []
        if not emails:
            return f"### 📬 Silas Drake (Mail Courier)\nChecked `{account}` inbox: No new unread emails found."
        lines = [f"### 📬 Silas Drake (Mail Courier) — Incoming Emails from `{account}` (`{len(emails)}` unread)\n"]
        for em in emails:
            lines.append(
                f"- **From:** `{em.get('sender')}`\n"
                f"  - **Subject:** {em.get('subject')}\n"
                f"  - **Date:** `{em.get('date')}`\n"
                f"  - **Preview:** {em.get('snippet') or 'N/A'}\n"
            )
        lines.append("\n*Silas Drake has delivered these emails to Marcus Vance for specialist triage.*")
        return "\n".join(lines)

    if tool_name == "enroll_buyer_post_close":
        return (
            f"### 🏡 Buyer Post-Close Smart Plan Activated\n"
            f"- **Client:** **{result.get('client_name')}** (`{result.get('email')}`)\n"
            f"- **Property Address:** `{result.get('property_address') or 'N/A'}`\n"
            f"- **Closing Date:** `{result.get('close_date')}`\n"
            f"- **New Construction:** `{'Yes (11-Month Warranty active)' if result.get('is_new_construction') else 'No'}`\n"
            f"- **Brevo List:** `Buyer Post-Close Drip` (ID: `{result.get('brevo_list_id')}`)\n"
            f"- **Sequence:** 12 touchpoints scheduled across Days 1–360 (Day 280 tax statement skipped per custom branding)\n"
            f"- **CRM Log:** Activation note attached to Twenty CRM contact timeline.\n\n"
            f"{result.get('message', '')}"
        )

    if tool_name == "list_post_close_drips":
        drips = result.get("drips", [])
        if not drips:
            return "### 🏡 Buyer Post-Close Smart Plan Enrollments\nNo active buyer drip enrollments found."
        lines = [f"### 🏡 Active Buyer Post-Close Drips (`{len(drips)}` clients enrolled)\n"]
        for d in drips:
            nc_tag = " [New Construction]" if d.get("is_new_construction") else ""
            lines.append(
                f"- **{d.get('name')}** (`{d.get('email')}`){nc_tag}\n"
                f"  - **Property:** `{d.get('property_address')}`\n"
                f"  - **Closed:** `{d.get('close_date')}` (`{d.get('days_elapsed')}` days ago)\n"
                f"  - **Progress:** {d.get('sent_count')} / 12 touchpoints sent\n"
                f"  - **Next Delivery:** `{d.get('next_template')}`\n"
            )
        return "\n".join(lines)

    if tool_name == "process_post_close_drips":
        logs = result.get("logs", [])
        lines = [
            f"### 📬 Buyer Post-Close Delivery Run Completed\n"
            f"- **Total Active Clients Checked:** `{result.get('total_checked', 0)}`\n"
            f"- **Emails Sent Today:** `{result.get('sent_count', 0)}`\n"
            f"- **Summary:** {result.get('summary', '')}\n"
        ]
        if logs:
            lines.append("**Activity Logs:**")
            for log_item in logs:
                lines.append(f"- {log_item}")
        return "\n".join(lines)

    return f"```json\n{json.dumps(result, indent=2)}\n```"
