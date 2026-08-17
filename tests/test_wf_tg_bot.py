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
            if not isinstance(kb, dict):  # expression-клавиатура целиком (= {{ {rows: ...} }})
                continue
            rows_val = kb.get("rows", [])
            if isinstance(rows_val, str):  # expression-клавиатура (динамические кнопки)
                continue
            for r in rows_val:
                if not isinstance(r, dict):
                    continue
                for b in (r.get("row", {}) if isinstance(r.get("row"), dict) else {}).get("buttons", []):
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

    def test_outgoing_telegram_nodes_have_navigation_buttons(self):
        """Every outgoing Telegram message (non answerCallbackQuery) must have
        an inline keyboard with cmd:menu and cmd:cancel, except listed
        service nodes.
        """
        full_exceptions = {
            n["name"] for n in self.wf["nodes"]
            if n["type"] == "n8n-nodes-base.telegram"
            and n.get("parameters", {}).get("operation") == "answerQuery"
        }
        # sendVideo node: action buttons are provided by separate TG sh buttons.
        full_exceptions.add("TG sh video")
        # Menu screens already expose the main navigation as their own buttons.
        menu_nodes = {
            "TG menu", "TG menu gen", "TG menu analytics", "TG menu publish",
            "TG menu system",
        }
        full_exceptions.update(menu_nodes)

        cancel_exceptions = {
            "TG start", "TG cancel", "TG ping", "TG status", "TG unknown"
        }
        # Informational one-off messages carry only the Menu navigation button.
        only_menu = {
            "TG help", "TG status", "TG ping", "TG reload", "TG mode",
            "TG topics", "TG competitors", "TG accounts", "TG budget",
            "TG clients", "TG creators", "TG creator", "TG creator content",
            "TG audience", "TG transcript", "TG comments", "TG upload avatar",
            "TG my avatars", "TG shorts", "TG publish type", "TG instruction",
            "TG hint",
        }
        cancel_exceptions.update(only_menu)

        # Expression-keyboard nodes: the Menu/Cancel buttons are produced
        # by upstream Code nodes (AVV Carousel build / AVV My avatars) and
        # pinned by tests/test_avv_carousel.py.
        expression_keyboard_nodes = {
            "TG avv carousel", "TG avv my avatars"
        }
        full_exceptions.update(expression_keyboard_nodes)

        menu_re = re.compile(r"\bcmd:menu\b")
        cancel_re = re.compile(r"\bcmd:cancel\b")

        def callback_data_strings(keyboard):
            """Yield callback_data values from a static or expression keyboard."""
            if isinstance(keyboard, str):
                yield keyboard
                return
            if not isinstance(keyboard, dict):
                return
            rows = keyboard.get("rows", [])
            if isinstance(rows, str):
                yield rows
                return
            for row in rows:
                if not isinstance(row, dict):
                    continue
                row_data = row.get("row", {})
                if not isinstance(row_data, dict):
                    continue
                for btn in row_data.get("buttons", []):
                    if not isinstance(btn, dict):
                        continue
                    cb = (btn.get("additionalFields") or {}).get(
                        "callback_data", ""
                    )
                    yield cb

        violations = []
        for n in self.wf["nodes"]:
            if n["type"] != "n8n-nodes-base.telegram":
                continue
            name = n["name"]
            params = n.get("parameters", {})
            if name in full_exceptions:
                continue

            reply_markup = params.get("replyMarkup", "")
            if reply_markup != "inlineKeyboard":
                violations.append(
                    f"{name}: replyMarkup is {reply_markup!r}, expected "
                    f"'inlineKeyboard'"
                )
                continue

            keyboard = params.get("inlineKeyboard", {})
            callbacks = list(callback_data_strings(keyboard))
            combined = " | ".join(callbacks)

            if not menu_re.search(combined):
                violations.append(f"{name}: missing cmd:menu button")
            if name not in cancel_exceptions and not cancel_re.search(combined):
                violations.append(f"{name}: missing cmd:cancel button")

        if violations:
            self.fail(
                "Telegram button coverage violations:\n"
                + "\n".join(f"  {i + 1}. {v}" for i, v in enumerate(violations))
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
