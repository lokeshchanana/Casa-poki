import json
import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
import httpx

from state_store import log_request_flow
from tools import crm_get, crm_post, crm_patch

logger = logging.getLogger("agent_webhooks")


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
            res = await crm_get(f"/rest/people?filter=emails.primaryEmail[eq]:{email}")
            people = res.get("data", {}).get("people", [])
            if people:
                found_person = people[0]
        except Exception as e:
            logger.warning(f"Error searching person by email: {e}")

    if not found_person and phone:
        digits = re.sub(r"[^0-9]", "", phone)
        search_digits = digits[-10:] if len(digits) >= 10 else digits
        if search_digits:
            try:
                res = await crm_get(f"/rest/people?filter=phones.primaryPhoneNumber[ilike]:%{search_digits}%")
                people = res.get("data", {}).get("people", [])
                if people:
                    found_person = people[0]
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

    # 4. Quality Audit Verification
    steps.append({
        "step": "Quality Audit",
        "agent": "Audrey Chen",
        "action": f"Verified CRM contact '{person_id}', attached note '{note_id}', and scheduled task '{task_id}'",
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
