import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional
import httpx

from n8n_catalog import N8N_BASE_URL, get_n8n_workflows
import vector_memory
from bigcapital_tools import bigcapital_client

logger = logging.getLogger("agent_tools")

# Twenty CRM Direct Integration Config
TWENTY_BASE_URL = os.environ.get("TWENTY_BASE_URL", "http://192.168.1.240:8085")
TWENTY_API_KEY = os.environ.get("TWENTY_API_KEY", "")

# Fallback n8n gateway if needed
N8N_CRM_GATEWAY_URL = f"{N8N_BASE_URL}/webhook/relaticle-crm-action"


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
        }
        mapped_contacts.append(c_obj)
        
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
        clean_phone = re.sub(r"[^0-9+]", "", str(args["phone_number"]))
        payload["phones"] = {"primaryPhoneNumber": clean_phone}
        
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
    if args.get("phone_number"):
        clean_phone = re.sub(r"[^0-9+]", "", str(args["phone_number"]))
        update_payload["phones"] = {"primaryPhoneNumber": clean_phone}
    if args.get("email"):
        update_payload["emails"] = {"primaryEmail": args["email"].strip()}
    if args.get("can_email") is not None:
        can_bool = str(args["can_email"]).lower() in ("true", "1", "yes")
        update_payload["canEmail"] = can_bool
        
    if not update_payload:
        return {"ok": False, "tool": "update_contact", "error": "No fields specified to update."}
        
    await crm_patch(f"/rest/people/{target_id}", update_payload)
    return {
        "ok": True,
        "tool": "update_contact",
        "direct": True,
        "updated_id": target_id,
        "message": "Contact updated successfully in Twenty CRM.",
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
    raw_res = await crm_get("/rest/opportunities?limit=50&order=createdAt:desc")
    opps_list = raw_res.get("data", {}).get("opportunities", [])
    mapped_opps = [
        {
            "id": o.get("id"),
            "name": o.get("name"),
            "contact_id": o.get("pointOfContactId"),
            "stage": o.get("stage"),
            "close_date": o.get("closeDate"),
        }
        for o in opps_list
    ]
    return {
        "ok": True,
        "tool": "manage_opportunities",
        "direct": True,
        "total": len(mapped_opps),
        "opportunities": mapped_opps,
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

            mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            mail.login(imap_user, imap_pass.replace(" ", ""))
            mail.select("INBOX")
            status, messages = mail.search(None, "UNSEEN")
            mail_ids = messages[0].split()
            emails = []
            for mid in mail_ids[-limit:]:
                res, msg_data = mail.fetch(mid, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        raw_sub = msg.get("Subject", "")
                        decoded_list = decode_header(raw_sub)
                        subject = ""
                        if decoded_list:
                            sub_bytes, enc = decoded_list[0]
                            subject = sub_bytes.decode(enc or "utf-8", errors="ignore") if isinstance(sub_bytes, bytes) else str(sub_bytes)
                        from_ = msg.get("From", "Unknown")
                        date_ = msg.get("Date", "")
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    pl = part.get_payload(decode=True)
                                    if pl:
                                        body = pl.decode(errors="ignore")[:300]
                                    break
                        else:
                            pl = msg.get_payload(decode=True)
                            if pl:
                                body = pl.decode(errors="ignore")[:300]
                        clean_body = re.sub(r"\s+", " ", body).strip()
                        emails.append(
                            {
                                "id": mid.decode(),
                                "sender": from_,
                                "subject": subject,
                                "date": date_,
                                "snippet": clean_body,
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
            f"### Contact Created in Twenty CRM (Direct REST)\n"
            f"- **Name:** **{result.get('name') or args.get('name')}**\n"
            f"- **ID:** `{result.get('id')}`\n"
            f"- **Status:** {result.get('message', 'Created successfully')}"
        )

    if tool_name == "update_contact":
        return (
            f"### Contact Updated in Twenty CRM (Direct REST)\n"
            f"- **Name / ID:** `{result.get('updated_id') or args.get('contact_id') or args.get('target_name')}`\n"
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

    return f"```json\n{json.dumps(result, indent=2)}\n```"
