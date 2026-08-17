#!/usr/bin/env python3
"""Routing seam tests (R01.3 / R01.2 / R01.4): every rendered button leads somewhere.

Public seam: the callback_data payloads produced by keyboards of wf-tg-bot
(static inlineKeyboard values, whole-expression keyboards and the Code nodes
that feed them) plus keyboards attached by OTHER workflows that send through
the same bot token (wf-creatify-webhook, wf-tg-alerts). All Telegram send
nodes in the repo share credential id 10000000-0000-4000-8000-000000000004,
and the bot webhook feeds wf-tg-bot 'tg-trigger' (allowed_updates:
message+callback_query, DEPLOYMENT.md §13) — so every such callback must be
routable by the wf-tg-bot router (Parser -> Switch cb / Switch cmd).

Expected side (ROUTED / TASK2_PENDING) is hand-derived from a manual read of
Parser jsCode, Switch cb and Switch cmd rules (17.08.2026) and from the spec
(stories 1a/1b/2/12). It is NOT computed from the workflow, so the button
scan and the router scan can disagree — that disagreement is the point.

Run: python3 -m pytest tests/test_tg_callback_routing.py -v
"""
import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF_BOT = os.path.join(ROOT, "workflows", "wf-tg-bot.json")
WF_ALERTS = os.path.join(ROOT, "workflows", "wf-tg-alerts.json")
# Keyboards outside wf-tg-bot riding the same bot token (same credential id):
# their callbacks hit the same webhook and must route through wf-tg-bot too.
WF_EXTERNAL = [
    ("wf-creatify-webhook", os.path.join(ROOT, "workflows", "wf-creatify-webhook.json")),
    ("wf-tg-alerts", WF_ALERTS),
]

# ---------------------------------------------------------------------------
# Hand-derived routing table: family prefix -> (router pool, expected entry).
# Sources: manual read of Parser jsCode callback grammar, Switch cb rightValue
# rules and Switch cmd rightValue rules (17.08.2026); sprint 16.08 duration
# fix (dur_30/dur_60/durc_30/durc_60 route WITHOUT the cmd: prefix).
# ---------------------------------------------------------------------------
ROUTED = {
    # cmd:<command> — Parser strips 'cmd:' then parseCommand; Switch cmd routes.
    "cmd:menu": ("switch_cmd", "menu"),
    "cmd:cancel": ("switch_cmd", "cancel"),
    "cmd:status": ("switch_cmd", "status"),
    "cmd:ping": ("switch_cmd", "ping"),
    "cmd:profile": ("switch_cmd", "profile"),
    "cmd:topics": ("switch_cmd", "topics"),
    "cmd:accounts": ("switch_cmd", "accounts"),
    "cmd:budget": ("switch_cmd", "budget"),
    "cmd:clients": ("switch_cmd", "clients"),
    "cmd:competitors": ("switch_cmd", "competitors"),
    "cmd:my_avatars": ("switch_cmd", "my_avatars"),
    "cmd:start_cycle": ("switch_cmd", "start_cycle"),
    "cmd:text_post": ("switch_cmd", "text_post"),
    "cmd:avatar_video": ("switch_cmd", "avatar_video"),
    # Parser command-map aliases (gen_url2video -> url2video, gen_shorts -> shorts).
    "cmd:gen_url2video": ("switch_cmd", "url2video"),
    "cmd:gen_shorts": ("switch_cmd", "shorts"),
    # menu_<section> collapses to command 'menu' (Parser startsWith('menu_')).
    "cmd:menu_gen": ("switch_cmd", "menu"),
    "cmd:menu_analytics": ("switch_cmd", "menu"),
    "cmd:menu_publish": ("switch_cmd", "menu"),
    "cmd:menu_system": ("switch_cmd", "menu"),
    "cmd:menu_help": ("switch_cmd", "menu"),
    # hint_<topic> collapses to command 'hint' (Parser startsWith('hint_')).
    "cmd:hint_mode": ("switch_cmd", "hint"),
    "cmd:hint_audience": ("switch_cmd", "hint"),
    "cmd:hint_comments": ("switch_cmd", "hint"),
    "cmd:hint_creator": ("switch_cmd", "hint"),
    "cmd:hint_creator_content": ("switch_cmd", "hint"),
    "cmd:hint_creators": ("switch_cmd", "hint"),
    "cmd:hint_publish_type": ("switch_cmd", "hint"),
    "cmd:hint_transcript": ("switch_cmd", "hint"),
    "cmd:hint_upload_avatar": ("switch_cmd", "hint"),
    # Duration buttons sent WITHOUT cmd: — the sprint 16.08 fix.
    "dur_30": ("switch_cmd", "dur_30"),
    "dur_60": ("switch_cmd", "dur_60"),
    "durc_30": ("switch_cmd", "durc_30"),
    "durc_60": ("switch_cmd", "durc_60"),
    # Two-segment actions (Parser 'action:entity' map).
    "approve:topic": ("switch_cb", "approve_topic"),
    "approve:script": ("switch_cb", "approve_script"),
    "edit:topic": ("switch_cb", "edit_topic"),
    "edit:script": ("switch_cb", "edit_script"),
    "reject:topic": ("switch_cb", "reject_topic"),
    "reject:script": ("switch_cb", "reject_script"),
    "reject:gen": ("switch_cb", "reject_gen"),
    "alt:topic": ("switch_cb", "alt_topic"),
    "regen:gen": ("switch_cb", "regen_gen"),
    "publish:gen": ("switch_cb", "publish_gen"),
    "confirm:publish": ("switch_cb", "confirm_publish"),
    "toggle:platform": ("switch_cb", "toggle_platform"),
    "toggle:ppm": ("switch_cb", "toggle_ppm"),
    # Single-action callbacks (Parser direct action matching, any suffix).
    "schedule": ("switch_cb", "schedule"),
    "tx_toggle": ("switch_cb", "tx_toggle"),
    "tx_publish": ("switch_cb", "tx_publish"),
    "ro_yes": ("switch_cb", "ro_yes"),
    "ro_no": ("switch_cb", "ro_no"),
    "ppm_done": ("switch_cb", "ppm_done"),
    "sc_ok": ("switch_cb", "sc_ok"),
    "sc_edit": ("switch_cb", "sc_edit"),
    "sc_regenerate": ("switch_cb", "sc_regenerate"),
    "vd_ok": ("switch_cb", "vd_ok"),
    "vd_regenerate": ("switch_cb", "vd_regenerate"),
    "vd_reject": ("switch_cb", "vd_reject"),
    # pf_* actions pass through Parser unchanged (action.startsWith('pf_')).
    "pf_add_doc": ("switch_cb", "pf_add_doc"),
    "pf_add_link": ("switch_cb", "pf_add_link"),
    "pf_del": ("switch_cb", "pf_del"),
    "pf_del_no": ("switch_cb", "pf_del_no"),
    "pf_del_yes": ("switch_cb", "pf_del_yes"),
    "pf_done": ("switch_cb", "pf_done"),
    "pf_edit": ("switch_cb", "pf_edit"),
    "pf_exit": ("switch_cb", "pf_exit"),
    "pf_list": ("switch_cb", "pf_list"),
    "pf_new": ("switch_cb", "pf_new"),
    "pf_platforms": ("switch_cb", "pf_platforms"),
    "pf_restart": ("switch_cb", "pf_restart"),
    "pf_resume": ("switch_cb", "pf_resume"),
    "pf_skip": ("switch_cb", "pf_skip"),
    "pf_switch": ("switch_cb", "pf_switch"),
    # Avatar flow callbacks that are fully wired today.
    "avv_sel": ("switch_cb", "avv_sel"),
    "avv_ok": ("switch_cb", "avv_ok"),
    "avv_again": ("switch_cb", "avv_again"),
    # Carousel callbacks wired by ticket 02 (stateless slide flip, own
    # avatars entry). The old stub prefix avv_select is gone: buttons of
    # deleted stubs in old chats fall through to the CB answer unknown
    # fallback (Parser no longer maps it).
    "avv_next": ("switch_cb", "avv_next"),
    "avv_my_avatars": ("switch_cb", "avv_my_avatars"),
}

# Buttons outside wf-tg-bot whose callbacks are NOT served by the wf-tg-bot
# router (different transport / answered elsewhere). Must stay justified.
EXTERNAL_UNROUTED = {}

# Static callback payloads whose expression literal is broken (stray
# backslash -> unterminated JS string -> dead button). Ticket 02 fixed the
# five dead AVV buttons; the list must stay empty — any new broken literal
# anywhere fails the test.
KNOWN_BROKEN_NODES = set()

TOKEN_RE = re.compile(r"[a-z_][a-z_0-9]*(?::[a-z_0-9]+)*")
CB_IN_CODE_RE = re.compile(r"callback_data\s*:\s*([^,\n}\]]+)")
IDENT_RE = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")
CONST_RE = r"(?:const|let|var)\s+%s\s*=\s*([^;\n]+)"


def load_wf(path):
    with open(path) as f:
        data = json.load(f)
    return data[0] if isinstance(data, list) else data


def static_token(expr):
    """Leading static token of a callback payload expression.

    '={{ "cmd:menu" }}' -> 'cmd:menu'
    "={{ 'approve:topic:' + $json.topic_id }}" -> 'approve:topic'
    """
    if not isinstance(expr, str):
        return None
    body = expr.strip()
    if body.startswith("={{"):
        body = body[3:]
    m = TOKEN_RE.match(body.lstrip("'\"` ").lstrip())
    if not m:
        return None
    return m.group(0).rstrip(":")


def code_tokens(js):
    """Callback payload tokens built inside a Code node (or expression string).

    Handles literal payloads, concatenations ('avv_next:' + index) and local
    const indirections (const okCb = 'avv_ok:' + avatarId;).
    """
    tokens = set()
    for m in CB_IN_CODE_RE.finditer(js):
        val = m.group(1).strip()
        if IDENT_RE.match(val):  # const-indirected payload
            cm = re.search(CONST_RE % re.escape(val), js)
            if not cm:
                tokens.add("?" + val)  # unresolvable -> must surface as violation
                continue
            val = cm.group(1).strip()
        tok = static_token(val)
        if tok:
            tokens.add(tok)
    return tokens


def telegram_payload_expressions(node):
    """All callback payload expressions of a Telegram node's keyboard."""
    params = node.get("parameters", {})
    kb = params.get("inlineKeyboard")
    if kb is None:
        return []
    if isinstance(kb, str):
        return code_tokens(kb)  # whole-expression keyboard
    rows = kb.get("rows", [])
    if isinstance(rows, str):
        return code_tokens(rows)
    found = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        for b in (r.get("row") or {}).get("buttons", []):
            cb = (b.get("additionalFields") or {}).get("callback_data")
            if isinstance(cb, str):
                found.append(cb)
    return found


def collect_tokens(wf, wf_label):
    """(source, token) pairs for every keyboard payload a workflow renders."""
    pairs = set()
    for n in wf.get("nodes", []):
        if n["type"] == "n8n-nodes-base.telegram":
            for expr in telegram_payload_expressions(n):
                tok = static_token(expr)
                if tok:
                    pairs.add((f"{wf_label}/{n['name']}", tok))
        elif n["type"] == "n8n-nodes-base.code":
            js = n.get("parameters", {}).get("jsCode", "")
            if js and "callback_data" in js:
                for tok in code_tokens(js):
                    pairs.add((f"{wf_label}/{n['name']} (code)", tok))
    return pairs


def switch_rightvalues(wf, node_name):
    for n in wf.get("nodes", []):
        if n.get("name") == node_name:
            return [
                c.get("rightValue")
                for r in n["parameters"]["rules"]["values"]
                for c in r.get("conditions", {}).get("conditions", [])
            ]
    return []


def resolve_handler(token):
    """Longest-prefix lookup of a token in the routing table."""
    parts = token.split(":")
    for size in range(len(parts), 0, -1):
        candidate = ":".join(parts[:size])
        if candidate in ROUTED:
            return candidate, ROUTED[candidate]
    return None, None


class TgCallbackRoutingTests(unittest.TestCase):
    """Every button the bot renders must route somewhere (no dead buttons)."""

    @classmethod
    def setUpClass(cls):
        cls.wf_bot = load_wf(WF_BOT)
        cls.switch_cb = set(switch_rightvalues(cls.wf_bot, "Switch cb"))
        cls.switch_cmd = set(switch_rightvalues(cls.wf_bot, "Switch cmd"))
        cls.parser_js = next(
            n["parameters"]["jsCode"] for n in cls.wf_bot["nodes"]
            if n.get("name") == "Parser"
        )
        cls.bot_tokens = collect_tokens(cls.wf_bot, "wf-tg-bot")
        cls.external_tokens = set()
        for label, path in WF_EXTERNAL:
            cls.external_tokens |= collect_tokens(load_wf(path), label)

    def _assert_routed(self, pairs, context):
        violations = []
        for source, token in sorted(pairs):
            if token.startswith("?"):
                violations.append(f"{source}: unresolvable payload {token[1:]!r}")
                continue
            key, target = resolve_handler(token)
            if key is None:
                violations.append(f"{source}: payload {token!r} has no handler")
            else:
                kind, name = target
                pool = self.switch_cmd if kind == "switch_cmd" else self.switch_cb
                if name not in pool:
                    violations.append(
                        f"{source}: {token!r} expects {kind}={name!r}, "
                        f"absent from router"
                    )
        self.assertFalse(
            violations,
            f"Dead buttons found ({context}):\n"
            + "\n".join(f"  - {v}" for v in violations),
        )

    def test_wf_tg_bot_buttons_all_routed(self):
        self.assertGreater(len(self.bot_tokens), 0, "no buttons collected")
        self._assert_routed(self.bot_tokens, "wf-tg-bot")

    def test_external_keyboards_all_routed_or_listed(self):
        """Buttons sent by other workflows through the same bot token."""
        pairs = {
            (source, token)
            for source, token in self.external_tokens
            if token not in EXTERNAL_UNROUTED
        }
        listed = {
            token for _, token in self.external_tokens
            if token in EXTERNAL_UNROUTED
        }
        for token in listed:
            self.assertIn(
                token, EXTERNAL_UNROUTED,
                f"exception {token!r} must be documented in EXTERNAL_UNROUTED",
            )
        self.assertGreater(len(pairs), 0, "no external buttons collected")
        self._assert_routed(pairs, "external keyboards (same bot token)")

    def test_duration_buttons_routed_without_cmd_prefix(self):
        """Sprint 16.08 etalon: dur_30/dur_60/durc_30/durc_60 route bare."""
        for tok in ("dur_30", "dur_60", "durc_30", "durc_60"):
            self.assertIn(tok, self.switch_cmd,
                          f"Switch cmd lost bare duration route {tok}")
            self.assertIn(f"'{tok}': '{tok}'", self.parser_js,
                          f"Parser lost command-map entry for {tok}")
            self.assertIn(tok, {t for _, t in self.bot_tokens},
                          f"duration button {tok} disappeared from keyboards")

    def test_avv_sel_handler_preserved(self):
        """R01.2: router keeps handling avv_sel after the bot update."""
        self.assertIn("avv_sel", self.switch_cb)
        self.assertIn("'avv_sel') cb = 'avv_sel'", self.parser_js)

    def test_carousel_prefixes_collected_and_routed(self):
        """Ticket 02 landed: carousel prefixes are emitted and routed."""
        collected = {t for _, t in self.bot_tokens}
        for prefix in ("avv_next", "avv_my_avatars", "avv_sel"):
            self.assertIn(prefix, collected,
                          f"{prefix} not emitted by any keyboard")
            self.assertIn(prefix, self.switch_cb,
                          f"Switch cb lost {prefix} route")

    def test_no_new_broken_callback_literals(self):
        """Stray backslash in a static ={{ "..." }} payload is a dead button."""
        broken = set()
        for n in self.wf_bot["nodes"]:
            if n["type"] != "n8n-nodes-base.telegram":
                continue
            for expr in telegram_payload_expressions(n):
                if isinstance(expr, str) and "\\" in expr:
                    broken.add((n["name"], expr))
        outside = {b for b in broken if b[0] not in KNOWN_BROKEN_NODES}
        self.assertFalse(
            outside,
            "Broken callback payloads outside the known AVV stub nodes:\n"
            + "\n".join(f"  {n}: {e!r}" for n, e in sorted(outside)),
        )


class WfTgAlertsMenuTests(unittest.TestCase):
    """R01.4: outgoing alert messages carry the 📋 Menu button.

    wf-tg-alerts sends through the same bot credential as wf-tg-bot
    (id 10000000-0000-4000-8000-000000000004), so its callback_query hits
    wf-tg-bot 'tg-trigger' and 'cmd:menu' is handled by the existing router
    (same pattern as the vd_* buttons of wf-creatify-webhook, live since
    DEPLOYMENT.md §13). Alerts carry no Cancel button (spec story 1b).
    """

    ALERTS_MENU_EXCEPTIONS = {
        # node name -> reason; currently none: the workflow has a single
        # sendMessage node and every alert is user-facing.
    }

    @classmethod
    def setUpClass(cls):
        cls.wf = load_wf(WF_ALERTS)

    def test_outgoing_alert_messages_have_menu_button(self):
        violations = []
        send_ops = {"sendMessage", "sendPhoto", "sendVideo", "sendDocument"}
        checked = 0
        for n in self.wf.get("nodes", []):
            if n["type"] != "n8n-nodes-base.telegram":
                continue
            params = n.get("parameters", {})
            if params.get("resource") == "callback":  # answerCallbackQuery
                continue
            if params.get("operation", "sendMessage") not in send_ops:
                continue
            if n["name"] in self.ALERTS_MENU_EXCEPTIONS:
                continue
            checked += 1
            if params.get("replyMarkup") != "inlineKeyboard":
                violations.append(f"{n['name']}: no inline keyboard")
                continue
            buttons = []
            rows = params.get("inlineKeyboard", {}).get("rows", [])
            if isinstance(rows, list):
                for r in rows:
                    if isinstance(r, dict):
                        buttons += (r.get("row") or {}).get("buttons", [])
            texts = [b.get("text") for b in buttons if isinstance(b, dict)]
            payloads = [
                static_token((b.get("additionalFields") or {}).get("callback_data"))
                for b in buttons if isinstance(b, dict)
            ]
            if "📋 Меню" not in texts:
                violations.append(f"{n['name']}: missing '📋 Меню' button")
            if "cmd:menu" not in payloads:
                violations.append(
                    f"{n['name']}: Меню button must send cmd:menu "
                    f"(payloads found: {payloads})"
                )
        self.assertGreater(checked, 0, "no outgoing alert nodes found")
        self.assertFalse(
            violations,
            "wf-tg-alerts navigation violations:\n"
            + "\n".join(f"  - {v}" for v in violations),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
