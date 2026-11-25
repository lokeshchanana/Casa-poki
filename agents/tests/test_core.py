"""
Offline unit & regression tests for Casa-poki agent-hub core logic.
Zero live network or CRM/Bigcapital side effects.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brevo_sync import format_e164_sms
from email_bills_watcher import parse_operating_bill
from gdrive_bills_watcher import parse_bill_details
from orchestrator import parse_antigravity_output
from state_store import categorize_request_flow


class TestFlowCategorization(unittest.TestCase):
    def test_infra_alerts_prioritized_over_crm(self):
        cat = categorize_request_flow(
            source="Uptime Kuma Alert Webhook",
            title="Infra Alert: Twenty CRM is DOWN",
            agents_involved=["Miles Miller", "Ian Torres", "Audrey Chen"],
        )
        self.assertEqual(cat, "infra")

    def test_home_assistant_categorized(self):
        cat = categorize_request_flow(
            source="HA Guardian Timer",
            title="Home Assistant Health Check",
            agents_involved=["Hannah Reed"],
        )
        self.assertEqual(cat, "home_assistant")

    def test_finance_categorized(self):
        cat = categorize_request_flow(
            source="Manager Chat UI",
            title="Ask Victor Sterling to run a full tax audit",
            agents_involved=["Marcus Vance", "Victor Sterling", "Audrey Chen"],
        )
        self.assertEqual(cat, "finance")


class TestEmailBillsParsing(unittest.TestCase):
    def test_staples_return_detected_and_tax_reconciled(self):
        body = """
        Here's your Staples receipt
        Date: 5/22/26
        Order Number: 2429014787
        START RETURN
        Subtotal $65.98
        Total $72.84
        """
        parsed = parse_operating_bill(
            sender="orders@staples.com",
            subject="Fwd: Here's your Staples receipt",
            date_str="2026-05-22",
            body_text=body,
            attachments_text="",
            msg_id="<test-return-1>",
        )
        self.assertIsNotNone(parsed)
        self.assertTrue(parsed.get("is_return"))
        self.assertEqual(parsed["reference_no"], "RET-2429014787")
        self.assertEqual(parsed["proof_status"], "REFUNDED_NET_ZERO")

    def test_cloudflare_missing_pdf_flagged(self):
        body = "Cloudflare Invoice IN-84013759 Amount: $11.55 Date of Issue Oct 16, 2026. Want your invoice attached? Enable email invoices."
        parsed = parse_operating_bill(
            sender="billing@cloudflare.com",
            subject="Your Cloudflare Invoice",
            date_str="2026-10-16",
            body_text=body,
            attachments_text="",
            msg_id="<test-cf-1>",
            has_pdf_attachment=False,
        )
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["proof_status"], "FLAGGED_MISSING_INVOICE_COPY")
        self.assertEqual(parsed["amount"], 11.55)


class TestDriveAmazonParsing(unittest.TestCase):
    def test_amazon_mixed_business_personal_allocation(self):
        ocr_text = """
        Order Summary
        Order placed October 17, 2026 Order # 113-6177088-0972239
        Item(s) Subtotal: $44.98
        Estimated tax to be collected: $4.68
        Grand Total: $49.66
        Delivered October 18
        67XL Ink Cartridges Black/Color Combo Pack Replacement for HP Ink
        Sold by: Colo Print US
        Return window closed on November 17, 2026
        $31.99
        Delivered October 19
        Silicone Ice Ball Molds for Whiskey - Set of 4 Round Makers with Lids
        Sold by: FOSOE
        Return window closed on November 17, 2026
        $12.99
        """
        parsed = parse_bill_details(ocr_text, "FILE_20261118_152515.pdf", "test-fid-1234567890")
        self.assertEqual(parsed["vendor"], "Amazon.com")
        self.assertEqual(parsed["reference_no"], "AMZN-113-6177088-0972239")
        self.assertEqual(parsed["bill_date"], "2026-10-17")
        self.assertEqual(parsed["subtotal"], 31.99)
        self.assertEqual(parsed["tax"], 3.33)
        self.assertEqual(parsed["amount"], 35.32)


class TestOrchestratorAndPhoneHelpers(unittest.TestCase):
    def test_parse_antigravity_tool_call(self):
        raw = '```json\n{"tool_call": {"name": "finance_tax_audit", "arguments": {"auto_fix_settlements": true}}}\n```'
        leading, calls = parse_antigravity_output(raw)
        self.assertEqual(leading, "")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["function"]["name"], "finance_tax_audit")

    def test_format_e164_sms(self):
        self.assertEqual(format_e164_sms("(801) 860-1052"), "+18018601052")
        self.assertEqual(format_e164_sms("1-801-860-1052"), "+18018601052")
        self.assertIsNone(format_e164_sms("123"))

    def test_failed_turn_persists_user_prompt_for_retry(self):
        import asyncio
        import tempfile
        import unittest.mock as mock
        import orchestrator
        import state_store

        orig_db = state_store.DB_PATH
        with tempfile.TemporaryDirectory() as tmpdir:
            state_store.DB_PATH = os.path.join(tmpdir, "test_agent_system.db")
            state_store.init_store()
            try:
                async def boom(*args, **kwargs):
                    raise RuntimeError("Simulated connection drop")

                async def run_test():
                    events = []
                    with mock.patch.object(orchestrator, "call_llm_chat", side_effect=boom):
                        async for ev in orchestrator.run_multi_agent_pipeline(
                            "Check Cloudflare invoice IN-84013759", session_id="test_retry_sess"
                        ):
                            events.append(ev)
                    return events

                events = asyncio.run(run_test())
                hist = state_store.get_chat_history("test_retry_sess", limit=10)
                self.assertEqual(len(hist), 2)
                self.assertEqual(hist[0]["role"], "user")
                self.assertEqual(hist[0]["content"], "Check Cloudflare invoice IN-84013759")
                self.assertEqual(hist[1]["role"], "assistant")
                self.assertIn("Request failed before completion", hist[1]["content"])
                self.assertTrue(any('"success": false' in e.lower() for e in events))
            finally:
                state_store.DB_PATH = orig_db


if __name__ == "__main__":
    unittest.main()
