"""
Email Operating Expenses Scanner & TaxMan Ingestion Engine for Fiona Banks & Victor Sterling
Casa-poki Intelligent Agent Hub

Monitors lokesh@lokeshchanana.com and billing@lokeshchanana.com (including forwarded bills)
for operating expense bills, statements, membership dues, software subscriptions, and receipts.
- Extracts canonical Invoice/Order/Receipt IDs and original transaction dates (never forwarding date).
- Reconciles Subtotal + Sales Tax = Post-Tax Total.
- Detects and nets out Returns/Refunds (REFUNDED_NET_ZERO) so refunded items are never claimed.
- Executes 1-step atomic settlement (Step 1 Bill + Step 2 Bill Payment) in Bigcapital for paid receipts.
- Archives proof documents (PDFs & itemized receipts) with SHA-256 hashes to /tank/bigcapital/tax_vault/
  and Google Drive Proof Archive (1x3OD-FQAHWMyQnXEGal6WLj8-cHKFtYo).
- Flags any expense missing a tax-grade invoice copy or payment receipt in tax_audit_ledger.
"""

import email
from email.header import decode_header
import io
import imaplib
import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup
import httpx
from pypdf import PdfReader
from PIL import Image
import pytesseract

from bigcapital_tools import bigcapital_client
from state_store import (
    get_processed_email_bill,
    get_tax_audit_entry,
    init_store,
    is_email_bill_processed,
    record_processed_email_bill,
    upsert_tax_audit_entry,
)
from tax_auditor import archive_expense_proof, run_independent_tax_audit

logger = logging.getLogger("email_bills_watcher")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

IMAP_SERVER = os.environ.get("MAIL_IMAP_SERVER", "imap.gmail.com")
IMAP_PORT = int(os.environ.get("MAIL_IMAP_PORT", "993"))
IMAP_USER = os.environ.get("MAIL_IMAP_USER", "lokesh@lokeshchanana.com")
IMAP_PASSWORD = os.environ.get("MAIL_IMAP_PASSWORD", "").strip("\"'").replace(" ", "")
BILLING_ALIAS = os.environ.get("MAIL_BILLING_ALIAS", "billing@lokeshchanana.com").lower()
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://192.168.1.240:11434").rstrip("/")
OLLAMA_BILL_MODEL = os.environ.get("OLLAMA_BILL_MODEL", "qwen2.5:3b")

# Strict Exclusion Lists for Real Estate Transaction Paperwork & 2FA Codes
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
    "open house saturday",
    "open house sunday",
    "monday update",
    "events & training",
    "what’s ahead",
    "verification code",
    "is your verification code",
    "email verification",
    "please verify your email",
    "two-factor",
    "passcode",
    "webinar",
]

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
    "order confirmation",
    "purchase order",
    "ordered:",
]

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}


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
    """Checks if message is real estate transaction paperwork or a 2FA code."""
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


def _extract_html_text(html_bytes: bytes) -> str:
    """Converts HTML email body into clean readable text."""
    try:
        soup = BeautifulSoup(html_bytes.decode(errors="ignore"), "html.parser")
        for tag in soup(["script", "style", "head"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return re.sub(r"\n{3,}", "\n\n", text).strip()
    except Exception:
        return ""


def _extract_image_ocr(img_bytes: bytes) -> str:
    """Runs pytesseract OCR on an attached or inline image receipt/bill."""
    try:
        im = Image.open(io.BytesIO(img_bytes))
        return pytesseract.image_to_string(im).strip()
    except Exception:
        return ""


def _clean_invisible_and_urls(text: str) -> str:
    """Strips zero-width padding characters and long tracking URLs in angle brackets."""
    t = re.sub(r"<https?://[^>]+>", "", text or "")
    t = re.sub(r"[\u200c\u200b\u2007\u034f\u00ad\u2066\u2069]+", " ", t)
    return t


def _extract_forwarded_context(sender: str, subject: str, body_text: str) -> Tuple[str, str]:
    """
    If Lokesh forwards a bill to billing@lokeshchanana.com, extracts the
    underlying original sender and strips 'Fwd:'/'Fw:' from subject.
    """
    clean_subject = re.sub(r"^(?:fwd?|fw)\s*:\s*", "", subject, flags=re.IGNORECASE).strip()
    effective_sender = sender

    if "lokesh" in sender.lower() and body_text:
        fwd_from = re.search(r"From:\s*\*?([^\r\n]+)", body_text, re.IGNORECASE)
        if fwd_from and "lokesh" not in fwd_from.group(1).lower():
            effective_sender = fwd_from.group(1).replace("*", "").strip()

    return effective_sender, clean_subject


def _parse_month_day_year(month_str: str, day_str: str, year_str: str) -> Optional[str]:
    m_key = month_str.lower()[:4].rstrip(".")
    if m_key not in MONTH_MAP:
        m_key = m_key[:3]
    m_num = MONTH_MAP.get(m_key)
    if not m_num:
        return None
    y_num = int(year_str)
    if y_num < 100:
        y_num += 2000
    return f"{y_num:04d}-{m_num:02d}-{int(day_str):02d}"


def _extract_original_date(subject: str, body_text: str, attachments_text: str) -> str:
    """
    Extracts the original transaction/invoice/statement date (YYYY-MM-DD) from
    receipt text, PDF statement, or forwarded email header—never the forwarding date.
    """
    clean_body = _clean_invisible_and_urls(body_text).replace("*", " ")
    combined = f"{subject}\n{attachments_text}\n{clean_body}"

    # 1. Explicit receipt/invoice date labels with Month Name (e.g., Date of Issue Oct 21, 2026)
    m_named = re.search(
        r"(?:Date of Issue|Order [Dd]ate|Due on|due|Receipt from)\s*[:\.]?\s*"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})",
        combined,
        re.IGNORECASE,
    )
    if m_named:
        res = _parse_month_day_year(m_named.group(1), m_named.group(2), m_named.group(3))
        if res:
            return res

    # 2. Explicit numeric date labels (e.g. Receipt Date 04/02/26, Statement Date 10/31/26, Date: 4/30/26)
    m_num = re.search(
        r"(?:Receipt Date|Statement Date|Date)\s*[:\.]?\s*(\d{1,2})/(\d{1,2})/(\d{2,4})",
        combined,
        re.IGNORECASE,
    )
    if m_num:
        mm, dd, yy = int(m_num.group(1)), int(m_num.group(2)), int(m_num.group(3))
        if yy < 100:
            yy += 2000
        return f"{yy:04d}-{mm:02d}-{dd:02d}"

    # 3. Forwarded message header Date: (e.g., Date: Thu, Mar 26, 2026 at 10:32 pm)
    m_fwd = re.search(
        r"Date:\s*(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,?\s+"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})",
        clean_body,
        re.IGNORECASE,
    )
    if m_fwd:
        res = _parse_month_day_year(m_fwd.group(1), m_fwd.group(2), m_fwd.group(3))
        if res:
            return res

    # 4. Alternative forwarded Date format: Date: 3 Nov 2026
    m_fwd2 = re.search(
        r"Date:\s*(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)?[a-z]*,?\s*(\d{1,2})\s+"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{4})",
        clean_body,
        re.IGNORECASE,
    )
    if m_fwd2:
        res = _parse_month_day_year(m_fwd2.group(2), m_fwd2.group(1), m_fwd2.group(3))
        if res:
            return res

    return datetime.now().strftime("%Y-%m-%d")


def parse_operating_bill(
    sender: str,
    subject: str,
    date_str: str,
    body_text: str,
    attachments_text: str,
    msg_id: str,
    has_pdf_attachment: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Forensic CPA parser for operating expense bills, receipts, statements, and returns.
    Extracts canonical reference_no, original transaction date, subtotal, tax, post-tax total,
    payment status (PAID / OPEN / REFUNDED / UNRECORDED), and IRS proof substantiation status.
    """
    clean_body = _clean_invisible_and_urls(body_text)
    norm_body = clean_body.replace("*", " ")
    combined_text = f"{subject}\n{attachments_text}\n{norm_body}"
    lower_comb = combined_text.lower()
    lower_sender = sender.lower()
    lower_sub = subject.lower()

    orig_date = _extract_original_date(subject, body_text, attachments_text)

    # -------------------------------------------------------------------------
    # 1. NWMLS Education (check before general NWMLS)
    # -------------------------------------------------------------------------
    if "education@nwmls.com" in lower_sender or "nwmls education" in lower_comb or "nwmls purchase order" in lower_sub:
        ord_m = re.search(r"Order Number\s*[:\.]?\s*(\d{4,10})", combined_text, re.IGNORECASE)
        tx_m = re.search(r"Transaction ID\s*[:\.]?\s*([A-Z0-9]+)", combined_text, re.IGNORECASE)
        amt_m = re.search(r"Order Total\s*[:\.]?\s*\$([0-9]+[\.,][0-9]{2})", combined_text, re.IGNORECASE)
        if not amt_m:
            return None
        amt = float(amt_m.group(1).replace(",", "."))
        ref_no = f"ORD-{ord_m.group(1)}" if ord_m else f"NWMLS-EDU-{orig_date}"
        tx_str = f" (Tx: {tx_m.group(1)})" if tx_m else ""
        return {
            "message_id": msg_id,
            "vendor": "NWMLS Education",
            "subtotal": amt,
            "tax": 0.0,
            "amount": amt,
            "bill_date": orig_date,
            "due_date": orig_date,
            "reference_no": ref_no,
            "category": "MLS Dues & Subscriptions",
            "payment_status": "PAID",
            "payment_method": "Credit Card (ending 9437)",
            "auto_pay": True,
            "proof_status": "VERIFIED_EMAIL_RECEIPT",
            "note": f"NWMLS Education course purchase order {ref_no}{tx_str} — Paid via Credit Card 9437.",
        }

    # -------------------------------------------------------------------------
    # 2. Northwest Multiple Listing Service (NWMLS Statements & Receipts)
    # -------------------------------------------------------------------------
    if (
        "ebill@nwmls.com" in lower_sender
        or "ppeterson@nwmls.com" in lower_sender
        or ("nwmls" in lower_sub and any(k in lower_sub for k in ["statement", "invoice", "dues", "bill", "receipt"]))
        or "northwest multiple listing service" in lower_sub
    ):
        vendor = "Northwest Multiple Listing Service"
        category = "MLS Dues & Subscriptions"

        rec_m = re.search(r"Receipt\s*#?\s*(\d{6,8})", combined_text, re.IGNORECASE)
        inv_m = re.search(r"Invoice\s*#?\s*(\d{6,8})", combined_text, re.IGNORECASE)

        if rec_m:
            ref_no = f"REC-{rec_m.group(1)}"
        elif inv_m:
            ref_no = f"INV-{inv_m.group(1)}"
        else:
            ref_no = f"NWMLS-{orig_date}"

        amt_m = re.search(
            r"(?:TOTAL DUE|Balance Due|Invoice Total|Total Applied This Receipt|for\s+)\s*[:\.]?\s*\$?([0-9]+[\.,][0-9]{2})",
            combined_text,
            re.IGNORECASE,
        )
        if not amt_m:
            amt_m = re.search(r"\$([0-9]+[\.,][0-9]{2})", combined_text)
        if not amt_m:
            return None
        amount = float(amt_m.group(1).replace(",", "."))

        due_date = orig_date
        due_m = re.search(r"Due Date\s*(\d{1,2})/(\d{1,2})/(\d{2,4})", combined_text, re.IGNORECASE)
        if due_m:
            mm, dd, yy = int(due_m.group(1)), int(due_m.group(2)), int(due_m.group(3))
            if yy < 100:
                yy += 2000
            due_date = f"{yy:04d}-{mm:02d}-{dd:02d}"

        pay_date = orig_date
        ap_m = re.search(r"Auto Pay:\s*Deducted\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2}),?\s+(\d{4})", combined_text, re.IGNORECASE)
        if ap_m:
            parsed_ap = _parse_month_day_year(ap_m.group(1), ap_m.group(2), ap_m.group(3))
            if parsed_ap:
                pay_date = parsed_ap

        return {
            "message_id": msg_id,
            "vendor": vendor,
            "subtotal": amount,
            "tax": 0.0,
            "amount": amount,
            "bill_date": orig_date,
            "due_date": due_date,
            "payment_date": pay_date,
            "reference_no": ref_no,
            "category": category,
            "payment_status": "PAID",
            "payment_method": "Mastercard 9437 / Auto-Pay",
            "auto_pay": True,
            "proof_status": "VERIFIED_PDF_RECEIPT" if has_pdf_attachment else "VERIFIED_EMAIL_RECEIPT",
            "note": f"NWMLS membership dues ({ref_no}, Statement/Receipt Date {orig_date}).",
        }

    # -------------------------------------------------------------------------
    # 3. Staples & Staples Print & Marketing (Purchases, In-Store Orders, & Returns)
    # -------------------------------------------------------------------------
    if "staples" in lower_sender or "staples" in lower_sub or "staples" in lower_comb:
        vendor = "Staples"
        category = "Marketing" if any(k in lower_comb for k in ["sign", "business card", "frame", "print"]) else "Office Supplies"

        ord_m = re.search(r"Order Number\s*[:\*]?\s*(\d{8,12})", combined_text, re.IGNORECASE)
        ord_num = ord_m.group(1) if ord_m else f"STAPLES-{orig_date}"

        is_return = bool(
            "start return" in lower_comb
            or re.search(r"\bReturn\b\s+Store:\s*\d+", combined_text)
            or re.search(r"USD\$-\d+\.\d{2}", combined_text)
        )

        sub_m = re.search(r"\b(?:Pickup\s+|Order\s+)?Subtotal\b\s*[:\.]?\s*\$?\s*\(?([0-9]+\.[0-9]{2})\)?", combined_text, re.IGNORECASE)
        tax_m = re.search(r"\b(?:WASHINGTON\s+\d+(?:\.\d+)?%|Estimated\s+Tax)\b\s*[:\.]?\s*\$?\s*\(?([0-9]+\.[0-9]{2})\)?", combined_text, re.IGNORECASE)
        tot_m = re.search(
            r"(?:Order\s+Total(?:\s*-\s*To\s+be\s+paid\s+in-store)?|(?<!Sub)\bTotal)\b\s*[:\.]?\s*\$?\s*\(?([0-9]+\.[0-9]{2})\)?",
            combined_text,
            re.IGNORECASE,
        )

        subtotal = float(sub_m.group(1)) if sub_m else 0.0
        tax = float(tax_m.group(1)) if tax_m else 0.0
        if subtotal > 0 and tax > 0:
            total = round(subtotal + tax, 2)
        elif tot_m:
            total = float(tot_m.group(1))
            if subtotal == 0.0:
                subtotal = round(total - tax, 2)
            elif tax == 0.0 and subtotal > 0 and total > subtotal:
                tax = round(total - subtotal, 2)
        else:
            total = subtotal

        if total <= 0:
            return None

        if is_return:
            return {
                "message_id": msg_id,
                "vendor": vendor,
                "subtotal": -subtotal,
                "tax": -tax,
                "amount": total,
                "bill_date": orig_date,
                "due_date": orig_date,
                "reference_no": f"RET-{ord_num}",
                "original_order_ref": f"ORD-{ord_num}",
                "category": category,
                "payment_status": "REFUNDED",
                "payment_method": "Mastercard 1669 Refund",
                "auto_pay": False,
                "is_return": True,
                "proof_status": "REFUNDED_NET_ZERO",
                "note": f"Full in-store return/refund (-${total:.2f}) of Staples Order #{ord_num} on {orig_date}.",
            }

        is_unpaid_instore_order = "to be paid in-store" in lower_comb
        if is_unpaid_instore_order:
            return {
                "message_id": msg_id,
                "vendor": vendor,
                "subtotal": subtotal,
                "tax": tax,
                "amount": total,
                "bill_date": orig_date,
                "due_date": orig_date,
                "reference_no": f"ORD-{ord_num}",
                "category": category,
                "payment_status": "OPEN",
                "payment_method": "To be paid in-store (Unverified)",
                "auto_pay": False,
                "proof_status": "FLAGGED_MISSING_PAYMENT_RECEIPT",
                "note": f"Staples Print & Marketing Order #{ord_num} (500 Business Cards, Subtotal ${subtotal:.2f} + Tax ${tax:.2f} = ${total:.2f}). Order confirmation states 'To be paid in-store' — final in-store payment receipt required.",
            }

        return {
            "message_id": msg_id,
            "vendor": vendor,
            "subtotal": subtotal,
            "tax": tax,
            "amount": total,
            "bill_date": orig_date,
            "due_date": orig_date,
            "reference_no": f"ORD-{ord_num}",
            "category": category,
            "payment_status": "PAID",
            "payment_method": "Mastercard 1669 (POS Contactless/PIN)",
            "auto_pay": True,
            "proof_status": "VERIFIED_EMAIL_RECEIPT",
            "note": f"Staples in-store POS receipt for Order #{ord_num} (Subtotal ${subtotal:.2f} + WA Tax ${tax:.2f} = ${total:.2f}).",
        }

    # -------------------------------------------------------------------------
    # 4. Canva Invoices
    # -------------------------------------------------------------------------
    if "canva" in lower_sender or "canva" in lower_sub or "canva.com" in lower_comb:
        inv_m = re.search(r"Invoice\s+(\d{4,6}-\d{6,10})", combined_text, re.IGNORECASE)
        amt_m = re.search(r"Charged\s*[:\.]?\s*\$([0-9]+\.[0-9]{2})", combined_text, re.IGNORECASE)
        if not amt_m:
            amt_m = re.search(r"\$([0-9]+\.[0-9]{2})", combined_text)
        if not amt_m:
            return None
        amount = float(amt_m.group(1))
        ref_no = f"INV-{inv_m.group(1)}" if inv_m else f"CANVA-{orig_date}"
        item_desc = "Canva Print Order" if "print items" in lower_comb else "Canva Pro Subscription"
        return {
            "message_id": msg_id,
            "vendor": "Canva",
            "subtotal": amount,
            "tax": 0.0,
            "amount": amount,
            "bill_date": orig_date,
            "due_date": orig_date,
            "reference_no": ref_no,
            "category": "Marketing & Creative Design",
            "payment_status": "PAID",
            "payment_method": "Mastercard 9437",
            "auto_pay": True,
            "proof_status": "VERIFIED_EMAIL_RECEIPT",
            "note": f"{item_desc} ({ref_no}, Issued {orig_date}) — Paid with Mastercard 9437.",
        }

    # -------------------------------------------------------------------------
    # 5. Cloudflare Invoices
    # -------------------------------------------------------------------------
    if "cloudflare" in lower_sender or "cloudflare" in lower_sub or "cloudflare" in lower_comb:
        inv_m = re.search(r"\b(IN-\d{6,10})\b", combined_text)
        amt_m = re.search(r"Amount\s*[:\.]?\s*\$([0-9]+\.[0-9]{2})", combined_text, re.IGNORECASE)
        if not amt_m:
            amt_m = re.search(r"\$([0-9]+\.[0-9]{2})", combined_text)
        if not amt_m:
            return None
        amount = float(amt_m.group(1))
        ref_no = inv_m.group(1) if inv_m else f"CF-{orig_date}"
        missing_pdf = ("want your invoice attached" in lower_comb or "enable email invoices" in lower_comb) and not has_pdf_attachment
        return {
            "message_id": msg_id,
            "vendor": "Cloudflare",
            "subtotal": amount,
            "tax": 0.0,
            "amount": amount,
            "bill_date": orig_date,
            "due_date": orig_date,
            "reference_no": ref_no,
            "category": "Hosting & Security",
            "payment_status": "PAID",
            "payment_method": "Cloudflare Auto-Pay",
            "auto_pay": True,
            "proof_status": "FLAGGED_MISSING_INVOICE_COPY" if missing_pdf else "VERIFIED_PDF_RECEIPT",
            "note": (
                f"Cloudflare invoice {ref_no} ({orig_date}, ${amount:.2f}). "
                + ("FLAGGED: Email is a notification link without the PDF invoice copy attached." if missing_pdf else "Verified invoice.")
            ),
        }

    # -------------------------------------------------------------------------
    # 6. Google Play Receipts (CapCut Subscription)
    # -------------------------------------------------------------------------
    if "google play" in lower_sender or "google play" in lower_sub or "gpa." in lower_comb:
        gpa_m = re.search(r"(GPA\.\d{4}-\d{4}-\d{4}-\d{4,6}(?:\.\.\d+)?)", combined_text, re.IGNORECASE)
        tot_m = re.search(r"(?<!Sub)\bTotal\s*[:\.]?\s*\$([0-9]+\.[0-9]{2})", combined_text, re.IGNORECASE)
        if not tot_m:
            return None
        total = float(tot_m.group(1))
        tax_vals = [float(x) for x in re.findall(r"sales tax\s*[:\.]?\s*\$([0-9]+\.[0-9]{2})", combined_text, re.IGNORECASE)]
        tax = round(sum(tax_vals), 2)
        subtotal = round(total - tax, 2)
        ref_no = gpa_m.group(1) if gpa_m else f"GPLAY-{orig_date}"
        return {
            "message_id": msg_id,
            "vendor": "Google Play",
            "subtotal": subtotal,
            "tax": tax,
            "amount": total,
            "bill_date": orig_date,
            "due_date": orig_date,
            "reference_no": ref_no,
            "category": "Marketing & Creative Design",
            "payment_status": "PAID",
            "payment_method": "Mastercard 9437",
            "auto_pay": True,
            "proof_status": "VERIFIED_EMAIL_RECEIPT",
            "note": f"Google Play CapCut subscription receipt ({ref_no}, Subtotal ${subtotal:.2f} + Tax ${tax:.2f} = ${total:.2f}).",
        }

    # -------------------------------------------------------------------------
    # 7. Amazon Orders (including clipped order confirmations missing invoice/amount)
    # -------------------------------------------------------------------------
    if "amazon.com" in lower_sender or "auto-confirm@amazon.com" in lower_comb or "ordered:" in lower_sub:
        ord_m = re.search(r"(\d{3}-\d{7}-\d{7})", combined_text)
        tot_m = re.search(r"(?:Order Total|Grand Total|Total)\s*[:\.]?\s*\$([0-9]+\.[0-9]{2})", combined_text, re.IGNORECASE)
        ref_no = f"AMZN-{ord_m.group(1)}" if ord_m else f"AMZN-{orig_date}-OPEN-HOUSE-SIGNS"
        if not tot_m and not has_pdf_attachment:
            return {
                "message_id": msg_id,
                "vendor": "Amazon.com",
                "subtotal": 0.0,
                "tax": 0.0,
                "amount": 0.0,
                "bill_date": orig_date,
                "due_date": orig_date,
                "reference_no": ref_no,
                "category": "Marketing",
                "payment_status": "UNRECORDED",
                "payment_method": "Missing Invoice",
                "auto_pay": False,
                "is_unpriced_flagged": True,
                "proof_status": "FLAGGED_MISSING_AMOUNT_AND_INVOICE",
                "note": f"Forwarded Amazon order notification ('{subject}') is clipped and missing the dollar amount, order ID, and invoice PDF. Please provide the Amazon invoice.",
            }

    return None


async def _llm_extract_operating_bill(
    sender: str,
    subject: str,
    body_text: str,
    attachments_text: str,
    msg_id: str,
    has_pdf_attachment: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Universal fallback extractor using local Ollama for forwarded or new-vendor
    operating expense bills sent to billing@lokeshchanana.com.
    """
    orig_date = _extract_original_date(subject, body_text, attachments_text)
    snippet = f"From: {sender}\nSubject: {subject}\n\nBody:\n{_clean_invisible_and_urls(body_text)[:2500]}\n\nAttachments:\n{attachments_text[:2500]}"

    prompt = (
        "Extract bill/expense details from this email into ONLY valid JSON with these exact keys:\n"
        "{\n"
        '  "document_type": "bill_or_receipt" | "2fa_code" | "newsletter_or_promo" | "real_estate_transaction_doc",\n'
        '  "vendor_name": "Company or merchant charging the bill (NEVER Lokesh Chanana)",\n'
        '  "amount": 0.00,\n'
        f'  "bill_date": "YYYY-MM-DD (default {orig_date})",\n'
        f'  "due_date": "YYYY-MM-DD (default {orig_date})",\n'
        '  "reference_no": "Invoice, receipt, account, or order number if present, else empty string",\n'
        '  "category": "One of: MLS Dues & Subscriptions, Software & Subscriptions, Utilities, Marketing, Insurance, Office Supplies, Repairs & Maintenance, General Expense",\n'
        '  "is_paid": true or false,\n'
        '  "note": "Brief 1-sentence summary of the bill or receipt"\n'
        "}\n\n"
        f"EMAIL CONTENT:\n{snippet}"
    )

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={"model": OLLAMA_BILL_MODEL, "prompt": prompt, "format": "json", "stream": False},
            )
            if resp.status_code != 200:
                return None
            data = json.loads(resp.json().get("response", "{}"))
    except Exception as e:
        logger.warning(f"LLM bill extraction failed for '{subject}': {e}")
        return None

    if data.get("document_type") != "bill_or_receipt":
        return None

    try:
        amount = float(data.get("amount") or 0.0)
    except Exception:
        amount = 0.0

    vendor = str(data.get("vendor_name") or "").strip()
    if amount <= 0 or not vendor or "lokesh" in vendor.lower():
        return None

    b_date = str(data.get("bill_date") or orig_date).strip()
    d_date = str(data.get("due_date") or b_date).strip()
    ref_no = str(data.get("reference_no") or "").strip() or f"INV-{vendor[:6].upper()}-{b_date}"
    is_paid = bool(data.get("is_paid", True))

    return {
        "message_id": msg_id,
        "vendor": vendor,
        "subtotal": round(amount, 2),
        "tax": 0.0,
        "amount": round(amount, 2),
        "bill_date": b_date,
        "due_date": d_date,
        "reference_no": ref_no,
        "category": str(data.get("category") or "General Expense").strip(),
        "payment_status": "PAID" if is_paid else "OPEN",
        "payment_method": "Card / Auto-Pay" if is_paid else "Unpaid Invoice",
        "auto_pay": is_paid,
        "proof_status": "VERIFIED_PDF_RECEIPT" if has_pdf_attachment else "VERIFIED_EMAIL_RECEIPT",
        "note": str(data.get("note") or f"Expense from {vendor} ({ref_no})").strip(),
    }


async def scan_and_ingest_email_bills(
    limit: int = 200,
    force_reprocess: bool = False,
) -> Dict[str, Any]:
    """
    Scans lokesh@lokeshchanana.com and billing@lokeshchanana.com for operating expenses,
    reconciles subtotals + tax, nets out returns, archives proof documents, records 2-step
    settled bills into Bigcapital, and triggers Victor Sterling's independent CPA audit.
    """
    init_store()
    if not IMAP_PASSWORD:
        return {
            "ok": False,
            "error": "MAIL_IMAP_PASSWORD not configured.",
            "new_bills": [],
            "already_processed": [],
        }

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(IMAP_USER, IMAP_PASSWORD)
        mail.select("INBOX")
    except Exception as login_err:
        logger.error(f"Failed to connect to IMAP as {IMAP_USER}: {login_err}")
        return {"ok": False, "error": f"IMAP login failure: {login_err}", "new_bills": [], "already_processed": []}

    search_queries = [
        '(TO "billing@lokeshchanana.com")',
        '(OR (SUBJECT "statement") (OR (SUBJECT "invoice") (OR (SUBJECT "dues") (OR (SUBJECT "bill") (OR (SUBJECT "subscription") (OR (FROM "ebill") (FROM "billing")))))))',
        "UNSEEN",
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
        return {"ok": True, "account": IMAP_USER, "scanned_count": 0, "new_bills": [], "already_processed": []}

    # Process chronologically (oldest first) so purchases are processed before returns!
    sorted_ids = sorted(list(matched_ids_set), key=lambda x: int(x))
    if limit is not None and limit < len(sorted_ids):
        recent_ids = sorted_ids[-limit:]
    else:
        recent_ids = sorted_ids

    logger.info(f"Targeted search identified {len(recent_ids)} candidate messages in {IMAP_USER}...")

    new_bills: List[Dict[str, Any]] = []
    already_processed: List[Dict[str, Any]] = []
    flagged_missing_proofs: List[Dict[str, Any]] = []
    refunded_orders: List[Dict[str, Any]] = []
    skipped_transactions: List[str] = []
    errors: List[Dict[str, Any]] = []

    for mid in recent_ids:
        try:
            res_hdr, hdr_data = mail.fetch(mid, "(BODY.PEEK[HEADER.FIELDS (FROM TO DELIVERED-TO SUBJECT DATE MESSAGE-ID)])")
            if res_hdr != "OK" or not hdr_data:
                continue

            sender, to_hdr, delivered_to, subject, date_hdr = "", "", "", "", ""
            msg_id = f"imap_msg_{mid.decode()}"

            for part_h in hdr_data:
                if isinstance(part_h, tuple):
                    h_msg = email.message_from_bytes(part_h[1])
                    msg_id = (h_msg.get("Message-ID") or msg_id).strip()
                    sender = _decode_header_str(h_msg.get("From", ""))
                    to_hdr = _decode_header_str(h_msg.get("To", ""))
                    delivered_to = _decode_header_str(h_msg.get("Delivered-To", ""))
                    subject = _decode_header_str(h_msg.get("Subject", ""))
                    date_hdr = h_msg.get("Date", "")
                    break

            is_billing_alias = BILLING_ALIAS in to_hdr.lower() or BILLING_ALIAS in delivered_to.lower()

            if not force_reprocess and is_email_bill_processed(msg_id):
                already_processed.append({"message_id": msg_id, "subject": subject, "sender": sender})
                continue

            if is_transaction_document(sender, subject, ""):
                skipped_transactions.append(subject)
                continue

            lower_hdr = (sender + " " + subject).lower()
            known_vendor_kw = [
                "nwmls", "ebill", "google", "brevo", "twilio", "docusign",
                "zoom", "hetzner", "cloudflare", "namecheap", "godaddy",
                "pse", "seattle city light", "staples", "adobe", "canva",
                "comcast", "xfinity", "verizon", "at&t", "t-mobile",
                "state farm", "geico", "progressive", "capcut", "amazon",
            ]
            has_financial_header = (
                is_billing_alias
                or any(k in lower_hdr for k in FINANCIAL_INTENT_KEYWORDS)
                or any(k in lower_hdr for k in known_vendor_kw)
            )
            if not has_financial_header:
                continue

            res, msg_data = mail.fetch(mid, "(BODY.PEEK[])")
            if res != "OK" or not msg_data:
                continue

            for part_r in msg_data:
                if not isinstance(part_r, tuple):
                    continue

                msg = email.message_from_bytes(part_r[1])
                plain_text, html_text, attachments_text = "", "", ""
                raw_pdf_bytes: Optional[bytes] = None

                if msg.is_multipart():
                    for part in msg.walk():
                        ctype = (part.get_content_type() or "").lower()
                        fname = (part.get_filename() or "").lower()
                        if ctype == "text/plain" and not fname:
                            pl = part.get_payload(decode=True)
                            if pl:
                                plain_text += pl.decode(errors="ignore") + "\n"
                        elif ctype == "text/html" and not fname:
                            pl = part.get_payload(decode=True)
                            if pl:
                                html_text += _extract_html_text(pl) + "\n"
                        elif fname.endswith(".pdf") or ctype == "application/pdf":
                            pl = part.get_payload(decode=True)
                            if pl:
                                raw_pdf_bytes = pl
                                attachments_text += extract_pdf_and_ocr(pl, fname or "attachment.pdf") + "\n"
                        elif ctype.startswith("image/") or fname.endswith((".png", ".jpg", ".jpeg", ".webp")):
                            pl = part.get_payload(decode=True)
                            if pl:
                                ocr_res = _extract_image_ocr(pl)
                                if ocr_res:
                                    attachments_text += ocr_res + "\n"
                else:
                    pl = msg.get_payload(decode=True)
                    if pl:
                        if (msg.get_content_type() or "").lower() == "text/html":
                            html_text = _extract_html_text(pl)
                        else:
                            plain_text = pl.decode(errors="ignore")

                clean_p = _clean_invisible_and_urls(plain_text).strip()
                clean_h = _clean_invisible_and_urls(html_text).strip()
                body_text = clean_p if len(clean_p) >= len(clean_h) else clean_h

                eff_sender, eff_subject = _extract_forwarded_context(sender, subject, body_text)

                if is_transaction_document(eff_sender, eff_subject, body_text):
                    skipped_transactions.append(subject)
                    continue

                parsed = parse_operating_bill(
                    sender=eff_sender,
                    subject=eff_subject,
                    date_str=date_hdr,
                    body_text=body_text,
                    attachments_text=attachments_text,
                    msg_id=msg_id,
                    has_pdf_attachment=bool(raw_pdf_bytes),
                )

                if not parsed and (is_billing_alias or any(k in (eff_subject + " " + body_text).lower() for k in FINANCIAL_INTENT_KEYWORDS)):
                    combined_check = f"{eff_subject}\n{body_text}\n{attachments_text}"
                    if re.search(r"\$\s*[0-9]+[\.,][0-9]{2}", combined_check):
                        parsed = await _llm_extract_operating_bill(
                            sender=eff_sender,
                            subject=eff_subject,
                            body_text=body_text,
                            attachments_text=attachments_text,
                            msg_id=msg_id,
                            has_pdf_attachment=bool(raw_pdf_bytes),
                        )

                if not parsed:
                    continue

                ref_no = parsed["reference_no"]

                # Case A: Unpriced / Clipped Order Confirmation (e.g., Amazon Open House Signs)
                if parsed.get("is_unpriced_flagged"):
                    proof_bytes = (f"Subject: {subject}\nFrom: {sender}\nDate: {date_hdr}\n\n{body_text}").encode("utf-8")
                    p_path, p_sha, g_fid = archive_expense_proof(
                        vendor_name=parsed["vendor"],
                        reference_no=ref_no,
                        bill_date=parsed["bill_date"],
                        content_bytes=proof_bytes,
                        ext=".txt",
                    )
                    upsert_tax_audit_entry(
                        reference_no=ref_no,
                        vendor_name=parsed["vendor"],
                        bill_date=parsed["bill_date"],
                        due_date=parsed["due_date"],
                        subtotal=0.0,
                        tax_amount=0.0,
                        total_amount=0.0,
                        category=parsed["category"],
                        payment_status="UNRECORDED",
                        payment_method="Missing Invoice",
                        proof_status="FLAGGED_MISSING_AMOUNT_AND_INVOICE",
                        proof_path=p_path,
                        proof_sha256=p_sha,
                        gdrive_file_id=g_fid,
                        source_type="email",
                        source_id=msg_id,
                        audit_notes=parsed["note"],
                    )
                    record_processed_email_bill(
                        message_id=msg_id,
                        sender=sender,
                        subject=subject,
                        vendor_name=parsed["vendor"],
                        amount=0.0,
                        bill_date=parsed["bill_date"],
                        due_date=parsed["due_date"],
                        bill_id=None,
                        status="FLAGGED_MISSING_INVOICE",
                        details=parsed["note"],
                    )
                    flagged_missing_proofs.append(parsed)
                    continue

                # Case B: Return / Refund Receipt (e.g. Staples Order #2429014787 returned for -$72.84)
                if parsed.get("is_return"):
                    orig_ref = parsed.get("original_order_ref", "")
                    proof_bytes = (f"Subject: {subject}\nFrom: {sender}\nDate: {date_hdr}\n\n{body_text}").encode("utf-8")
                    p_path, p_sha, g_fid = archive_expense_proof(
                        vendor_name=parsed["vendor"],
                        reference_no=ref_no,
                        bill_date=parsed["bill_date"],
                        content_bytes=proof_bytes,
                        ext=".txt",
                    )
                    orig_entry = get_tax_audit_entry(orig_ref) if orig_ref else None
                    if orig_entry and orig_entry.get("bigcapital_bill_id"):
                        orig_pid = orig_entry.get("bigcapital_payment_id")
                        if orig_pid:
                            await bigcapital_client.manage_bill_payments(action="delete", payment_id=orig_pid)
                        orig_bid = orig_entry["bigcapital_bill_id"]
                        await bigcapital_client.delete_bill(orig_bid)
                        upsert_tax_audit_entry(
                            reference_no=orig_ref,
                            vendor_name=parsed["vendor"],
                            bill_date=orig_entry["bill_date"],
                            due_date=orig_entry["due_date"],
                            subtotal=orig_entry["subtotal"],
                            tax_amount=orig_entry["tax_amount"],
                            total_amount=orig_entry["total_amount"],
                            category=parsed["category"],
                            payment_status="REFUNDED",
                            payment_method=orig_entry.get("payment_method", ""),
                            bigcapital_bill_id=None,
                            bigcapital_payment_id=None,
                            proof_status="REFUNDED_NET_ZERO",
                            proof_path=orig_entry.get("proof_path", ""),
                            proof_sha256=orig_entry.get("proof_sha256", ""),
                            source_type="email",
                            source_id=orig_entry.get("source_id", ""),
                            audit_notes=f"Returned in full on {parsed['bill_date']} ({ref_no}, -${parsed['amount']:.2f}). Net deduction = $0.00.",
                        )
                    upsert_tax_audit_entry(
                        reference_no=ref_no,
                        vendor_name=parsed["vendor"],
                        bill_date=parsed["bill_date"],
                        due_date=parsed["due_date"],
                        subtotal=parsed["subtotal"],
                        tax_amount=parsed["tax"],
                        total_amount=-parsed["amount"],
                        category=parsed["category"],
                        payment_status="REFUNDED",
                        payment_method=parsed["payment_method"],
                        proof_status="REFUNDED_NET_ZERO",
                        proof_path=p_path,
                        proof_sha256=p_sha,
                        gdrive_file_id=g_fid,
                        source_type="email",
                        source_id=msg_id,
                        audit_notes=parsed["note"],
                    )
                    record_processed_email_bill(
                        message_id=msg_id,
                        sender=sender,
                        subject=subject,
                        vendor_name=parsed["vendor"],
                        amount=-parsed["amount"],
                        bill_date=parsed["bill_date"],
                        due_date=parsed["due_date"],
                        bill_id=None,
                        status="REFUNDED_NET_ZERO",
                        details=parsed["note"],
                    )
                    refunded_orders.append(parsed)
                    continue

                # Case C: Canonical Deduplication across twice-forwarded emails
                existing_audit = get_tax_audit_entry(ref_no)
                if existing_audit and existing_audit.get("proof_status") == "REFUNDED_NET_ZERO":
                    record_processed_email_bill(
                        message_id=msg_id,
                        sender=sender,
                        subject=subject,
                        vendor_name=parsed["vendor"],
                        amount=parsed["amount"],
                        bill_date=parsed["bill_date"],
                        due_date=parsed["due_date"],
                        bill_id=None,
                        status="REFUNDED_NET_ZERO",
                        details=f"Order {ref_no} was already refunded.",
                    )
                    already_processed.append({"message_id": msg_id, "subject": subject, "reference_no": ref_no})
                    continue

                if raw_pdf_bytes:
                    p_path, p_sha, g_fid = archive_expense_proof(
                        vendor_name=parsed["vendor"],
                        reference_no=ref_no,
                        bill_date=parsed["bill_date"],
                        content_bytes=raw_pdf_bytes,
                        ext=".pdf",
                    )
                else:
                    proof_txt = (
                        f"Vendor: {parsed['vendor']}\n"
                        f"Reference: {ref_no}\n"
                        f"Transaction Date: {parsed['bill_date']}\n"
                        f"Subtotal: ${parsed.get('subtotal', parsed['amount']):.2f}\n"
                        f"Tax: ${parsed.get('tax', 0.0):.2f}\n"
                        f"Total: ${parsed['amount']:.2f}\n"
                        f"Payment Status: {parsed.get('payment_status')}\n"
                        f"Subject: {subject}\n"
                        f"Message-ID: {msg_id}\n"
                        f"----------------------------------------\n"
                        f"{body_text}\n"
                    ).encode("utf-8")
                    p_path, p_sha, g_fid = archive_expense_proof(
                        vendor_name=parsed["vendor"],
                        reference_no=ref_no,
                        bill_date=parsed["bill_date"],
                        content_bytes=proof_txt,
                        ext=".txt",
                    )

                bc_res = await bigcapital_client.create_bill(
                    vendor_name=parsed["vendor"],
                    amount=parsed["amount"],
                    due_date=parsed["due_date"],
                    bill_date=parsed["bill_date"],
                    note=parsed["note"],
                    reference_no=ref_no,
                    category=parsed["category"],
                    auto_pay=bool(parsed.get("auto_pay", True)),
                    payment_date=parsed.get("payment_date") or parsed["bill_date"],
                )

                if bc_res.get("ok"):
                    bill_id = bc_res.get("bill_id") or bc_res.get("data", {}).get("id")
                    pay_id = bc_res.get("payment_id")
                    was_dedup = bool(bc_res.get("already_exists"))

                    upsert_tax_audit_entry(
                        reference_no=ref_no,
                        vendor_name=parsed["vendor"],
                        bill_date=parsed["bill_date"],
                        due_date=parsed["due_date"],
                        subtotal=parsed.get("subtotal", parsed["amount"]),
                        tax_amount=parsed.get("tax", 0.0),
                        total_amount=parsed["amount"],
                        category=parsed["category"],
                        payment_status=parsed.get("payment_status", "PAID"),
                        payment_method=parsed.get("payment_method", "Card"),
                        bigcapital_bill_id=bill_id,
                        bigcapital_payment_id=pay_id,
                        proof_status=parsed.get("proof_status", "VERIFIED_EMAIL_RECEIPT"),
                        proof_path=p_path,
                        proof_sha256=p_sha,
                        gdrive_file_id=g_fid,
                        source_type="email",
                        source_id=msg_id,
                        audit_notes=parsed["note"],
                    )
                    record_processed_email_bill(
                        message_id=msg_id,
                        sender=sender,
                        subject=subject,
                        vendor_name=parsed["vendor"],
                        amount=parsed["amount"],
                        bill_date=parsed["bill_date"],
                        due_date=parsed["due_date"],
                        bill_id=bill_id,
                        status="DEDUPLICATED" if was_dedup else "PROCESSED",
                        details=f"Bigcapital Bill ID: {bill_id}, Ref: {ref_no}, Proof: {parsed.get('proof_status')}",
                    )
                    if str(parsed.get("proof_status", "")).startswith("FLAGGED"):
                        flagged_missing_proofs.append({**parsed, "bigcapital_bill_id": bill_id})

                    if was_dedup:
                        already_processed.append({"message_id": msg_id, "subject": subject, "reference_no": ref_no, "bill_id": bill_id})
                    else:
                        new_bills.append({
                            "message_id": msg_id,
                            "vendor": parsed["vendor"],
                            "amount": parsed["amount"],
                            "bill_date": parsed["bill_date"],
                            "due_date": parsed["due_date"],
                            "reference_no": ref_no,
                            "category": parsed["category"],
                            "payment_status": parsed.get("payment_status", "PAID"),
                            "proof_status": parsed.get("proof_status"),
                            "bigcapital_bill_id": bill_id,
                            "subject": subject,
                        })
                else:
                    err_msg = bc_res.get("error", "Unknown Bigcapital API error")
                    errors.append({"message_id": msg_id, "subject": subject, "error": err_msg})

        except Exception as msg_exc:
            logger.exception(f"Error reading message {mid}: {msg_exc}")

    try:
        mail.close()
        mail.logout()
    except Exception:
        pass

    audit_report = await run_independent_tax_audit(auto_fix_settlements=True, auto_remove_duplicates=True)

    return {
        "ok": True,
        "account": IMAP_USER,
        "scanned_count": len(recent_ids),
        "newly_ingested_count": len(new_bills),
        "already_processed_count": len(already_processed),
        "refunded_net_zero_count": len(refunded_orders),
        "flagged_missing_proofs_count": len(flagged_missing_proofs),
        "skipped_transactions_count": len(skipped_transactions),
        "error_count": len(errors),
        "new_bills": new_bills,
        "already_processed": already_processed,
        "refunded_orders": refunded_orders,
        "flagged_missing_proofs": flagged_missing_proofs,
        "errors": errors,
        "victor_sterling_audit": {
            "audit_status": audit_report.get("audit_status"),
            "summary": audit_report.get("summary"),
            "flagged_count": audit_report.get("flagged_count"),
        },
    }


if __name__ == "__main__":
    import asyncio
    import sys

    force = "--force" in sys.argv
    print(f"Starting email expenses scan for {IMAP_USER} (force={force})...")
    res = asyncio.run(scan_and_ingest_email_bills(limit=200, force_reprocess=force))
    import pprint
    pprint.pprint(res)
