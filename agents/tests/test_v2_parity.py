import asyncio
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import state_store
from context_manager import inspect_artifact_data, store_or_inline_tool_output
from hooks import pre_tool_use_hook
from llm_gateway import parse_antigravity_output, select_model_tier
from multimodal import save_and_extract_attachment
from subagent_runtime import SPECIALIST_TOOL_MAP, get_tools_for_agent
from web_research import fetch_webpage


class TestAgentHubV2Parity(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig_db = state_store.DB_PATH
        state_store.DB_PATH = os.path.join(self._tmp.name, "test_agent_system.db")
        state_store.init_store()

    def tearDown(self):
        state_store.DB_PATH = self._orig_db
        self._tmp.cleanup()

    def test_parallel_tool_call_parser(self):
        raw = '```json\n{"tool_calls":[{"name":"web_search","arguments":{"query":"WA rates"}},{"name":"ha_health_check","arguments":{}}]}\n```'
        leading, calls = parse_antigravity_output(raw)
        self.assertEqual(leading, "")
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["function"]["name"], "web_search")
        self.assertEqual(calls[1]["function"]["name"], "ha_health_check")

    def test_model_tier_routing(self):
        self.assertIn("flash", select_model_tier(task_type="audit"))
        self.assertIn("carbon", select_model_tier(agent_name="tax_auditor"))
        self.assertIn("hydrogen", select_model_tier(agent_name="manager", user_message="hello"))

    def test_all_12_specialists_have_tools(self):
        for spec_id in SPECIALIST_TOOL_MAP:
            tools = get_tools_for_agent(spec_id)
            self.assertGreater(len(tools), 0, f"Specialist {spec_id} resolved 0 tools")

    def test_pre_tool_use_hook_keeps_add_update_automated_and_gates_deletes(self):
        self.assertEqual(
            pre_tool_use_hook("create_contact", {"name": "Lokesh", "email": "lokeshchanana@gmail.com"})["decision"],
            "ALLOW",
        )
        self.assertEqual(
            pre_tool_use_hook("update_contact", {"contact_id": "123", "market": "Bellevue"})["decision"],
            "ALLOW",
        )
        self.assertEqual(
            pre_tool_use_hook("finance_record_bill", {"vendor": "Test", "total": 10.0})["decision"],
            "ALLOW",
        )
        self.assertEqual(
            pre_tool_use_hook("delete_contact", {"contact_id": "123"})["decision"],
            "REQUIRE_APPROVAL",
        )
        self.assertEqual(
            pre_tool_use_hook("crm_entity_operation", {"entity": "people", "action": "delete", "id": "123"})["decision"],
            "REQUIRE_APPROVAL",
        )
        self.assertEqual(
            pre_tool_use_hook("create_contact", {"name": "Fake", "email": "foo@example.com"})["decision"],
            "BLOCK",
        )
        self.assertEqual(
            pre_tool_use_hook("infra_restart_container", {"container_name": "real-estate"})["decision"],
            "BLOCK",
        )

    def test_artifact_store_prevents_silent_truncation(self):
        big_payload = {"ok": True, "contacts": [{"id": i, "name": f"Client {i}"} for i in range(300)]}
        preview_str = store_or_inline_tool_output("sess_1", "search_contacts", big_payload, max_inline_chars=1500)
        preview = json.loads(preview_str)
        self.assertTrue(preview.get("stored_full_output"))
        art_id = preview["artifact_id"]
        page = inspect_artifact_data(art_id, query="Client 250", offset=0, limit=10)
        self.assertTrue(page["ok"])
        self.assertEqual(page["total_matching"], 1)
        self.assertEqual(page["items"][0]["id"], 250)

    def test_zero_spend_search_quota_hard_cap(self):
        res_ok = state_store.reserve_search_quota("tavily", credits=35, monthly_limit=900, daily_limit=35)
        self.assertTrue(res_ok["allowed"])
        res_blocked = state_store.reserve_search_quota("tavily", credits=1, monthly_limit=900, daily_limit=35)
        self.assertFalse(res_blocked["allowed"])
        self.assertEqual(res_blocked["reason"], "free_tier_cap_reached")

    def test_ssrf_guard_blocks_internal_ips(self):
        res1 = asyncio.run(fetch_webpage("http://127.0.0.1:8094/api/manager/health"))
        self.assertFalse(res1["ok"])
        res2 = asyncio.run(fetch_webpage("http://192.168.1.240:8085/"))
        self.assertFalse(res2["ok"])

    def test_multimodal_text_extraction(self):
        res = save_and_extract_attachment("sample.txt", b"Invoice #991 Total $42.50", "text/plain")
        self.assertTrue(res["ok"])
        self.assertIn("Invoice #991", res["extracted_text"])


if __name__ == "__main__":
    unittest.main()
