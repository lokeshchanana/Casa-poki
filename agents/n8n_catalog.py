import json
import os
import sqlite3
from typing import Any, Dict, List, Optional
import httpx

N8N_DB_PATH = os.environ.get("N8N_DB_PATH", "/tank/n8n/database.sqlite")
N8N_BASE_URL = os.environ.get("N8N_BASE_URL", "http://192.168.1.240:5678")

# Enriched capability metadata for known workflows so the IT Agent knows exact schemas
KNOWN_WORKFLOW_CAPABILITIES: Dict[str, Dict[str, Any]] = {
    "crmRelaticleAssistant": {
        "capability_key": "crm_full_management",
        "domain": "crm",
        "summary": "Deterministic Twenty CRM API Gateway: search/create/update/delete contacts, manage companies, tasks, notes, opportunities/deals, and custom fields.",
        "webhook_url": f"{N8N_BASE_URL}/webhook/relaticle-crm-action",
        "method": "POST",
        "payload_type": "json_webhook",
        "input_schema": {
            "tool": "search_contacts | create_contact | update_contact | delete_contact | manage_companies | manage_tasks | manage_notes | manage_opportunities | manage_custom_fields",
            "action": "list | search | create | update | delete",
            "query": "Search keyword / contact name / email / phone / market / 'today' / 'all'",
            "id": "Record ID (optional if name is provided)",
            "name": "Contact or company or deal name",
            "phone_number": "Phone number",
            "email": "Email address",
            "can_email": "'True' or 'False'",
            "role": "Customer | Buyer | Seller | Real estate agent | Contractor | lender"
        },
        "keywords": [
            "crm", "contact", "contacts", "person", "people", "search", "find", "lookup",
            "phone", "email", "can_email", "permission", "create contact", "add contact",
            "update contact", "delete contact", "company", "companies", "task", "tasks",
            "note", "notes", "opportunity", "opportunities", "deal", "deals", "custom field",
            "twenty", "twenty crm", "relaticle", "client", "lead"
        ]
    },
    "wGB3XfRGWgbbvOGP": {
        "capability_key": "open_house_signin_intake",
        "domain": "crm",
        "summary": "Ingest Open House visitor sign-in data into Twenty CRM (creates/updates person, logs property note, and creates follow-up task).",
        "webhook_url": f"{N8N_BASE_URL}/webhook/open-house-sign-in",
        "method": "POST",
        "payload_type": "json_webhook",
        "input_schema": {
            "fullName": "Visitor full name (required)",
            "email": "Visitor email",
            "phone": "Visitor phone",
            "propertyAddress": "Open house property address",
            "workingWithAgent": "Yes/No",
            "timeline": "Buying timeline"
        },
        "keywords": [
            "open house", "sign in", "check in", "visitor intake", "register visitor"
        ]
    },
    "websiteContactWf01": {
        "capability_key": "website_contact_intake",
        "domain": "crm",
        "summary": "Process website contact form submissions into Twenty CRM contacts, notes, and follow-up tasks.",
        "webhook_url": f"{N8N_BASE_URL}/webhook/website-contact",
        "method": "POST",
        "payload_type": "json_webhook",
        "input_schema": {
            "name": "Sender full name (required)",
            "email": "Sender email",
            "phone": "Sender phone",
            "message": "Inquiry message",
            "intent": "buying / selling / general"
        },
        "keywords": [
            "website contact", "contact form", "website inquiry", "web lead"
        ]
    },
    "gbpEventPoster01": {
        "capability_key": "gbp_open_house_event_poster",
        "domain": "marketing",
        "summary": "Watches Google Calendar for Open Houses, researches property via Ollama, and posts event to Google Business Profile.",
        "webhook_url": None,
        "method": "TRIGGER",
        "payload_type": "calendar_trigger",
        "input_schema": {},
        "keywords": [
            "google business profile", "gbp", "google calendar", "open house event", "post event"
        ]
    },
    "twentyBrevoSyncWf01": {
        "capability_key": "twenty_brevo_contact_sync",
        "domain": "marketing",
        "summary": "Bi-directional synchronization between Twenty CRM and Brevo: pushes contacts segmented by roles into corresponding Brevo lists, and syncs Brevo unsubscribes/bounces back to Twenty CRM.",
        "webhook_url": f"{N8N_BASE_URL}/webhook/twenty-brevo-sync",
        "method": "POST",
        "payload_type": "json_webhook",
        "input_schema": {
            "trigger": "manual | webhook | schedule"
        },
        "keywords": [
            "brevo", "sendinblue", "newsletter", "email marketing", "sync contacts", "email list",
            "unsubscribe", "bounce", "brevo sync", "twenty brevo"
        ]
    }
}


def get_n8n_workflows() -> List[Dict[str, Any]]:
    """
    Read all workflows directly from the n8n SQLite database (zero LLM tokens)
    and enrich them with webhook paths, trigger types, tools, and status.
    """
    workflows: List[Dict[str, Any]] = []
    if not os.path.exists(N8N_DB_PATH):
        return workflows

    try:
        conn = sqlite3.connect(f"file:{N8N_DB_PATH}?mode=ro", uri=True)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, active, nodes, updatedAt FROM workflow_entity ORDER BY active DESC, updatedAt DESC"
        )
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        return [{"error": f"Failed to read n8n database: {str(e)}"}]

    for wf_id, name, active, nodes_raw, updated_at in rows:
        try:
            nodes = json.loads(nodes_raw) if nodes_raw else []
        except Exception:
            nodes = []

        # Ignore empty scratch workflows with 0 nodes
        if len(nodes) == 0 and not active:
            continue

        triggers = []
        webhooks = []
        tools = []
        node_names = []

        for n in nodes:
            n_name = n.get("name", "")
            n_type = n.get("type", "")
            params = n.get("parameters", {}) or {}
            node_names.append(n_name)

            if "webhook" in n_type.lower() and "respond" not in n_type.lower():
                path = params.get("path") or n.get("webhookId") or ""
                http_method = params.get("httpMethod", "POST")
                triggers.append({"type": "webhook", "path": path, "method": http_method})
                if path:
                    webhooks.append(f"{N8N_BASE_URL}/webhook/{path}")
            elif "chattrigger" in n_type.lower():
                wh_id = n.get("webhookId") or params.get("path") or ""
                triggers.append({"type": "chatTrigger", "webhookId": wh_id, "method": "POST"})
                if wh_id:
                    webhooks.append(f"{N8N_BASE_URL}/webhook/{wh_id}/chat")
            elif "trigger" in n_type.lower():
                triggers.append({"type": n_type.split(".")[-1], "name": n_name})

            if "tool" in n_type.lower():
                tools.append({
                    "name": params.get("name") or n_name,
                    "description": params.get("description") or ""
                })

        known = KNOWN_WORKFLOW_CAPABILITIES.get(wf_id, {})
        webhook_url = known.get("webhook_url") or (webhooks[0] if webhooks else None)

        workflows.append({
            "id": wf_id,
            "name": name,
            "active": bool(active),
            "updated_at": updated_at,
            "domain": known.get("domain", "general"),
            "capability_key": known.get("capability_key", wf_id),
            "summary": known.get(
                "summary",
                f"n8n workflow with {len(nodes)} nodes ({', '.join(node_names[:5])})"
            ),
            "triggers": triggers,
            "webhook_url": webhook_url,
            "payload_type": known.get(
                "payload_type",
                "n8n_chat" if any(t.get("type") == "chatTrigger" for t in triggers) else "json_webhook"
            ),
            "input_schema": known.get("input_schema", {}),
            "tools": tools,
            "node_count": len(nodes),
            "nodes": node_names,
        })

    return workflows


def inspect_latest_n8n_execution(workflow_id: str = "crmRelaticleAssistant") -> Dict[str, Any]:
    """
    Inspects the most recent execution of `workflow_id` in /tank/n8n/database.sqlite
    to determine:
      1. Which tool nodes were actually invoked (e.g. search_contacts, delete_contact)
      2. If status == 'error', the exact underlying NodeOperationError / ToolInputParsingException message.
    """
    if not os.path.exists(N8N_DB_PATH):
        return {"found": False}

    try:
        conn = sqlite3.connect(f"file:{N8N_DB_PATH}?mode=ro", uri=True)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT e.id, e.status, e.startedAt, e.stoppedAt, d.data
            FROM execution_entity e
            LEFT JOIN execution_data d ON e.id = d.executionId
            WHERE e.workflowId = ?
            ORDER BY e.id DESC
            LIMIT 1
            """,
            (workflow_id,),
        )
        row = cur.fetchone()
        conn.close()
        if not row:
            return {"found": False}

        exec_id, status, started_at, stopped_at, raw_data = row
        tools_invoked: List[str] = []
        error_details: List[str] = []

        known_tools = {
            "search_contacts",
            "create_contact",
            "update_contact",
            "delete_contact",
            "manage_companies",
            "manage_tasks",
            "manage_notes",
            "manage_opportunities",
            "manage_custom_fields",
        }

        if raw_data:
            try:
                parsed_list = json.loads(raw_data)
                for item in parsed_list:
                    if isinstance(item, str):
                        if item in known_tools and item not in tools_invoked:
                            tools_invoked.append(item)
                        elif any(
                            err_kw in item
                            for err_kw in [
                                "ToolInputParsingException",
                                "Received tool input did not match expected schema",
                                "Expected ",
                                "NodeOperationError",
                                "ECONNREFUSED",
                            ]
                        ):
                            if len(item) < 600 and item not in error_details:
                                error_details.append(item.strip())
            except Exception:
                pass

        return {
            "found": True,
            "execution_id": exec_id,
            "status": status,
            "started_at": started_at,
            "stopped_at": stopped_at,
            "tools_invoked": tools_invoked,
            "error_detail": " | ".join(error_details) if error_details else None,
        }
    except Exception as e:
        return {"found": False, "error": str(e)}


async def execute_n8n_workflow(
    workflow: Dict[str, Any],
    payload: Dict[str, Any],
    session_id: str = "it_agent_session"
) -> Dict[str, Any]:
    """
    Execute an active n8n workflow via its Webhook or ChatTrigger URL.
    """
    if not workflow.get("active"):
        return {
            "ok": False,
            "error_code": "WORKFLOW_INACTIVE",
            "message": f"Workflow '{workflow.get('name')}' ({workflow.get('id')}) exists in n8n but is currently INACTIVE."
        }

    webhook_url = workflow.get("webhook_url")
    if not webhook_url:
        return {
            "ok": False,
            "error_code": "NO_WEBHOOK_TRIGGER",
            "message": f"Workflow '{workflow.get('name')}' ({workflow.get('id')}) does not expose a callable HTTP webhook trigger."
        }

    payload_type = workflow.get("payload_type", "json_webhook")

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            if payload_type == "n8n_chat":
                chat_input = (
                    payload.get("chatInput")
                    or payload.get("query")
                    or payload.get("instruction")
                    or json.dumps(payload)
                )
                req_body = {
                    "action": "sendMessage",
                    "chatInput": chat_input,
                    "sessionId": session_id
                }
                resp = await client.post(webhook_url, json=req_body)
                if resp.status_code >= 400:
                    return {
                        "ok": False,
                        "error_code": f"HTTP_{resp.status_code}",
                        "message": f"n8n webhook returned status {resp.status_code}: {resp.text[:500]}"
                    }

                # Parse streaming or JSON lines output from n8n chat trigger
                raw_text = resp.text
                accumulated = []
                for line in raw_text.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if obj.get("type") == "item" and isinstance(obj.get("content"), str):
                            accumulated.append(obj["content"])
                        elif "output" in obj and isinstance(obj["output"], str):
                            accumulated.append(obj["output"])
                        elif obj.get("type") == "error":
                            return {
                                "ok": False,
                                "error_code": "N8N_WORKFLOW_ERROR",
                                "message": obj.get("message", "Unknown n8n chat workflow error")
                            }
                    except Exception:
                        if not line.startswith("{"):
                            accumulated.append(line)

                final_output = "".join(accumulated).strip() or raw_text.strip()
                return {
                    "ok": True,
                    "workflow_id": workflow.get("id"),
                    "workflow_name": workflow.get("name"),
                    "webhook_url": webhook_url,
                    "output": final_output
                }
            else:
                resp = await client.post(webhook_url, json=payload)
                if resp.status_code >= 400:
                    return {
                        "ok": False,
                        "error_code": f"HTTP_{resp.status_code}",
                        "message": f"n8n webhook returned status {resp.status_code}: {resp.text[:500]}"
                    }
                try:
                    data = resp.json()
                except Exception:
                    data = resp.text
                return {
                    "ok": True,
                    "workflow_id": workflow.get("id"),
                    "workflow_name": workflow.get("name"),
                    "webhook_url": webhook_url,
                    "output": data
                }
    except Exception as e:
        return {
            "ok": False,
            "error_code": "EXECUTION_EXCEPTION",
            "message": f"Error calling n8n workflow '{workflow.get('name')}': {str(e)}"
        }
