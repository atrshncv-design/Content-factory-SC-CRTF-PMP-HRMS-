#!/usr/bin/env python3
"""A1-fix2: сценарий текстового поста в wf-tg-bot (404 нод -> 429 нод).

Мутирует base/wf-tg-bot.json:
  1. Parser: +text_post в C-маппинг; +tx_toggle/tx_publish в обработку callback.
  2. Switch cmd: правило text_post (index 33) -> out[33]=TX Build, fallback (Gate Build) -> out[34].
  3. Switch cb: правила tx_toggle (13) / tx_publish (14); fallback CB answer unknown -> out[15].
  4. Switch gate: правило quick_text (5); fallback TG unknown -> out[6].
  5. Gate Check: state QUICK_TEXT_AWAIT -> mode quick_text.
  6. 25 новых нод ветки TX (Build -> ask -> gate -> save -> platforms -> toggle -> publish -> result).
Сериализация как в base: indent=1, ensure_ascii=False, без trailing newline.
"""
import json
import re
import uuid

BASE = "/Users/aleksandrtrisenkov/Desktop/PROGRAMMING/РАБОЧИЕ ПРОЕКТЫ/КОНТЕНТ-ЗАВОД-API-MVP/.scratch/review-full-14aug/base/wf-tg-bot.json"
OUT = "/Users/aleksandrtrisenkov/Desktop/PROGRAMMING/РАБОЧИЕ ПРОЕКТЫ/КОНТЕНТ-ЗАВОД-API-MVP/.scratch/review-full-14aug/fixes/wf-tg-bot.json"

raw = open(BASE, encoding="utf-8").read()
data = json.loads(raw)
wf = data[0]
nodes = wf["nodes"]
conns = wf["connections"]
byname = {n["name"]: n for n in nodes}

# --- esc-эталон: байт-точно из GD Format ---
esc_line = re.search(r"const esc = s =>[^\n]*", byname["GD Format"]["parameters"]["jsCode"]).group(0)
assert "replace(/([_*[\\\\]`])/g" in esc_line or "\\\\$1" in esc_line or "\\$1" in esc_line, esc_line
print("esc_line:", repr(esc_line))

def js(*lines):
    return "\n" + "\n".join(lines) + "\n"

def nid():
    return str(uuid.uuid4())

def code_node(name, body, pos):
    return {
        "id": nid(), "name": name, "type": "n8n-nodes-base.code", "typeVersion": 2,
        "position": pos,
        "parameters": {"mode": "runOnceForAllItems", "language": "javaScript", "jsCode": js(*body)},
    }

def http_db(name, pos):
    return {
        "id": nid(), "name": name, "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.5,
        "position": pos,
        "parameters": {
            "method": "POST", "url": "http://db-bridge:8787/query", "sendHeaders": True,
            "headerParameters": {"parameters": [{"name": "X-BRIDGE-TOKEN", "value": "={{ $env.FACTORY_DB_BRIDGE_TOKEN }}"}]},
            "sendBody": True, "contentType": "json", "specifyBody": "json",
            "jsonBody": "={{ $json }}", "options": {"timeout": 15000},
        },
    }

def tg_msg(name, pos, rows):
    return {
        "id": nid(), "name": name, "type": "n8n-nodes-base.telegram", "typeVersion": 2.2,
        "position": pos,
        "parameters": {
            "resource": "message", "operation": "sendMessage",
            "chatId": "={{ $('Parser').first().json.chat_id }}", "text": "={{ $json.text }}",
            "additionalFields": {"appendAttribution": False},
            "replyMarkup": "inlineKeyboard",
            "inlineKeyboard": {"rows": [{"row": {"buttons": [{"text": t, "additionalFields": {"callback_data": cb}} for t, cb in r]}} for r in rows]},
        },
    }

def tg_answer(name, pos, emoji):
    return {
        "id": nid(), "name": name, "type": "n8n-nodes-base.telegram", "typeVersion": 2.2,
        "position": pos,
        "parameters": {
            "resource": "callback", "operation": "answerQuery",
            "queryId": "={{ $('Parser').first().json.query_id }}",
            "additionalFields": {"text": emoji},
        },
    }

def switch_node(name, pos, rules_right, fallback="extra"):
    base_rule = {
        "conditions": {
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
            "conditions": [{"leftValue": "={{ $json.command }}", "rightValue": "", "operator": {"type": "string", "operation": "equals"}}],
            "combinator": "and",
        }
    }
    rules = []
    for rv, lv in rules_right:
        r = json.loads(json.dumps(base_rule))
        r["conditions"]["conditions"][0]["leftValue"] = lv
        r["conditions"]["conditions"][0]["rightValue"] = rv
        rules.append(r)
    return {
        "id": nid(), "name": name, "type": "n8n-nodes-base.switch", "typeVersion": 2.2,
        "position": pos,
        "parameters": {"mode": "rules", "rules": {"values": rules}, "options": {"fallbackOutput": fallback}},
    }

def http_publish(name, pos):
    return {
        "id": nid(), "name": name, "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.5,
        "position": pos,
        "parameters": {
            "method": "POST", "url": "http://localhost:5678/webhook/factory/publish",
            "sendBody": True, "contentType": "json", "specifyBody": "json",
            "jsonBody": "={{ $json.body }}",
            "options": {"timeout": 120000, "response": {"response": {"neverError": True}}},
        },
    }

# ============================================================ 1. Parser
p = byname["Parser"]
pc = p["parameters"]["jsCode"]
old_c = "    'gen_url2video': 'url2video', 'gen_shorts': 'shorts',\n  };"
new_c = ("    'gen_url2video': 'url2video', 'gen_shorts': 'shorts',\n"
         "    'text_post': 'text_post', 'текстовый пост': 'text_post', '/text_post': 'text_post', '/текстовый пост': 'text_post',\n"
         "  };")
assert pc.count(old_c) == 1, "C-map anchor not unique"
pc = pc.replace(old_c, new_c)
old_cb = "    else if (map[action] && map[action][entityType]) cb = map[action][entityType];"
new_cb = ("    else if (action === 'tx_toggle') cb = 'tx_toggle';\n"
          "    else if (action === 'tx_publish') cb = 'tx_publish';\n"
          "    else if (map[action] && map[action][entityType]) cb = map[action][entityType];")
assert pc.count(old_cb) == 1, "callback anchor not unique"
pc = pc.replace(old_cb, new_cb)
p["parameters"]["jsCode"] = pc

# ============================================================ 2. Switch cmd
scmd = byname["Switch cmd"]
last_rule = json.loads(json.dumps(scmd["parameters"]["rules"]["values"][-1]))
last_rule["conditions"]["conditions"][0]["rightValue"] = "text_post"
scmd["parameters"]["rules"]["values"].append(last_rule)
cmd_main = conns["Switch cmd"]["main"]
assert cmd_main[-1][0]["node"] == "Gate Build", cmd_main[-1]
cmd_main.insert(33, [{"node": "TX Build", "type": "main", "index": 0}])  # Gate Build -> 34

# ============================================================ 3. Switch cb
scb = byname["Switch cb"]
for rv in ("tx_toggle", "tx_publish"):
    r = json.loads(json.dumps(scb["parameters"]["rules"]["values"][-1]))
    r["conditions"]["conditions"][0]["rightValue"] = rv
    scb["parameters"]["rules"]["values"].append(r)
cb_main = conns["Switch cb"]["main"]
assert cb_main[-1][0]["node"] == "CB answer unknown", cb_main[-1]
cb_main.insert(13, [{"node": "TX answer", "type": "main", "index": 0}])
cb_main.insert(14, [{"node": "TX answer pub", "type": "main", "index": 0}])  # CB answer unknown -> 15

# ============================================================ 4. Switch gate
sg = byname["Switch gate"]
r = json.loads(json.dumps(sg["parameters"]["rules"]["values"][-1]))
r["conditions"]["conditions"][0]["rightValue"] = "quick_text"
sg["parameters"]["rules"]["values"].append(r)
gate_main = conns["Switch gate"]["main"]
assert gate_main[-1][0]["node"] == "TG unknown", gate_main[-1]
gate_main.insert(5, [{"node": "TX Save text", "type": "main", "index": 0}])  # TG unknown -> 6

# ============================================================ 5. Gate Check
gc = byname["Gate Check"]
gjs = gc["parameters"]["jsCode"]
old_g = "return [{ json: { mode: 'normal' } }];"
new_g = ("if (p.command === 'unknown' && state === 'QUICK_TEXT_AWAIT') return [{ json: { mode: 'quick_text' } }];\n"
         "return [{ json: { mode: 'normal' } }];")
assert gjs.count(old_g) == 1, "gate normal anchor"
gc["parameters"]["jsCode"] = gjs.replace(old_g, new_g)

# ============================================================ 6. New nodes
NEW = {}
def add(n):
    assert n["name"] not in byname and n["name"] not in NEW, n["name"]
    NEW[n["name"]] = n
    nodes.append(n)

# -- ask: /text_post
add(code_node("TX Build", [
    "return [{ json: { sql: \"UPDATE sessions SET state='QUICK_TEXT_AWAIT', quick_payload=NULL, updated_at=datetime('now') WHERE tg_user_id = ?\", params: [941296693] } }];",
], [7400, 0]))
add(http_db("TX HTTP build", [7640, 0]))
add(code_node("TX Format ask", [
    "const p = $('Parser').first().json;",
    esc_line,
    "const text = esc('📝 Пришли текст поста');",
    "return [{ json: { chat_id: p.chat_id, text: text } }];",
], [7880, 0]))
add(tg_msg("TG tx ask", [8120, 0], [
    [("🧹 Отмена", "cmd:cancel"), ("📋 Меню", "cmd:menu")],
]))

# -- gate: текст при QUICK_TEXT_AWAIT
add(code_node("TX Save text", [
    "const p = $('Parser').first().json;",
    "const text = String(p.raw || '').trim();",
    "return [{ json: { sql: \"UPDATE sessions SET quick_payload = json(?), state = 'QUICK_TEXT_PLATFORMS', updated_at = datetime('now') WHERE tg_user_id = ?\", params: [JSON.stringify({ text: text }), 941296693] } }];",
], [7400, 220]))
add(http_db("TX HTTP save", [7640, 220]))
add(code_node("TX Format platforms", [
    "const p = $('Parser').first().json;",
    esc_line,
    "const lines = ['📤 Выбери площадки:', '', '☐ Threads', '☐ X', '☐ VK', '☐ Telegram', '', 'Нажми на площадку — затем «✅ Опубликовать».'];",
    "return [{ json: { chat_id: p.chat_id, text: esc(lines.join('\\n')) } }];",
], [7880, 220]))
add(tg_msg("TG tx platforms", [8120, 220], [
    [("☐ Threads", "tx_toggle:platform:threads"), ("☐ X", "tx_toggle:platform:x")],
    [("☐ VK", "tx_toggle:platform:vk"), ("☐ Telegram", "tx_toggle:platform:telegram")],
    [("✅ Опубликовать", "tx_publish")],
    [("🧹 Отмена", "cmd:cancel"), ("📋 Меню", "cmd:menu")],
]))

# -- toggle: tx_toggle:platform:<p>
add(tg_answer("TX answer", [7400, 440], "☑️"))
add(code_node("TX Toggle select", [
    "return [{ json: { sql: \"SELECT quick_payload FROM sessions WHERE tg_user_id = ?\", params: [941296693] } }];",
], [7640, 440]))
add(http_db("TX HTTP select", [7880, 440]))
add(code_node("TX Toggle", [
    "const p = $('Parser').first().json;",
    "const rows = $('TX HTTP select').first().json.rows || [];",
    "let payload = {};",
    "try { payload = JSON.parse((rows[0] && rows[0].quick_payload) || '{}'); } catch (e) { payload = {}; }",
    "let platforms = Array.isArray(payload.platforms) ? payload.platforms : [];",
    "const plat = p.entity_id;",
    "const i = platforms.indexOf(plat);",
    "if (i >= 0) platforms.splice(i, 1); else platforms.push(plat);",
    "payload.platforms = platforms;",
    "return [{ json: { sql: \"UPDATE sessions SET quick_payload = json(?), updated_at = datetime('now') WHERE tg_user_id = ?\", params: [JSON.stringify(payload), 941296693] } }];",
], [8120, 440]))
add(http_db("TX HTTP update", [8360, 440]))
add(code_node("TX Toggle Format", [
    "const p = $('Parser').first().json;",
    esc_line,
    "const pl = $('TX Toggle').first().json.platforms || [];",
    "const names = { threads: 'Threads', x: 'X', vk: 'VK', telegram: 'Telegram' };",
    "const lines = ['📤 Выбери площадки:', ''];",
    "for (const key of ['threads', 'x', 'vk', 'telegram']) lines.push((pl.indexOf(key) >= 0 ? '☑️' : '☐') + ' ' + names[key]);",
    "return [{ json: { chat_id: p.chat_id, text: esc(lines.join('\\n')) } }];",
], [8600, 440]))

# -- publish: tx_publish
add(tg_answer("TX answer pub", [7400, 660], "📤"))
add(code_node("TX Build select", [
    "return [{ json: { sql: \"SELECT quick_payload FROM sessions WHERE tg_user_id = ?\", params: [941296693] } }];",
], [7640, 660]))
add(http_db("TX HTTP select pub", [7880, 660]))
add(code_node("TX Build body", [
    "const rows = $('TX HTTP select pub').first().json.rows || [];",
    "let payload = {};",
    "try { payload = JSON.parse((rows[0] && rows[0].quick_payload) || '{}'); } catch (e) { payload = {}; }",
    "const platforms = Array.isArray(payload.platforms) ? payload.platforms : [];",
    "const content = (typeof payload.text === 'string' ? payload.text : '').trim();",
    "if (!platforms.length) return [{ json: { ok: false, error: 'выбери платформу' } }];",
    "if (!content) return [{ json: { ok: false, error: 'текст поста не получен' } }];",
    "return [{ json: { ok: true, body: { platforms: platforms, content: content, captions: {}, post_at: null, generation_id: null, file_ids: [] } } }];",
], [7880, 660]))
add(switch_node("Switch TX valid", [8120, 660], [("true", "={{ $json.ok }}")], fallback="extra"))
add(http_publish("TX HTTP publish", [8360, 660]))
add(code_node("TX Format result", [
    "const p = $('Parser').first().json;",
    esc_line,
    "const body = $('TX Build body').first().json.body || {};",
    "const platforms = Array.isArray(body.platforms) ? body.platforms : [];",
    "let r = null;",
    "try { r = $('TX HTTP publish').first().json; } catch (e) { r = null; }",
    "const resp = (r && typeof r.body === 'object' && r.body) ? r.body : (r || {});",
    "if (resp && resp.post_id !== undefined && resp.post_id !== null) {",
    "  return [{ json: { chat_id: p.chat_id, text: '✅ Опубликовано в: ' + esc(platforms.join(', ')) } }];",
    "}",
    "const e = resp.error;",
    "const msg = (typeof e === 'string' && e) ? e : (e && e.message) || 'сервис публикации не ответил';",
    "return [{ json: { chat_id: p.chat_id, text: '❌ Ошибка публикации: ' + esc(msg) } }];",
], [8600, 660]))
add(code_node("TX Reset", [
    "return [{ json: { sql: \"UPDATE sessions SET state = 'IDLE', quick_payload = NULL, updated_at = datetime('now') WHERE tg_user_id = ?\", params: [941296693] } }];",
], [8840, 660]))
add(http_db("TX HTTP reset", [9080, 660]))
add(tg_msg("TG tx result", [9320, 660], [
    [("📝 Новый пост", "cmd:text_post"), ("📋 Меню", "cmd:menu")],
]))
add(code_node("TX Format err", [
    "const p = $('Parser').first().json;",
    esc_line,
    "const err = $('TX Build body').first().json.error || 'что-то пошло не так';",
    "return [{ json: { chat_id: p.chat_id, text: '☝️ ' + esc(err) } }];",
], [8360, 880]))
add(tg_msg("TG tx err", [8600, 880], [
    [("📋 Меню", "cmd:menu")],
]))

# ============================================================ 7. Connections for new nodes
def conn(src, targets):
    assert src not in conns or src not in NEW, f"conns already has {src}"
    conns[src] = {"main": [[{"node": t, "type": "main", "index": 0}] for t in targets]}

conn("TX Build", ["TX HTTP build"])
conn("TX HTTP build", ["TX Format ask"])
conn("TX Format ask", ["TG tx ask"])
conn("TX Save text", ["TX HTTP save"])
conn("TX HTTP save", ["TX Format platforms"])
conn("TX Format platforms", ["TG tx platforms"])
conn("TX answer", ["TX Toggle select"])
conn("TX Toggle select", ["TX HTTP select"])
conn("TX HTTP select", ["TX Toggle"])
conn("TX Toggle", ["TX HTTP update"])
conn("TX HTTP update", ["TX Toggle Format"])
conn("TX Toggle Format", ["TG tx platforms"])
conn("TX answer pub", ["TX Build select"])
conn("TX Build select", ["TX HTTP select pub"])
conn("TX HTTP select pub", ["TX Build body"])
conn("TX Build body", ["Switch TX valid"])
conn("Switch TX valid", ["TX HTTP publish", "TX Format err"])
conn("TX HTTP publish", ["TX Format result"])
conn("TX Format result", ["TX Reset"])
conn("TX Reset", ["TX HTTP reset"])
conn("TX HTTP reset", ["TG tx result"])
conn("TX Format err", ["TG tx err"])

# ============================================================ 8. Serialize как base
out = json.dumps(data, ensure_ascii=False, indent=1)
assert not out.endswith("\n")
with open(OUT, "w", encoding="utf-8") as f:
    f.write(out)

print("OK nodes:", len(nodes), "| new:", len(NEW))
print("Switch cmd rules:", len(scmd["parameters"]["rules"]["values"]), "| out:", len(conns["Switch cmd"]["main"]))
print("Switch cb rules:", len(scb["parameters"]["rules"]["values"]), "| out:", len(cb_main))
print("Switch gate rules:", len(sg["parameters"]["rules"]["values"]), "| out:", len(gate_main))
print("Switch cmd out[33]:", conns["Switch cmd"]["main"][33][0]["node"], "| out[34]:", conns["Switch cmd"]["main"][34][0]["node"])
print("Switch cb out[13]:", cb_main[13][0]["node"], "| out[14]:", cb_main[14][0]["node"], "| out[15]:", cb_main[15][0]["node"])
print("Switch gate out[5]:", gate_main[5][0]["node"], "| out[6]:", gate_main[6][0]["node"])
print("written:", OUT)
