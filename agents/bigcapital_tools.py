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


def _snake_to_camel(s: str) -> str:
    """Converts snake_case string to camelCase. Leaves camelCase or single words unchanged."""
    if "_" not in s:
        return s
    parts = s.split("_")
    return parts[0] + "".join(x.capitalize() for x in parts[1:])


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
        auto_pay: bool = False,
        payment_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record an incoming bill in Bigcapital with strict idempotency and optional 1-step atomic payment settlement."""
        # 1. Resolve or create vendor
        vendor_res = await self.get_or_create_vendor(vendor_name)
        if not vendor_res.get("ok"):
            return {"ok": False, "error": f"Failed to resolve vendor '{vendor_name}': {vendor_res.get('error')}"}
        vendor_id = vendor_res["vendor_id"]

        # 2. Dates
        today_str = datetime.now().strftime("%Y-%m-%d")
        b_date = bill_date or today_str
        d_date = due_date or b_date
        clean_ref = (reference_no or "").strip()

        # 3. Idempotency / Anti-Duplication Guardrail against live Bigcapital ledger
        existing_res = await self.list_bills(limit=200)
        if existing_res.get("ok"):
            for eb in existing_res.get("bills", []):
                eb_id = eb.get("id")
                eb_ref = (eb.get("reference_no") or eb.get("referenceNo") or "").strip()
                eb_vid = eb.get("vendor_id") or (eb.get("vendor") or {}).get("id")
                eb_date = eb.get("bill_date") or eb.get("billDate")
                eb_tot = round(float(eb.get("total") or eb.get("amount") or 0.0), 2)
                eb_due = round(float(eb.get("due_amount") or 0.0), 2)

                ref_match = bool(
                    clean_ref
                    and not clean_ref.startswith("BILL-")
                    and eb_ref.lower() == clean_ref.lower()
                )
                tuple_match = bool(
                    not clean_ref
                    and eb_vid == vendor_id
                    and eb_date == b_date
                    and eb_tot == round(float(amount), 2)
                )

                if ref_match or tuple_match:
                    logger.info(f"Idempotency match: Bill #{eb_id} already exists for {vendor_name} (Ref={eb_ref}). Updating/returning existing bill.")
                    if eb_tot != round(float(amount), 2) or eb_date != b_date:
                        await self.update_bill(
                            bill_id=eb_id,
                            vendor_name=vendor_name,
                            amount=float(amount),
                            bill_date=b_date,
                            due_date=d_date,
                            reference_no=clean_ref or eb_ref,
                            note=note,
                            category=category,
                        )
                    payment_id = None
                    if auto_pay and eb_due > 0:
                        pay_res = await self.record_bill_payment(
                            bill_id=eb_id,
                            amount=round(float(amount), 2),
                            payment_date=payment_date or b_date,
                            statement=f"Auto-settled 1-step payment for {clean_ref or eb_ref} ({vendor_name})",
                        )
                        if pay_res.get("ok"):
                            payment_id = pay_res.get("payment_id")
                            eb_due = 0.0
                    return {
                        "ok": True,
                        "already_exists": True,
                        "bill_id": eb_id,
                        "payment_id": payment_id,
                        "vendor_name": vendor_name,
                        "vendor_id": vendor_id,
                        "amount": float(amount),
                        "bill_date": b_date,
                        "due_date": d_date,
                        "status": "PAID" if (auto_pay or eb_due == 0) else "OPEN",
                        "message": f"Bill #{eb_id} already exists for {vendor_name} (${amount:,.2f}) — deduplicated.",
                    }

        # 4. Resolve default item id
        item_id = await self.get_default_item_id()
        bill_num = f"BILL-{datetime.now().strftime('%Y%m%d')}-{int(datetime.now().timestamp()*1000)%100000:05d}"

        # 5. Line items
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
            "referenceNo": clean_ref or bill_num,
            "note": note or f"Recorded by Fiona Banks for {vendor_name}",
            "open": is_open,
            "entries": entries,
        }

        res = await self._request("POST", "/api/bills", payload=payload)
        if res.get("ok"):
            bill_id = res.get("data", {}).get("id")
            payment_id = None
            status_str = "OPEN" if is_open else "DRAFT"
            if auto_pay and bill_id:
                pay_res = await self.record_bill_payment(
                    bill_id=bill_id,
                    amount=round(float(amount), 2),
                    payment_date=payment_date or b_date,
                    statement=f"Auto-settled 1-step payment for {clean_ref or bill_num} ({vendor_name})",
                )
                if pay_res.get("ok"):
                    payment_id = pay_res.get("payment_id")
                    status_str = "PAID"
            return {
                "ok": True,
                "bill_id": bill_id,
                "payment_id": payment_id,
                "vendor_name": vendor_name,
                "vendor_id": vendor_id,
                "amount": float(amount),
                "bill_date": b_date,
                "due_date": d_date,
                "status": status_str,
                "message": f"Successfully created bill #{bill_id} ({status_str}) for {vendor_name} (${amount:,.2f})",
            }
        return {"ok": False, "error": res.get("error")}

    async def list_bills(self, status: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
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

    async def update_bill(
        self,
        bill_id: Optional[int] = None,
        vendor_name: Optional[str] = None,
        reference_no: Optional[str] = None,
        amount: Optional[float] = None,
        due_date: Optional[str] = None,
        bill_date: Optional[str] = None,
        note: Optional[str] = None,
        category: Optional[str] = None,
        open: Optional[bool] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Update an existing bill in Bigcapital (PUT /api/bills/{bill_id})."""
        # 1. Resolve bill_id if not given directly
        if not bill_id:
            bills_res = await self.list_bills(limit=100)
            if bills_res.get("ok"):
                for b in bills_res.get("bills", []):
                    b_ref = (b.get("reference_no") or b.get("referenceNo") or "").lower()
                    b_vname = (b.get("vendor_name") or "").lower()
                    b_num = (b.get("bill_number") or b.get("billNumber") or "").lower()
                    if reference_no and reference_no.lower() in (b_ref, b_num):
                        bill_id = b.get("id")
                        break
                    if vendor_name and vendor_name.lower() in b_vname:
                        bill_id = b.get("id")
                        break
        if not bill_id:
            return {"ok": False, "error": "bill_id is required or could not be resolved from vendor/reference."}

        # 2. Fetch current bill data
        curr_res = await self._request("GET", f"/api/bills/{bill_id}")
        if not curr_res.get("ok"):
            return {"ok": False, "error": f"Bill #{bill_id} not found: {curr_res.get('error')}"}
        curr = curr_res.get("data", {})

        # 3. Resolve vendor if vendor_name was passed and changed
        vendor_id = curr.get("vendor_id") or curr.get("vendorId")
        if vendor_name:
            v_res = await self.get_or_create_vendor(vendor_name)
            if v_res.get("ok"):
                vendor_id = v_res.get("vendor_id")

        # 4. Handle entries / rate
        entries = curr.get("entries") or []
        if amount is not None:
            amt_float = float(amount)
            if entries:
                entries[0]["rate"] = amt_float
                if note or category:
                    desc = note or entries[0].get("description") or f"Bill #{bill_id}"
                    entries[0]["description"] = f"[{category}] {desc}" if category else desc
            else:
                item_id = await self.get_default_item_id()
                entries = [{
                    "index": 1,
                    "itemId": item_id,
                    "rate": amt_float,
                    "quantity": 1,
                    "description": f"[{category}] {note}" if category else (note or f"Bill #{bill_id}"),
                    "costAccountId": 1020,
                }]

        # 5. Build PUT payload preserving required Bigcapital fields
        payload = {
            "vendorId": vendor_id,
            "billNumber": curr.get("bill_number") or curr.get("billNumber"),
            "billDate": bill_date or curr.get("bill_date") or curr.get("billDate"),
            "dueDate": due_date or curr.get("due_date") or curr.get("dueDate"),
            "referenceNo": reference_no or curr.get("reference_no") or curr.get("referenceNo"),
            "note": note if note is not None else (curr.get("note") or ""),
            "open": open if open is not None else curr.get("open", True),
            "entries": entries,
        }

        # Dynamically map any extra kwargs
        for k, v in kwargs.items():
            if k not in ("tool", "action", "direct", "sessionId", "session_id") and v is not None:
                payload[_snake_to_camel(k)] = v

        res = await self._request("PUT", f"/api/bills/{bill_id}", payload=payload)
        if res.get("ok"):
            return {
                "ok": True,
                "bill_id": bill_id,
                "amount": float(amount) if amount is not None else float(curr.get("amount", 0)),
                "vendor_id": vendor_id,
                "due_date": payload["dueDate"],
                "bill_date": payload["billDate"],
                "note": payload["note"],
                "status": "OPEN" if payload["open"] else "DRAFT",
                "message": f"Successfully updated bill #{bill_id} in Bigcapital.",
            }
        return {"ok": False, "error": res.get("error")}

    async def manage_vendors(
        self,
        action: str = "list",
        vendor_id: Optional[int] = None,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        note: Optional[str] = None,
        company_name: Optional[str] = None,
        website: Optional[str] = None,
        address: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        postcode: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 50,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Manage Bigcapital vendors (list, get, create, update, delete)."""
        act = (action or "list").strip().lower()

        if act == "list":
            params = {"page_size": limit}
            if query or name:
                params["filter"] = query or name
            res = await self._request("GET", "/api/vendors", params=params)
            if not res.get("ok"):
                return {"ok": False, "error": res.get("error")}
            vendors = res.get("data", {}).get("data", [])
            return {"ok": True, "total": len(vendors), "vendors": vendors}

        elif act in ("get", "read"):
            if not vendor_id:
                if name:
                    existing = await self.list_vendors(query=name)
                    if existing:
                        vendor_id = existing[0]["id"]
            if not vendor_id:
                return {"ok": False, "error": "vendor_id or valid name is required."}
            res = await self._request("GET", f"/api/vendors/{vendor_id}")
            if not res.get("ok"):
                return {"ok": False, "error": res.get("error")}
            return {"ok": True, "vendor_id": vendor_id, "vendor": res.get("data", {})}

        elif act in ("create", "add"):
            clean_name = (name or company_name or "").strip()
            if not clean_name:
                return {"ok": False, "error": "Vendor name is required."}
            payload = {
                "displayName": clean_name,
                "companyName": company_name or clean_name,
                "currencyCode": "USD",
                "active": True,
            }
            if email:
                payload["email"] = email.strip()
            if phone:
                payload["workPhone"] = phone.strip()
            if note:
                payload["note"] = note.strip()
            if website:
                payload["website"] = website.strip()
            if address:
                payload["billingAddress1"] = address.strip()
            if city:
                payload["billingAddressCity"] = city.strip()
            if state:
                payload["billingAddressState"] = state.strip()
            if postcode:
                payload["billingAddressPostcode"] = postcode.strip()

            for k, v in kwargs.items():
                if v is not None:
                    payload[_snake_to_camel(k)] = v

            res = await self._request("POST", "/api/vendors", payload=payload)
            if res.get("ok"):
                new_id = res.get("data", {}).get("id")
                return {
                    "ok": True,
                    "vendor_id": new_id,
                    "name": clean_name,
                    "message": f"Successfully created vendor '{clean_name}' (ID: {new_id}).",
                }
            return {"ok": False, "error": res.get("error")}

        elif act in ("update", "edit", "patch"):
            if not vendor_id and name:
                existing = await self.list_vendors(query=name)
                if existing:
                    vendor_id = existing[0]["id"]
            if not vendor_id:
                return {"ok": False, "error": "vendor_id is required to update vendor."}

            curr_res = await self._request("GET", f"/api/vendors/{vendor_id}")
            if not curr_res.get("ok"):
                return {"ok": False, "error": f"Vendor #{vendor_id} not found: {curr_res.get('error')}"}
            curr = curr_res.get("data", {})

            clean_name = (name or curr.get("display_name") or curr.get("displayName") or "").strip()
            payload = {
                "displayName": clean_name,
                "companyName": company_name or curr.get("company_name") or curr.get("companyName") or clean_name,
                "currencyCode": "USD",
                "active": True,
            }
            if email is not None:
                payload["email"] = email.strip()
            elif curr.get("email"):
                payload["email"] = curr["email"]

            if phone is not None:
                payload["workPhone"] = phone.strip()
            elif curr.get("work_phone") or curr.get("workPhone"):
                payload["workPhone"] = curr.get("work_phone") or curr.get("workPhone")

            if note is not None:
                payload["note"] = note.strip()
            elif curr.get("note"):
                payload["note"] = curr["note"]

            if website is not None:
                payload["website"] = website.strip()
            elif curr.get("website"):
                payload["website"] = curr["website"]

            if address is not None:
                payload["billingAddress1"] = address.strip()
            if city is not None:
                payload["billingAddressCity"] = city.strip()
            if state is not None:
                payload["billingAddressState"] = state.strip()
            if postcode is not None:
                payload["billingAddressPostcode"] = postcode.strip()

            for k, v in kwargs.items():
                if v is not None:
                    payload[_snake_to_camel(k)] = v

            res = await self._request("PUT", f"/api/vendors/{vendor_id}", payload=payload)
            if res.get("ok"):
                return {
                    "ok": True,
                    "vendor_id": vendor_id,
                    "name": clean_name,
                    "updated_fields": list(payload.keys()),
                    "message": f"Successfully updated vendor '{clean_name}' (ID: {vendor_id}).",
                }
            return {"ok": False, "error": res.get("error")}

        elif act in ("delete", "remove"):
            if not vendor_id and name:
                existing = await self.list_vendors(query=name)
                if existing:
                    vendor_id = existing[0]["id"]
            if not vendor_id:
                return {"ok": False, "error": "vendor_id is required to delete vendor."}
            res = await self._request("DELETE", f"/api/vendors/{vendor_id}")
            if res.get("ok"):
                return {
                    "ok": True,
                    "vendor_id": vendor_id,
                    "message": f"Successfully deleted vendor #{vendor_id}.",
                }
            return {"ok": False, "error": res.get("error")}

        return {"ok": False, "error": f"Unsupported vendor action '{act}'."}

    async def manage_bill_payments(
        self,
        action: str = "list",
        payment_id: Optional[int] = None,
        bill_id: Optional[int] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Manage Bigcapital bill payments (list, get, delete)."""
        act = (action or "list").strip().lower()

        if act == "list":
            params = {"page_size": limit}
            res = await self._request("GET", "/api/bill-payments", params=params)
            if not res.get("ok"):
                return {"ok": False, "error": res.get("error")}
            payments = res.get("data", {}).get("data", [])
            return {"ok": True, "total": len(payments), "payments": payments}

        elif act in ("get", "read"):
            if not payment_id:
                return {"ok": False, "error": "payment_id is required."}
            res = await self._request("GET", f"/api/bill-payments/{payment_id}")
            if not res.get("ok"):
                return {"ok": False, "error": res.get("error")}
            return {"ok": True, "payment_id": payment_id, "payment": res.get("data", {})}

        elif act in ("delete", "void"):
            if not payment_id:
                return {"ok": False, "error": "payment_id is required to void/delete payment."}
            res = await self._request("DELETE", f"/api/bill-payments/{payment_id}")
            if res.get("ok"):
                return {"ok": True, "payment_id": payment_id, "message": f"Successfully deleted bill payment #{payment_id}."}
            return {"ok": False, "error": res.get("error")}

        return {"ok": False, "error": f"Unsupported bill payment action '{act}'."}

    async def entity_operation(
        self,
        entity: str,
        action: str = "list",
        id: Optional[Any] = None,
        data: Optional[Dict[str, Any]] = None,
        filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Universal dynamic CRUD gateway for Bigcapital REST API."""
        raw_entity = (entity or "bills").strip().lower()
        entity_map = {
            "bill": "bills",
            "bills": "bills",
            "vendor": "vendors",
            "vendors": "vendors",
            "payment": "bill-payments",
            "payments": "bill-payments",
            "bill_payment": "bill-payments",
            "bill_payments": "bill-payments",
            "bill-payment": "bill-payments",
            "bill-payments": "bill-payments",
            "account": "accounts",
            "accounts": "accounts",
            "item": "items",
            "items": "items",
            "customer": "customers",
            "customers": "customers",
            "invoice": "sale-invoices",
            "invoices": "sale-invoices",
            "sale_invoice": "sale-invoices",
            "sale_invoices": "sale-invoices",
            "expense": "expenses",
            "expenses": "expenses",
        }
        endpoint_entity = entity_map.get(raw_entity, raw_entity)
        act = (action or "list").strip().lower()

        # Normalize data dict if provided
        normalized_data: Dict[str, Any] = {}
        if isinstance(data, dict):
            for k, v in data.items():
                camel_k = _snake_to_camel(k)
                normalized_data[camel_k] = v

        if act in ("get", "read"):
            if id:
                res = await self._request("GET", f"/api/{endpoint_entity}/{id}")
                return {
                    "ok": res.get("ok", False),
                    "entity": endpoint_entity,
                    "action": "get",
                    "id": id,
                    "data": res.get("data", {}),
                    "error": res.get("error"),
                    "message": f"Retrieved {endpoint_entity} #{id}.",
                }
            else:
                params = {"page_size": 50}
                if filter:
                    params["filter"] = filter
                res = await self._request("GET", f"/api/{endpoint_entity}", params=params)
                return {
                    "ok": res.get("ok", False),
                    "entity": endpoint_entity,
                    "action": "list",
                    "data": res.get("data", {}),
                    "error": res.get("error"),
                    "message": f"Listed {endpoint_entity} records.",
                }

        elif act in ("list", "search"):
            params = {"page_size": 50}
            if filter:
                params["filter"] = filter
            res = await self._request("GET", f"/api/{endpoint_entity}", params=params)
            return {
                "ok": res.get("ok", False),
                "entity": endpoint_entity,
                "action": "list",
                "data": res.get("data", {}),
                "error": res.get("error"),
                "message": f"Listed {endpoint_entity} records.",
            }

        elif act in ("create", "post", "add"):
            res = await self._request("POST", f"/api/{endpoint_entity}", payload=normalized_data)
            created_data = res.get("data", {})
            created_id = created_data.get("id") if isinstance(created_data, dict) else None
            return {
                "ok": res.get("ok", False),
                "entity": endpoint_entity,
                "action": "create",
                "id": created_id,
                "data": created_data,
                "error": res.get("error"),
                "message": f"Created {endpoint_entity} record (ID: {created_id}).",
            }

        elif act in ("update", "put", "edit"):
            if not id:
                return {"ok": False, "error": f"ID is required to update {endpoint_entity}."}
            res = await self._request("PUT", f"/api/{endpoint_entity}/{id}", payload=normalized_data)
            return {
                "ok": res.get("ok", False),
                "entity": endpoint_entity,
                "action": "update",
                "id": id,
                "data": res.get("data", {}),
                "error": res.get("error"),
                "message": f"Updated {endpoint_entity} #{id}.",
            }

        elif act in ("delete", "remove"):
            if not id:
                return {"ok": False, "error": f"ID is required to delete {endpoint_entity}."}
            res = await self._request("DELETE", f"/api/{endpoint_entity}/{id}")
            return {
                "ok": res.get("ok", False),
                "entity": endpoint_entity,
                "action": "delete",
                "id": id,
                "error": res.get("error"),
                "message": f"Deleted {endpoint_entity} #{id}.",
            }

        return {"ok": False, "error": f"Unsupported action '{act}' for {endpoint_entity}."}

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
            status = (b.get("status") or "").upper()
            due_amt = float(b.get("due_amount", 0) or 0)
            total_payable += due_amt
            if status == "PAID" or due_amt == 0:
                total_paid_bills += 1
            else:
                total_open_bills += 1

        due_res = await self.get_due_bills()
        due_bills = due_res.get("due_bills", []) if due_res.get("ok") else []
        urgent_count = len(due_bills) if due_bills else sum(1 for b in bills if b.get("is_overdue") and float(b.get("due_amount", 0) or 0) > 0)

        return {
            "ok": True,
            "app_url": "https://finance.lokeshchanana.com",
            "total_open_bills": total_open_bills,
            "total_paid_bills": total_paid_bills,
            "total_payable_usd": round(total_payable, 2),
            "urgent_due_bills": urgent_count,
            "recent_bills_sample": bills[:5],
        }


# Global singleton instance
bigcapital_client = BigcapitalClient()
