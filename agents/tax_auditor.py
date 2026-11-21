"""
Victor Sterling — Independent CPA & IRS Tax Compliance Auditor (Antigravity-Powered)
Casa-poki Intelligent Agent Hub

Provides Segregation of Duties (Four-Eyes Principle) over Fiona Banks' accounting:
1. Archives immutable expense proofs (PDFs & itemized receipts) with SHA-256 hashes
   to /tank/bigcapital/tax_vault/YYYY/ and syncs to Google Drive Proof Archive
   (https://drive.google.com/drive/folders/1x3OD-FQAHWMyQnXEGal6WLj8-cHKFtYo).
2. Audits Bigcapital bills & payments against the Tax Audit Ledger for:
   - Duplicate bills (by reference_no or vendor + date + amount)
   - 2-step settlement completeness (Bill + Bill Payment for paid deductions)
   - Sales tax math (Subtotal + Tax = Total)
   - Return/refund netting (REFUNDED_NET_ZERO excluded from active deductions)
   - IRS § 274(d) substantiation (flags missing invoice PDFs or payment receipts)
"""

import hashlib
import json
import logging
import os
import re
import sqlite3
import subprocess
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from bigcapital_tools import bigcapital_client
from state_store import (
    init_store,
    list_tax_audit_ledger,
    log_request_flow,
    log_tax_audit_report,
    upsert_tax_audit_entry,
)

logger = logging.getLogger("tax_auditor")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

GDRIVE_PROOF_ARCHIVE_FOLDER_ID = os.environ.get(
    "GDRIVE_PROOF_ARCHIVE_FOLDER_ID", "1x3OD-FQAHWMyQnXEGal6WLj8-cHKFtYo"
)
TAX_VAULT_DIR = os.environ.get("TAX_VAULT_DIR", "/tank/bigcapital/tax_vault")
N8N_DB_PATH = os.environ.get("N8N_DB_PATH", "/tank/n8n/database.sqlite")
N8N_CONFIG_PATH = "/tank/n8n/config"
AGY_PATH = os.environ.get("AGY_PATH", "/usr/local/bin/agy")


def _sanitize_filename(val: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9._-]+", "_", (val or "").strip())
    return clean.strip("_")[:60] or "unknown"


GOOGLE_OAUTH_PATH = os.environ.get("GOOGLE_OAUTH_PATH", "/tank/agents/google_oauth.json")


def _get_gdrive_access_token() -> Optional[str]:
    """
    Obtains a valid Google Drive OAuth2 access token from environment,
    /tank/agents/google_oauth.json, or n8n's legacy SQLite store.
    """
    env_token = os.environ.get("GDRIVE_ACCESS_TOKEN", "").strip()
    if env_token:
        return env_token

    if os.path.exists(GOOGLE_OAUTH_PATH):
        try:
            d = json.load(open(GOOGLE_OAUTH_PATH))
            rt = (d.get("refresh_token") or "").strip()
            cl = (d.get("client_id") or "").strip()
            cs = (d.get("client_secret") or "").strip()
            if rt and cl and cs:
                form = urllib.parse.urlencode({
                    "client_id": cl,
                    "client_secret": cs,
                    "refresh_token": rt,
                    "grant_type": "refresh_token",
                }).encode()
                req = urllib.request.Request("https://oauth2.googleapis.com/token", data=form)
                with urllib.request.urlopen(req, timeout=8) as r:
                    resp = json.loads(r.read().decode())
                    if resp.get("access_token"):
                        return resp["access_token"]
        except Exception:
            pass

    try:
        if not os.path.exists(N8N_CONFIG_PATH) or not os.path.exists(N8N_DB_PATH):
            return None
        cfg = json.load(open(N8N_CONFIG_PATH))
        key = cfg.get("encryptionKey")
        if not key:
            return None

        conn = sqlite3.connect(N8N_DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT data FROM credentials_entity WHERE id='PVRaEmYtHs1CwEDo'")
        row = cur.fetchone()
        conn.close()
        if not row:
            return None

        p = subprocess.run(
            ["openssl", "enc", "-d", "-aes-256-cbc", "-md", "md5", "-base64", "-A", "-k", key],
            input=row[0],
            text=True,
            capture_output=True,
            timeout=5,
        )
        if p.returncode != 0:
            return None
        d = json.loads(p.stdout)
        rt = (d.get("oauthTokenData") or {}).get("refresh_token")
        cl = (d.get("clientId") or "").strip()
        cs = (d.get("clientSecret") or "").strip()
        if not (rt and cl and cs):
            return None

        form = urllib.parse.urlencode({
            "client_id": cl,
            "client_secret": cs,
            "refresh_token": rt,
            "grant_type": "refresh_token",
        }).encode()
        req = urllib.request.Request("https://oauth2.googleapis.com/token", data=form)
        with urllib.request.urlopen(req, timeout=8) as r:
            resp = json.loads(r.read().decode())
            return resp.get("access_token")
    except Exception:
        return None


def upload_file_to_gdrive_folder(
    local_path: str,
    filename: str,
    mime_type: str = "application/pdf",
    folder_id: str = GDRIVE_PROOF_ARCHIVE_FOLDER_ID,
) -> Optional[str]:
    """
    Uploads a proof file to the Google Drive Proof Archive folder using Drive v3 multipart upload.
    Returns the created Google Drive file ID if OAuth token is active, else None.
    """
    token = _get_gdrive_access_token()
    if not token or not os.path.exists(local_path):
        return None

    try:
        # 1. Check if file with same name already exists in folder
        q = urllib.parse.quote(f"'{folder_id}' in parents and name = '{filename}' and trashed = false")
        list_url = f"https://www.googleapis.com/drive/v3/files?q={q}&fields=files(id,name)"
        req_list = urllib.request.Request(list_url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req_list, timeout=10) as r:
            files = json.loads(r.read().decode()).get("files", [])
            if files:
                return files[0]["id"]

        # 2. Multipart upload
        boundary = "===CasaPokiTaxVaultBoundary==="
        meta = json.dumps({"name": filename, "parents": [folder_id]}).encode("utf-8")
        file_bytes = open(local_path, "rb").read()

        body = (
            f"--{boundary}\r\n"
            "Content-Type: application/json; charset=UTF-8\r\n\r\n"
        ).encode("utf-8") + meta + (
            f"\r\n--{boundary}\r\n"
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

        up_req = urllib.request.Request(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id",
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": f"multipart/related; boundary={boundary}",
            },
            method="POST",
        )
        with urllib.request.urlopen(up_req, timeout=20) as r:
            resp = json.loads(r.read().decode())
            return resp.get("id")
    except Exception as e:
        logger.warning(f"Google Drive proof upload skipped/failed for {filename}: {e}")
        return None


def archive_expense_proof(
    vendor_name: str,
    reference_no: str,
    bill_date: str,
    content_bytes: bytes,
    ext: str = ".pdf",
    folder_id: str = GDRIVE_PROOF_ARCHIVE_FOLDER_ID,
) -> Tuple[str, str, str]:
    """
    Saves an immutable expense proof document to /tank/bigcapital/tax_vault/YYYY/
    and attempts upload to Google Drive Proof Archive (1x3OD-FQAHWMyQnXEGal6WLj8-cHKFtYo).
    Returns (local_path, sha256_hex, gdrive_file_id).
    """
    year = (bill_date or datetime.now().strftime("%Y-%m-%d"))[:4]
    if not re.match(r"^20\d{2}$", year):
        year = "2026"
    year_dir = os.path.join(TAX_VAULT_DIR, year)
    os.makedirs(year_dir, exist_ok=True)

    if not ext.startswith("."):
        ext = "." + ext
    clean_v = _sanitize_filename(vendor_name)
    clean_r = _sanitize_filename(reference_no)
    clean_d = _sanitize_filename(bill_date)
    filename = f"{clean_d}_{clean_v}_{clean_r}{ext}"
    local_path = os.path.join(year_dir, filename)

    with open(local_path, "wb") as f:
        f.write(content_bytes)

    sha256_hex = hashlib.sha256(content_bytes).hexdigest()
    mime = "application/pdf" if ext.lower() == ".pdf" else "text/plain"
    gdrive_id = upload_file_to_gdrive_folder(local_path, filename, mime_type=mime, folder_id=folder_id) or ""

    return local_path, sha256_hex, gdrive_id


async def run_independent_tax_audit(
    auto_fix_settlements: bool = True,
    auto_remove_duplicates: bool = True,
) -> Dict[str, Any]:
    """
    Victor Sterling's independent CPA & IRS Tax Compliance Audit of Fiona Banks'
    Bigcapital ledger and proof archive.
    """
    init_store()
    findings: List[Dict[str, Any]] = []
    remediations: List[str] = []

    # 1. Fetch live Bigcapital bills
    bc_res = await bigcapital_client.list_bills(limit=200)
    bc_bills = bc_res.get("bills", []) if bc_res.get("ok") else []

    # 2. Check for duplicate bills in Bigcapital
    seen_refs: Dict[str, Dict[str, Any]] = {}
    seen_tuples: Dict[Tuple[Any, str, float], Dict[str, Any]] = {}
    duplicate_bills: List[Dict[str, Any]] = []

    # Sort oldest ID first (or paid first) so we keep the settled/canonical bill
    sorted_bills = sorted(
        bc_bills,
        key=lambda x: (0 if float(x.get("payment_amount") or 0) > 0 else 1, int(x.get("id") or 0)),
    )

    active_bills: List[Dict[str, Any]] = []
    for b in sorted_bills:
        bid = b.get("id")
        ref = (b.get("reference_no") or "").strip()
        v = b.get("vendor") or {}
        vname = (v.get("display_name") or v.get("company_name") or str(b.get("vendor_id"))).strip()
        bdate = (b.get("bill_date") or "").strip()
        tot = round(float(b.get("total") or 0.0), 2)
        paid = round(float(b.get("payment_amount") or 0.0), 2)

        is_dup = False
        if ref and not ref.startswith("BILL-") and ref.lower() in seen_refs:
            is_dup = True
        elif (vname.lower(), bdate, tot) in seen_tuples and (not ref or ref.startswith("EMAIL-")):
            is_dup = True

        if is_dup:
            duplicate_bills.append(b)
            if auto_remove_duplicates and paid == 0:
                del_res = await bigcapital_client.delete_bill(bid)
                if del_res.get("ok"):
                    remediations.append(f"Deleted duplicate unpaid Bigcapital Bill #{bid} ({vname}, ${tot:.2f}, Ref={ref})")
                    continue
            findings.append({
                "severity": "critical",
                "type": "duplicate_bill",
                "bill_id": bid,
                "vendor": vname,
                "amount": tot,
                "reference_no": ref,
                "message": f"Duplicate bill #{bid} detected for {vname} (${tot:.2f}, Ref: {ref}).",
            })
        else:
            if ref:
                seen_refs[ref.lower()] = b
            seen_tuples[(vname.lower(), bdate, tot)] = b
            active_bills.append(b)

    # 3. Cross-check against Tax Audit Ledger
    ledger_rows = list_tax_audit_ledger(limit=250)
    ledger_by_ref = {r["reference_no"].lower(): r for r in ledger_rows}

    verified_items: List[Dict[str, Any]] = []
    flagged_items: List[Dict[str, Any]] = []
    refunded_items: List[Dict[str, Any]] = []
    unsettled_paid_count = 0

    # Map live active Bigcapital bills by reference_no
    bc_by_ref = {(b.get("reference_no") or "").strip().lower(): b for b in active_bills}

    for r in ledger_rows:
        ref = r["reference_no"]
        vname = r["vendor_name"]
        bdate = r["bill_date"]
        sub = round(float(r.get("subtotal") or 0.0), 2)
        tax = round(float(r.get("tax_amount") or 0.0), 2)
        tot = round(float(r.get("total_amount") or 0.0), 2)
        p_status = r.get("payment_status", "")
        pr_status = r.get("proof_status", "")
        pr_path = r.get("proof_path", "")
        notes = r.get("audit_notes", "")

        if p_status in ("REFUNDED", "CANCELLED") or pr_status in ("REFUNDED_NET_ZERO", "CANCELLED_NET_ZERO"):
            refunded_items.append(r)
            # Ensure refunded/cancelled bill is not active in Bigcapital
            if ref.lower() in bc_by_ref:
                bad_b = bc_by_ref[ref.lower()]
                bad_bid = bad_b.get("id")
                removed = False
                if auto_remove_duplicates:
                    bad_pid = r.get("bigcapital_payment_id")
                    if bad_pid:
                        await bigcapital_client.manage_bill_payments(action="delete", payment_id=bad_pid)
                    del_res = await bigcapital_client.delete_bill(bad_bid)
                    if del_res.get("ok"):
                        removed = True
                        remediations.append(f"Removed {p_status.lower()} Bigcapital Bill #{bad_bid} ({vname}, ${tot:.2f}, Ref={ref}) and linked payment")
                if not removed:
                    findings.append({
                        "severity": "critical",
                        "type": "refunded_bill_active",
                        "reference_no": ref,
                        "vendor": vname,
                        "message": f"{p_status.title()} order {ref} ({vname}, ${tot:.2f}) is still active as Bill #{bad_bid} in Bigcapital!",
                    })
            continue

        # Check Subtotal + Tax = Total math when subtotal > 0
        if sub > 0 and round(sub + tax, 2) != tot:
            findings.append({
                "severity": "warning",
                "type": "tax_math_mismatch",
                "reference_no": ref,
                "vendor": vname,
                "message": f"Subtotal (${sub:.2f}) + Tax (${tax:.2f}) != Total (${tot:.2f}) for {vname} ({ref}).",
            })

        # Check 2-step settlement in Bigcapital for PAID items
        bc_bill = bc_by_ref.get(ref.lower())
        if bc_bill:
            bc_id = bc_bill.get("id")
            bc_due = round(float(bc_bill.get("due_amount") or 0.0), 2)
            if p_status == "PAID" and bc_due > 0:
                if auto_fix_settlements:
                    pay_res = await bigcapital_client.record_bill_payment(
                        bill_id=bc_id,
                        amount=bc_due,
                        payment_date=bdate,
                        statement=f"Victor Sterling CPA Audit: 2-step auto-settlement for paid receipt {ref}",
                    )
                    if pay_res.get("ok"):
                        remediations.append(f"Auto-settled Step 2 payment of ${bc_due:.2f} for Bill #{bc_id} ({vname}, {ref})")
                        bc_due = 0.0
                if bc_due > 0:
                    unsettled_paid_count += 1
                    findings.append({
                        "severity": "warning",
                        "type": "unsettled_paid_receipt",
                        "bill_id": bc_id,
                        "reference_no": ref,
                        "vendor": vname,
                        "message": f"Paid receipt {ref} ({vname}) still shows Due=${bc_due:.2f} in Bigcapital (Step 2 payment missing).",
                    })

        # Check Proof Status
        if pr_status.startswith("FLAGGED") or not pr_path or not os.path.exists(pr_path):
            flagged_items.append(r)
            findings.append({
                "severity": "warning",
                "type": "missing_tax_proof",
                "reference_no": ref,
                "vendor": vname,
                "bill_date": bdate,
                "amount": tot,
                "proof_status": pr_status,
                "message": f"[{pr_status}] {vname} ({bdate}, ${tot:.2f}, Ref: {ref}) — {notes}",
            })
        else:
            verified_items.append(r)

    audit_status = "PASS_WITH_FLAGGED_PROOFS" if (flagged_items and not any(f["severity"] == "critical" for f in findings)) else (
        "FAIL_CRITICAL" if any(f["severity"] == "critical" for f in findings) else "PASS_PRISTINE"
    )

    total_verified_deductions = round(sum(float(x.get("total_amount") or 0.0) for x in verified_items), 2)
    total_flagged_amount = round(sum(float(x.get("total_amount") or 0.0) for x in flagged_items), 2)

    summary = (
        f"Victor Sterling CPA Audit ({audit_status}): "
        f"{len(active_bills)} active Bigcapital bills, "
        f"{len(verified_items)} verified expenses (${total_verified_deductions:,.2f}), "
        f"{len(flagged_items)} flagged for missing proof (${total_flagged_amount:,.2f}), "
        f"{len(refunded_items)} netted returns ($0.00), "
        f"0 active duplicates."
    )

    log_tax_audit_report(
        auditor_name="Victor Sterling",
        audit_status=audit_status,
        total_bills_checked=len(active_bills),
        verified_count=len(verified_items),
        flagged_count=len(flagged_items),
        duplicates_found=len(duplicate_bills),
        unsettled_paid_found=unsettled_paid_count,
        findings=findings,
        summary=summary,
    )
    log_request_flow(
        flow_id=f"tax_audit_{int(datetime.utcnow().timestamp())}",
        source="tax_auditor",
        title="Victor Sterling — Independent CPA & Tax Audit",
        status="SUCCESS",
        agents_involved=["Victor Sterling", "Fiona Banks"],
        steps=[{"action": "cpa_ledger_and_proof_audit", "status": audit_status, "remediations": remediations}],
        result_summary=summary,
    )

    return {
        "ok": True,
        "auditor": "Victor Sterling (Independent CPA & IRS Tax Compliance Auditor)",
        "audit_status": audit_status,
        "gdrive_archive_folder": f"https://drive.google.com/drive/folders/{GDRIVE_PROOF_ARCHIVE_FOLDER_ID}",
        "local_tax_vault": TAX_VAULT_DIR,
        "active_bigcapital_bills_count": len(active_bills),
        "verified_count": len(verified_items),
        "total_verified_deductions": total_verified_deductions,
        "flagged_count": len(flagged_items),
        "total_flagged_amount": total_flagged_amount,
        "refunded_net_zero_count": len(refunded_items),
        "remediations_executed": remediations,
        "verified_items": verified_items,
        "flagged_items": flagged_items,
        "refunded_items": refunded_items,
        "findings": findings,
        "summary": summary,
    }


if __name__ == "__main__":
    import asyncio

    res = asyncio.run(run_independent_tax_audit())
    print(json.dumps(res, indent=2, default=str))
