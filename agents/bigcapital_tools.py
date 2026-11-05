"""
Bigcapital Accounting Client & Tool Suite for Fiona Banks (Financial Controller)
Casa-poki Intelligent Agent Hub
"""

import json
import logging
import os
import httpx
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("bigcapital_tools")

BIGCAPITAL_BASE_URL = os.environ.get("BIGCAPITAL_BASE_URL", "http://192.168.1.240:8096")
BIGCAPITAL_API_KEY = os.environ.get(
    "BIGCAPITAL_API_KEY",
    "bc_69a9abfed2d38ab07257031f867fa6999b6614c4a551931993fd1a66271e50f65dd64d0c794456933d2b456fb6dbe583",
)


class BigcapitalClient:
    """Async API Client for Bigcapital Core Accounting."""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = (base_url or BIGCAPITAL_BASE_URL).rstrip("/")
        self.api_key = api_key or BIGCAPITAL_API_KEY
        self._default_item_id = None
        self._default_expense_account_id = None

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 15.0,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                resp = await client.request(
                    method=method,
                    url=url,
                    json=payload,
                    params=params,
                    headers=self._get_headers(),
                )
                text = resp.text
                try:
                    data = resp.json() if text else {}
                except Exception:
                    data = {"raw": text}

                if resp.status_code >= 400:
                    # Ignore expected empty state for due bills
                    if endpoint == "/api/bills/due" and "BILL_NOT_FOUND" in text:
                        return {"ok": True, "status": 200, "data": []}
                    logger.error(f"Bigcapital API error [{resp.status_code}] {method} {url}: {text}")
                    return {
                        "ok": False,
                        "status": resp.status_code,
                        "error": data.get("message") or data.get("error") or text,
                        "raw": data,
                    }
                return {"ok": True, "status": resp.status_code, "data": data}
            except Exception as e:
                logger.exception(f"Bigcapital connection failure {method} {url}: {e}")
                return {"ok": False, "status": 500, "error": str(e)}

    # --------------------------------------------------------------------------
    # Accounts & Catalogs
    # --------------------------------------------------------------------------
    async def list_accounts(self) -> List[Dict[str, Any]]:
        res = await self._request("GET", "/api/accounts")
        if res.get("ok"):
            return res.get("data", {}).get("accounts", [])
        return []

    async def get_default_item_id(self) -> int:
        if self._default_item_id:
            return self._default_item_id
        res = await self._request("GET", "/api/items")
        if res.get("ok"):
            items = res.get("data", {}).get("data", [])
            for it in items:
                if it.get("purchasable", True):
                    self._default_item_id = it.get("id")
                    return self._default_item_id
        # Fallback to create or default
        create_res = await self._request(
            "POST",
            "/api/items",
            payload={
                "name": "General Expense / Bill Item",
                "type": "service",
                "purchasable": True,
                "costAccountId": 1020,
            },
        )
        if create_res.get("ok"):
            self._default_item_id = create_res.get("data", {}).get("id", 1000)
            return self._default_item_id
        return 1000

    # --------------------------------------------------------------------------
    # Vendors
    # --------------------------------------------------------------------------
    async def list_vendors(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        params = {"filter": query} if query else None
        res = await self._request("GET", "/api/vendors", params=params)
        if res.get("ok"):
            return res.get("data", {}).get("data", [])
        return []

    async def get_or_create_vendor(
        self,
        name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        clean_name = name.strip()
        existing = await self.list_vendors(query=clean_name)
        for v in existing:
            if v.get("display_name", "").lower() == clean_name.lower() or v.get("company_name", "").lower() == clean_name.lower():
                return {"ok": True, "vendor_id": v["id"], "vendor": v, "created": False}

        # Create new vendor
        payload = {
            "displayName": clean_name,
            "companyName": clean_name,
            "currencyCode": "USD",
            "active": True,
        }
        if email:
            payload["email"] = email
        if phone:
            payload["workPhone"] = phone
        if note:
            payload["note"] = note

        res = await self._request("POST", "/api/vendors", payload=payload)
        if res.get("ok"):
            vendor_id = res.get("data", {}).get("id")
            return {"ok": True, "vendor_id": vendor_id, "created": True}
        return {"ok": False, "error": res.get("error")}

    # --------------------------------------------------------------------------
    # Bills Management
    # --------------------------------------------------------------------------
    async def create_bill(
        self,
        vendor_name: str,
        amount: float,
        due_date: Optional[str] = None,
        bill_date: Optional[str] = None,
        note: Optional[str] = None,
        reference_no: Optional[str] = None,
        category: Optional[str] = None,
        cost_account_id: int = 1020,  # Default: Office expenses
        is_open: bool = True,
    ) -> Dict[str, Any]:
        """Record an incoming bill in Bigcapital."""
        # 1. Resolve or create vendor
        vendor_res = await self.get_or_create_vendor(vendor_name)
        if not vendor_res.get("ok"):
            return {"ok": False, "error": f"Failed to resolve vendor '{vendor_name}': {vendor_res.get('error')}"}
        vendor_id = vendor_res["vendor_id"]

        # 2. Resolve default item id
        item_id = await self.get_default_item_id()

        # 3. Dates
        today_str = datetime.now().strftime("%Y-%m-%d")
        b_date = bill_date or today_str
        d_date = due_date or b_date
        bill_num = f"BILL-{datetime.now().strftime('%Y%m%d')}-{int(datetime.now().timestamp()*1000)%100000:05d}"

        # 4. Line items
        description = note or f"{vendor_name} Bill"
        if category:
            description = f"[{category}] {description}"

        entries = [
            {
                "index": 1,
                "itemId": item_id,
                "rate": float(amount),
                "quantity": 1,
                "description": description,
                "costAccountId": cost_account_id,
            }
        ]

        payload = {
            "vendorId": vendor_id,
            "billNumber": bill_num,
            "billDate": b_date,
            "dueDate": d_date,
            "referenceNo": reference_no or bill_num,
            "note": note or f"Recorded by Fiona Banks for {vendor_name}",
            "open": is_open,
            "entries": entries,
        }

        res = await self._request("POST", "/api/bills", payload=payload)
        if res.get("ok"):
            bill_id = res.get("data", {}).get("id")
            return {
                "ok": True,
                "bill_id": bill_id,
                "vendor_name": vendor_name,
                "vendor_id": vendor_id,
                "amount": float(amount),
                "bill_date": b_date,
                "due_date": d_date,
                "status": "OPEN" if is_open else "DRAFT",
                "message": f"Successfully created bill #{bill_id} for {vendor_name} (${amount:,.2f})",
            }
        return {"ok": False, "error": res.get("error")}

    async def list_bills(self, status: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
        """List bills from Bigcapital with status and balance."""
        params = {"page_size": limit}
        res = await self._request("GET", "/api/bills", params=params)
        if not res.get("ok"):
            return {"ok": False, "error": res.get("error")}
        bills = res.get("data", {}).get("data", [])
        return {"ok": True, "total": len(bills), "bills": bills}

    async def get_due_bills(self) -> Dict[str, Any]:
        """Retrieve all currently due bills."""
        res = await self._request("GET", "/api/bills/due")
        if not res.get("ok"):
            # If no due bills exist, Bigcapital returns 400 BILL_NOT_FOUND
            if "BILL_NOT_FOUND" in str(res.get("raw")):
                return {"ok": True, "due_bills": []}
            return {"ok": False, "error": res.get("error")}
        return {"ok": True, "due_bills": res.get("data", [])}

    async def delete_bill(self, bill_id: int) -> Dict[str, Any]:
        """Delete a bill by ID (used for test cleanups and cancellations)."""
        res = await self._request("DELETE", f"/api/bills/{bill_id}")
        return res

    # --------------------------------------------------------------------------
    # Bill Payments & Settlements
    # --------------------------------------------------------------------------
    async def record_bill_payment(
        self,
        bill_id: int,
        amount: Optional[float] = None,
        payment_date: Optional[str] = None,
        payment_account_id: int = 1001,  # Default Cash/Bank account
        statement: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record a settlement/payment for an open bill."""
        # 1. Fetch bill details to verify balance and vendorId
        bill_res = await self._request("GET", f"/api/bills/{bill_id}")
        if not bill_res.get("ok"):
            return {"ok": False, "error": f"Bill #{bill_id} not found: {bill_res.get('error')}"}
        bill = bill_res.get("data", {})
        vendor_id = bill.get("vendor_id")
        due_amount = float(bill.get("due_amount", bill.get("amount", 0)))
        pay_amount = float(amount) if amount is not None else due_amount

        today_str = datetime.now().strftime("%Y-%m-%d")
        payload = {
            "vendorId": vendor_id,
            "amount": pay_amount,
            "paymentAccountId": payment_account_id,
            "paymentNumber": f"PAY-{bill_id}-{int(datetime.now().timestamp())}",
            "paymentDate": payment_date or today_str,
            "exchangeRate": 1,
            "statement": statement or f"Payment recorded by Fiona Banks for Bill #{bill_id}",
            "entries": [{"billId": bill_id, "paymentAmount": pay_amount}],
            "branchId": 0,
            "attachments": [],
        }

        res = await self._request("POST", "/api/bill-payments", payload=payload)
        if res.get("ok"):
            return {
                "ok": True,
                "bill_id": bill_id,
                "payment_id": res.get("data", {}).get("id"),
                "amount": pay_amount,
                "message": f"Successfully recorded payment of ${pay_amount:,.2f} against Bill #{bill_id}",
            }
        return {"ok": False, "error": res.get("error")}

    # --------------------------------------------------------------------------
    # Historical Batch Import
    # --------------------------------------------------------------------------
    async def import_historical_bills(self, bills_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Batch-import historical bills into Bigcapital with automatic vendor resolution."""
        results = []
        success_count = 0
        failure_count = 0

        for idx, item in enumerate(bills_data):
            vendor = item.get("vendor") or item.get("vendor_name")
            amount = item.get("amount", 0)
            bill_date = item.get("bill_date") or item.get("date")
            due_date = item.get("due_date") or bill_date
            note = item.get("note") or item.get("description") or f"Historical import entry #{idx+1}"
            ref_no = item.get("reference_no") or item.get("invoice_no") or ""
            is_paid = item.get("is_paid", False)

            creation = await self.create_bill(
                vendor_name=vendor,
                amount=amount,
                bill_date=bill_date,
                due_date=due_date,
                note=note,
                reference_no=ref_no,
                is_open=True,
            )
            if creation.get("ok"):
                bill_id = creation["bill_id"]
                if is_paid:
                    # Settle payment if historically already paid
                    pay_res = await self.record_bill_payment(
                        bill_id=bill_id,
                        amount=amount,
                        payment_date=bill_date,
                        statement=f"Historical payment settlement ({ref_no})",
                    )
                    creation["payment_status"] = "SETTLED" if pay_res.get("ok") else "UNSETTLED"
                results.append(creation)
                success_count += 1
            else:
                results.append({"ok": False, "vendor": vendor, "amount": amount, "error": creation.get("error")})
                failure_count += 1

        return {
            "ok": True,
            "total_submitted": len(bills_data),
            "imported": success_count,
            "failed": failure_count,
            "details": results,
        }

    # --------------------------------------------------------------------------
    # Financial Dashboard & Balance Inquiries
    # --------------------------------------------------------------------------
    async def get_financial_dashboard(self) -> Dict[str, Any]:
        """Summary of accounts payable, active bills, and vendor balances."""
        bills_res = await self.list_bills(limit=50)
        bills = bills_res.get("bills", []) if bills_res.get("ok") else []

        total_payable = 0.0
        total_open_bills = 0
        total_paid_bills = 0

        for b in bills:
            status = b.get("status", "").upper()
            due_amt = float(b.get("due_amount", 0) or 0)
            total_payable += due_amt
            if status == "PAID" or due_amt == 0:
                total_paid_bills += 1
            else:
                total_open_bills += 1

        due_res = await self.get_due_bills()
        due_bills = due_res.get("due_bills", []) if due_res.get("ok") else []

        return {
            "ok": True,
            "app_url": "https://finance.lokeshchanana.com",
            "total_open_bills": total_open_bills,
            "total_paid_bills": total_paid_bills,
            "total_payable_usd": round(total_payable, 2),
            "urgent_due_bills": len(due_bills),
            "recent_bills_sample": bills[:5],
        }


# Global singleton instance
bigcapital_client = BigcapitalClient()
