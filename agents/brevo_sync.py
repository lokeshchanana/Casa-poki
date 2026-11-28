"""
Twenty CRM <-> Brevo Contact Sync & Compliance Handler
Migrated from n8n workflow 'twentyBrevoSyncWf01'.
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional
import httpx

from state_store import cancel_post_close_drip, log_request_flow

logger = logging.getLogger("brevo_sync")

TWENTY_BASE_URL = os.environ.get("TWENTY_BASE_URL", "http://192.168.1.240:8085")
TWENTY_API_KEY = os.environ.get("TWENTY_API_KEY", "")
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
BREVO_BASE_URL = "https://api.brevo.com/v3"

ROLE_LIST_DEFAULTS = {
    "customer": 3,
    "buyer": 4,
    "seller": 5,
    "lead": 6,
    "real estate agent": 7,
    "contractor": 8,
    "lender": 9,
}


def _twenty_headers() -> Dict[str, str]:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if TWENTY_API_KEY:
        headers["Authorization"] = f"Bearer {TWENTY_API_KEY}"
    return headers


def _brevo_headers() -> Dict[str, str]:
    return {
        "api-key": BREVO_API_KEY,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def format_e164_sms(raw_phone: str) -> Optional[str]:
    digits = re.sub(r"[^0-9]", "", str(raw_phone or ""))
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    if 10 <= len(digits) <= 15:
        return f"+{digits}"
    return None


async def sync_single_contact_to_brevo(
    email: str,
    name: str,
    phone: str = "",
    role: str = "Customer",
    market: str = "",
    lead_source: str = "Website",
    ext_id: str = "",
    list_map: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """Upserts a single contact into Brevo with role-based list mapping and SMS retry."""
    clean_email = (email or "").strip().lower()
    if not clean_email or not BREVO_API_KEY:
        return {"skipped": True, "reason": "No email or BREVO_API_KEY missing"}

    resolved_map = list_map or ROLE_LIST_DEFAULTS
    target_list_id = resolved_map.get((role or "customer").lower(), resolved_map.get("customer", 3))

    parts = (name or "").strip().split()
    first_name = parts[0] if parts else ""
    last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

    attributes: Dict[str, Any] = {
        "FIRSTNAME": first_name,
        "LASTNAME": last_name,
        "ROLE": role or "Customer",
        "MARKET": market or "",
        "LEAD_SOURCE": lead_source or "Website",
        "EXT_ID": ext_id or "",
    }
    sms = format_e164_sms(phone)
    if sms:
        attributes["SMS"] = sms

    payload = {
        "email": clean_email,
        "attributes": attributes,
        "listIds": [target_list_id],
        "updateEnabled": True,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(f"{BREVO_BASE_URL}/contacts", headers=_brevo_headers(), json=payload)
            if 200 <= resp.status_code < 300:
                return {"ok": True, "status": resp.status_code}
            if resp.status_code == 400 and "SMS" in resp.text and "SMS" in payload["attributes"]:
                del payload["attributes"]["SMS"]
                retry = await client.post(f"{BREVO_BASE_URL}/contacts", headers=_brevo_headers(), json=payload)
                return {"ok": 200 <= retry.status_code < 300, "status": retry.status_code}
            return {"ok": False, "status": resp.status_code, "error": resp.text[:200]}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _is_buyer_or_past_client(person: Dict[str, Any]) -> bool:
    """Returns True if contact is a Buyer or Past Client (must be preserved with canEmail=False)."""
    role = str(person.get("contactRole") or "").strip().lower()
    stage = str(person.get("lifecycleStage") or "").strip().lower()
    past_type = str(person.get("pastClientType") or "").strip().lower()
    return "buyer" in role or "past" in stage or bool(past_type)


async def _apply_brevo_blacklist_to_person(
    client: httpx.AsyncClient,
    person: Dict[str, Any],
    email: str,
) -> str:
    """
    Owner compliance rule:
    - Buyer or Past Client -> Keep in Twenty CRM and mark canEmail = False.
    - Customer / generic -> Delete from Twenty CRM.
    """
    person_id = person.get("id")
    if not person_id:
        return "Contact missing ID in Twenty CRM"

    if _is_buyer_or_past_client(person):
        if person.get("canEmail") is False:
            return "Already marked canEmail = false (Buyer/Past Client)"
        patch_res = await client.patch(
            f"{TWENTY_BASE_URL}/rest/people/{person_id}",
            headers=_twenty_headers(),
            json={"canEmail": False},
        )
        return (
            "Kept Buyer/Past Client in Twenty CRM and marked canEmail = false"
            if 200 <= patch_res.status_code < 300
            else f"Failed to mark canEmail = false (HTTP {patch_res.status_code})"
        )

    del_res = await client.delete(
        f"{TWENTY_BASE_URL}/rest/people/{person_id}",
        headers=_twenty_headers(),
    )
    return (
        "Deleted Customer from Twenty CRM"
        if 200 <= del_res.status_code < 300
        else f"Failed to delete Customer from Twenty CRM (HTTP {del_res.status_code})"
    )


async def handle_brevo_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handles Brevo unsubscribe / hardBounce / complaint / spam events:
    - Cancels any active post-close drip.
    - Buyer / Past Client -> Keep and set canEmail = False.
    - Customer -> Delete from Twenty CRM.
    """
    event = (payload.get("event") or "").strip().lower()
    if event not in ("unsubscribed", "unsubscribe", "hard_bounce", "hardbounce", "complaint", "spam"):
        return {"success": False, "reason": f"Unhandled Brevo event '{event}'"}

    email = (payload.get("email") or "").strip().lower()
    if not email:
        return {"success": False, "reason": "No email in Brevo event"}

    cancel_post_close_drip(email)

    async with httpx.AsyncClient(timeout=15.0) as client:
        find_res = await client.get(
            f"{TWENTY_BASE_URL}/rest/people",
            params={"filter": f"emails.primaryEmail[eq]:{email}"},
            headers=_twenty_headers(),
        )
        people = (find_res.json().get("data") or {}).get("people") or []
        if people:
            action = await _apply_brevo_blacklist_to_person(client, people[0], email)
        else:
            action = "Contact not found in Twenty CRM"

    log_request_flow(
        flow_id=f"brevo_event_{email}_{event}",
        source="Brevo Compliance Webhook",
        title=f"Brevo {event}: {email}",
        status="completed",
        agents_involved=["Miles Miller", "Maya Reyes"],
        steps=[{"step": "Brevo Compliance", "agent": "Miles Miller", "action": action, "status": "ok"}],
        payload_preview={"event": event, "email": email},
        result_summary=action,
        category="crm",
    )
    return {"success": True, "event": event, "email": email, "action": action}


async def reconcile_brevo_blacklists(
    client: Optional[httpx.AsyncClient] = None,
    twenty_people: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Two-way safety net: fetches all emailBlacklisted contacts from Brevo and ensures
    every matching Twenty CRM contact is either deleted (Customer) or marked canEmail=False (Buyer/Past Client).
    """
    if not BREVO_API_KEY or not TWENTY_API_KEY:
        return {"ok": False, "reconciled": 0, "blacklisted_emails": set()}

    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(timeout=20.0)

    blacklisted_emails = set()
    reconciled_actions: List[Dict[str, str]] = []
    try:
        offset = 0
        limit = 100
        while True:
            r = await client.get(
                f"{BREVO_BASE_URL}/contacts?limit={limit}&offset={offset}",
                headers=_brevo_headers(),
            )
            if r.status_code >= 400:
                break
            batch = (r.json() or {}).get("contacts") or []
            for c in batch:
                em = (c.get("email") or "").strip().lower()
                if em and c.get("emailBlacklisted"):
                    blacklisted_emails.add(em)
            if len(batch) < limit:
                break
            offset += limit

        if twenty_people is None:
            t_res = await client.get(f"{TWENTY_BASE_URL}/rest/people?limit=500", headers=_twenty_headers())
            twenty_people = ((t_res.json() or {}).get("data") or {}).get("people") or []

        for p in twenty_people:
            em = ((p.get("emails") or {}).get("primaryEmail") or "").strip().lower()
            if not em or em not in blacklisted_emails:
                continue
            # Skip already-marked Buyer/Past Client to avoid redundant writes
            if _is_buyer_or_past_client(p) and p.get("canEmail") is False:
                continue
            cancel_post_close_drip(em)
            act = await _apply_brevo_blacklist_to_person(client, p, em)
            reconciled_actions.append({"email": em, "action": act})
            log_request_flow(
                flow_id=f"brevo_reconcile_{em}",
                source="Brevo Compliance Reconciliation",
                title=f"Brevo Blacklist Sync: {em}",
                status="completed",
                agents_involved=["Miles Miller", "Maya Reyes"],
                steps=[{"step": "Blacklist Reconciliation", "agent": "Miles Miller", "action": act, "status": "ok"}],
                payload_preview={"email": em},
                result_summary=act,
                category="crm",
            )
    finally:
        if owns_client:
            await client.aclose()

    return {
        "ok": True,
        "blacklisted_count": len(blacklisted_emails),
        "reconciled": len(reconciled_actions),
        "details": reconciled_actions,
        "blacklisted_emails": blacklisted_emails,
    }


async def sync_twenty_to_brevo() -> Dict[str, Any]:
    """Full two-way compliance reconciliation + Twenty CRM -> Brevo contact sync across all role lists."""
    if not BREVO_API_KEY or not TWENTY_API_KEY:
        return {"success": False, "error": "Missing BREVO_API_KEY or TWENTY_API_KEY"}

    async with httpx.AsyncClient(timeout=20.0) as client:
        twenty_res = await client.get(f"{TWENTY_BASE_URL}/rest/people?limit=500", headers=_twenty_headers())
        people = ((twenty_res.json() or {}).get("data") or {}).get("people") or []

        # Step 1: Pull Brevo unsubscribes/bounces -> Twenty CRM before pushing
        recon = await reconcile_brevo_blacklists(client=client, twenty_people=people)
        blacklisted_emails = recon.get("blacklisted_emails") or set()

        # Refresh people list if any contacts were deleted/updated during reconciliation
        if recon.get("reconciled", 0) > 0:
            twenty_res = await client.get(f"{TWENTY_BASE_URL}/rest/people?limit=500", headers=_twenty_headers())
            people = ((twenty_res.json() or {}).get("data") or {}).get("people") or []

        list_res = await client.get(f"{BREVO_BASE_URL}/contacts/lists?limit=50", headers=_brevo_headers())
        brevo_lists = (list_res.json() or {}).get("lists") or []
        list_map: Dict[str, int] = {
            str(l.get("name", "")).lower(): int(l["id"])
            for l in brevo_lists
            if l.get("name") and l.get("id")
        }
        default_list_id = list_map.get("customer", 3)

        synced = 0
        skipped_no_email = 0
        failed = 0

        for p in people:
            email = ((p.get("emails") or {}).get("primaryEmail") or "").strip().lower()
            if not email or p.get("canEmail") is False or email in blacklisted_emails:
                skipped_no_email += 1
                continue

            role = p.get("contactRole") or "Customer"
            role_lower = role.lower()
            target_list_id = list_map.get(role_lower)
            if not target_list_id:
                c_res = await client.post(
                    f"{BREVO_BASE_URL}/contacts/lists",
                    headers=_brevo_headers(),
                    json={"name": role, "folderId": 1},
                )
                if 200 <= c_res.status_code < 300 and c_res.json().get("id"):
                    target_list_id = int(c_res.json()["id"])
                    list_map[role_lower] = target_list_id
                else:
                    target_list_id = default_list_id

            name_obj = p.get("name") or {}
            full_name = f"{name_obj.get('firstName', '')} {name_obj.get('lastName', '')}".strip()
            raw_phone = (p.get("phones") or {}).get("primaryPhoneNumber") or ""

            res = await sync_single_contact_to_brevo(
                email=email,
                name=full_name,
                phone=raw_phone,
                role=role,
                market=p.get("market") or "",
                lead_source=p.get("leadSource") or "",
                ext_id=p.get("id") or "",
                list_map=list_map,
            )
            if res.get("ok"):
                synced += 1
            else:
                failed += 1

    return {
        "success": True,
        "totalTwentyContacts": len(people),
        "syncedToBrevo": synced,
        "skippedNoEmail": skipped_no_email,
        "failed": failed,
        "roleLists": list_map,
    }
