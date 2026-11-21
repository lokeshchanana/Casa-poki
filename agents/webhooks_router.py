"""
Native Webhook & Google OAuth Router for agent-hub.
Replaces n8n workflows:
  - wGB3XfRGWgbbvOGP (Open House Sign-In -> CRM Intake)
  - websiteContactWf01 (Website Contact Form -> CRM Intake)
  - twentyBrevoSyncWf01 (Twenty CRM <-> Brevo Sync & Compliance)
  - PVRaEmYtHs1CwEDo (Google Drive OAuth2 Token Management)
"""

import json
import logging
import os
import re
import time
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from brevo_sync import (
    TWENTY_BASE_URL,
    _twenty_headers,
    format_e164_sms,
    handle_brevo_event,
    sync_single_contact_to_brevo,
    sync_twenty_to_brevo,
)
from state_store import log_request_flow

logger = logging.getLogger("webhooks_router")
router = APIRouter()

SMSGATE_ENABLED = os.environ.get("SMSGATE_ENABLED", "true").lower() in ("1", "true", "yes")
SMSGATE_ENDPOINT = os.environ.get("SMSGATE_ENDPOINT", "https://api.sms-gate.app/3rdparty/v1/messages")
SMSGATE_LOGIN = os.environ.get("SMSGATE_LOGIN", "")
SMSGATE_PASSWORD = os.environ.get("SMSGATE_PASSWORD", "")
SMSGATE_SIM_SLOT = int(os.environ.get("SMSGATE_SIM_SLOT", "0"))
GOOGLE_OAUTH_PATH = os.environ.get("GOOGLE_OAUTH_PATH", "/tank/agents/google_oauth.json")

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def _normalize_phone(num: Any) -> str:
    if not num:
        return ""
    s = str(num).strip()
    if s.startswith("+"):
        return "+" + re.sub(r"[^0-9]", "", s)
    digits = re.sub(r"[^0-9]", "", s)
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return f"+{digits}" if digits else ""


def _la_timestamp() -> str:
    return datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%m/%d/%Y, %I:%M:%S %p")


async def _crm_request(endpoint: str, method: str = "GET", payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{TWENTY_BASE_URL}{endpoint}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.request(method, url, headers=_twenty_headers(), json=payload)
            try:
                data = resp.json()
            except Exception:
                data = resp.text
            return {"ok": 200 <= resp.status_code < 300, "status": resp.status_code, "data": data}
    except Exception as exc:
        return {"ok": False, "status": 500, "data": {"message": str(exc)}}


async def _find_crm_person(email: str, phone: str) -> Optional[Dict[str, Any]]:
    if email:
        res = await _crm_request(f"/rest/people?filter=emails.primaryEmail[eq]:{urllib.parse.quote(email)}")
        people = ((res.get("data") or {}).get("data") or {}).get("people") or []
        if people:
            return people[0]
    if phone:
        digits = re.sub(r"[^0-9]", "", phone)
        tail = digits[-10:] if len(digits) >= 10 else digits
        if tail:
            res = await _crm_request(f"/rest/people?filter=phones.primaryPhoneNumber[ilike]:%25{urllib.parse.quote(tail)}%25")
            people = ((res.get("data") or {}).get("data") or {}).get("people") or []
            if people:
                return people[0]
    return None


async def _attach_crm_note(person_id: Optional[str], title: str, markdown: str) -> Optional[str]:
    res = await _crm_request("/rest/notes", "POST", {"title": title, "bodyV2": {"markdown": markdown}})
    note_id = (((res.get("data") or {}).get("data") or {}).get("createNote") or {}).get("id")
    if note_id and person_id:
        await _crm_request("/rest/noteTargets", "POST", {"noteId": note_id, "targetPersonId": person_id})
    return note_id


async def _attach_crm_task(person_id: Optional[str], title: str, markdown: str) -> Optional[str]:
    res = await _crm_request("/rest/tasks", "POST", {"title": title, "bodyV2": {"markdown": markdown}, "status": "TODO"})
    task_id = (((res.get("data") or {}).get("data") or {}).get("createTask") or {}).get("id")
    if task_id and person_id:
        await _crm_request("/rest/taskTargets", "POST", {"taskId": task_id, "targetPersonId": person_id})
    return task_id


async def _send_smsgate(phone: str, text: str) -> Dict[str, Any]:
    digits = re.sub(r"[^0-9]", "", phone or "")
    if not SMSGATE_ENABLED or len(digits) < 10:
        return {"skipped": True, "reason": "SMSGate disabled or no valid phone"}
    if not SMSGATE_LOGIN or not SMSGATE_PASSWORD:
        return {"skipped": True, "reason": "SMSGate credentials not configured"}

    payload = {
        "phoneNumbers": [phone],
        "simSlot": SMSGATE_SIM_SLOT,
        "textMessage": {"text": text},
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                SMSGATE_ENDPOINT,
                auth=(SMSGATE_LOGIN, SMSGATE_PASSWORD),
                json=payload,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            try:
                data = resp.json()
            except Exception:
                data = resp.text
            return {"ok": 200 <= resp.status_code < 300, "status": resp.status_code, "data": data}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@router.post("/webhook/open-house-sign-in")
@router.post("/api/manager/webhook/open-house-sign-in")
async def open_house_sign_in_webhook(request: Request) -> Dict[str, Any]:
    start_ts = time.time()
    payload = await request.json()
    if isinstance(payload.get("body"), dict):
        payload = payload["body"]

    name = (payload.get("name") or payload.get("Name") or "").strip()
    raw_phone = payload.get("phone") or payload.get("phone_number") or payload.get("Phone #") or payload.get("Phone Number") or ""
    phone = _normalize_phone(raw_phone)
    email = (payload.get("email") or payload.get("Email") or "").strip().lower()
    feedback = (payload.get("feedback") or payload.get("Feedback") or "").strip()
    working_with_agent = str(payload.get("working_with_agent") or payload.get("agent") or payload.get("Are you working with an agent?") or "No").strip()
    agent_name = (payload.get("agent_name") or payload.get("agentName") or "").strip()
    property_address = (payload.get("property_address") or payload.get("property") or payload.get("propertyAddress") or "").strip()
    city = (payload.get("city") or payload.get("market") or payload.get("City") or payload.get("Market") or "Greater Seattle").strip()

    needs = payload.get("current_needs") or payload.get("needs") or payload.get("CURRENT NEEDS?") or []
    if isinstance(needs, str):
        try:
            needs = json.loads(needs)
        except Exception:
            needs = [needs]
    if not isinstance(needs, list):
        needs = [str(needs)]
    needs_str = ", ".join(str(n).strip() for n in needs if str(n).strip()) or "Not specified"

    if not name and not email and not phone:
        return {"success": False, "message": "Name, email, or phone is required."}

    action = (payload.get("action") or "create").lower()
    budget = (payload.get("budget") or "").strip()
    house_prefs = (payload.get("house_preferences") or payload.get("housePreferences") or payload.get("preferences") or "").strip()
    notes = (payload.get("notes") or "").strip()

    parts = (name or "Open House Visitor").split()
    first_name = parts[0] or "Visitor"
    last_name = " ".join(parts[1:])

    # 0. Roster Edit / Note Update
    if action in ("update_guest", "add_note"):
        target_id = payload.get("personId") or payload.get("id")
        if target_id and not UUID_RE.match(str(target_id)):
            target_id = None
        if not target_id:
            found = await _find_crm_person(email, phone)
            target_id = found.get("id") if found else None

        if not target_id:
            create_payload: Dict[str, Any] = {
                "name": {"firstName": first_name, "lastName": last_name},
                "leadSource": "Open House",
                "market": city,
                "contactRole": "Customer",
                "canEmail": True,
            }
            if phone:
                create_payload["phones"] = {"primaryPhoneNumber": phone}
            if email:
                create_payload["emails"] = {"primaryEmail": email}
            c_res = await _crm_request("/rest/people", "POST", create_payload)
            target_id = (((c_res.get("data") or {}).get("data") or {}).get("createPerson") or {}).get("id")
        else:
            patch_payload: Dict[str, Any] = {"leadSource": "Open House", "contactRole": "Customer"}
            if name:
                patch_payload["name"] = {"firstName": first_name, "lastName": last_name}
            if phone:
                patch_payload["phones"] = {"primaryPhoneNumber": phone}
            if email:
                patch_payload["emails"] = {"primaryEmail": email}
            if city:
                patch_payload["market"] = city
            await _crm_request(f"/rest/people/{target_id}", "PATCH", patch_payload)

        note_lines = [
            f"Open House Roster Update & Notes ({city})",
            "--------------------------------------------------",
            f"Guest Name: {name or 'Visitor'}",
            f"Phone: {phone}" if phone else None,
            f"Email: {email}" if email else None,
            f"Property: {property_address}" if property_address else None,
            f"Updated: {_la_timestamp()}",
            "",
            "Buyer Criteria & Details:",
            f"• Target Budget: {budget}" if budget else None,
            f"• House Preferences: {house_prefs}" if house_prefs else None,
            f"• Plans / Timeline: {needs_str}" if needs_str else None,
            f"• Working with Agent: {working_with_agent}" + (f" ({agent_name})" if agent_name else "") if working_with_agent else None,
            f"• Property Feedback: {feedback}" if feedback else None,
            f"\nAgent Conversation Notes:\n{notes}" if notes else None,
        ]
        note_md = "\n".join(line for line in note_lines if line is not None)
        note_id = await _attach_crm_note(target_id, f"Open House Notes - {name or 'Visitor'} ({city})", note_md)

        task_id = None
        if budget or house_prefs or notes:
            task_title = f"Follow up with {name or 'Visitor'} ({'Budget: ' + budget if budget else city + ' Open House'})"
            task_md = (
                f"Updated Open House Roster Notes ({city}):\n"
                f"• Budget: {budget or 'Not specified'}\n"
                f"• House Preferences: {house_prefs or 'Not specified'}\n"
                f"• Agent Notes: {notes or 'None'}\n"
                f"• Feedback: {feedback or 'None'}\n"
                f"• Phone: {phone or 'N/A'}\n"
                f"• Email: {email or 'N/A'}"
            )
            task_id = await _attach_crm_task(target_id, task_title, task_md)

        if email:
            await sync_single_contact_to_brevo(email, name, phone, "Customer", city, "Open House", target_id or "")

        log_request_flow(
            flow_id=f"oh_update_{int(time.time() * 1000)}",
            source="Open House Roster",
            title=f"Roster Update: {name or email or phone} ({city})",
            status="completed",
            agents_involved=["Miles Miller"],
            steps=[{"step": "CRM Roster Update", "agent": "Miles Miller", "action": f"Updated {name} in Twenty CRM", "status": "ok"}],
            payload_preview={"name": name, "city": city, "action": action},
            result_summary=f"Updated details & notes for {name or 'visitor'}",
            duration_ms=int((time.time() - start_ts) * 1000),
            category="crm",
        )
        return {
            "success": True,
            "status": "guest_updated",
            "personId": target_id,
            "noteId": note_id,
            "taskId": task_id,
            "name": name,
            "budget": budget,
            "housePreferences": house_prefs,
            "notes": notes,
            "message": f"Updated details & notes for {name or 'visitor'}",
        }

    # 1. Existing Contact Check
    found = await _find_crm_person(email, phone)
    if found:
        person_id = found.get("id")
        upd: Dict[str, Any] = {
            "leadSource": "Open House",
            "market": city or found.get("market"),
            "contactRole": "Customer",
        }
        fn_cur = ((found.get("name") or {}).get("firstName") or "").lower()
        if name and (not fn_cur or fn_cur.startswith("guest")):
            upd["name"] = {"firstName": first_name, "lastName": last_name}
        if phone and not (found.get("phones") or {}).get("primaryPhoneNumber"):
            upd["phones"] = {"primaryPhoneNumber": phone}
        if email and not (found.get("emails") or {}).get("primaryEmail"):
            upd["emails"] = {"primaryEmail": email}
        await _crm_request(f"/rest/people/{person_id}", "PATCH", upd)

        cur_name_obj = found.get("name") or {}
        customer_name = name or f"{cur_name_obj.get('firstName', '')} {cur_name_obj.get('lastName', '')}".strip() or "Friend"
        await _attach_crm_task(
            person_id,
            f"Follow up with {customer_name} (Repeat Open House Visit - {city})",
            f"Repeat open house visit from {city}.\nNeeds: {needs_str}\nFeedback: {feedback or 'None'}\nPhone: {phone or 'N/A'}\nEmail: {email or 'N/A'}",
        )
        sync_email = email or ((found.get("emails") or {}).get("primaryEmail") or "")
        if sync_email:
            await sync_single_contact_to_brevo(
                sync_email,
                customer_name,
                phone or ((found.get("phones") or {}).get("primaryPhoneNumber") or ""),
                "Customer",
                city,
                "Open House",
                person_id or "",
            )
        log_request_flow(
            flow_id=f"oh_repeat_{int(time.time() * 1000)}",
            source="Open House Sign-In",
            title=f"Repeat Open House Guest: {customer_name} ({city})",
            status="completed",
            agents_involved=["Miles Miller"],
            steps=[{"step": "CRM Intake", "agent": "Miles Miller", "action": f"Matched existing contact {customer_name}", "status": "ok"}],
            payload_preview={"name": customer_name, "city": city},
            result_summary=f"Welcome back, {customer_name}!",
            duration_ms=int((time.time() - start_ts) * 1000),
            category="crm",
        )
        return {
            "success": True,
            "status": "existing_contact_updated",
            "personId": person_id,
            "name": customer_name,
            "market": city,
            "lead_source": "Open House",
            "smsGateResult": {"skipped": True, "reason": "Existing contact in CRM - text automation skipped"},
            "message": f"Welcome back, {customer_name}!",
        }

    # 2. Brand New Open House Guest
    new_person: Dict[str, Any] = {
        "name": {"firstName": first_name, "lastName": last_name},
        "leadSource": "Open House",
        "market": city,
        "canEmail": True,
        "contactRole": "Customer",
    }
    if phone:
        new_person["phones"] = {"primaryPhoneNumber": phone}
    if email:
        new_person["emails"] = {"primaryEmail": email}

    c_res = await _crm_request("/rest/people", "POST", new_person)
    if not c_res.get("ok"):
        return {
            "success": False,
            "error": ((c_res.get("data") or {}).get("message") if isinstance(c_res.get("data"), dict) else None) or "Failed to create person in Twenty CRM",
            "details": c_res.get("data"),
        }

    new_person_id = (((c_res.get("data") or {}).get("data") or {}).get("createPerson") or {}).get("id")
    note_md = (
        f"Open House Sign-In Details\n--------------------------\n"
        f"Full Name: {name}\nPhone: {phone or 'Not provided'}\nEmail: {email or 'Not provided'}\n"
        f"Market / City: {city}\nProperty: {property_address or 'Open House'}\n"
        f"Working with Agent: {working_with_agent}" + (f" ({agent_name})" if agent_name else "") + "\n"
        f"Current Needs: {needs_str}\nFeedback: {feedback or 'None provided'}\nTimestamp: {_la_timestamp()}"
    )
    await _attach_crm_note(new_person_id, f"Open House Sign-In - {city}", note_md)
    await _crm_request("/rest/opportunities", "POST", {"name": f"[Customer] {name}", "pointOfContactId": new_person_id, "stage": "NEW"})
    await _attach_crm_task(
        new_person_id,
        f"Follow up with {name} (Open House Lead - {city})",
        f"Follow up with open house lead from {city}.\nNeeds: {needs_str}\nFeedback: {feedback or 'None'}\nPhone: {phone or 'N/A'}\nEmail: {email or 'N/A'}",
    )

    market_desc = f"{city} open house" if city else "today's open house"
    if working_with_agent == "Yes":
        sms_text = (
            f"Hi {name}, this is Lokesh Chanana (Loki). Thank you for touring the {market_desc} today!\n\n"
            f"Dropping my direct contact card for your records:\nhttps://lokeshchanana.com/loki.vcf\n\n"
            f"Please feel free to have your agent reach out to me directly if they need disclosure packets or offer guidelines. Have a great day!"
        )
    else:
        sms_text = (
            f"Hi {name}, this is Lokesh Chanana (Loki). Thank you for visiting the {market_desc} today!\n\n"
            f"Dropping my direct contact card so you have it saved:\nhttps://lokeshchanana.com/loki.vcf\n\n"
            f"Feel free to text or call if you have any questions about this property or anything in the area. Have a wonderful weekend!"
        )

    sms_res = await _send_smsgate(phone, sms_text) if phone else None
    if email:
        await sync_single_contact_to_brevo(email, name, phone, "Customer", city, "Open House", new_person_id or "")

    log_request_flow(
        flow_id=f"oh_new_{int(time.time() * 1000)}",
        source="Open House Sign-In",
        title=f"New Open House Lead: {name} ({city})",
        status="completed",
        agents_involved=["Miles Miller", "Maya Reyes"],
        steps=[{"step": "CRM & Brevo Intake", "agent": "Miles Miller", "action": f"Created lead {name} + Opportunity + Task", "status": "ok"}],
        payload_preview={"name": name, "city": city, "email": email},
        result_summary=f"Welcome, {name}! Your sign-in has been received.",
        duration_ms=int((time.time() - start_ts) * 1000),
        category="crm",
    )
    return {
        "success": True,
        "status": "created",
        "personId": new_person_id,
        "name": name,
        "market": city,
        "lead_source": "Open House",
        "smsGateResult": sms_res,
        "message": f"Welcome, {name}! Your sign-in has been received.",
    }


@router.post("/webhook/website-contact")
@router.post("/api/manager/webhook/website-contact")
async def website_contact_webhook(request: Request) -> Dict[str, Any]:
    start_ts = time.time()
    payload = await request.json()
    if isinstance(payload.get("body"), dict):
        payload = payload["body"]

    name = (payload.get("name") or payload.get("Name") or "").strip()
    raw_phone = payload.get("phone") or payload.get("phone_number") or payload.get("Phone") or ""
    phone = _normalize_phone(raw_phone)
    email = (payload.get("email") or payload.get("Email") or "").strip().lower()
    purpose = (payload.get("purpose") or payload.get("subject") or payload.get("Purpose") or "General Inquiry").strip()
    message = (payload.get("message") or payload.get("comments") or payload.get("inquiry") or "").strip()

    if not name and not email and not phone:
        return {"success": False, "message": "Name, email, or phone is required."}

    parts = (name or "Website Visitor").split()
    first_name = parts[0] or "Website"
    last_name = " ".join(parts[1:])

    found = await _find_crm_person(email, phone)
    if found:
        person_id = found.get("id")
        upd: Dict[str, Any] = {"leadSource": "Website", "contactRole": "Customer"}
        fn_cur = (found.get("name") or {}).get("firstName") or ""
        if name and (not fn_cur or fn_cur == "Website"):
            upd["name"] = {"firstName": first_name, "lastName": last_name}
        if phone and not (found.get("phones") or {}).get("primaryPhoneNumber"):
            upd["phones"] = {"primaryPhoneNumber": phone}
        if email and not (found.get("emails") or {}).get("primaryEmail"):
            upd["emails"] = {"primaryEmail": email}
        await _crm_request(f"/rest/people/{person_id}", "PATCH", upd)
    else:
        new_person: Dict[str, Any] = {
            "name": {"firstName": first_name, "lastName": last_name},
            "leadSource": "Website",
            "contactRole": "Customer",
            "canEmail": True,
        }
        if email:
            new_person["emails"] = {"primaryEmail": email}
        if phone:
            new_person["phones"] = {"primaryPhoneNumber": phone}
        c_res = await _crm_request("/rest/people", "POST", new_person)
        if not c_res.get("ok"):
            return {
                "success": False,
                "error": ((c_res.get("data") or {}).get("message") if isinstance(c_res.get("data"), dict) else None) or "Failed to create person in Twenty CRM",
                "details": c_res.get("data"),
            }
        person_id = (((c_res.get("data") or {}).get("data") or {}).get("createPerson") or {}).get("id")
        await _crm_request("/rest/opportunities", "POST", {"name": f"[Website Lead] {name or 'Inquiry'}", "pointOfContactId": person_id, "stage": "NEW"})

    note_md = (
        f"Website Contact Inquiry\n-----------------------\n"
        f"Full Name: {name or 'Not provided'}\nPurpose of Contact: {purpose}\n"
        f"Phone: {phone or raw_phone or 'Not provided'}\nEmail: {email or 'Not provided'}\n"
        f"Inquiry Details: {message or 'None provided'}\nTimestamp: {_la_timestamp()}"
    )
    await _attach_crm_note(person_id, f"Website Inquiry - {purpose} ({datetime.utcnow().strftime('%Y-%m-%d')})", note_md)
    await _attach_crm_task(
        person_id,
        f"Website Inquiry: {name or 'New Lead'} - {purpose}",
        f"Website inquiry received from {name or 'Lead'}.\nPurpose: {purpose}\nMessage: {message or 'None'}\nPhone: {phone or 'N/A'}\nEmail: {email or 'N/A'}",
    )

    first_short = (name or "").split()[0] if name else "there"
    sms_text = (
        f"Hi {first_short}, this is Lokesh Chanana (Loki). Thank you for reaching out through my website (lokeshchanana.com)!\n\n"
        f"I have received your message regarding {purpose.lower()} and will get back to you shortly.\n\n"
        f"In the meantime, feel free to save my direct contact card to your phone:\nhttps://lokeshchanana.com/loki.vcf"
    )
    sms_res = await _send_smsgate(phone, sms_text) if phone else None
    if email:
        await sync_single_contact_to_brevo(email, name, phone, "Customer", "Greater Seattle", "Website", person_id or "")

    log_request_flow(
        flow_id=f"web_contact_{int(time.time() * 1000)}",
        source="Website Contact Form",
        title=f"Website Inquiry: {name or email} ({purpose})",
        status="completed",
        agents_involved=["Miles Miller", "Maya Reyes"],
        steps=[{"step": "Website Lead Intake", "agent": "Miles Miller", "action": f"Processed {purpose} for {name}", "status": "ok"}],
        payload_preview={"name": name, "purpose": purpose, "email": email},
        result_summary=f"Thank you, {name}! Your inquiry has been received.",
        duration_ms=int((time.time() - start_ts) * 1000),
        category="crm",
    )
    return {
        "success": True,
        "personId": person_id,
        "name": name,
        "purpose": purpose,
        "lead_source": "Website",
        "smsGateResult": sms_res,
        "message": f"Thank you, {name}! Your inquiry has been received. Loki will get back to you shortly.",
    }


@router.post("/webhook/twenty-brevo-sync")
@router.post("/api/manager/webhook/twenty-brevo-sync")
async def twenty_brevo_sync_webhook() -> Dict[str, Any]:
    return await sync_twenty_to_brevo()


@router.post("/webhook/brevo-event-webhook")
@router.post("/api/manager/webhook/brevo-event-webhook")
async def brevo_event_webhook(request: Request) -> Dict[str, Any]:
    payload = await request.json()
    if isinstance(payload.get("body"), dict):
        payload = payload["body"]
    return await handle_brevo_event(payload)


# =============================================================================
# Standalone Google Drive OAuth2 Token Management (Replaces n8n credential store)
# =============================================================================

@router.get("/api/oauth/google/status")
def google_oauth_status() -> Dict[str, Any]:
    if not os.path.exists(GOOGLE_OAUTH_PATH):
        return {"configured": False, "path": GOOGLE_OAUTH_PATH}
    data = json.load(open(GOOGLE_OAUTH_PATH))
    return {
        "configured": bool(data.get("client_id") and data.get("client_secret")),
        "has_refresh_token": bool(data.get("refresh_token")),
        "scope": data.get("scope"),
        "updated_at": data.get("updated_at"),
    }


@router.get("/api/oauth/google/start")
def google_oauth_start(request: Request) -> RedirectResponse:
    data = json.load(open(GOOGLE_OAUTH_PATH))
    redirect_uri = str(request.base_url).rstrip("/") + "/api/oauth/google/callback"
    params = urllib.parse.urlencode({
        "client_id": data["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/drive",
        "access_type": "offline",
        "prompt": "consent",
    })
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


@router.get("/api/oauth/google/callback")
async def google_oauth_callback(request: Request, code: str = "", error: str = "") -> HTMLResponse:
    if error or not code:
        return HTMLResponse(f"<h3>Google OAuth Error:</h3><pre>{error or 'Missing code'}</pre>", status_code=400)
    data = json.load(open(GOOGLE_OAUTH_PATH))
    redirect_uri = str(request.base_url).rstrip("/") + "/api/oauth/google/callback"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": data["client_id"],
                "client_secret": data["client_secret"],
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    tok = resp.json()
    if "refresh_token" in tok:
        data["refresh_token"] = tok["refresh_token"]
    data["updated_at"] = datetime.utcnow().isoformat() + "Z"
    with open(GOOGLE_OAUTH_PATH, "w") as f:
        json.dump(data, f, indent=2)
    os.chmod(GOOGLE_OAUTH_PATH, 0o600)
    return HTMLResponse("<h3>Google Drive OAuth Connected!</h3><p>Tokens saved to /tank/agents/google_oauth.json. You can close this tab.</p>")
