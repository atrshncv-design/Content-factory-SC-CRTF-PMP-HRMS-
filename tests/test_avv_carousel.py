#!/usr/bin/env python3
"""Carousel seam tests (R02/R03/R04/R05/R06/R07, ticket 02).

Public seam (spec «Границы и швы»): the slide payloads produced by the
'AVV Carousel build' Code node, the editMessageMedia HTTP node, the
'Switch cb' router outputs and the wf-creatify-webhook stage3 keyboards.
Expected values come from .autopilot/avatar-carousel/avatars-20.json
(ticket 01 output, user-approved) and from the spec template
«🎭 N/20 · Имя, ~возраст · Ниша: …» — never from the code under test.

Run: python3 -m pytest tests/test_avv_carousel.py -v
"""
import json
import os
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF_BOT = os.path.join(ROOT, "workflows", "wf-tg-bot.json")
WF_WEBHOOK = os.path.join(ROOT, "workflows", "wf-creatify-webhook.json")
AVATARS = os.path.join(ROOT, ".autopilot", "avatar-carousel", "avatars-20.json")

# Node names — the interfaces.md contract (ticket 02 zone).
BUILD = "AVV Carousel build"
NEXT = "AVV Carousel next"
EDIT = "AVV Carousel edit"
TG_CAROUSEL = "TG avv carousel"


def load_wf(path):
    with open(path) as f:
        data = json.load(f)
    return data[0] if isinstance(data, list) else data


def run_js(js, input_json, nodes=None, indices=None):
    """Execute a Code node body with n8n expression mocks via node.

    With `indices`, the same node body runs once per index (the builder
    reads $json.index at call time, so mutating the live mock between
    calls yields every slide of the carousel in one node process).
    """
    nodes = nodes or {}
    script = """
const items = [{ json: %s }];
const $input = { first: () => items[0], all: () => items };
const $json = items[0].json;
const NODES = %s;
const $ = (name) => ({ first: () => ({ json: NODES[name] || {} }) });
const main = new Function('$input', '$json', '$', %s);
let out;
if (%s) {
  out = %s.map((i) => { $json.index = i; return main($input, $json, $); });
} else {
  out = main($input, $json, $);
}
console.log(JSON.stringify(out));
""" % (
        json.dumps(input_json),
        json.dumps(nodes),
        json.dumps(js),
        "true" if indices else "false",
        json.dumps(indices or []),
    )
    result = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            "node failed: " + result.stderr.decode("utf-8")[:500]
        )
    return json.loads(result.stdout.decode("utf-8"))


class CarouselSlideTests(unittest.TestCase):
    """R02–R07: slide payload contract of AVV Carousel build."""

    @classmethod
    def setUpClass(cls):
        with open(AVATARS) as f:
            cls.avatars = json.load(f)
        wf = load_wf(WF_BOT)
        cls.nodes = {n["name"]: n for n in wf["nodes"]}
        cls.build_js = cls.nodes[BUILD]["parameters"]["jsCode"]
        # All 20 slides from one node run: the builder reads $json.index at
        # call time, so the live mock object is mutated between calls.
        cls.slides = [
            run[0]["json"]
            for run in run_js(
                cls.build_js, {"index": 0}, indices=list(range(20)),
            )
        ]

    def test_twenty_slides_one_per_avatar_in_order(self):
        """R03/R04: 20 slides, photos follow avatars-20.json order."""
        self.assertEqual(len(self.slides), 20)
        for i, slide in enumerate(self.slides):
            self.assertEqual(slide["photo"], self.avatars[i]["img"], i)
            self.assertEqual(slide["index"], i)

    def test_alternation_starts_male(self):
        """R04: М → Ж alternation, first slide is male (avatars-20.json)."""
        genders = [a["gender"] for a in self.avatars]
        self.assertEqual(genders[0], "m")
        self.assertEqual(
            [g for g in genders[::2]], ["m"] * 10,
            "even positions must be male",
        )
        self.assertEqual(
            [g for g in genders[1::2]], ["f"] * 10,
            "odd positions must be female",
        )
        # First slide shows the approved male pick: Sam (avatars-20.json [0]).
        self.assertEqual(self.slides[0]["avatar_id"], self.avatars[0]["id"])
        self.assertEqual(self.avatars[0]["name"], "Sam")

    def test_caption_card_format(self):
        """R03.1/R02: caption carries N/20, name, age, niche (spec template)."""
        # Expected strings hand-built from avatars-20.json + spec template.
        self.assertEqual(
            self.slides[0]["caption"],
            "🎭 1/20 · Sam, ≈45 · Ниша: бизнес-эксперт, финансы",
        )
        self.assertEqual(
            self.slides[19]["caption"],
            "🎭 20/20 · Leonora, ≈70 · Ниша: образование, наставница 50+",
        )
        for i, slide in enumerate(self.slides):
            a = self.avatars[i]
            self.assertIn("/20 · ", slide["caption"])
            self.assertIn(a["name"], slide["caption"])
            self.assertIn(a["age_label"], slide["caption"])
            self.assertIn(a["niche"], slide["caption"])

    def test_keyboard_n8n_form(self):
        """R05: n8n rows form with all 5 carousel buttons (spec story 7)."""
        kb = self.slides[0]["kbN8n"]
        rows = kb["rows"]
        self.assertEqual(len(rows), 2)
        b1 = rows[0]["row"]["buttons"]
        b2 = rows[1]["row"]["buttons"]
        self.assertEqual(b1[0]["text"], "✅ Выбрать")
        self.assertEqual(
            b1[0]["additionalFields"]["callback_data"],
            "avv_sel:" + self.avatars[0]["id"],
        )
        self.assertEqual(b1[1]["text"], "➡️ Далее")
        self.assertEqual(
            b1[1]["additionalFields"]["callback_data"], "avv_next:0"
        )
        texts2 = [b["text"] for b in b2]
        self.assertEqual(
            texts2, ["👤 Мои аватары", "📋 Меню", "🧹 Отмена"]
        )
        payloads2 = [b["additionalFields"]["callback_data"] for b in b2]
        self.assertEqual(
            payloads2, ["avv_my_avatars", "cmd:menu", "cmd:cancel"]
        )

    def test_keyboard_telegram_api_form(self):
        """R06: kbApi is Telegram API inline_keyboard (not n8n rows)."""
        kb = self.slides[7]["kbApi"]
        self.assertIsInstance(kb, list)
        self.assertEqual(len(kb), 2)
        for row in kb:
            self.assertIsInstance(row, list)
        flat = [b for row in kb for b in row]
        self.assertEqual(len(flat), 5)
        for b in flat:
            self.assertIn("text", b)
            self.assertIn("callback_data", b)
            self.assertNotIn("additionalFields", b)
        payloads = [b["callback_data"] for b in flat]
        self.assertEqual(
            payloads,
            [
                "avv_sel:" + self.avatars[7]["id"],
                "avv_next:7",
                "avv_my_avatars",
                "cmd:menu",
                "cmd:cancel",
            ],
        )


class CarouselNextTests(unittest.TestCase):
    """R04/R07: stateless next-index callback closes the circle of 20."""

    @classmethod
    def setUpClass(cls):
        wf = load_wf(WF_BOT)
        cls.nodes = {n["name"]: n for n in wf["nodes"]}
        cls.next_js = cls.nodes[NEXT]["parameters"]["jsCode"]

    def _next(self, entity_type):
        out = run_js(
            self.next_js, {"index": 0},
            nodes={"Parser": {"entity_type": entity_type}},
        )
        return out[0]["json"]["index"]

    def test_next_on_last_slide_wraps_to_first(self):
        """Spec story 6: «Далее» on the 20th leads to the 1st (mod 20)."""
        self.assertEqual(self._next("19"), 0)
        self.assertEqual(self._next("5"), 6)
        self.assertEqual(self._next("0"), 1)

    def test_next_marks_edit_mode(self):
        out = run_js(
            self.next_js, {"index": 0},
            nodes={"Parser": {"entity_type": "3"}},
        )[0]["json"]
        self.assertEqual(out["mode"], "edit")


class CarouselEditNodeTests(unittest.TestCase):
    """R06: editMessageMedia HTTP node contract (spec §1)."""

    @classmethod
    def setUpClass(cls):
        wf = load_wf(WF_BOT)
        cls.node = {n["name"]: n for n in wf["nodes"]}[EDIT]

    def test_url_uses_env_token_by_name(self):
        url = self.node["parameters"]["url"]
        self.assertEqual(
            url,
            "https://api.telegram.org/bot{{$env.TELEGRAM_BOT_TOKEN}}"
            "/editMessageMedia",
        )
        self.assertNotIn(":895", url)

    def test_body_is_telegram_api_form(self):
        body = self.node["parameters"]["jsonBody"]
        for needle in (
            "media", "reply_markup", "inline_keyboard", "$json.kbApi",
            "$json.photo", "$json.caption", "message_id",
        ):
            self.assertIn(needle, body, needle)

    def test_never_error_is_nested(self):
        opts = self.node["parameters"]["options"]
        self.assertIs(
            opts["response"]["response"]["neverError"], True
        )

    def test_no_token_value_in_workflow(self):
        raw = open(WF_BOT, encoding="utf-8").read()
        self.assertNotRegex(raw, r"bot\d{6,}:")

    def test_edit_check_falls_back_on_missing_message(self):
        """R06.2: ok:false -> 'resend' (fallback sendPhoto of new slide)."""
        wf = load_wf(WF_BOT)
        js = {
            n["name"]: n for n in wf["nodes"]
        }["AVV Carousel edit check"]["parameters"]["jsCode"]
        slide = {"photo": "https://cdn/x.png", "caption": "c", "kbN8n": {},
                 "kbApi": [], "chat_id": 1, "index": 2, "avatar_id": "z"}
        resend = run_js(
            js, {"ok": False, "description": "Bad Request: message to edit not found"},
            nodes={"AVV Carousel build": slide},
        )[0]["json"]
        self.assertEqual(resend["result"], "resend")
        self.assertEqual(resend["photo"], "https://cdn/x.png")
        sent = run_js(
            js, {"ok": True, "result": {"message_id": 5}},
            nodes={"AVV Carousel build": slide},
        )[0]["json"]
        self.assertEqual(sent["result"], "sent")


class CarouselWiringTests(unittest.TestCase):
    """R02/R05/R06.1: router outputs and node graph of the carousel."""

    @classmethod
    def setUpClass(cls):
        wf = load_wf(WF_BOT)
        cls.nodes = {n["name"]: n for n in wf["nodes"]}
        cls.conns = wf["connections"]

    def targets(self, src):
        return {
            c["node"]
            for branch in self.conns.get(src, {}).get("main", [])
            for c in (branch or [])
        }

    def test_switch_cb_routes_carousel_prefixes(self):
        rules = [
            r["conditions"]["conditions"][0]["rightValue"]
            for r in self.nodes["Switch cb"]["parameters"]["rules"]["values"]
        ]
        for prefix in ("avv_next", "avv_sel", "avv_my_avatars", "avv_again"):
            self.assertIn(prefix, rules)
        self.assertNotIn("avv_select", rules)

    def test_switch_cb_output_targets(self):
        main = self.conns["Switch cb"]["main"]
        rules = [
            r["conditions"]["conditions"][0]["rightValue"]
            for r in self.nodes["Switch cb"]["parameters"]["rules"]["values"]
        ]
        by_rule = {
            rv: [c["node"] for c in (main[i] or [])]
            for i, rv in enumerate(rules)
        }
        self.assertEqual(by_rule["avv_next"], ["AVV answer next"])
        self.assertEqual(by_rule["avv_sel"], ["AVV answer sel"])
        self.assertEqual(by_rule["avv_my_avatars"], ["AVV answer my"])

    def test_answer_nodes_answer_callback_query(self):
        for name in ("AVV answer next", "AVV answer sel", "AVV answer my"):
            node = self.nodes[name]
            params = node["parameters"]
            self.assertEqual(params["resource"], "callback", name)
            self.assertEqual(params["operation"], "answerQuery", name)
            self.assertIn("$('Parser').first().json.query_id",
                          params["queryId"], name)

    def test_entry_and_next_graph(self):
        """Entry: state update -> build -> send; next: build -> edit chain."""
        self.assertEqual(self.targets("AVV HTTP state"), {"AVV Carousel build"})
        self.assertEqual(self.targets("AVV Carousel build"),
                         {"Switch avv carousel mode"})
        self.assertEqual(
            self.targets("Switch avv carousel mode"),
            {"AVV Carousel edit", TG_CAROUSEL},
        )
        self.assertEqual(self.targets("AVV answer next"),
                         {"AVV Carousel next"})
        self.assertEqual(self.targets("AVV Carousel next"),
                         {"AVV Carousel build"})
        self.assertEqual(self.targets("AVV Carousel edit"),
                         {"AVV Carousel edit check"})
        self.assertEqual(self.targets("AVV Carousel edit check"),
                         {"Switch avv carousel edit"})
        self.assertEqual(self.targets("Switch avv carousel edit"),
                         {TG_CAROUSEL})

    def test_first_message_is_sendphoto_with_expression_keyboard(self):
        node = self.nodes[TG_CAROUSEL]
        p = node["parameters"]
        self.assertEqual(p["operation"], "sendPhoto")
        self.assertEqual(p["inlineKeyboard"], "={{ $json.kbN8n }}")
        self.assertEqual(p["additionalFields"]["caption"],
                         "={{ $json.caption }}")
        self.assertEqual(node["typeVersion"], 1.2)

    def test_select_and_my_avatars_paths(self):
        self.assertEqual(self.targets("AVV answer sel"),
                         {"AVV Save avatar"})
        self.assertEqual(self.targets("AVV Save avatar"),
                         {"TG avv ask topic"})
        self.assertEqual(self.targets("AVV answer my"),
                         {"AVV HTTP my avatars"})
        self.assertEqual(self.targets("AVV HTTP my avatars"),
                         {"AVV My avatars"})
        self.assertEqual(self.targets("AVV My avatars"),
                         {"TG avv my avatars"})

    def test_old_stub_flow_removed(self):
        """Ticket 02: недострой прошлой сессии выпилен (acceptance)."""
        gone = [
            "AVV Build avatars", "AVV HTTP avatars", "AVV Ask avatar",
            "TG avv ask avatar", "TG avv none", "AVV Build preview",
            "AVV Preview sel", "Switch avv preview", "TG avv preview photo",
            "TG avv preview text", "AVV Select", "TG avv selected",
            "TG avv delete next", "TG avv delete select", "TG avv delete my",
        ]
        for name in gone:
            self.assertNotIn(name, self.nodes, name)
            self.assertNotIn(name, self.conns, name + " still a connection source")
        parser_js = self.nodes["Parser"]["parameters"]["jsCode"]
        self.assertNotIn("'avv_select'", parser_js)


class MyAvatarsTests(unittest.TestCase):
    """R05 story 13 (A01): own avatars list selects via avv_sel:<id>."""

    @classmethod
    def setUpClass(cls):
        wf = load_wf(WF_BOT)
        js = {
            n["name"]: n for n in wf["nodes"]
        }["AVV My avatars"]["parameters"]["jsCode"]
        cls.js = js

    def _run(self, rows):
        return run_js(
            self.js, {"index": 0},
            nodes={"Parser": {"chat_id": 42},
                   "AVV HTTP my avatars": {"rows": rows}},
        )[0]["json"]

    def test_own_avatar_buttons_use_avv_sel(self):
        out = self._run([
            {"persona_id": "uuid-1", "creator_name": "Мой аватар"},
            {"persona_id": "uuid-2", "creator_name": "Второй"},
        ])
        cbs = [
            b["additionalFields"]["callback_data"]
            for r in out["rows"] for b in r["row"]["buttons"]
        ]
        self.assertIn("avv_sel:uuid-1", cbs)
        self.assertIn("avv_sel:uuid-2", cbs)
        self.assertIn("cmd:menu", cbs)
        self.assertIn("cmd:cancel", cbs)

    def test_empty_list_offers_stock_carousel(self):
        out = self._run([])
        cbs = [
            b["additionalFields"]["callback_data"]
            for r in out["rows"] for b in r["row"]["buttons"]
        ]
        # avv_next:19 -> next slide is index 0 (first male stock avatar).
        self.assertEqual(
            cbs, ["avv_next:19", "cmd:menu", "cmd:cancel"]
        )


class Stage3AutoKeyboardTests(unittest.TestCase):
    """Task 03 follow-up: auto sendVideo carries the manual stage3 keyboard.

    Etalon: the live manual node (vd_* callbacks routed by Switch cb,
    cmd:menu handled by Switch cmd — wf-creatify-webhook rides the same
    bot token, DEPLOYMENT.md §13).
    """

    def _buttons(self, nodes, name):
        params = nodes[name]["parameters"]
        self.assertEqual(params.get("replyMarkup"), "inlineKeyboard", name)
        rows = params["inlineKeyboard"]["rows"]
        return [
            (b["text"], b["additionalFields"]["callback_data"])
            for r in rows for b in r["row"]["buttons"]
        ]

    def test_auto_keyboard_matches_manual(self):
        wf = load_wf(WF_WEBHOOK)
        nodes = {n["name"]: n for n in wf["nodes"]}
        manual = self._buttons(nodes, "Telegram stage3")
        self.assertEqual(
            manual,
            [
                ("✅ Опубликовать", "={{ 'vd_ok' }}"),
                ("🔁 Перегенерировать", "={{ 'vd_regenerate' }}"),
                ("❌ Отклонить", "={{ 'vd_reject' }}"),
                ("📋 Меню", '={{ "cmd:menu" }}'),
            ],
        )
        self.assertEqual(self._buttons(nodes, "Telegram stage3 auto"), manual)


if __name__ == "__main__":
    unittest.main(verbosity=2)
