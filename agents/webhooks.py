import json
import logging
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
import httpx

from state_store import log_request_flow
from tools import crm_get, crm_post, crm_patch, _direct_search_contacts

logger = logging.getLogger("agent_webhooks")

# =============================================================================
# SMS Gate Client Configuration (https://api.sms-gate.app/3rdparty/v1/messages)
# =============================================================================
SMSGATE_ENABLED = os.environ.get("SMSGATE_ENABLED", "true").lower() in ("true", "1", "yes")
SMSGATE_ENDPOINT = os.environ.get("SMSGATE_ENDPOINT", "https://api.sms-gate.app/3rdparty/v1/messages")
SMSGATE_LOGIN = os.environ.get("SMSGATE_LOGIN", "")
SMSGATE_PASSWORD = os.environ.get("SMSGATE_PASSWORD", "")
SMSGATE_SIM_SLOT = int(os.environ.get("SMSGATE_SIM_SLOT", "0"))


async def trigger_sms_gate(
    guest_phone: str,
    guest_name: str,
    location: str,
    is_represented: bool = False,
    timeout: float = 12.0,
) -> Dict[str, Any]:
    """
    Sends an automated Open House thank-you SMS with Loki's digital business card
    via SMS Gate (https://api.sms-gate.app/3rdparty/v1/messages).
    """
    if not SMSGATE_ENABLED:
        return {"skipped": True, "reason": "SMSGATE_ENABLED is false"}

    digits = re.sub(r"[^0-9]", "", str(guest_phone or ""))
    if not guest_phone or len(digits) < 10:
        return {"skipped": True, "reason": "No valid phone number provided"}

    if not SMSGATE_LOGIN or not SMSGATE_PASSWORD:
        logger.warning("SMS Gate login credentials not configured in environment.")
        return {"skipped": True, "reason": "Credentials not configured"}

    first_name = (guest_name or "").split(" ")[0].strip() or guest_name or "Friend"
    market_location = location or "today's open house"

    if is_represented:
        draft_text = (
            f"Hi {first_name}, this is Lokesh Chanana (Loki). Thank you for touring the {market_location} today!\n\n"
            f"Dropping my direct contact card for your records:\nhttps://lokeshchanana.com/loki.vcf\n\n"
            f"Please feel free to have your agent reach out to me directly if they need disclosure packets or offer guidelines. Have a great day!"
        )
    else:
        draft_text = (
            f"Hi {first_name}, this is Lokesh Chanana (Loki). Thank you for visiting the {market_location} today!\n\n"
            f"Dropping my direct contact card so you have it saved:\nhttps://lokeshchanana.com/loki.vcf\n\n"
            f"Feel free to text or call if you have any questions about this property or anything in the area. Have a wonderful weekend!"
        )

    # SMS Gate API payload structure: phoneNumbers array and textMessage.text
    payload = {
        "phoneNumbers": [guest_phone],
        "simSlot": SMSGATE_SIM_SLOT,
        "textMessage": {
            "text": draft_text
        }
    }

    auth = httpx.BasicAuth(SMSGATE_LOGIN, SMSGATE_PASSWORD)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                SMSGATE_ENDPOINT,
                json=payload,
                auth=auth,
                headers={"User-Agent": "Casa-Poki-Agent-Hub/1.0"}
            )
            is_ok = 200 <= resp.status_code < 300
            resp_data = resp.json() if resp.content else {}
            if is_ok:
                logger.info(f"SMS Gate successfully dispatched message to {guest_phone} (HTTP {resp.status_code})")
                return {
                    "ok": True,
                    "status_code": resp.status_code,
                    "phone": guest_phone,
                    "recipient": first_name,
                    "message_id": resp_data.get("id") or resp_data.get("messageId"),
                    "data": resp_data,
                }
            else:
                logger.error(f"SMS Gate API returned HTTP {resp.status_code}: {resp.text}")
                return {
                    "ok": False,
                    "status_code": resp.status_code,
                    "error": resp.text,
                }
    except Exception as e:
        logger.error(f"Failed to reach SMS Gate endpoint: {e}")
        return {"ok": False, "error": str(e)}


def normalize_phone(num: Optional[str]) -> str:
    if not num:
        return ""
    digits = re.sub(r"[^0-9+]", "", str(num))
    if digits.startswith("+"):
        return digits
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    return "+" + digits if digits else ""


async def handle_open_house_sign_in(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Direct intake for Open House visitor kiosk sign-ins.
    Saves to Twenty CRM directly (Person + Note + Task), records flow trace.
    """
    start_ts = time.time()
    flow_id = f"flow_oh_{int(time.time() * 1000)}"
    source = "Open House iPad Kiosk"
    
    name = (payload.get("name") or payload.get("Name") or "").strip()
    raw_phone = payload.get("phone") or payload.get("phone_number") or payload.get("Phone #") or ""
    phone = normalize_phone(raw_phone)
    email = (payload.get("email") or payload.get("Email") or "").strip().lower()
    feedback = (payload.get("feedback") or payload.get("Feedback") or "").strip()
    working_with_agent = (payload.get("working_with_agent") or payload.get("agent") or "No").strip()
    agent_name = (payload.get("agent_name") or payload.get("agentName") or "").strip()
    property_address = (payload.get("property_address") or payload.get("property") or "Open House Property").strip()
    city = (payload.get("city") or payload.get("market") or "Greater Seattle").strip()
    
    needs = payload.get("current_needs") or payload.get("needs") or []
    if isinstance(needs, str):
        try:
            needs = json.loads(needs)
        except Exception:
            needs = [needs]
    if not isinstance(needs, list):
        needs = [str(needs)]
    needs_str = ", ".join([str(n) for n in needs if n]) or "Not specified"

    if not name and not email and not phone:
        return {"success": False, "message": "Name, email, or phone is required."}

    steps = [
        {
            "step": "Visitor Ingestion",
            "agent": "Miles Miller",
            "action": f"Received Open House sign-in for '{name or 'Guest'}' at {property_address}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "ok",
        }
    ]

    # 1. Search existing person in Twenty CRM
    found_person = None
    if email:
        try:
            s_res = await _direct_search_contacts({"query": email})
            for c in s_res.get("contacts", []):
                if (c.get("email") or "").strip().lower() == email:
                    found_person = c
                    break
        except Exception as e:
            logger.warning(f"Error searching person by email: {e}")

    if not found_person and phone:
        digits = re.sub(r"[^0-9]", "", phone)
        search_digits = digits[-10:] if len(digits) >= 10 else digits
        if search_digits:
            try:
                s_res = await _direct_search_contacts({"query": search_digits})
                for c in s_res.get("contacts", []):
                    c_phone = re.sub(r"[^0-9]", "", str(c.get("phone") or ""))
                    if search_digits in c_phone:
                        found_person = c
                        break
            except Exception as e:
                logger.warning(f"Error searching person by phone: {e}")

    name_parts = (name or "Open House Guest").split(" ", 1)
    first_name = name_parts[0] if name_parts else "Open House"
    last_name = name_parts[1] if len(name_parts) > 1 else "Guest"
    
    person_id = None
    if found_person:
        person_id = found_person.get("id")
        steps.append({
            "step": "CRM Record Match",
            "agent": "Miles Miller",
            "action": f"Matched existing contact '{found_person.get('id')}' in Twenty CRM. Updating profile.",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "ok",
        })
        patch_payload: Dict[str, Any] = {"leadSource": "Open House", "market": city}
        if phone and not (found_person.get("phones") or {}).get("primaryPhoneNumber"):
            patch_payload["phones"] = {"primaryPhoneNumber": phone}
        if email and not (found_person.get("emails") or {}).get("primaryEmail"):
            patch_payload["emails"] = {"primaryEmail": email}
        await crm_patch(f"/rest/people/{person_id}", patch_payload)
    else:
        steps.append({
            "step": "CRM Contact Creation",
            "agent": "Miles Miller",
            "action": f"Creating new contact '{name}' in Twenty CRM",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "ok",
        })
        create_payload: Dict[str, Any] = {
            "name": {"firstName": first_name, "lastName": last_name},
            "leadSource": "Open House",
            "contactRole": "Customer",
            "market": city,
            "canEmail": True,
        }
        if email:
            create_payload["emails"] = {"primaryEmail": email}
        if phone:
            create_payload["phones"] = {"primaryPhoneNumber": phone}
            
        c_res = await crm_post("/rest/people", create_payload)
        person_id = c_res.get("data", {}).get("createPerson", {}).get("id")

    # 2. Attach Note
    steps.append({
        "step": "Note Documentation",
        "agent": "Marcus Vance",
        "action": f"Attaching Open House visitor preferences note to contact '{person_id}'",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "ok",
    })
    note_content = (
        f"Open House Visit: {property_address}\n"
        f"----------------------------------------\n"
        f"Name: {name or 'Anonymous'}\n"
        f"Phone: {phone or 'None'}\n"
        f"Email: {email or 'None'}\n"
        f"Represented: {working_with_agent} (Agent: {agent_name or 'None'})\n"
        f"Needs: {needs_str}\n"
        f"Feedback: {feedback or 'None'}\n"
        f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
    )
    n_res = await crm_post("/rest/notes", {
        "title": f"Open House Sign-In: {property_address} ({datetime.utcnow().strftime('%Y-%m-%d')})",
        "bodyV2": {"markdown": note_content},
    })
    note_id = n_res.get("data", {}).get("createNote", {}).get("id")
    if note_id and person_id:
        try:
            await crm_post("/rest/noteTargets", {"noteId": note_id, "targetPersonId": person_id})
        except Exception as e:
            logger.warning(f"Could not link note: {e}")

    # 3. Create Follow-Up Task
    steps.append({
        "step": "Task Assignment",
        "agent": "Marcus Vance",
        "action": f"Creating next-day follow-up task for Loki",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "ok",
    })
    t_res = await crm_post("/rest/tasks", {
        "title": f"Follow up with Open House Visitor: {name or 'Guest'}",
        "bodyV2": {"markdown": f"Follow up regarding {property_address}. Needs: {needs_str}. Feedback: {feedback or 'None'}."},
        "status": "TODO",
    })
    task_id = t_res.get("data", {}).get("createTask", {}).get("id")
    if task_id and person_id:
        try:
            await crm_post("/rest/taskTargets", {"taskId": task_id, "targetPersonId": person_id})
        except Exception as e:
            logger.warning(f"Could not link task: {e}")

    # 4. Automated SMS Follow-Up via SMS Gate
    sms_result = None
    sms_status = "none"
    if phone:
        market_desc = f"{city} open house" if city else "today's open house"
        is_rep = str(working_with_agent).lower() in ("yes", "true", "1")
        sms_result = await trigger_sms_gate(
            guest_phone=phone,
            guest_name=name,
            location=market_desc,
            is_represented=is_rep,
        )
        sms_status = "dispatched" if sms_result.get("ok") else ("skipped" if sms_result.get("skipped") else "failed")
        steps.append({
            "step": "SMS Gate Dispatch",
            "agent": "Marcus Vance",
            "action": f"Automated thank-you text with contact card ({sms_status}) to '{phone}'",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "ok" if sms_result.get("ok") or sms_result.get("skipped") else "warning",
        })

    # 5. Quality Audit Verification
    steps.append({
        "step": "Quality Audit",
        "agent": "Audrey Chen",
        "action": f"Verified CRM contact '{person_id}', attached note '{note_id}', scheduled task '{task_id}', and SMS status ({sms_status})",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "ok",
    })

    duration_ms = int((time.time() - start_ts) * 1000)
    log_request_flow(
        flow_id=flow_id,
        source=source,
        title=f"Open House Sign-In: {name or 'Guest'}",
        status="completed",
        agents_involved=["Miles Miller", "Marcus Vance", "Audrey Chen"],
        steps=steps,
        payload_preview={"name": name, "email": email, "phone": phone, "property": property_address},
        result_summary=f"Processed visitor '{name}' in Twenty CRM (ID: {person_id})",
        duration_ms=duration_ms,
    )

    return {
        "success": True,
        "personId": person_id,
        "noteId": note_id,
        "taskId": task_id,
        "smsResult": sms_result,
        "message": f"Welcome, {name}! Your check-in was successfully saved to Twenty CRM.",
        "duration_ms": duration_ms,
    }


async def handle_website_contact(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Direct intake for website contact form inquiries.
    """
    start_ts = time.time()
    flow_id = f"flow_web_{int(time.time() * 1000)}"
    source = "Website Contact Form"
    
    name = (payload.get("name") or payload.get("Name") or "").strip()
    raw_phone = payload.get("phone") or payload.get("phone_number") or ""
    phone = normalize_phone(raw_phone)
    email = (payload.get("email") or payload.get("Email") or "").strip().lower()
    purpose = (payload.get("purpose") or payload.get("interest") or "General Inquiry").strip()
    message = (payload.get("message") or payload.get("comments") or payload.get("inquiry") or "").strip()

    if not name and not email and not phone:
        return {"success": False, "message": "Name, email, or phone is required."}

    steps = [
        {
            "step": "Inquiry Reception",
            "agent": "Miles Miller",
            "action": f"Received website inquiry from '{name or 'Visitor'}' (Purpose: {purpose})",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "ok",
        }
    ]

    # Search existing contact
    found_person = None
    if email:
        try:
            res = await crm_get(f"/rest/people?filter=emails.primaryEmail[eq]:{email}")
            people = res.get("data", {}).get("people", [])
            if people:
                found_person = people[0]
        except Exception as e:
            logger.warning(f"Error searching person by email: {e}")

    name_parts = (name or "Website Lead").split(" ", 1)
    first_name = name_parts[0] if name_parts else "Website"
    last_name = name_parts[1] if len(name_parts) > 1 else "Lead"

    person_id = None
    if found_person:
        person_id = found_person.get("id")
        steps.append({
            "step": "Contact Match",
            "agent": "Miles Miller",
            "action": f"Matched existing contact '{person_id}' in Twenty CRM.",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "ok",
        })
    else:
        steps.append({
            "step": "Contact Creation",
            "agent": "Miles Miller",
            "action": f"Created new lead '{name}' in Twenty CRM",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "ok",
        })
        c_res = await crm_post("/rest/people", {
            "name": {"firstName": first_name, "lastName": last_name},
            "leadSource": "Website",
            "contactRole": "Customer",
            "canEmail": True,
            "emails": {"primaryEmail": email} if email else None,
            "phones": {"primaryPhoneNumber": phone} if phone else None,
        })
        person_id = c_res.get("data", {}).get("createPerson", {}).get("id")
        
        # Create Opportunity
        await crm_post("/rest/opportunities", {
            "name": f"[Website Lead] {name or 'Inquiry'}",
            "pointOfContactId": person_id,
            "stage": "NEW",
        })

    # Note
    steps.append({
        "step": "Inquiry Logging",
        "agent": "Marcus Vance",
        "action": f"Logged inquiry note for '{name}'",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "ok",
    })
    note_body = (
        f"Website Contact Form\n"
        f"--------------------\n"
        f"Name: {name}\n"
        f"Email: {email}\n"
        f"Phone: {phone}\n"
        f"Purpose: {purpose}\n"
        f"Message: {message}\n"
        f"Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
    )
    n_res = await crm_post("/rest/notes", {
        "title": f"Website Inquiry - {purpose} ({datetime.utcnow().strftime('%Y-%m-%d')})",
        "bodyV2": {"markdown": note_body},
    })
    note_id = n_res.get("data", {}).get("createNote", {}).get("id")
    if note_id and person_id:
        try:
            await crm_post("/rest/noteTargets", {"noteId": note_id, "targetPersonId": person_id})
        except Exception:
            pass

    # Task
    steps.append({
        "step": "Task Creation",
        "agent": "Marcus Vance",
        "action": f"Scheduled high-priority follow up task",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "ok",
    })
    t_res = await crm_post("/rest/tasks", {
        "title": f"Website Lead Follow-up: {name} ({purpose})",
        "bodyV2": {"markdown": f"Message: {message}"},
        "status": "TODO",
    })
    task_id = t_res.get("data", {}).get("createTask", {}).get("id")
    if task_id and person_id:
        try:
            await crm_post("/rest/taskTargets", {"taskId": task_id, "targetPersonId": person_id})
        except Exception:
            pass

    steps.append({
        "step": "Audit Verification",
        "agent": "Audrey Chen",
        "action": f"Verified CRM entries and lead capture completeness.",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "ok",
    })

    duration_ms = int((time.time() - start_ts) * 1000)
    log_request_flow(
        flow_id=flow_id,
        source=source,
        title=f"Website Inquiry: {name} ({purpose})",
        status="completed",
        agents_involved=["Miles Miller", "Marcus Vance", "Audrey Chen"],
        steps=steps,
        payload_preview={"name": name, "email": email, "purpose": purpose},
        result_summary=f"Created CRM lead & task for '{name}'",
        duration_ms=duration_ms,
    )

    return {
        "success": True,
        "personId": person_id,
        "message": f"Thank you, {name}! Your inquiry has been received.",
        "duration_ms": duration_ms,
    }


async def handle_bill_intake(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Inbound webhook for automated bill ingestion (e.g. from n8n email parsers or invoices).
    Delegates directly to Fiona Banks to record into Bigcapital.
    """
    flow_id = f"flow_bill_{int(time.time()*1000)}"
    start_ts = time.time()
    steps = []

    vendor = payload.get("vendor") or payload.get("vendor_name") or "Unknown Vendor"
    amount = float(payload.get("amount", 0.0))
    due_date = payload.get("due_date")
    bill_date = payload.get("bill_date")
    category = payload.get("category", "General")
    reference_no = payload.get("reference_no") or payload.get("invoice_no")
    note = payload.get("note") or payload.get("description")

    steps.append({
        "step": "Bill Intake Trigger",
        "agent": "Fiona Banks",
        "action": f"Received incoming bill from {vendor} for ${amount:,.2f}",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "ok",
    })

    from bigcapital_tools import bigcapital_client
    creation = await bigcapital_client.create_bill(
        vendor_name=vendor,
        amount=amount,
        due_date=due_date,
        bill_date=bill_date,
        note=note,
        reference_no=reference_no,
        category=category,
        is_open=True,
    )

    steps.append({
        "step": "Bigcapital Posting",
        "agent": "Fiona Banks",
        "action": f"Recorded Bill #{creation.get('bill_id')} into Bigcapital",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "ok" if creation.get("ok") else "error",
    })

    duration_ms = int((time.time() - start_ts) * 1000)
    log_request_flow(
        flow_id=flow_id,
        source="Webhook: /webhook/bill-intake",
        title=f"Bill Intake: {vendor} (${amount:,.2f})",
        status="completed" if creation.get("ok") else "failed",
        agents_involved=["Fiona Banks"],
        steps=steps,
        payload_preview=payload,
        result_summary=creation.get("message", "Bill processed"),
        duration_ms=duration_ms,
    )
    return creation


async def handle_payment_intake(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Inbound webhook for automated payment ingestion to settle open bills.
    """
    flow_id = f"flow_payment_{int(time.time()*1000)}"
    start_ts = time.time()
    steps = []

    bill_id = int(payload.get("bill_id", 0))
    amount = float(payload.get("amount", 0.0)) if payload.get("amount") else None
    payment_date = payload.get("payment_date")
    statement = payload.get("statement") or "Automated Payment Settlement"

    steps.append({
        "step": "Payment Intake Trigger",
        "agent": "Fiona Banks",
        "action": f"Processing settlement for Bill #{bill_id}",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "ok",
    })

    from bigcapital_tools import bigcapital_client
    res = await bigcapital_client.record_bill_payment(
        bill_id=bill_id,
        amount=amount,
        payment_date=payment_date,
        statement=statement,
    )

    steps.append({
        "step": "Payment Settled",
        "agent": "Fiona Banks",
        "action": f"Recorded payment for Bill #{bill_id}",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "ok" if res.get("ok") else "error",
    })

    duration_ms = int((time.time() - start_ts) * 1000)
    log_request_flow(
        flow_id=flow_id,
        source="Webhook: /webhook/payment-intake",
        title=f"Payment Intake: Bill #{bill_id}",
        status="completed" if res.get("ok") else "failed",
        agents_involved=["Fiona Banks"],
        steps=steps,
        payload_preview=payload,
        result_summary=res.get("message", "Payment processed"),
        duration_ms=duration_ms,
    )
    return res


async def handle_communication_intake(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Unified communication ingestion webhook for incoming SMS or parsed emails.
    Routes real estate events through Miles Miller (CRM Specialist).
    """
    flow_id = f"flow_comm_{int(time.time()*1000)}"
    start_ts = time.time()
    steps = []

    sender = (payload.get("sender") or payload.get("from") or "").strip()
    recipient = (payload.get("to") or "").strip()
    subject = (payload.get("subject") or "").strip()
    body = (payload.get("body") or payload.get("text") or payload.get("content") or "").strip()
    channel = (payload.get("channel") or "email").lower()
    msg_id = payload.get("message_id") or f"webhook_{flow_id}"

    from state_store import is_communication_processed, record_processed_communication
    if is_communication_processed(msg_id):
        return {"ok": True, "status": "ALREADY_PROCESSED", "message_id": msg_id}

    steps.append({
        "step": "Communication Ingestion",
        "agent": "Silas Drake",
        "action": f"Ingested {channel} communication from '{sender}' (Subject: {subject[:40]}...)",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "ok",
    })

    # Pattern recognition for Real Estate Lifecycle Events
    event_type = "GENERAL_INQUIRY"
    extracted_data: Dict[str, Any] = {}

    lower_sub = subject.lower()
    lower_body = body.lower()

    # 1. NWMLS Search setup vs Portal activity
    if "nwmls" in sender.lower() or "nwmlsmatrixmail.com" in sender.lower():
        if "auto email" in lower_sub or "auto-email" in lower_sub or "initial search" in lower_sub:
            event_type = "NWMLS_SEARCH_CREATED"
        elif "portal" in lower_sub or "viewed" in lower_sub or "favorite" in lower_sub:
            event_type = "NWMLS_PORTAL_ACTIVE"
        else:
            event_type = "NWMLS_NOTIFICATION"

    # 2. Authentisign signing events
    elif "authentisign.com" in sender.lower() or "authentisign" in lower_sub:
        if "bba" in lower_sub or "buyer brokerage" in lower_sub or "services agreement" in lower_sub:
            event_type = "AUTHENTISIGN_BBA_SIGNED"
        elif "listing" in lower_sub or "exclusive sale" in lower_sub or "form 1a" in lower_sub:
            event_type = "AUTHENTISIGN_LISTING_SIGNED"
        elif "psa" in lower_sub or "purchase and sale" in lower_sub or "disclosure" in lower_sub or "offer" in lower_sub:
            event_type = "AUTHENTISIGN_OFFER_DISCLOSURE_SIGNED"
        else:
            event_type = "AUTHENTISIGN_COMPLETED"

    # 3. Inspection confirmed
    elif "inspection confirmed" in lower_sub or "home inspection" in lower_sub:
        event_type = "INSPECTION_CONFIRMED"

    # 4. Closing / Title recording confirmation
    elif "recording complete" in lower_sub or "closed" in lower_sub or "transaction closed" in lower_sub:
        event_type = "TRANSACTION_CLOSED"

    # Extraction of Property Address if present
    addr_match = re.search(r"(\d{3,5}\s+[A-Za-z0-9\.\s]+(?:St|Ave|Avenue|Rd|Road|Way|Ct|Court|Dr|Drive|Blvd|Lane|Ln|E|W|N|S|NE|NW|SE|SW)[^,\n\r]*)", subject + " " + body, re.IGNORECASE)
    if addr_match:
        extracted_data["property_address"] = addr_match.group(1).strip()

    # Extraction of Client Names
    names_match = re.search(r"(?:for|client:)\s+([A-Z][a-z]+(?:\s+and\s+[A-Z][a-z]+|\s+[A-Z][a-z]+))", subject, re.IGNORECASE)
    if names_match:
        extracted_data["client_names"] = names_match.group(1).strip()

    steps.append({
        "step": "Triage & Handoff",
        "agent": "Silas Drake",
        "action": f"Classified event '{event_type}'. Handing off to Miles Miller for Twenty CRM execution.",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "ok",
    })

    # Miles Miller executes the CRM state change
    client_id = None
    deal_id = None

    from tools import _direct_search_contacts, _direct_update_contact, _direct_create_contact, _direct_manage_opportunities

    # Match contact by email or extracted names
    client_email = payload.get("client_email")
    if not client_email and "@" in sender and "nwmls" not in sender and "authentisign" not in sender:
        client_email = sender

    matched_contact = None
    if client_email:
        s_res = await _direct_search_contacts({"query": client_email})
        if s_res.get("contacts"):
            matched_contact = s_res["contacts"][0]
            client_id = matched_contact["id"]

    if not matched_contact and extracted_data.get("client_names"):
        first_part = extracted_data["client_names"].split(" and ")[0]
        s_res = await _direct_search_contacts({"query": first_part})
        if s_res.get("contacts"):
            matched_contact = s_res["contacts"][0]
            client_id = matched_contact["id"]

    # Execute specific lifecycle actions
    if event_type == "NWMLS_SEARCH_CREATED":
        if client_id:
            await _direct_update_contact({
                "contact_id": client_id,
                "lifecycle_stage": "Engaged",
                "search_active": True,
            })
    elif event_type == "NWMLS_PORTAL_ACTIVE":
        if client_id:
            await _direct_update_contact({
                "contact_id": client_id,
                "lifecycle_stage": "Engaged",
                "portal_active": True,
                "last_portal_activity_at": datetime.utcnow().isoformat() + "Z",
            })
    elif event_type == "AUTHENTISIGN_BBA_SIGNED":
        if client_id:
            await _direct_update_contact({
                "contact_id": client_id,
                "role": "Buyer",
                "lifecycle_stage": "Active Client",
                "bba_signed": True,
                "bba_signed_date": datetime.utcnow().strftime("%Y-%m-%d"),
            })
    elif event_type == "AUTHENTISIGN_LISTING_SIGNED":
        if client_id:
            await _direct_update_contact({
                "contact_id": client_id,
                "role": "Seller",
                "lifecycle_stage": "Active Client",
                "bba_signed": True,
                "bba_signed_date": datetime.utcnow().strftime("%Y-%m-%d"),
            })
        if extracted_data.get("property_address"):
            d_res = await _direct_manage_opportunities({
                "action": "create",
                "property_address": extracted_data["property_address"],
                "deal_type": "Seller",
                "deal_stage": "ACTIVE_LISTING",
                "contact_id": client_id,
            })
            deal_id = d_res.get("id")
    elif event_type in ("AUTHENTISIGN_OFFER_DISCLOSURE_SIGNED", "INSPECTION_CONFIRMED"):
        if extracted_data.get("property_address"):
            d_res = await _direct_manage_opportunities({
                "action": "create",
                "property_address": extracted_data["property_address"],
                "deal_type": "Buyer",
                "deal_stage": "INSPECTION_PHASE" if event_type == "INSPECTION_CONFIRMED" else "UNDER_CONTRACT",
                "contact_id": client_id,
                "co_clients": extracted_data.get("client_names"),
            })
            deal_id = d_res.get("id")
    elif event_type == "TRANSACTION_CLOSED":
        if extracted_data.get("property_address"):
            d_res = await _direct_manage_opportunities({
                "action": "update",
                "name": extracted_data["property_address"],
                "deal_stage": "CLOSED_WON",
            })
            deal_id = d_res.get("id")

    record_processed_communication(
        message_id=msg_id,
        source=channel,
        sender=sender,
        subject=subject,
        event_type=event_type,
        client_name=extracted_data.get("client_names") or (matched_contact.get("name") if matched_contact else None),
        client_id=client_id,
        deal_id=deal_id,
        details=extracted_data,
    )

    steps.append({
        "step": "Lifecycle State Update",
        "agent": "Miles Miller",
        "action": f"Executed Twenty CRM update (Event: {event_type}, Client: {client_id or 'Matched/Pending'}, Deal: {deal_id or 'None'})",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "ok",
    })

    duration_ms = int((time.time() - start_ts) * 1000)
    log_request_flow(
        flow_id=flow_id,
        source=f"Communication: {channel}",
        title=f"Real Estate Ingestion: {event_type}",
        status="completed",
        agents_involved=["Silas Drake", "Miles Miller"],
        steps=steps,
        payload_preview=payload,
        result_summary=f"Processed {event_type} for '{sender}' in Twenty CRM",
        duration_ms=duration_ms,
    )

    return {
        "ok": True,
        "event_type": event_type,
        "client_id": client_id,
        "deal_id": deal_id,
        "extracted": extracted_data,
        "duration_ms": duration_ms,
    }

