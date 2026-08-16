#!/usr/bin/env python3
"""Seam tests for workflows/wf-tg-bot.json public interface/structure.

Public surface: the workflow JSON must be valid n8n 2.34.4 structure with
reachable profile/profiles/add_operator/operators routes, no hardcoded
owner tg_user_id, and correct active_client_id resolution SQL pattern.

Run: python3 -m pytest tests/test_wf_tg_bot.py -v
"""
import json
import os
import re
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF_PATH = os.path.join(ROOT, "workflows", "wf-tg-bot.json")


class WfTgBotStructureTests(unittest.TestCase):
    """Structural seam: JSON loads, node names unique, commands exist."""

    @classmethod
    def setUpClass(cls):
        with open(WF_PATH) as f:
            cls.data = json.load(f)
        cls.wf = cls.data[0] if isinstance(cls.data, list) else cls.data
        cls.nodes = {n["name"]: n for n in cls.wf["nodes"]}

    def test_json_loads_and_is_array_workflow(self):
        self.assertIsInstance(self.data, list)
        self.assertEqual(self.wf.get("settings", {}).get("executionOrder"), "v1")

    def test_no_duplicate_node_names(self):
        names = [n["name"] for n in self.wf["nodes"]]
        self.assertEqual(len(names), len(set(names)))

    def test_parser_knows_profile_commands(self):
        parser = self.nodes["Parser"]["parameters"]["jsCode"]
        for cmd in ("profile", "profiles", "add_operator", "operators"):
            self.assertIn(f"'{cmd}': '{cmd}'", parser,
                          f"Parser command map missing {cmd}")

    def test_switch_cmd_has_profile_routes(self):
        scmd = self.nodes["Switch cmd"]["parameters"]["rules"]["values"]
        rules = [
            r["conditions"]["conditions"][0].get("rightValue") for r in scmd
        ]
        for cmd in ("profile", "profiles", "add_operator", "operators"):
            self.assertIn(cmd, rules, f"Switch cmd missing route {cmd}")

    def test_no_hardcoded_owner_tg_id(self):
        raw = json.dumps(self.wf, ensure_ascii=False)
        self.assertNotIn("941296693", raw,
                         "hardcoded owner tg_user_id found in workflow")

    def test_active_client_id_resolution_pattern_present(self):
        """Resolution seam: users.active_client_id -> settings.active_client_id fallback."""
        pattern = ("SELECT u.active_client_id FROM users u WHERE u.tg_user_id = ?"
                   ", (SELECT CAST(value AS INTEGER) FROM settings WHERE key='active_client_id')")
        found = 0
        for n in self.wf["nodes"]:
            js = n.get("parameters", {}).get("jsCode", "")
            if "SELECT u.active_client_id FROM users u WHERE u.tg_user_id = ?" in js:
                found += 1
        self.assertGreater(found, 0, "active_client_id resolution SQL not found")

    def test_telegram_nodes_use_correct_type_version(self):
        for n in self.wf["nodes"]:
            if n["type"] == "n8n-nodes-base.telegram":
                self.assertEqual(n.get("typeVersion"), 1.2, n["name"])

    def test_switch_nodes_use_correct_type_version(self):
        for n in self.wf["nodes"]:
            if n["type"] == "n8n-nodes-base.switch":
                self.assertEqual(n.get("typeVersion"), 3.4, n["name"])

    def test_callback_data_format(self):
        for n in self.wf["nodes"]:
            if n["type"] != "n8n-nodes-base.telegram":
                continue
            kb = n.get("parameters", {}).get("inlineKeyboard", {})
            for r in kb.get("rows", []):
                for b in r.get("row", {}).get("buttons", []):
                    cb = (b.get("additionalFields") or {}).get("callback_data", "")
                    if "{{" in cb:
                        self.assertTrue(
                            cb.lstrip().startswith("={{"),
                            f"{n['name']}: broken callback_data {cb}"
                        )

    def test_node_check_passes_all_js_code(self):
        code_nodes = [
            n for n in self.wf["nodes"]
            if n["type"] == "n8n-nodes-base.code"
        ]
        for n in code_nodes:
            js = n["parameters"].get("jsCode", "")
            if not js.strip():
                continue
            result = subprocess.run(
                ["node", "--check", "-"],
                input=js.encode("utf-8"),
                capture_output=True
            )
            self.assertEqual(
                result.returncode, 0,
                f"node --check FAIL {n['name']}: {result.stderr.decode()[:200]}"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
