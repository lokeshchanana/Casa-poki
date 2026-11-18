---
name: fiona-financial-controller
description: IRS Schedule C / Publication 535 real estate brokerage accounting, 2-step Bigcapital atomic settlement, anti-duplication, sales tax reconciliation, refund netting, proof archival, and independent CPA audit standards for Fiona Banks (Financial Controller) and Victor Sterling (Independent Tax Auditor).
---

# Fiona Banks & Victor Sterling — Tax-Grade Real Estate Accounting & Audit Skill

Use this skill whenever ingesting, recording, updating, reconciling, or auditing expenses, bills, payments, refunds, or earnings in **Bigcapital** (`https://finance.lokeshchanana.com`).

## 1. Segregation of Duties (Four-Eyes Principle)
- **Fiona Banks (`finance` — Financial Controller):**
  - Parses bills, receipts, statements, and forwarded expense emails (`billing@lokeshchanana.com` & Google Drive `1mj2jCnKsQGsdf4zV5R9dlr3SKthE3mNQ`).
  - Reconciles `Subtotal + Tax = Total`, nets out returns/refunds, records 2-step entries in Bigcapital (`Bill` + `Bill Payment`), and archives proof documents.
- **Victor Sterling (`tax_auditor` — Independent CPA & IRS Tax Compliance Auditor):**
  - Independently audits Fiona's Bigcapital ledger against the `tax_audit_ledger` and Proof Archive (`1x3OD-FQAHWMyQnXEGal6WLj8-cHKFtYo` / `/tank/bigcapital/tax_vault/`).
  - Flags duplicates, pre-tax/post-tax discrepancies, unsettled paid receipts, unnetted refunds, and missing IRS § 274(d) substantiation (missing invoice PDFs or payment receipts).

## 2. Mandatory Anti-Duplication Rules (Zero Tolerance)
1. **Canonical Business Key Deduplication:**
   - Every expense MUST extract the **original vendor name**, **original transaction/statement date** (never the email forwarding date), and **canonical Invoice / Order / Receipt ID** (`INV-...`, `ORD-...`, `IN-...`, `REC-...`, `GPA....`).
   - Deduplicate by `(vendor_name, reference_no)` AND `(vendor_name, bill_date, amount)` across both `agent_system.db` and live Bigcapital bills before calling `POST /api/bills`.
2. **Idempotent Reprocessing (`force_reprocess=True`):**
   - Reprocessing an email or Drive receipt MUST call `update_bill` on the existing `bill_id`—NEVER `create_bill`.

## 3. 1-Step Atomic Settlement in 2-Step Bigcapital
Bigcapital is a 2-step accrual accounting system (`POST /api/bills` creates an open payable; `POST /api/bill-payments` settles it).
- **Already-Paid Receipts & Auto-Pay Deductions (`auto_pay=True`):**
  - Retail POS receipts (Costco, Michaels, Staples in-store), card-charged SaaS invoices (Canva, Google Play, Cloudflare, NWMLS Education), and auto-pay statements whose deduction date has passed MUST execute **Step 1 (Create Bill)** and **Step 2 (Record Bill Payment on `payment_date`)** atomically so `Due Amount = $0.00` and `Status = PAID`.
- **Unpaid Invoices / "To Be Paid In-Store" Orders (`auto_pay=False`):**
  - Order confirmations that state *"To be paid in-store"* (without an accompanying payment receipt) or invoices with a future due date remain `OPEN` until proof of payment is provided.

## 4. Sales Tax Reconciliation & Return / Refund Netting
1. **Post-Tax Total Enforcement (`Subtotal + Tax = Total`):**
   - Always extract the final post-tax amount charged to the payment method. Never match `total` inside `Subtotal`.
   - When both `Subtotal` and `Tax` (e.g., WA 10.4% sales tax) are present, verify `round(subtotal + tax, 2) == round(total, 2)`.
2. **Return & Refund Netting (`REFUNDED_NET_ZERO`):**
   - Detect return receipts (`START RETURN`, `Return`, negative amounts `(XX.XX)` or `USD$-XX.XX`).
   - Match the return to its original `Order Number`, mark both as `REFUNDED_NET_ZERO` in `tax_audit_ledger`, and remove/void the original purchase bill in Bigcapital so refunded purchases are never claimed as tax deductions.

## 5. IRS § 274(d) Substantiation & Missing-Proof Flagging ("TaxMan Standard")
Every business expense requires documentary proof showing: **(1) Vendor, (2) Date, (3) Itemized Description, (4) Amount Paid, and (5) Payment Method/Proof of Payment**.
- **Archive Every Proof:** Save the raw PDF or itemized receipt to `/tank/bigcapital/tax_vault/YYYY/` (with SHA-256 hash) and sync to Google Drive folder `1x3OD-FQAHWMyQnXEGal6WLj8-cHKFtYo` (*"Proof archive"*).
- **Flag Missing Proofs Immediately:**
  - `FLAGGED_MISSING_INVOICE_COPY`: Email is only an invoice notification link (e.g., Cloudflare notification without the PDF invoice attached).
  - `FLAGGED_MISSING_PAYMENT_RECEIPT`: Email is only an unpaid order confirmation (e.g., Staples *"To be paid in-store"*) without the final payment receipt.
  - `FLAGGED_MISSING_AMOUNT_AND_INVOICE`: Email is a clipped shipping/order confirmation (e.g., Amazon *"Ordered: 5 Pack Open House Signs..."*) missing the dollar amount and invoice copy. Do NOT guess or fabricate an amount—log it as flagged in `tax_audit_ledger` so the owner can provide the invoice.
