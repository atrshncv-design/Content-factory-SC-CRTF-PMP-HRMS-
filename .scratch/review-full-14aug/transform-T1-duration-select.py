#!/usr/bin/env python3
"""T1 (14.08.2026): выбор длительности ролика в ручном цикле (wf-tg-bot.json, 510 нод).

РЕШЕНИЕ ПОЛЬЗОВАТЕЛЯ: в ручном режиме (mode=manual) бот ПЕРЕД генерацией спрашивает
длительность кнопками (30/60/90 + своя), сценарий пишется под выбранную длину,
video_length в payload = выбранная (не LLM-догадка).

Правки:
1. Гейт после старта цикла (между SC HTTP setstate и SC Build analytics body):
   DR Build settings -> DR HTTP settings -> DR Check -> Switch DR gate:
   manual -> CYCLE_DUR_AWAIT + кнопки (DR Build ask state -> DR HTTP ask state ->
   DR Format ask -> TG DR ask); auto/прочее -> SC Build analytics body (как раньше).
2. Обработка выбора:
   - кнопки cmd:durc_30/60/90 (+ cmd:durc_custom «своя», cmd:cancel, cmd:menu):
     Parser: префикс durc_ -> command='durc' (новое правило Switch cmd) ->
     DR Build state -> DR HTTP state -> DR Parse (валидация 15-300, паттерн
     durValid из DU Parse state) -> Switch DR route;
   - текст-число в CYCLE_DUR_AWAIT: Gate Check (+CYCLE_DUR_AWAIT -> 'cycle_dur')
     -> Switch gate (новое правило) -> DR Build state (та же цепочка).
   - dur_ok -> DR Build save (state=CYCLE_ANALYTICS_PENDING, quick_payload=
     {"duration": N}) -> DR HTTP save -> DR Format ok -> TG DR ok -> SC Build
     analytics body (цикл продолжается); dur_wrong/ask_custom -> повторный запрос.
3. Сценарист (CT Build bridge prompt): длительность из quick_payload
   (CT Build qp -> CT HTTP qp, вставлены между CT HTTP session и CT Build bridge
   prompt): «(N сек, ~round(N*65/30) слов, русский)» вместо жёстких 30/65.
4. json-builder (AS Build bridge prompt): длительность из quick_payload
   (AS Build qp -> AS HTTP qp, вставлены между AS HTTP select script и AS Build
   bridge prompt); принудительный payload.video_length = выбранная в
   AS Build submit body (НЕ из LLM).
5. auto-режим: AU-цепочка НЕ тронута; выбор не показывается (Switch DR gate
   fallback -> аналитика); settings.video_length в воркфлоу НЕТ -> дефолт 30.

Сериализация: json.dumps(ensure_ascii=False, indent=1), без trailing newline.
"""
import json
import re
import sys
import uuid

PATH = "/Users/aleksandrtrisenkov/Desktop/PROGRAMMING/РАБОЧИЕ ПРОЕКТЫ/КОНТЕНТ-ЗАВОД-API-MVP/.scratch/review-full-14aug/fixes/wf-tg-bot.json"

with open(PATH, encoding="utf-8") as f:
    data = json.load(f)
wf = data[0]
nodes = wf["nodes"]
conns = wf["connections"]
by_name = {n["name"]: n for n in nodes}

# ---------- байт-точные эталоны из базы ----------
esc_line = re.search(r"const esc = s =>[^\n]*", by_name["MO Format"]["parameters"]["jsCode"]).group(0)
DB_HTTP = by_name["DU HTTP state"]["parameters"]  # db-bridge POST эталон
CN_SQL = re.search(r'sql: "(UPDATE[^"]+)"', by_name["CN Build"]["parameters"]["jsCode"]).group(1)
SC_SQL = re.search(r'sql: "(UPDATE[^"]+)"', by_name["SC Build setstate"]["parameters"]["jsCode"]).group(1)
A2_SQL = re.search(r'sql: "(UPDATE[^"]+)"', by_name["AS Build session"]["parameters"]["jsCode"]).group(1)

print("эталоны:", len(DB_HTTP), "esc:", esc_line)

# ---------- helpers ----------
def new_node(name, ntype, tv, params, pos):
    assert name not in by_name, f"дубль имени {name}"
    node = {
        "parameters": params,
        "id": str(uuid.uuid4()),
        "name": name,
        "type": ntype,
        "typeVersion": tv,
        "position": pos,
    }
    nodes.append(node)
    by_name[name] = node
    return node


def code(name, js, pos):
    return new_node(name, "n8n-nodes-base.code", 2, {"mode": "runOnceForAllItems", "language": "javaScript", "jsCode": js}, pos)


def http(name, pos):
    return new_node(name, "n8n-nodes-base.httpRequest", 4.5, json.loads(json.dumps(DB_HTTP)), pos)


def switch(name, rules_right, pos):
    rules = {
        "values": [
            {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                    "conditions": [
                        {"leftValue": "={{ $json." + ("command" if name == "Switch cmd" else "mode") + " }}",
                         "rightValue": rv,
                         "operator": {"type": "string", "operation": "equals"}},
                    ],
                    "combinator": "and",
                }
            }
            for rv in rules_right
        ]
    }
    return new_node(name, "n8n-nodes-base.switch", 3.4,
                    {"mode": "rules", "rules": rules, "options": {"fallbackOutput": "extra"}}, pos)


def tg(name, rows, pos, chat_from="Parser", text_from="$json.text"):
    buttons = [[{"text": t, "additionalFields": {"callback_data": cb}} for (t, cb) in row] for row in rows]
    params = {
        "resource": "message",
        "operation": "sendMessage",
        "chatId": "={{ $('Parser').first().json.chat_id }}",
        "text": "={{ $json.text }}",
        "additionalFields": {"appendAttribution": False},
        "replyMarkup": "inlineKeyboard",
        "inlineKeyboard": {"rows": [{"row": {"buttons": btns}} for btns in buttons]},
    }
    return new_node(name, "n8n-nodes-base.telegram", 1.2, params, pos)


def add_conn(src, dst):
    conns.setdefault(src, {}).setdefault("main", []).append([{"node": dst, "type": "main", "index": 0}])


def set_first_conn(src, dst):
    main = conns[src]["main"]
    main[0] = [{"node": dst, "type": "main", "index": 0}]


DUR_BUTTONS = [
    [("⏱ 30 сек", "cmd:durc_30"), ("⏱ 60 сек", "cmd:durc_60"), ("⏱ 90 сек", "cmd:durc_90")],
    [("🔢 Своя (напиши число)", "cmd:durc_custom")],
    [("🧹 Отмена", "cmd:cancel"), ("📋 Меню", "cmd:menu")],
]

# ---------- 1. гейт после старта цикла ----------
code("DR Build settings", "\nreturn [{ json: { sql: \"SELECT key, value FROM settings WHERE key = 'mode'\", params: [] } }];\n", [1290, -640])
http("DR HTTP settings", [1330, -640])
code("DR Check", "\nconst rows = $('DR HTTP settings').first().json.rows || [];\nconst mode = (rows[0] && rows[0].value) || 'manual';\nreturn [{ json: { mode: mode } }];\n", [1370, -640])
switch("Switch DR gate", ["manual"], [1410, -640])

code("DR Build ask state",
     "\nconst p = $('Parser').first().json;\nreturn [{ json: { sql: \"UPDATE sessions SET state = 'CYCLE_DUR_AWAIT', quick_payload = NULL, updated_at = datetime('now') WHERE tg_user_id = ?\", params: [p.tg_user_id] } }];\n",
     [1450, -760])
http("DR HTTP ask state", [1490, -760])
code("DR Format ask",
     "\nconst p = $('Parser').first().json;\n" + esc_line + "\nconst text = esc('⏱ Выбери длительность ролика (15–300 сек). Сценарий и видео будут под неё.');\nreturn [{ json: { chat_id: p.chat_id, text: text } }];\n",
     [1530, -760])
tg("TG DR ask", DUR_BUTTONS, [1570, -760])

# ---------- 2. обработка выбора (durc-команда и текст-число) ----------
code("DR Build state",
     "\nconst p = $('Parser').first().json;\nreturn [{ json: { sql: 'SELECT state, quick_payload FROM sessions WHERE tg_user_id = ?', params: [p.tg_user_id] } }];\n",
     [1450, -560])
http("DR HTTP state", [1490, -560])
code("DR Parse",
     "\nconst p = $('Parser').first().json;\nconst rows = $('DR HTTP state').first().json.rows || [];\nconst state = (rows[0] && rows[0].state) || 'IDLE';\nlet mode = 'not_await';\nlet dur = 0;\nif (state === 'CYCLE_DUR_AWAIT') {\n  if (p.command === 'durc' && (!p.args.value || p.args.value === 'custom')) {\n    mode = 'ask_custom';\n  } else {\n    const raw = String(p.args.value || p.raw || '').replace(/\\D/g, '');\n    dur = Number(raw) || 0;\n    mode = (dur >= 15 && dur <= 300) ? 'dur_ok' : 'dur_wrong';\n  }\n}\nreturn [{ json: { mode: mode, state: state, dur: dur } }];\n",
     [1530, -560])
switch("Switch DR route", ["dur_ok", "dur_wrong", "ask_custom"], [1570, -560])

code("DR Build save",
     "\nconst p = $('Parser').first().json;\nconst st = $('DR Parse').first().json;\nreturn [{ json: { sql: \"UPDATE sessions SET state = 'CYCLE_ANALYTICS_PENDING', quick_payload = ?, updated_at = datetime('now') WHERE tg_user_id = ?\", params: [JSON.stringify({ duration: Number(st.dur) }), p.tg_user_id] } }];\n",
     [1610, -640])
http("DR HTTP save", [1650, -640])
code("DR Format ok",
     "\nconst p = $('Parser').first().json;\nconst st = $('DR Parse').first().json;\n" + esc_line + "\nconst text = esc('✅ Длительность: ' + st.dur + ' сек. Запускаю цикл…');\nreturn [{ json: { chat_id: p.chat_id, text: text } }];\n",
     [1690, -640])
tg("TG DR ok", [[("🧹 Отмена", "cmd:cancel"), ("📋 Меню", "cmd:menu")]], [1730, -640])

code("DR Format wrong",
     "\nconst p = $('Parser').first().json;\n" + esc_line + "\nconst text = esc('⏱ Длительность ролика — от 15 до 300 секунд. Напиши число (например, 45) или выбери кнопкой.');\nreturn [{ json: { chat_id: p.chat_id, text: text } }];\n",
     [1610, -480])
tg("TG DR wrong", DUR_BUTTONS, [1650, -480])

code("DR Format custom",
     "\nconst p = $('Parser').first().json;\n" + esc_line + "\nconst text = esc('🔢 Напиши число секунд (15–300). Например: 45');\nreturn [{ json: { chat_id: p.chat_id, text: text } }];\n",
     [1610, -400])

# ---------- 3-4. quick_payload для CT (сценарист) и AS (json-builder) ----------
code("CT Build qp",
     "\nconst p = $('Parser').first().json;\nreturn [{ json: { sql: 'SELECT quick_payload FROM sessions WHERE tg_user_id = ?', params: [p.tg_user_id] } }];\n",
     [3220, 0])
http("CT HTTP qp", [3260, 0])
code("AS Build qp",
     "\nconst p = $('Parser').first().json;\nreturn [{ json: { sql: 'SELECT quick_payload FROM sessions WHERE tg_user_id = ?', params: [p.tg_user_id] } }];\n",
     [4820, 0])
http("AS HTTP qp", [4860, 0])

# ---------- правки существующих нод ----------
parser = by_name["Parser"]["parameters"]["jsCode"]
assert "durc_" not in parser, "Parser уже пропатчен?"
parser = parser.replace(
    "  else if (t.startsWith('dur_')) { command = 'dur'; args.value = t.slice(4) || null; }\n",
    "  else if (t.startsWith('dur_')) { command = 'dur'; args.value = t.slice(4) || null; }\n"
    "  else if (t.startsWith('durc_')) { command = 'durc'; args.value = t.slice(5) || null; }\n",
)
parser = parser.replace(
    "    'text_post': 'text_post', 'текстовый пост': 'text_post', '/text_post': 'text_post', '/текстовый пост': 'text_post',\n",
    "    'text_post': 'text_post', 'текстовый пост': 'text_post', '/text_post': 'text_post', '/текстовый пост': 'text_post',\n"
    "    'durc': 'durc',\n",
)
by_name["Parser"]["parameters"]["jsCode"] = parser

gate_check = by_name["Gate Check"]["parameters"]["jsCode"]
assert "CYCLE_DUR_AWAIT" not in gate_check, "Gate Check уже пропатчен?"
gate_check = gate_check.replace(
    "if (p.command === 'unknown' && state === 'QUICK_TEXT_AWAIT') return [{ json: { mode: 'quick_text' } }];\n",
    "if (p.command === 'unknown' && state === 'QUICK_TEXT_AWAIT') return [{ json: { mode: 'quick_text' } }];\n"
    "if (p.command === 'unknown' && state === 'CYCLE_DUR_AWAIT') return [{ json: { mode: 'cycle_dur' } }];\n",
)
by_name["Gate Check"]["parameters"]["jsCode"] = gate_check

# Switch cmd: новое правило 'durc' (перед fallback)
sw_cmd = by_name["Switch cmd"]
sw_cmd["parameters"]["rules"]["values"].append({
    "conditions": {
        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
        "conditions": [{"leftValue": "={{ $json.command }}", "rightValue": "durc",
                        "operator": {"type": "string", "operation": "equals"}}],
        "combinator": "and",
    }
})
conns["Switch cmd"]["main"].insert(34, [{"node": "DR Build state", "type": "main", "index": 0}])

# Switch gate: новое правило 'cycle_dur' (перед fallback)
sw_gate = by_name["Switch gate"]
sw_gate["parameters"]["rules"]["values"].append({
    "conditions": {
        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
        "conditions": [{"leftValue": "={{ $json.mode }}", "rightValue": "cycle_dur",
                        "operator": {"type": "string", "operation": "equals"}}],
        "combinator": "and",
    }
})
conns["Switch gate"]["main"].insert(6, [{"node": "DR Build state", "type": "main", "index": 0}])

# SC HTTP setstate -> DR Build settings (гейт длительности)
set_first_conn("SC HTTP setstate", "DR Build settings")

# CT: CT HTTP session -> CT Build qp -> CT HTTP qp -> CT Build bridge prompt
set_first_conn("CT HTTP session", "CT Build qp")
add_conn("CT HTTP qp", "CT Build bridge prompt")

# AS: AS HTTP select script -> AS Build qp -> AS HTTP qp -> AS Build bridge prompt
set_first_conn("AS HTTP select script", "AS Build qp")
add_conn("AS HTTP qp", "AS Build bridge prompt")

# Связи новых нод
add_conn("DR Build settings", "DR HTTP settings")
add_conn("DR HTTP settings", "DR Check")
add_conn("DR Check", "Switch DR gate")
conns.setdefault("Switch DR gate", {})["main"] = [
    [{"node": "DR Build ask state", "type": "main", "index": 0}],   # manual
    [{"node": "SC Build analytics body", "type": "main", "index": 0}],  # fallback (auto)
]
add_conn("DR Build ask state", "DR HTTP ask state")
add_conn("DR HTTP ask state", "DR Format ask")
add_conn("DR Format ask", "TG DR ask")

add_conn("DR Build state", "DR HTTP state")
add_conn("DR HTTP state", "DR Parse")
add_conn("DR Parse", "Switch DR route")
conns.setdefault("Switch DR route", {})["main"] = [
    [{"node": "DR Build save", "type": "main", "index": 0}],     # dur_ok
    [{"node": "DR Format wrong", "type": "main", "index": 0}],   # dur_wrong
    [{"node": "DR Format custom", "type": "main", "index": 0}],  # ask_custom
    [{"node": "TG unknown", "type": "main", "index": 0}],        # fallback (not_await)
]
add_conn("DR Build save", "DR HTTP save")
add_conn("DR HTTP save", "DR Format ok")
add_conn("DR Format ok", "TG DR ok")
add_conn("TG DR ok", "SC Build analytics body")
add_conn("DR Format wrong", "TG DR wrong")
add_conn("DR Format custom", "TG DR wrong")

# ---------- параметризация промптов ----------
CT_PROMPT = """
const topic = ($('CT HTTP topic').first().json.rows || [])[0] || {};
const qpRows = ($('CT HTTP qp').first().json.rows || []);
let dur = 30;
try { const q = JSON.parse((qpRows[0] && qpRows[0].quick_payload) || '{}'); dur = Number(q.duration) || 30; } catch (e) {}
const words = Math.round(dur * 65 / 30);
const prompt = 'Напиши сценарий короткого вертикального видео (' + dur + ' сек, ~' + words + ' слов, русский) для клиента Robotec (промышленная робототехника, интегратор KUKA; тон: экспертно-деловой, ROI, окупаемость).\\nТема: ' + (topic.title || '') + '\\nИсточник: ' + (topic.source_url || '') + '\\nРационале: ' + (topic.rationale || '') + '\\n\\nВерни строго JSON: {"hook", "body", "cta", "full_text", "target_length_sec", "estimated_words", "format_tag", "notes"}. Без markdown.';
return [{ json: { skill: 'scriptwriter', prompt: prompt } }];
"""
by_name["CT Build bridge prompt"]["parameters"]["jsCode"] = CT_PROMPT

AS_PROMPT = """
const p = $('Parser').first().json;
const linkId = $('AS HTTP creatify-link').first().json.link_id || '';
const script = ($('AS HTTP select script').first().json.rows || [])[0] || {};
const qpRows = ($('AS HTTP qp').first().json.rows || []);
let dur = 30;
try { const q = JSON.parse((qpRows[0] && qpRows[0].quick_payload) || '{}'); dur = Number(q.duration) || 30; } catch (e) {}
const prompt = 'Собери валидный JSON для POST /api/link_to_videos (creatify) по сценарию.\\nСценарий: ' + (script.full_text || '') + ' (длина ' + dur + ' сек)\\nlink (UUID): ' + linkId + '\\nwebhook_url: __WEBHOOK_URL__/webhook/factory/creatify/6d8f2a41c9e7b3d5f0a1c4e8\\nvoice: русский экспертный; avatar: не задан; язык: ru; aspect_ratio: 9x16; target_platform: Instagram; model_version: aurora_v1_fast.\\nВерни ТОЛЬКО JSON payload (name, link, visual_style, script_style, aspect_ratio, video_length, language, target_audience, target_platform, model_version, override_script, webhook_url). Без markdown.';
return [{ json: { skill: 'json-builder', prompt: prompt } }];
"""
by_name["AS Build bridge prompt"]["parameters"]["jsCode"] = AS_PROMPT

AS_SUBMIT = """
const p = $('Parser').first().json;
const pl = $('AS Parse payload').first().json;
const linkId = $('AS HTTP creatify-link').first().json.link_id || '';
const qpRows = ($('AS HTTP qp').first().json.rows || []);
let dur = 30;
try { const q = JSON.parse((qpRows[0] && qpRows[0].quick_payload) || '{}'); dur = Number(q.duration) || 30; } catch (e) {}
const payload = Object.assign({}, pl.payload, { video_length: dur });
return [{ json: { script_id: Number(p.entity_id), client_id: 1, json_payload: payload, link_id: String(linkId) } }];
"""
by_name["AS Build submit body"]["parameters"]["jsCode"] = AS_SUBMIT

# ---------- сериализация (байт-точно как база) ----------
out = json.dumps(data, ensure_ascii=False, indent=1)
assert not out.endswith("\n")
with open(PATH, "w", encoding="utf-8") as f:
    f.write(out)

print("OK. Нод:", len(nodes))
print("Новые ноды:", len([n for n in nodes if n["name"] in (
    "DR Build settings", "DR HTTP settings", "DR Check", "Switch DR gate",
    "DR Build ask state", "DR HTTP ask state", "DR Format ask", "TG DR ask",
    "DR Build state", "DR HTTP state", "DR Parse", "Switch DR route",
    "DR Build save", "DR HTTP save", "DR Format ok", "TG DR ok",
    "DR Format wrong", "TG DR wrong", "DR Format custom",
    "CT Build qp", "CT HTTP qp", "AS Build qp", "AS HTTP qp")]))
