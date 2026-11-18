"""
Google Drive Bills Watcher & OCR Ingestion Engine for Fiona Banks
Casa-poki Intelligent Agent Hub

Monitors Google Drive folders for bill/receipt uploads, performs OCR on PDFs
and images, extracts financial entities, deduplicates via agent_system.db,
and records the bills into Bigcapital accounting.
"""

import io
import logging
import os
import re
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional

from PIL import Image
from pypdf import PdfReader
import pytesseract

from bigcapital_tools import bigcapital_client
from state_store import (
    init_store,
    is_drive_bill_processed,
    record_processed_drive_bill,
    list_processed_drive_bills,
)

logger = logging.getLogger("gdrive_bills_watcher")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

DEFAULT_BILLS_FOLDER_ID = os.environ.get(
    "GDRIVE_BILLS_FOLDER_ID", "1mj2jCnKsQGsdf4zV5R9dlr3SKthE3mNQ"
)


def fetch_drive_folder_files(folder_id: str = DEFAULT_BILLS_FOLDER_ID) -> List[Dict[str, str]]:
    """
    Scrapes the public/shared Google Drive folder view to extract available files.
    Returns a list of dicts: [{'file_id': str, 'file_name': str}]
    """
    url = f"https://drive.google.com/drive/folders/{folder_id}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        logger.error(f"Failed to access Google Drive folder {folder_id}: {e}")
        return []

    files: List[Dict[str, str]] = []
    seen_ids = set()

    # Pattern 1: aria-label with filename and ssk attribute containing file ID
    # e.g.: aria-label="Receipt.pdf PDF Shared" ... ssk='5:auSv138:1tJKtHDmRVN0talKs6URQjZCQB8Ydw1xr-0-16'
    pattern1 = re.compile(
        r'aria-label=[\"\']([^\"\']+\.(?:pdf|png|jpe?g|webp|csv|xlsx|docx))[^\"\']*[\"\'][^>]*?ssk=[\"\'][^\"\']*?:([a-zA-Z0-9_-]{25,})',
        re.IGNORECASE,
    )
    for fname, raw_id in pattern1.findall(html):
        clean_id = re.sub(r"-[0-9]+.*$", "", raw_id)
        if clean_id not in seen_ids:
            seen_ids.add(clean_id)
            files.append({"file_id": clean_id, "file_name": fname.strip()})

    # Pattern 2: reverse ordering (ssk before aria-label)
    pattern2 = re.compile(
        r'ssk=[\"\'][^\"\']*?:([a-zA-Z0-9_-]{25,})[\"\'][^>]*?aria-label=[\"\']([^\"\']+\.(?:pdf|png|jpe?g|webp|csv|xlsx|docx))',
        re.IGNORECASE,
    )
    for raw_id, fname in pattern2.findall(html):
        clean_id = re.sub(r"-[0-9]+.*$", "", raw_id)
        if clean_id not in seen_ids:
            seen_ids.add(clean_id)
            files.append({"file_id": clean_id, "file_name": fname.strip()})

    # Pattern 3: Fallback by searching for common document extensions and surrounding 28-35 char IDs
    if not files:
        fname_matches = set(
            re.findall(
                r'\"([^\"]+\.(?:pdf|png|jpe?g|webp))\"',
                html,
                re.IGNORECASE,
            )
        )
        for fname in fname_matches:
            pos = html.find(fname)
            if pos != -1:
                snippet = html[max(0, pos - 500) : pos + 500]
                cand_ids = re.findall(r"[a-zA-Z0-9_-]{28,35}", snippet)
                for cid in cand_ids:
                    if cid != folder_id and not cid.startswith("http") and cid not in seen_ids:
                        seen_ids.add(cid)
                        files.append({"file_id": cid, "file_name": fname.strip()})
                        break

    logger.info(f"Discovered {len(files)} files in Google Drive folder {folder_id}")
    return files


def download_drive_file(file_id: str) -> bytes:
    """Downloads raw file bytes from Google Drive public stream."""
    url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def extract_text_and_ocr(file_bytes: bytes, file_name: str) -> str:
    """
    Extracts text from PDF documents (native text + embedded image OCR)
    or image files using pytesseract.
    """
    extracted_text = []

    # Check if PDF
    if file_bytes.startswith(b"%PDF") or file_name.lower().endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    extracted_text.append(page_text.strip())

                # OCR all raster images embedded in the page
                for img_file in page.images:
                    try:
                        im = Image.open(io.BytesIO(img_file.data))
                        ocr_res = pytesseract.image_to_string(im)
                        if ocr_res and ocr_res.strip():
                            extracted_text.append(ocr_res.strip())
                    except Exception as img_err:
                        logger.warning(f"Failed to OCR embedded image in {file_name}: {img_err}")
        except Exception as pdf_err:
            logger.warning(f"PdfReader encountered issue with {file_name}: {pdf_err}. Trying direct image OCR.")
            try:
                im = Image.open(io.BytesIO(file_bytes))
                ocr_res = pytesseract.image_to_string(im)
                if ocr_res and ocr_res.strip():
                    extracted_text.append(ocr_res.strip())
            except Exception:
                pass
    else:
        # Standard image format (.png, .jpg, etc.)
        try:
            im = Image.open(io.BytesIO(file_bytes))
            ocr_res = pytesseract.image_to_string(im)
            if ocr_res and ocr_res.strip():
                extracted_text.append(ocr_res.strip())
        except Exception as img_err:
            logger.error(f"Failed to process image {file_name}: {img_err}")

    return "\n\n".join(extracted_text)


def parse_bill_details(ocr_text: str, file_name: str, file_id: str) -> Dict[str, Any]:
    """
    Parses vendor name, total amount, dates, and category from extracted receipt/bill text.
    """
    lower_text = ocr_text.lower()
    lower_fn = file_name.lower()

    # 1. Vendor Recognition
    vendor = None
    known_vendors = [
        ("costco", "Costco Wholesale"),
        ("michaels", "Michaels"),
        ("home depot", "The Home Depot"),
        ("lowe", "Lowe's"),
        ("amazon", "Amazon"),
        ("target", "Target"),
        ("walmart", "Walmart"),
        ("puget sound energy", "Puget Sound Energy"),
        ("pse", "Puget Sound Energy"),
        ("seattle city light", "Seattle City Light"),
        ("sherwin", "Sherwin-Williams"),
        ("wayfair", "Wayfair"),
        ("ikea", "IKEA"),
        ("fred meyer", "Fred Meyer"),
        ("safeway", "Safeway"),
        ("best buy", "Best Buy"),
        ("staples", "Staples"),
        ("office depot", "Office Depot"),
        ("usps", "USPS"),
        ("fedex", "FedEx"),
        ("ups", "UPS"),
    ]
    for key, vname in known_vendors:
        if key in lower_fn or key in lower_text:
            vendor = vname
            break

    if not vendor:
        # Fallback to top non-empty lines of text
        for line in ocr_text.splitlines():
            clean = line.strip()
            if len(clean) > 3 and not re.match(r"^[0-9\W]+$", clean):
                vendor = clean
                break

    if not vendor:
        clean_fn = re.sub(r"[-_]\d+.*", "", file_name.split(".")[0])
        vendor = clean_fn.strip() or "Unknown Vendor"

    # 2. Financial Calculations (Subtotal, Tax, Total)
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None

    sub_match = re.search(r"subtotal\s*[:\.]?\s*\$?([0-9]+[\.,][0-9]{2})", ocr_text, re.IGNORECASE)
    if sub_match:
        try:
            subtotal = float(sub_match.group(1).replace(",", "."))
        except Exception:
            pass

    tax_match = re.search(r"(?:sales\s+)?ta[xk]\s*[:\.]?\s*(?:(\d+(?:\.\d+)?)%)?\s*\$?([0-9]+[\.,][0-9]{2})", ocr_text, re.IGNORECASE)
    if tax_match:
        try:
            tax = float(tax_match.group(2).replace(",", "."))
            if subtotal is not None and tax_match.group(1):
                rate_pct = float(tax_match.group(1))
                expected_tax = round(subtotal * (rate_pct / 100.0), 2)
                if abs(tax - expected_tax) <= 0.05:
                    tax = expected_tax
        except Exception:
            pass

    # Reconciled Total
    if subtotal is not None and tax is not None:
        calc_total = round(subtotal + tax, 2)
        total = calc_total

    if total is None:
        tot_matches = re.findall(r"\b(?:total|amount due|balance due)\b\s*[:\.]?\s*\$?([0-9]+[\.,][0-9]{2})", ocr_text, re.IGNORECASE)
        if tot_matches:
            try:
                total = float(tot_matches[-1].replace(",", "."))
            except Exception:
                pass

    if total is None:
        all_amounts = [float(x.replace(",", ".")) for x in re.findall(r"\$?([0-9]+[\.,][0-9]{2})", ocr_text)]
        if all_amounts:
            total = max(all_amounts)
        else:
            total = 0.0

    # 3. Bill & Due Date
    bill_date = None
    fn_date = re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2}),?\s+(\d{4})", file_name, re.IGNORECASE)
    if fn_date:
        try:
            dt = datetime.strptime(f"{fn_date.group(1)[:3]} {fn_date.group(2)} {fn_date.group(3)}", "%b %d %Y")
            bill_date = dt.strftime("%Y-%m-%d")
        except Exception:
            pass
    else:
        fn_iso = re.search(r"(\d{4})[-_]?(\d{2})[-_]?(\d{2})", file_name)
        if fn_iso:
            bill_date = f"{fn_iso.group(1)}-{fn_iso.group(2)}-{fn_iso.group(3)}"

    if not bill_date:
        txt_date = re.search(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})", ocr_text)
        if txt_date:
            m, d, y = txt_date.groups()
            if len(y) == 2:
                y = "20" + y
            try:
                dt = datetime.strptime(f"{m} {d} {y}", "%m %d %Y")
                bill_date = dt.strftime("%Y-%m-%d")
            except Exception:
                pass

    if not bill_date:
        bill_date = datetime.now().strftime("%Y-%m-%d")

    # 4. Expense Categorization & Note
    category = "General Expense"
    if any(w in lower_fn or w in lower_text for w in ["marketing", "flyer", "ad", "promo", "move in"]):
        category = "Marketing"
    elif any(w in lower_fn or w in lower_text for w in ["office", "paper", "stationery", "desk", "supplies"]):
        category = "Office Supplies"
    elif any(w in lower_fn or w in lower_text for w in ["repair", "hardware", "tool", "plumbing", "paint"]):
        category = "Repairs & Maintenance"
    elif any(w in lower_fn or w in lower_text for w in ["utility", "electric", "power", "water", "gas", "internet"]):
        category = "Utilities"

    note = f"Drive receipt ({file_name}) - Category: {category}"

    return {
        "file_id": file_id,
        "file_name": file_name,
        "vendor": vendor,
        "amount": round(total, 2),
        "subtotal": subtotal,
        "tax": tax,
        "bill_date": bill_date,
        "due_date": bill_date,
        "category": category,
        "note": note,
    }


async def scan_and_ingest_drive_bills(
    folder_id: str = DEFAULT_BILLS_FOLDER_ID,
    force_reprocess: bool = False,
) -> Dict[str, Any]:
    """
    Main orchestration routine:
    1. Scans Google Drive folder for bill files.
    2. Downloads and runs OCR on any new/unprocessed files.
    3. Records parsed bills into Bigcapital.
    4. Records state in processed_drive_bills table.
    """
    init_store()
    files = fetch_drive_folder_files(folder_id)
    if not files:
        return {
            "ok": True,
            "folder_id": folder_id,
            "message": "No files found in folder or folder is empty.",
            "new_bills": [],
            "already_processed": [],
            "errors": [],
        }

    new_bills: List[Dict[str, Any]] = []
    already_processed: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    for f in files:
        fid = f["file_id"]
        fname = f["file_name"]

        # Check deduplication
        if not force_reprocess and is_drive_bill_processed(fid):
            already_processed.append({"file_id": fid, "file_name": fname})
            continue

        try:
            logger.info(f"Downloading file {fname} (ID: {fid})...")
            file_bytes = download_drive_file(fid)
            if not file_bytes:
                errors.append({"file_id": fid, "file_name": fname, "error": "Empty file content downloaded"})
                continue

            logger.info(f"Extracting OCR text from {fname}...")
            ocr_text = extract_text_and_ocr(file_bytes, fname)
            parsed = parse_bill_details(ocr_text, fname, fid)

            if parsed["amount"] <= 0:
                logger.warning(f"Could not determine valid amount for {fname}. Total was 0.0")
                record_processed_drive_bill(
                    file_id=fid,
                    file_name=fname,
                    vendor_name=parsed["vendor"],
                    amount=0.0,
                    bill_date=parsed["bill_date"],
                    bill_id=None,
                    status="FLAGGED_ZERO_AMOUNT",
                    details=f"OCR extracted text length: {len(ocr_text)}",
                )
                errors.append({
                    "file_id": fid,
                    "file_name": fname,
                    "error": "Parsed amount is zero. Manual review required.",
                })
                continue

            ref_no = f"GDRIVE-{fid[:12]}"
            logger.info(
                f"Ingesting into Bigcapital: Vendor={parsed['vendor']}, Amount={parsed['amount']}, Date={parsed['bill_date']}"
            )
            bc_res = await bigcapital_client.create_bill(
                vendor_name=parsed["vendor"],
                amount=parsed["amount"],
                due_date=parsed["due_date"],
                bill_date=parsed["bill_date"],
                note=parsed["note"],
                reference_no=ref_no,
                category=parsed["category"],
                auto_pay=True,
                payment_date=parsed["bill_date"],
            )

            if bc_res.get("ok"):
                bill_id = bc_res.get("bill_id") or bc_res.get("data", {}).get("id")
                pay_id = bc_res.get("payment_id")
                from tax_auditor import archive_expense_proof
                from state_store import upsert_tax_audit_entry

                proof_path, proof_sha, gdrive_fid = archive_expense_proof(
                    vendor_name=parsed["vendor"],
                    reference_no=ref_no,
                    bill_date=parsed["bill_date"],
                    content_bytes=file_bytes,
                    ext=".pdf",
                )
                upsert_tax_audit_entry(
                    reference_no=ref_no,
                    vendor_name=parsed["vendor"],
                    bill_date=parsed["bill_date"],
                    due_date=parsed["due_date"],
                    subtotal=parsed.get("subtotal") or parsed["amount"],
                    tax_amount=parsed.get("tax") or 0.0,
                    total_amount=parsed["amount"],
                    category=parsed["category"],
                    payment_status="PAID",
                    payment_method="Card / POS Receipt",
                    bigcapital_bill_id=bill_id,
                    bigcapital_payment_id=pay_id,
                    proof_status="VERIFIED_PDF_RECEIPT",
                    proof_path=proof_path,
                    proof_sha256=proof_sha,
                    gdrive_file_id=gdrive_fid or fid,
                    source_type="gdrive",
                    source_id=fid,
                    audit_notes=f"Verified Google Drive PDF receipt ({fname})",
                )
                record_processed_drive_bill(
                    file_id=fid,
                    file_name=fname,
                    vendor_name=parsed["vendor"],
                    amount=parsed["amount"],
                    bill_date=parsed["bill_date"],
                    bill_id=bill_id,
                    status="PROCESSED",
                    details=f"Bigcapital Bill ID: {bill_id}, Payment ID: {pay_id}, Note: {parsed['note']}",
                )
                new_bills.append({
                    "file_id": fid,
                    "file_name": fname,
                    "vendor": parsed["vendor"],
                    "amount": parsed["amount"],
                    "bill_date": parsed["bill_date"],
                    "category": parsed["category"],
                    "bigcapital_bill_id": bill_id,
                })
            else:
                err_msg = bc_res.get("error", "Unknown Bigcapital API error")
                logger.error(f"Failed to record bill in Bigcapital for {fname}: {err_msg}")
                errors.append({"file_id": fid, "file_name": fname, "error": err_msg})

        except Exception as file_exc:
            logger.exception(f"Error processing drive bill file {fname}: {file_exc}")
            errors.append({"file_id": fid, "file_name": fname, "error": str(file_exc)})

    return {
        "ok": True,
        "folder_id": folder_id,
        "scanned_count": len(files),
        "newly_ingested_count": len(new_bills),
        "already_processed_count": len(already_processed),
        "error_count": len(errors),
        "new_bills": new_bills,
        "already_processed": already_processed,
        "errors": errors,
    }


if __name__ == "__main__":
    import asyncio
    import sys

    force = "--force" in sys.argv
    fid = DEFAULT_BILLS_FOLDER_ID
    for i, arg in enumerate(sys.argv):
        if arg == "--folder-id" and i + 1 < len(sys.argv):
            fid = sys.argv[i + 1]

    print(f"Starting Google Drive bills scan for folder {fid} (force={force})...")
    res = asyncio.run(scan_and_ingest_drive_bills(folder_id=fid, force_reprocess=force))
    import pprint
    pprint.pprint(res)
