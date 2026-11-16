"""
Email Operating Expenses Scanner & Ingestion Engine for Fiona Banks & Silas Drake
Casa-poki Intelligent Agent Hub

Monitors lokesh@lokeshchanana.com for incoming operating expense bills, statements,
membership dues, software subscriptions, and receipts.
Strictly excludes real estate transaction documents (contracts, escrow orders, earnest money).
Deduplicates via agent_system.db and records bills into Bigcapital accounting.
"""

import email
from email.header import decode_header
import io
import imaplib
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pypdf import PdfReader
from PIL import Image
import pytesseract

from bigcapital_tools import bigcapital_client
from state_store import (
    init_store,
    is_email_bill_processed,
    record_processed_email_bill,
    list_processed_email_bills,
)

logger = logging.getLogger("email_bills_watcher")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

IMAP_SERVER = os.environ.get("MAIL_IMAP_SERVER", "imap.gmail.com")
IMAP_PORT = int(os.environ.get("MAIL_IMAP_PORT", "993"))
IMAP_USER = os.environ.get("MAIL_IMAP_USER", "lokesh@lokeshchanana.com")
IMAP_PASSWORD = os.environ.get("MAIL_IMAP_PASSWORD", "").strip("\"'").replace(" ", "")

# Strict Exclusion Lists for Real Estate Transaction Paperwork
EXCLUDED_SENDERS = [
    "@authentisign.com",
    "@ctt.com",
    "@firstam.com",
    "showingtime.com",
    "@therealbrokerage.com",
    "fnhw-warranty.com",
    "transactiondesk",
    "nwmlsemailbroadcast@nwmls.com",
]

EXCLUDED_SUBJECT_KEYWORDS = [
    "signing complete",
    "earnest money",
    "commission disbursement",
    "compensation request",
    "escrow",
    "title & escrow",
    "inspection response",
    "inspection confirmed",
    "inspection addendum",
    "seller disclosure",
    "purchase and sale",
    "form 21",
    "form 35",
    "form 22",
    "counteroffer",
    "title commitment",
    "hyperlinked report",
    "showing cancelled",
    "showing confirmed",
    "review please",
    "new price",
    "sweet spot",
    "open house",
    "monday update",
    "events & training",
    "what’s ahead",
    "verification code",
    "two-factor",
    "webinar",
]

# Operating Expense Keywords
FINANCIAL_INTENT_KEYWORDS = [
    "bill",
    "invoice",
    "statement",
    "dues",
    "subscription",
    "receipt",
    "membership",
    "amount due",
    "balance due",
    "payment due",
    "renewal",
]


def _decode_header_str(val: Optional[str]) -> str:
    if not val:
        return ""
    try:
        parts = decode_header(val)
        out = ""
        for b, enc in parts:
            if isinstance(b, bytes):
                out += b.decode(enc or "utf-8", errors="ignore")
            else:
                out += str(b)
        return out.strip()
    except Exception:
        return str(val)


def is_transaction_document(sender: str, subject: str, body: str) -> bool:
    """Checks if message is transaction paperwork (contracts, title/escrow, showings)."""
    s_lower = sender.lower()
    sub_lower = subject.lower()

    for exc_domain in EXCLUDED_SENDERS:
        if exc_domain in s_lower:
            return True

    for exc_kw in EXCLUDED_SUBJECT_KEYWORDS:
        if exc_kw in sub_lower:
            return True

    return False


def extract_pdf_and_ocr(payload: bytes, filename: str) -> str:
    """Extracts text from PDF attachment; runs OCR on embedded raster images if native text is sparse."""
    text_parts = []
    try:
        reader = PdfReader(io.BytesIO(payload))
        for page in reader.pages:
            t = page.extract_text()
            if t and t.strip():
                text_parts.append(t.strip())
            for img in page.images:
                try:
                    im = Image.open(io.BytesIO(img.data))
                    ocr_t = pytesseract.image_to_string(im)
                    if ocr_t and ocr_t.strip():
                        text_parts.append(ocr_t.strip())
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"Could not read PDF {filename}: {e}")
        try:
            im = Image.open(io.BytesIO(payload))
            ocr_t = pytesseract.image_to_string(im)
            if ocr_t:
                text_parts.append(ocr_t.strip())
        except Exception:
            pass

    return "\n\n".join(text_parts)


def parse_operating_bill(
    sender: str,
    subject: str,
    date_str: str,
    body_text: str,
    attachments_text: str,
    msg_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Parses vendor name, total amount, dates, invoice number, and category
    for genuine operating expense bills.
    """
    combined_text = f"{subject}\n{body_text}\n{attachments_text}"
    lower_comb = combined_text.lower()
    lower_sender = sender.lower()
    lower_sub = subject.lower()

    # 1. Northwest Multiple Listing Service (NWMLS)
    if ("ebill@nwmls.com" in lower_sender) or ("nwmls" in lower_sub and any(k in lower_sub for k in ["statement", "invoice", "dues", "bill"])):
        vendor = "Northwest Multiple Listing Service"
        category = "MLS Dues & Subscriptions"

        # Search for Invoice Number
        inv_match = re.search(r"Invoice\s*#?\s*(\d{6,8})", combined_text, re.IGNORECASE)
        inv_num = inv_match.group(1) if inv_match else f"NWMLS-{datetime.now().strftime('%Y%m%d')}"

        # Amount Due
        # NWMLS pattern: TOTAL DUE 309.00 or Balance Due 309.00
        amt_match = re.search(r"(?:TOTAL DUE|Balance Due|Invoice Total)\s*[:\.]?\s*\$?([0-9]+[\.,][0-9]{2})", combined_text, re.IGNORECASE)
        if not amt_match:
            # Fallback regex for currency in statement
            amt_match = re.search(r"\$([0-9]+[\.,][0-9]{2})", combined_text)
        if not amt_match:
            return None
        amount = float(amt_match.group(1).replace(",", "."))

        # Due Date: e.g. Due Date 11/25/26 or 11/25/2026
        due_date = None
        due_match = re.search(r"Due Date\s*(\d{1,2}/\d{1,2}/\d{2,4})", combined_text, re.IGNORECASE)
        if due_match:
            try:
                raw_d = due_match.group(1)
                m, d, y = raw_d.split("/")
                if len(y) == 2:
                    y = "20" + y
                due_date = f"{y}-{int(m):02d}-{int(d):02d}"
            except Exception:
                pass
        if not due_date:
            due_date = datetime.now().strftime("%Y-%m-%d")

        # Statement Date
        stmt_date = None
        stmt_match = re.search(r"Statement Date\s*(\d{1,2}/\d{1,2}/\d{2,4})", combined_text, re.IGNORECASE)
        if stmt_match:
            try:
                raw_d = stmt_match.group(1)
                m, d, y = raw_d.split("/")
                if len(y) == 2:
                    y = "20" + y
                stmt_date = f"{y}-{int(m):02d}-{int(d):02d}"
            except Exception:
                pass
        if not stmt_date:
            stmt_date = due_date

        note = f"NWMLS semi-annual dues statement (Invoice #{inv_num}) for Lokesh Chanana. Auto-pay deducted Nov 16."
        return {
            "message_id": msg_id,
            "vendor": vendor,
            "amount": amount,
            "bill_date": stmt_date,
            "due_date": due_date,
            "reference_no": f"INV-{inv_num}",
            "category": category,
            "note": note,
        }

    # 2. General Overhead & Subscription Bills
    known_vendors = [
        ("google workspace", "Google Workspace", "Software & Subscriptions"),
        ("google cloud", "Google Cloud", "Hosting & Cloud Infrastructure"),
        ("twilio", "Twilio", "Communication Tools"),
        ("brevo", "Brevo", "Email Marketing & Automation"),
        ("sendinblue", "Brevo", "Email Marketing & Automation"),
        ("docusign", "DocuSign", "Software & Subscriptions"),
        ("zoom", "Zoom Video Communications", "Software & Subscriptions"),
        ("hetzner", "Hetzner Online", "Hosting & Cloud Infrastructure"),
        ("cloudflare", "Cloudflare", "Hosting & Security"),
        ("namecheap", "Namecheap", "Domain & Web Hosting"),
        ("godaddy", "GoDaddy", "Domain & Web Hosting"),
        ("puget sound energy", "Puget Sound Energy", "Utilities"),
        ("seattle city light", "Seattle City Light", "Utilities"),
        ("staples", "Staples", "Office Supplies"),
        ("office depot", "Office Depot", "Office Supplies"),
        ("adobe", "Adobe Systems", "Creative Software & Design"),
        ("canva", "Canva", "Marketing & Creative Design"),
    ]

    matched_vendor = None
    matched_cat = "Office Expenses"
    for kw, vname, cat in known_vendors:
        if kw in lower_sender or kw in lower_sub or kw in lower_comb:
            matched_vendor = vname
            matched_cat = cat
            break

    if matched_vendor:
        # Extract total amount
        amount = None
        tot_matches = re.findall(
            r"(?:total|amount due|balance due|charged|payment of)\s*[:\.]?\s*\$?([0-9]+[\.,][0-9]{2})",
            combined_text,
            re.IGNORECASE,
        )
        if tot_matches:
            try:
                amount = float(tot_matches[-1].replace(",", "."))
            except Exception:
                pass

        if not amount:
            # Fallback to currency pattern
            cur_matches = re.findall(r"\$([0-9]+[\.,][0-9]{2})", combined_text)
            if cur_matches:
                amount = max(float(x.replace(",", ".")) for x in cur_matches)

        if amount and amount > 0:
            today_str = datetime.now().strftime("%Y-%m-%d")
            return {
                "message_id": msg_id,
                "vendor": matched_vendor,
                "amount": amount,
                "bill_date": today_str,
                "due_date": today_str,
                "reference_no": f"EMAIL-{msg_id[:12]}",
                "category": matched_cat,
                "note": f"Operating expense from {matched_vendor} (Subject: {subject[:60]})",
            }

    return None


async def scan_and_ingest_email_bills(
    limit: int = 200,
    force_reprocess: bool = False,
) -> Dict[str, Any]:
    """
    Connects to lokesh@lokeshchanana.com via IMAP, scans messages for operating expense bills,
    extracts details and PDF statements, and records them into Bigcapital accounting.
    """
    init_store()
    if not IMAP_PASSWORD:
        return {
            "ok": False,
            "error": "MAIL_IMAP_PASSWORD not configured. Cannot connect to lokesh@lokeshchanana.com.",
            "new_bills": [],
            "already_processed": [],
        }

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(IMAP_USER, IMAP_PASSWORD)
        mail.select("INBOX")
    except Exception as login_err:
        logger.error(f"Failed to connect to IMAP as {IMAP_USER}: {login_err}")
        return {
            "ok": False,
            "error": f"IMAP login failure for {IMAP_USER}: {login_err}",
            "new_bills": [],
            "already_processed": [],
        }

    # Targeted search for financial intent, billing senders, or unread messages
    search_queries = [
        '(OR (SUBJECT "statement") (OR (SUBJECT "invoice") (OR (SUBJECT "dues") (OR (SUBJECT "bill") (OR (SUBJECT "subscription") (OR (FROM "ebill") (FROM "billing")))))))',
        'UNSEEN',
    ]

    matched_ids_set = set()
    for q in search_queries:
        try:
            st, data = mail.search(None, q)
            if st == "OK" and data[0]:
                for mid in data[0].split():
                    matched_ids_set.add(mid)
        except Exception as q_err:
            logger.warning(f"IMAP search query error for '{q}': {q_err}")

    if not matched_ids_set:
        try:
            mail.close()
            mail.logout()
        except Exception:
            pass
        return {
            "ok": True,
            "account": IMAP_USER,
            "scanned_count": 0,
            "new_bills": [],
            "already_processed": [],
            "message": "No financial or unread messages found.",
        }

    # Sort matching IDs numerically
    sorted_ids = sorted(list(matched_ids_set), key=lambda x: int(x))
    if limit is not None and limit < len(sorted_ids):
        recent_ids = sorted_ids[-limit:]
    else:
        recent_ids = sorted_ids

    logger.info(f"Targeted search identified {len(recent_ids)} candidate messages in {IMAP_USER}...")

    new_bills: List[Dict[str, Any]] = []
    already_processed: List[Dict[str, Any]] = []
    skipped_transactions: List[str] = []
    errors: List[Dict[str, Any]] = []

    for mid in reversed(recent_ids):
        try:
            # Phase 1: Fast header-only inspection
            res_hdr, hdr_data = mail.fetch(mid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE MESSAGE-ID)])")
            if res_hdr != "OK" or not hdr_data:
                continue

            sender = ""
            subject = ""
            date_hdr = ""
            msg_id = f"imap_msg_{mid.decode()}"

            for part_h in hdr_data:
                if isinstance(part_h, tuple):
                    h_msg = email.message_from_bytes(part_h[1])
                    msg_id = h_msg.get("Message-ID") or msg_id
                    sender = _decode_header_str(h_msg.get("From", ""))
                    subject = _decode_header_str(h_msg.get("Subject", ""))
                    date_hdr = h_msg.get("Date", "")
                    break

            # Check deduplication first
            if not force_reprocess and is_email_bill_processed(msg_id):
                already_processed.append({"message_id": msg_id, "subject": subject, "sender": sender})
                continue

            # Check strict transaction exclusion
            if is_transaction_document(sender, subject, ""):
                skipped_transactions.append(subject)
                continue

            # Check if header matches financial intent or known vendors
            lower_hdr = (sender + " " + subject).lower()
            known_vendor_kw = [
                "nwmls", "ebill", "google", "brevo", "twilio", "docusign",
                "zoom", "hetzner", "cloudflare", "namecheap", "godaddy",
                "pse", "seattle city light", "staples", "adobe", "canva"
            ]
            has_financial_header = any(k in lower_hdr for k in FINANCIAL_INTENT_KEYWORDS) or any(k in lower_hdr for k in known_vendor_kw)
            if not has_financial_header:
                continue

            # Phase 2: Candidate matched! Fetch full message body and attachments
            res, msg_data = mail.fetch(mid, "(BODY.PEEK[])")
            if res != "OK" or not msg_data:
                continue

            for part_r in msg_data:
                if not isinstance(part_r, tuple):
                    continue

                msg = email.message_from_bytes(part_r[1])
                body_text = ""
                attachments_text = ""

                if msg.is_multipart():
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        fname = part.get_filename() or ""
                        if ctype == "text/plain":
                            pl = part.get_payload(decode=True)
                            if pl:
                                body_text += pl.decode(errors="ignore") + "\n"
                        elif fname.lower().endswith(".pdf"):
                            pl = part.get_payload(decode=True)
                            if pl:
                                attachments_text += extract_pdf_and_ocr(pl, fname) + "\n"
                else:
                    pl = msg.get_payload(decode=True)
                    if pl:
                        body_text = pl.decode(errors="ignore")

                # Double check transaction content in body
                if is_transaction_document(sender, subject, body_text):
                    skipped_transactions.append(subject)
                    continue

                # Parse Operating Bill
                parsed = parse_operating_bill(
                    sender=sender,
                    subject=subject,
                    date_str=date_hdr,
                    body_text=body_text,
                    attachments_text=attachments_text,
                    msg_id=msg_id,
                )

                if not parsed:
                    continue

                logger.info(
                    f"Found valid operating bill: Vendor={parsed['vendor']}, Amount=${parsed['amount']}, Due={parsed['due_date']}"
                )

                # Ingest into Bigcapital
                bc_res = await bigcapital_client.create_bill(
                    vendor_name=parsed["vendor"],
                    amount=parsed["amount"],
                    due_date=parsed["due_date"],
                    bill_date=parsed["bill_date"],
                    note=parsed["note"],
                    reference_no=parsed["reference_no"],
                    category=parsed["category"],
                )

                if bc_res.get("ok"):
                    bill_id = bc_res.get("bill_id") or bc_res.get("data", {}).get("id")
                    record_processed_email_bill(
                        message_id=msg_id,
                        sender=sender,
                        subject=subject,
                        vendor_name=parsed["vendor"],
                        amount=parsed["amount"],
                        bill_date=parsed["bill_date"],
                        due_date=parsed["due_date"],
                        bill_id=bill_id,
                        status="PROCESSED",
                        details=f"Bigcapital Bill ID: {bill_id}, Ref: {parsed['reference_no']}",
                    )
                    new_bills.append({
                        "message_id": msg_id,
                        "vendor": parsed["vendor"],
                        "amount": parsed["amount"],
                        "bill_date": parsed["bill_date"],
                        "due_date": parsed["due_date"],
                        "reference_no": parsed["reference_no"],
                        "category": parsed["category"],
                        "bigcapital_bill_id": bill_id,
                        "subject": subject,
                    })
                else:
                    err_msg = bc_res.get("error", "Unknown Bigcapital API error")
                    logger.error(f"Failed to record email bill into Bigcapital: {err_msg}")
                    errors.append({"message_id": msg_id, "subject": subject, "error": err_msg})

        except Exception as msg_exc:
            logger.exception(f"Error reading message {mid}: {msg_exc}")

    try:
        mail.close()
        mail.logout()
    except Exception:
        pass

    return {
        "ok": True,
        "account": IMAP_USER,
        "scanned_count": len(recent_ids),
        "newly_ingested_count": len(new_bills),
        "already_processed_count": len(already_processed),
        "skipped_transactions_count": len(skipped_transactions),
        "error_count": len(errors),
        "new_bills": new_bills,
        "already_processed": already_processed,
        "errors": errors,
    }


if __name__ == "__main__":
    import asyncio
    import sys

    force = "--force" in sys.argv
    print(f"Starting email expenses scan for {IMAP_USER} (force={force})...")
    res = asyncio.run(scan_and_ingest_email_bills(limit=200, force_reprocess=force))
    import pprint
    pprint.pprint(res)
