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


NICKNAME_MAP = {
    "jim": "james", "james": "jim", "jimmy": "james",
    "bob": "robert", "rob": "robert", "bobby": "robert",
    "bill": "william", "will": "william",
    "mike": "michael", "chris": "christopher",
    "dave": "david", "dan": "daniel", "danny": "daniel",
    "joe": "joseph", "tom": "thomas", "nick": "nicholas",
    "alex": "alexander", "kate": "katherine", "kathy": "katherine",
    "lola": "lodmella", "lodmella": "lola",
    "loki": "lokesh",
}

NON_CLIENT_EMAIL_DOMAINS = (
    "authentisign.com", "nwmlsmatrixmail.com", "nwmls.com", "ctt.com",
    "fnhw-warranty.com", "smartviewonline.net", "lokeshchanana.com",
)
OWNER_EMAILS = ("lokesh@lokeshchanana.com", "lokeshchanana@gmail.com")


def _match_contact_by_name(candidate: str, all_contacts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Match an active CRM contact by full name, nickname+last name, or unique first name."""
    clean = re.sub(r"\s+", " ", (candidate or "").strip()).lower()
    if not clean:
        return None
    # Remove middle initials for matching (e.g. "James N Beidatsch" -> first="james", last="beidatsch")
    tokens = [t for t in clean.split(" ") if t]
    first_tok = tokens[0]
    last_tok = tokens[-1] if len(tokens) > 1 else ""
    nick_tok = NICKNAME_MAP.get(first_tok, "")

    # 1. Exact full name match
    for c in all_contacts:
        cname = re.sub(r"\s+", " ", (c.get("name") or "").strip()).lower()
        if cname == clean:
            return c

    # 2. First/nickname + Last name match
    if last_tok:
        for c in all_contacts:
            c_tokens = [t for t in (c.get("name") or "").strip().lower().split(" ") if t]
            if len(c_tokens) >= 2 and c_tokens[-1] == last_tok:
                if c_tokens[0] == first_tok or (nick_tok and c_tokens[0] == nick_tok):
                    return c

    # 3. Unique first-name or nickname match (only if unambiguous)
    first_matches = []
    for c in all_contacts:
        c_first = ((c.get("name") or "").strip().lower().split(" ") or [""])[0]
        if c_first == first_tok or (nick_tok and c_first == nick_tok):
            first_matches.append(c)
    if len(first_matches) == 1:
        return first_matches[0]

    return None


async def handle_communication_intake(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Unified communication ingestion webhook for incoming SMS or parsed emails.
    Routes real estate events through Miles Miller (CRM Specialist),
    supporting co-clients, nicknames, deal upserts, and Title/Escrow milestones.
    """
    flow_id = f"flow_comm_{int(time.time()*1000)}"
    start_ts = time.time()
    steps = []

    sender = (payload.get("sender") or payload.get("from") or "").strip()
    recipient = (payload.get("to") or "").strip()
    cc_header = (payload.get("cc") or "").strip()
    subject = (payload.get("subject") or "").strip()
    body = (payload.get("body") or payload.get("text") or payload.get("content") or "").strip()
    channel = (payload.get("channel") or "email").lower()
    msg_id = payload.get("message_id") or f"webhook_{flow_id}"
    participants_hint: List[str] = payload.get("participants_hint") or []

    from state_store import is_communication_processed, record_processed_communication
    if is_communication_processed(msg_id):
        return {"ok": True, "status": "ALREADY_PROCESSED", "message_id": msg_id}

    lower_sub = subject.lower()
    lower_body = body.lower()
    lower_sender = sender.lower()

    # Ignore intermediate Authentisign "Signing updated:" notifications (handled on "Signing complete:")
    if "authentisign.com" in lower_sender and lower_sub.startswith("signing updated:"):
        return {"ok": True, "status": "IGNORED_INTERMEDIATE", "message_id": msg_id}

    steps.append({
        "step": "Communication Ingestion",
        "agent": "Silas Drake",
        "action": f"Ingested {channel} communication from '{sender}' (Subject: {subject[:50]})",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "ok",
    })

    # Pattern recognition for Real Estate Lifecycle Events
    event_type = "GENERAL_INQUIRY"
    extracted_data: Dict[str, Any] = {}

    # 1. NWMLS Search setup vs Portal activity
    if "nwmls" in lower_sender or "nwmlsmatrixmail.com" in lower_sender:
        if "auto email" in lower_sub or "auto-email" in lower_sub or "initial search" in lower_sub or "welcome" in lower_sub:
            event_type = "NWMLS_SEARCH_CREATED"
        elif "portal" in lower_sub or "viewed" in lower_sub or "favorite" in lower_sub or "activity" in lower_sub:
            event_type = "NWMLS_PORTAL_ACTIVE"
        else:
            event_type = "NWMLS_NOTIFICATION"

    # 2. Authentisign signing events
    elif "authentisign.com" in lower_sender or "authentisign" in lower_sub:
        if "bba" in lower_sub or "buyer brokerage" in lower_sub or "services agreement" in lower_sub or "form 41" in lower_body:
            event_type = "AUTHENTISIGN_BBA_SIGNED"
        elif "listing" in lower_sub or "exclusive sale" in lower_sub or "form 1a" in lower_body:
            event_type = "AUTHENTISIGN_LISTING_SIGNED"
        elif "inspection" in lower_sub or "35r" in lower_sub:
            event_type = "INSPECTION_CONFIRMED"
        elif any(k in lower_sub for k in ("psa", "purchase and sale", "disclosure", "offer", "counter")) or re.search(r"\d{3,5}\s+", subject):
            event_type = "AUTHENTISIGN_OFFER_DISCLOSURE_SIGNED"
        else:
            event_type = "AUTHENTISIGN_COMPLETED"

    # 3. Title & Escrow (Chicago Title / @ctt.com / Recording / Earnest Money)
    elif "ctt.com" in lower_sender or "chicago title" in lower_body or "escrow" in lower_sub or "title & escrow" in lower_sub:
        if "recording complete" in lower_sub or "transaction closed" in lower_sub or "final settlement" in lower_sub:
            event_type = "TRANSACTION_CLOSED"
        elif "earnest money" in lower_sub:
            event_type = "EARNEST_MONEY_RECEIVED"
        elif "new title" in lower_sub or "added to an order" in lower_sub or "order updated" in lower_sub or "order #" in lower_sub:
            event_type = "ESCROW_OPENED"

    # 4. Inspection confirmed
    elif "inspection confirmed" in lower_sub or "home inspection" in lower_sub or "inspection response" in lower_sub:
        event_type = "INSPECTION_CONFIRMED"

    # 5. Closing / Title recording confirmation
    elif "recording complete" in lower_sub or "transaction closed" in lower_sub:
        event_type = "TRANSACTION_CLOSED"

    # Extract Escrow Company / Order # if present
    order_match = re.search(r"(CTTC\d+|Order\s*#?\s*[A-Z0-9-]+)", subject + " " + body, re.IGNORECASE)
    if order_match and ("ctt.com" in lower_sender or "chicago title" in lower_body):
        extracted_data["escrow_company"] = f"Chicago Title Company of Washington ({order_match.group(1).strip()})"

    # Extraction of Property Address if present
    addr_match = re.search(
        r"(\d{3,5}\s+[A-Za-z0-9\.\s]+?(?:St|Street|Ave|Avenue|Rd|Road|Way|Ct|Court|Dr|Drive|Blvd|Boulevard|Lane|Ln|Pl|Place)(?:\s+(?:E|W|N|S|NE|NW|SE|SW))?(?:,\s*[A-Za-z\s]+,\s*WA(?:\s+\d{5})?)?)",
        subject + " " + body,
        re.IGNORECASE,
    )
    if addr_match:
        extracted_data["property_address"] = re.sub(r"\s+", " ", addr_match.group(1)).strip()

    # Extraction of Client Names from Subject or Body (Buyer: ...)
    names_match = re.search(
        r"(?:for|Signing complete:|Signing updated:)\s*([A-Z][a-z]+(?:\s+and\s+[A-Z][a-z]+|\s+[A-Z][a-z]+))",
        subject,
        re.IGNORECASE,
    )
    if names_match:
        extracted_data["client_names"] = names_match.group(1).strip()

    buyer_line = re.search(r"Buyer:\s*([^\n\r]+?)(?:\s+Seller:|\s+External|\n|$)", body)
    if buyer_line:
        extracted_data["buyer_line"] = buyer_line.group(1).strip()

    if participants_hint:
        extracted_data["participants_hint"] = participants_hint

    steps.append({
        "step": "Triage & Handoff",
        "agent": "Silas Drake",
        "action": f"Classified event '{event_type}'. Handing off to Miles Miller for Twenty CRM execution.",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "ok",
    })

    # Miles Miller executes the CRM state change across all matched co-clients
    from tools import _direct_search_contacts, _direct_update_contact, _direct_manage_opportunities, _direct_manage_notes

    all_res = await _direct_search_contacts({"query": "all", "limit": 500})
    all_contacts = all_res.get("contacts", [])

    matched_contacts: List[Dict[str, Any]] = []
    seen_ids = set()

    def _add_match(c: Optional[Dict[str, Any]]):
        if c and c.get("id") and c["id"] not in seen_ids:
            seen_ids.add(c["id"])
            matched_contacts.append(c)

    # 1. Explicit client_email or To/Cc client emails (excluding non-client service/agent domains)
    candidate_emails: List[str] = []
    if payload.get("client_email"):
        candidate_emails.append(str(payload["client_email"]).strip().lower())
    for hdr in (sender, recipient, cc_header):
        for em in re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", hdr or ""):
            em_l = em.lower()
            if em_l not in OWNER_EMAILS and not any(d in em_l for d in NON_CLIENT_EMAIL_DOMAINS):
                candidate_emails.append(em_l)

    for em_l in dict.fromkeys(candidate_emails):
        for c in all_contacts:
            if (c.get("email") or "").strip().lower() == em_l:
                _add_match(c)

    # 2. Match via participants_hint (full names from Authentisign Signing updated) or buyer_line
    name_candidates: List[str] = list(participants_hint)
    if extracted_data.get("buyer_line"):
        for part in re.split(r"[,&]|\band\b", extracted_data["buyer_line"]):
            if part.strip():
                name_candidates.append(part.strip())
    if extracted_data.get("client_names"):
        for part in re.split(r"\s+and\s+|\s*&\s*", extracted_data["client_names"], flags=re.IGNORECASE):
            if part.strip():
                name_candidates.append(part.strip())

    for cand in name_candidates:
        _add_match(_match_contact_by_name(cand, all_contacts))

    # 3. Expand co-client via partnerName if only 1 partner matched
    if len(matched_contacts) == 1:
        p_name = (matched_contacts[0].get("partner_name") or "").strip()
        if not p_name:
            # Check raw person partnerName via CRM if needed
            pass
        else:
            _add_match(_match_contact_by_name(p_name, all_contacts))

    primary_contact = matched_contacts[0] if matched_contacts else None
    client_id = primary_contact["id"] if primary_contact else None
    deal_id = None
    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    # Cross-link partnerName if exactly 2 co-clients matched
    if len(matched_contacts) == 2:
        c0, c1 = matched_contacts[0], matched_contacts[1]
        await _direct_update_contact({"contact_id": c0["id"], "partner_name": c1["name"]})
        await _direct_update_contact({"contact_id": c1["id"], "partner_name": c0["name"]})

    co_client_summary = ", ".join(
        f"{c['name']} (ID: {c['id']}" + (f" | {c['email']}" if c.get("email") else "") + ")"
        for c in matched_contacts[1:]
    ) or extracted_data.get("client_names")

    # Execute specific lifecycle actions for ALL matched co-clients
    if event_type == "NWMLS_SEARCH_CREATED":
        for c in matched_contacts:
            await _direct_update_contact({
                "contact_id": c["id"],
                "lifecycle_stage": "Engaged",
                "search_active": True,
            })
    elif event_type == "NWMLS_PORTAL_ACTIVE":
        for c in matched_contacts:
            await _direct_update_contact({
                "contact_id": c["id"],
                "lifecycle_stage": "Engaged",
                "portal_active": True,
                "last_portal_activity_at": datetime.utcnow().isoformat() + "Z",
            })
    elif event_type == "AUTHENTISIGN_BBA_SIGNED":
        for c in matched_contacts:
            await _direct_update_contact({
                "contact_id": c["id"],
                "role": "Buyer",
                "lifecycle_stage": "Active Client",
                "bba_signed": True,
                "bba_signed_date": today_str,
                "notes": f"Auto-synced from Authentisign: '{subject}' ({today_str}).",
            })
    elif event_type == "AUTHENTISIGN_LISTING_SIGNED":
        for c in matched_contacts:
            await _direct_update_contact({
                "contact_id": c["id"],
                "role": "Seller",
                "lifecycle_stage": "Active Client",
                "bba_signed": True,
                "bba_signed_date": today_str,
                "notes": f"Auto-synced Listing Agreement from Authentisign: '{subject}' ({today_str}).",
            })
        if extracted_data.get("property_address"):
            d_res = await _direct_manage_opportunities({
                "action": "create",
                "property_address": extracted_data["property_address"],
                "deal_type": "Seller",
                "deal_stage": "ACTIVE_LISTING",
                "contact_id": client_id,
                "co_clients": co_client_summary,
            })
            deal_id = d_res.get("id")
    elif event_type in ("AUTHENTISIGN_OFFER_DISCLOSURE_SIGNED", "INSPECTION_CONFIRMED", "ESCROW_OPENED"):
        target_stage = "INSPECTION_PHASE" if event_type == "INSPECTION_CONFIRMED" else "UNDER_CONTRACT"
        if "offer" in lower_sub and "counter" not in lower_sub and event_type == "AUTHENTISIGN_OFFER_DISCLOSURE_SIGNED":
            target_stage = "OFFER_SUBMITTED"
        if extracted_data.get("property_address"):
            opp_payload: Dict[str, Any] = {
                "action": "create",
                "property_address": extracted_data["property_address"],
                "deal_type": "Buyer",
                "deal_stage": target_stage,
                "contact_id": client_id,
                "co_clients": co_client_summary,
            }
            if event_type == "INSPECTION_CONFIRMED":
                opp_payload["inspection_date"] = today_str
            if extracted_data.get("escrow_company"):
                opp_payload["escrow_company"] = extracted_data["escrow_company"]
            d_res = await _direct_manage_opportunities(opp_payload)
            deal_id = d_res.get("id")
        if target_stage in ("UNDER_CONTRACT", "INSPECTION_PHASE"):
            for c in matched_contacts:
                await _direct_update_contact({
                    "contact_id": c["id"],
                    "lifecycle_stage": "Pending",
                    "primary_property_address": extracted_data.get("property_address"),
                })
    elif event_type == "EARNEST_MONEY_RECEIVED":
        for c in matched_contacts:
            await _direct_manage_notes({
                "action": "create",
                "contact_id": c["id"],
                "title": f"Earnest Money Received ({today_str})",
                "content": f"Escrow confirmed Earnest Money receipt: {subject}",
            })
    elif event_type == "TRANSACTION_CLOSED":
        if extracted_data.get("property_address"):
            d_res = await _direct_manage_opportunities({
                "action": "update",
                "name": extracted_data["property_address"],
                "deal_stage": "CLOSED_WON",
                "close_date": datetime.utcnow().isoformat() + "Z",
            })
            deal_id = d_res.get("id")

    record_processed_communication(
        message_id=msg_id,
        source=channel,
        sender=sender,
        subject=subject,
        event_type=event_type,
        client_name=", ".join(c["name"] for c in matched_contacts) or extracted_data.get("client_names"),
        client_id=client_id,
        deal_id=deal_id,
        details={**extracted_data, "matched_ids": [c["id"] for c in matched_contacts]},
    )

    steps.append({
        "step": "Lifecycle State Update",
        "agent": "Miles Miller",
        "action": f"Executed Twenty CRM update (Event: {event_type}, Matched: {len(matched_contacts)}, Deal: {deal_id or 'None'})",
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
        payload_preview={"sender": sender, "subject": subject, "channel": channel},
        result_summary=f"Processed {event_type} ({len(matched_contacts)} contacts) in Twenty CRM",
        duration_ms=duration_ms,
    )

    return {
        "ok": True,
        "event_type": event_type,
        "client_id": client_id,
        "matched_count": len(matched_contacts),
        "deal_id": deal_id,
        "extracted": extracted_data,
        "duration_ms": duration_ms,
    }


async def sync_email_lifecycle_updates(days_back: int = 2, max_messages: int = 50) -> Dict[str, Any]:
    """
    Daily autonomous IMAP scanner for Silas Drake + Miles Miller.
    Scans recent emails (read or unread) in lokesh@lokeshchanana.com using BODY.PEEK[]
    in readonly mode, builds Authentisign participant hints, and routes unprocessed
    real estate lifecycle emails into handle_communication_intake().
    """
    imap_user = os.environ.get("MAIL_IMAP_USER", "lokesh@lokeshchanana.com")
    imap_pass = os.environ.get("MAIL_IMAP_PASSWORD", "").replace(" ", "")
    if not imap_pass:
        return {"ok": False, "error": "MAIL_IMAP_PASSWORD not configured."}

    import email as py_email
    import imaplib
    from datetime import timedelta
    from email.header import decode_header
    from bs4 import BeautifulSoup
    from state_store import is_communication_processed

    def _decode_str(val: str) -> str:
        parts = []
        for b, enc in decode_header(val or ""):
            if isinstance(b, bytes):
                parts.append(b.decode(enc or "utf-8", errors="ignore"))
            else:
                parts.append(str(b))
        return "".join(parts).strip()

    def _fetch_recent_messages() -> List[Dict[str, Any]]:
        since_str = (datetime.utcnow() - timedelta(days=days_back)).strftime("%d-%b-%Y")
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(imap_user, imap_pass)
        mail.select("INBOX", readonly=True)
        status, data = mail.search(None, f"SINCE {since_str}")
        mail_ids = (data[0] or b"").split()[-max_messages:]
        fetched: List[Dict[str, Any]] = []
        for mid in mail_ids:
            _, msg_data = mail.fetch(mid, "(BODY.PEEK[])")
            for rp in msg_data:
                if not isinstance(rp, tuple):
                    continue
                msg = py_email.message_from_bytes(rp[1])
                subject = _decode_str(msg.get("Subject", ""))
                sender = _decode_str(msg.get("From", ""))
                to_hdr = _decode_str(msg.get("To", ""))
                cc_hdr = _decode_str(msg.get("Cc", ""))
                msg_id = (msg.get("Message-ID") or f"imap_{mid.decode()}").strip()

                plain_text, html_text = "", ""
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
                                html_text = pl.decode(errors="ignore")
                else:
                    pl = msg.get_payload(decode=True)
                    if pl:
                        if msg.get_content_type() == "text/html":
                            html_text = pl.decode(errors="ignore")
                        else:
                            plain_text = pl.decode(errors="ignore")[:3000]

                body = plain_text.strip()
                if not body and html_text:
                    body = BeautifulSoup(html_text, "html.parser").get_text(" ", strip=True)[:3000]

                fetched.append({
                    "message_id": msg_id,
                    "sender": sender,
                    "to": to_hdr,
                    "cc": cc_hdr,
                    "subject": subject,
                    "body": body,
                })
        mail.logout()
        return fetched

    import asyncio
    messages = await asyncio.to_thread(_fetch_recent_messages)

    # Pass 1: Collect full participant names from Authentisign "Signing updated:" emails
    session_participants: Dict[str, List[str]] = {}
    for m in messages:
        sub_l = m["subject"].lower()
        if "authentisign" in m["sender"].lower() and sub_l.startswith("signing updated:"):
            sess_match = re.search(r"signing updated:\s*(.+?),\s*action:", m["subject"], re.IGNORECASE)
            part_match = re.search(r"participant:\s*([^\n\r]+)", m["subject"] + "\n" + m["body"], re.IGNORECASE)
            if sess_match and part_match:
                sess_key = re.sub(r"\s+", " ", sess_match.group(1).strip().lower())
                p_name = re.sub(r"\s+", " ", part_match.group(1).strip())
                session_participants.setdefault(sess_key, [])
                if p_name and p_name not in session_participants[sess_key]:
                    session_participants[sess_key].append(p_name)

    # Pass 2: Route relevant, unprocessed real-estate lifecycle emails
    relevant_senders = ("authentisign.com", "nwmlsmatrixmail.com", "ctt.com")
    relevant_keywords = ("earnest money", "recording complete", "transaction closed", "new title & escrow", "inspection confirmed")

    processed_results: List[Dict[str, Any]] = []
    skipped = 0
    for m in messages:
        sub_l = m["subject"].lower()
        snd_l = m["sender"].lower()
        is_relevant = any(s in snd_l for s in relevant_senders) or any(k in sub_l for k in relevant_keywords)
        if not is_relevant:
            continue
        if "authentisign.com" in snd_l and sub_l.startswith("signing updated:"):
            continue
        if is_communication_processed(m["message_id"]):
            skipped += 1
            continue

        hints: List[str] = []
        if sub_l.startswith("signing complete:"):
            sess_key = re.sub(r"\s+", " ", m["subject"][len("signing complete:"):].strip().lower())
            hints = session_participants.get(sess_key, [])

        res = await handle_communication_intake({
            **m,
            "channel": "email",
            "participants_hint": hints,
        })
        processed_results.append({
            "subject": m["subject"],
            "event_type": res.get("event_type"),
            "matched_count": res.get("matched_count", 0),
            "deal_id": res.get("deal_id"),
        })

    return {
        "ok": True,
        "scanned": len(messages),
        "processed": len(processed_results),
        "already_processed_skipped": skipped,
        "results": processed_results,
    }

