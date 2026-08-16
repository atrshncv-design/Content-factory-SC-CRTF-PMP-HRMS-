#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T32: авто-режим (users.auto_approve) — трансформер wf-tg-bot.json.

1. Parser: команда «авто»/«авто вкл»/«авто выкл» (+ auto/on/off) → command 'auto' + args.action.
2. Switch cmd: правило out[44] command==auto → AUT Build role (fallback уезжает в конец).
3. AUT-цепочка (владелец): SELECT role+auto_approve → role-gate admin → UPDATE users.auto_approve → «⚙️ Авто-режим: вкл/выкл».
4. Реальный флаг в quick_payload: SH Verify build / AU Verify build / AU RG build / SH Update state
   (json_set-подзапрос к users.auto_approve, COALESCE NULL→0).
5. SCRIPT_AWAIT-скип при auto=1:
   - SH: Switch SH parse out[4] → SH AA Build → SH AA HTTP → SH AA Check → Switch SH AA (auto → SH Update state; verify → SH Verify build)
   - AU: Switch AU parse out[0] → AU AA Build → AU AA HTTP → AU Verify build (return + поля) → AU Verify HTTP → AU Verify route → Switch AU verify (auto → SC Cont build; verify → AU Verify format)
6. sc_*/vd_* при auto=1 → сразу ✅:
   - read-ноды SC RG / VD RG / VD RJ += подзапрос users.auto_approve
   - SC RG route: aa==1 && SCRIPT_AWAIT → au_video/sh_video (Switch SC RG += sh_video/au_video)
   - VD RG / VD RJ route: aa==1 && VIDEO_AWAIT → publish (Switch VD RG/VD RJ += publish → VD OK Build session)
   - SC ED: aa==1 && SCRIPT_AWAIT → au_video/sh_video (новая цепочка SC ED read/HTTP/route + Switch SC ED)
   - VD OK Build session: generation_id из $input (приходит и из VD OK route, и из VD RG/VD RJ publish)
"""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(BASE, 'wf-tg-bot.json')
raw = open(PATH, encoding='utf-8').read()
wf = json.loads(raw)
w = wf[0]
nodes = w['nodes']
conns = w['connections']
by_name = {n['name']: n for n in nodes}

def get(name):
    return by_name[name]

def add_node(name, ntype, tver, pos, params, node_id=None):
    n = {"parameters": params, "name": name, "type": ntype, "typeVersion": tver, "position": pos}
    n["id"] = node_id if node_id else "a032%04d-0000-4000-8000-%012d" % (len(nodes) + 1, len(nodes) + 1)
    nodes.append(n)
    by_name[name] = n
    return n

def add_conn(src, out_idx, dst, src_main=None):
    if src not in conns:
        conns[src] = {"main": src_main if src_main is not None else [[]]}
    main = conns[src]["main"]
    while len(main) <= out_idx:
        main.append([])
    main[out_idx].append({"node": dst, "type": "main", "index": 0})

def set_conn_target(src, out_idx, dst):
    main = conns[src]["main"]
    main[out_idx] = [{"node": dst, "type": "main", "index": 0}]

HTTP_PARAMS = {
    "method": "POST",
    "url": "http://db-bridge:8787/query",
    "sendHeaders": True,
    "headerParameters": {"parameters": [{"name": "X-BRIDGE-TOKEN", "value": "={{ $env.FACTORY_DB_BRIDGE_TOKEN }}"}]},
    "sendBody": True,
    "contentType": "json",
    "specifyBody": "json",
    "jsonBody": "={{ $json }}",
    "options": {"timeout": 15000},
}

ESC = r"const esc = s => String(s ?? '').replace(/([_*\[\]`])/g, '\\$1');"
READ_SQL = ("SELECT state, quick_payload, (SELECT COALESCE(auto_approve, 0) FROM users WHERE tg_user_id = ?) "
            "AS auto_approve FROM sessions WHERE tg_user_id = ?")

# ---------------------------------------------------------------- 1. Parser
parser = get('Parser')
pjs = parser['parameters']['jsCode']

old_args = "  const args = { url: null, id: null, value: null, platform: null, handle: null, section: null };"
assert old_args in pjs, "Parser: args-инициализация не найдена"
pjs = pjs.replace(old_args,
                  "  const args = { url: null, id: null, value: null, platform: null, handle: null, section: null, action: null };")

old_q = "  else if (t.startsWith('вопрос ') || t.startsWith('/вопросы ')) { command = 'questions'; args.action = 'set'; const N = /^\\d+$/.test(words[1] || '') ? parseInt(words[1], 10) : null; args.n = N; args.value = words.slice(2).join(' ') || null; }"
assert old_q in pjs, "Parser: ветка вопросов не найдена"
auto_branches = (old_q +
    "\n  else if (t === 'авто' || t === '/авто' || t === 'auto' || t === '/auto') { command = 'auto'; args.action = 'toggle'; }" +
    "\n  else if (t.startsWith('авто вкл') || t.startsWith('/авто вкл') || t.startsWith('auto on') || t.startsWith('/auto on')) { command = 'auto'; args.action = 'on'; }" +
    "\n  else if (t.startsWith('авто выкл') || t.startsWith('/авто выкл') || t.startsWith('auto off') || t.startsWith('/auto off')) { command = 'auto'; args.action = 'off'; }")
pjs = pjs.replace(old_q, auto_branches)
parser['parameters']['jsCode'] = pjs

# ---------------------------------------------------------------- 2. Switch cmd
scmd = get('Switch cmd')
scmd['parameters']['rules']['values'].append({
    "conditions": {
        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
        "conditions": [{"leftValue": "={{ $json.command }}", "rightValue": "auto",
                        "operator": {"type": "string", "operation": "equals"}}],
        "combinator": "and",
    }
})
scmd_main = conns['Switch cmd']['main']
assert scmd_main[-1] == [{"node": "Gate Build", "type": "main", "index": 0}], "Switch cmd fallback не Gate Build"
gate = scmd_main.pop(-1)
scmd_main.append([{"node": "AUT Build role", "type": "main", "index": 0}])
scmd_main.append(gate)

# ---------------------------------------------------------------- 3. AUT chain (владелец)
add_node("AUT Build role", "n8n-nodes-base.code", 2, [600, 4400],
         {"mode": "runOnceForAllItems", "language": "javaScript",
          "jsCode": "const p = $('Parser').first().json;\nreturn [{ json: { sql: \"SELECT role, COALESCE(auto_approve, 0) AS auto_approve FROM users WHERE tg_user_id = ?\", params: [p.tg_user_id] } }];"})
add_node("AUT HTTP role", "n8n-nodes-base.httpRequest", 4.5, [880, 4400], dict(HTTP_PARAMS))
add_node("AUT Check role", "n8n-nodes-base.code", 2, [1160, 4400],
         {"mode": "runOnceForAllItems", "language": "javaScript",
          "jsCode": "const rows = $('AUT HTTP role').first().json.rows || [];\nconst role = rows.length ? rows[0].role : null;\nconst cur = rows.length ? Number(rows[0].auto_approve) || 0 : 0;\nif (role !== 'admin') return [{ json: { ok: false, text: '⛔ Только владелец может управлять авто-режимом' } }];\nreturn [{ json: { ok: true, cur: cur } }];"})
add_node("Switch AUT role", "n8n-nodes-base.switch", 3.4, [1440, 4400],
         {"mode": "rules", "rules": {"values": [{"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"}, "conditions": [{"leftValue": "={{ $json.ok }}", "rightValue": True, "operator": {"type": "boolean", "operation": "equals"}}], "combinator": "and"}}]}, "options": {"fallbackOutput": "extra"}})
add_node("AUT Build update", "n8n-nodes-base.code", 2, [1760, 4240],
         {"mode": "runOnceForAllItems", "language": "javaScript",
          "jsCode": "const p = $('Parser').first().json;\nconst cur = Number($('AUT Check role').first().json.cur) || 0;\nconst action = String((p.args && p.args.action) || 'toggle');\nlet next = 0;\nif (action === 'on') next = 1;\nelse if (action === 'off') next = 0;\nelse next = cur ? 0 : 1;\nreturn [{ json: { sql: \"UPDATE users SET auto_approve = ? WHERE tg_user_id = ?\", params: [next, p.tg_user_id], next: next } }];"})
add_node("AUT HTTP update", "n8n-nodes-base.httpRequest", 4.5, [2040, 4240], dict(HTTP_PARAMS))
add_node("AUT Format", "n8n-nodes-base.code", 2, [2320, 4240],
         {"mode": "runOnceForAllItems", "language": "javaScript",
          "jsCode": "const p = $('Parser').first().json;\n" + ESC + "\nconst next = Number($('AUT Build update').first().json.next) || 0;\nconst text = '⚙️ Авто-режим: ' + (next ? 'вкл' : 'выкл');\nreturn [{ json: { chat_id: p.chat_id, text: esc(text) } }];"})
tg_aut = add_node("TG AUT", "n8n-nodes-base.telegram", 1.2, [2600, 4240],
                  {"resource": "message", "operation": "sendMessage", "chatId": "={{ $('Parser').first().json.chat_id }}",
                   "text": "={{ $json.text }}", "additionalFields": {"appendAttribution": False},
                   "inlineKeyboard": {"rows": [{"row": {"buttons": [{"text": "📋 Меню", "additionalFields": {"callback_data": "cmd:menu"}}]}}]},
                   "replyMarkup": "inlineKeyboard"},
                  node_id="a0320000-0000-4000-8000-000000000001")
tg_aut["credentials"] = {"telegramApi": {"id": "10000000-0000-4000-8000-000000000004", "name": "telegram"}}
add_node("AUT Format denied", "n8n-nodes-base.code", 2, [1760, 4560],
         {"mode": "runOnceForAllItems", "language": "javaScript",
          "jsCode": "const p = $('Parser').first().json;\n" + ESC + "\nreturn [{ json: { chat_id: p.chat_id, text: esc('⛔ Только владелец может управлять авто-режимом') } }];"})
tg_autd = add_node("TG AUT denied", "n8n-nodes-base.telegram", 1.2, [2040, 4560],
                   {"resource": "message", "operation": "sendMessage", "chatId": "={{ $('Parser').first().json.chat_id }}",
                    "text": "={{ $json.text }}", "additionalFields": {"appendAttribution": False},
                    "inlineKeyboard": {"rows": [{"row": {"buttons": [{"text": "📋 Меню", "additionalFields": {"callback_data": "cmd:menu"}}]}}]},
                    "replyMarkup": "inlineKeyboard"},
                   node_id="a0320000-0000-4000-8000-000000000002")
tg_autd["credentials"] = {"telegramApi": {"id": "10000000-0000-4000-8000-000000000004", "name": "telegram"}}

add_conn("AUT Build role", 0, "AUT HTTP role")
add_conn("AUT HTTP role", 0, "AUT Check role")
add_conn("AUT Check role", 0, "Switch AUT role")
add_conn("Switch AUT role", 0, "AUT Build update")
add_conn("AUT Build update", 0, "AUT HTTP update")
add_conn("AUT HTTP update", 0, "AUT Format")
add_conn("AUT Format", 0, "TG AUT")
add_conn("Switch AUT role", 1, "AUT Format denied")
add_conn("AUT Format denied", 0, "TG AUT denied")

# ---------------------------------------------------------------- 4. Реальный флаг в payload (json_set)
JSON_SET = "quick_payload=json_set(?, '$.auto_approve', COALESCE((SELECT auto_approve FROM users WHERE tg_user_id = ?), 0))"

# SH Verify build
shv = get('SH Verify build')
shv_js = shv['parameters']['jsCode']
assert "UPDATE sessions SET state='SCRIPT_AWAIT', quick_payload=?" in shv_js, "SH Verify build: SQL не найден"
shv_js = shv_js.replace(
    "UPDATE sessions SET state='SCRIPT_AWAIT', quick_payload=?, updated_at=datetime('now') WHERE tg_user_id = ?",
    "UPDATE sessions SET state='SCRIPT_AWAIT', " + JSON_SET + ", updated_at=datetime('now') WHERE tg_user_id = ?")
assert "params: [payload, p.tg_user_id]" in shv_js, "SH Verify build: params не найден"
shv_js = shv_js.replace("params: [payload, p.tg_user_id]", "params: [payload, p.tg_user_id, p.tg_user_id]")
shv['parameters']['jsCode'] = shv_js

# AU Verify build
auv = get('AU Verify build')
auv_js = auv['parameters']['jsCode']
assert "UPDATE sessions SET state='SCRIPT_AWAIT', quick_payload=?" in auv_js, "AU Verify build: SQL не найден"
auv_js = auv_js.replace(
    "UPDATE sessions SET state='SCRIPT_AWAIT', quick_payload=?, updated_at=datetime('now') WHERE tg_user_id = ?",
    "UPDATE sessions SET state='SCRIPT_AWAIT', " + JSON_SET + ", updated_at=datetime('now') WHERE tg_user_id = ?")
assert "params: [payload, p.tg_user_id]" in auv_js, "AU Verify build: params не найден"
auv_js = auv_js.replace("params: [payload, p.tg_user_id]", "params: [payload, p.tg_user_id, p.tg_user_id]")
# добавить scriptFull const + поля в return
old_payload = "const payload = JSON.stringify({\n  flow: 'au', topic_id: topicId, script: script,\n  script_full: { hook: String((s && s.hook) || ''), body: String((s && s.body) || ''), cta: String((s && s.cta) || ''), target_length: Number((s && s.target_length) || 30), format_tag: String((s && s.format_tag) || 'auto'), full_text: script },\n  source_url: sourceUrl, video_length: videoLength, attempts: attempts,\n  topic_title: topicTitle, topic_rationale: topicRationale, auto_approve: 0\n});"
assert old_payload in auv_js, "AU Verify build: payload-блок не найден"
new_payload = ("const scriptFull = { hook: String((s && s.hook) || ''), body: String((s && s.body) || ''), cta: String((s && s.cta) || ''), target_length: Number((s && s.target_length) || 30), format_tag: String((s && s.format_tag) || 'auto'), full_text: script };\n"
               "const payload = JSON.stringify({\n  flow: 'au', topic_id: topicId, script: script,\n  script_full: scriptFull,\n  source_url: sourceUrl, video_length: videoLength, attempts: attempts,\n  topic_title: topicTitle, topic_rationale: topicRationale, auto_approve: 0\n});")
auv_js = auv_js.replace(old_payload, new_payload)
old_ret = "return [{ json: { sql: \"UPDATE sessions SET state='SCRIPT_AWAIT', quick_payload=json_set(?, '$.auto_approve', COALESCE((SELECT auto_approve FROM users WHERE tg_user_id = ?), 0)), updated_at=datetime('now') WHERE tg_user_id = ?\", params: [payload, p.tg_user_id, p.tg_user_id], chat_id: p.chat_id, text: text } }];"
assert old_ret in auv_js, "AU Verify build: return не найден"
new_ret = ("return [{ json: { sql: \"UPDATE sessions SET state='SCRIPT_AWAIT', quick_payload=json_set(?, '$.auto_approve', COALESCE((SELECT auto_approve FROM users WHERE tg_user_id = ?), 0)), updated_at=datetime('now') WHERE tg_user_id = ?\", params: [payload, p.tg_user_id, p.tg_user_id], chat_id: p.chat_id, text: text, script: script, script_full: scriptFull, topic_id: topicId, source_url: sourceUrl, video_length: videoLength } }];")
auv_js = auv_js.replace(old_ret, new_ret)
auv['parameters']['jsCode'] = auv_js

# AU RG build
aurg = get('AU RG build')
aurg_js = aurg['parameters']['jsCode']
assert "UPDATE sessions SET state = 'CYCLE_GENERATION_PENDING', quick_payload = ?" in aurg_js, "AU RG build: SQL не найден"
aurg_js = aurg_js.replace(
    "UPDATE sessions SET state = 'CYCLE_GENERATION_PENDING', quick_payload = ?, updated_at = datetime('now') WHERE tg_user_id = ?",
    "UPDATE sessions SET state = 'CYCLE_GENERATION_PENDING', quick_payload = json_set(?, '$.auto_approve', COALESCE((SELECT auto_approve FROM users WHERE tg_user_id = ?), 0)), updated_at = datetime('now') WHERE tg_user_id = ?")
assert "params: [payload, p.tg_user_id]" in aurg_js, "AU RG build: params не найден"
aurg_js = aurg_js.replace("params: [payload, p.tg_user_id]", "params: [payload, p.tg_user_id, p.tg_user_id]")
aurg['parameters']['jsCode'] = aurg_js

# SH Update state
shus = get('SH Update state')
shus_js = shus['parameters']['jsCode']
assert "UPDATE sessions SET state='QUICK_SHORTS_GENERATING', quick_payload=?" in shus_js, "SH Update state: SQL не найден"
shus_js = shus_js.replace(
    "UPDATE sessions SET state='QUICK_SHORTS_GENERATING', quick_payload=?, updated_at=datetime('now') WHERE tg_user_id = ?",
    "UPDATE sessions SET state='QUICK_SHORTS_GENERATING', " + JSON_SET + ", updated_at=datetime('now') WHERE tg_user_id = ?")
assert "params: [JSON.stringify(payload), p.tg_user_id]" in shus_js, "SH Update state: params не найден"
shus_js = shus_js.replace("params: [JSON.stringify(payload), p.tg_user_id]",
                          "params: [JSON.stringify(payload), p.tg_user_id, p.tg_user_id]")
shus['parameters']['jsCode'] = shus_js

# ---------------------------------------------------------------- 5a. SH AA chain (SCRIPT_AWAIT-skip)
# ⚠️ Двойное выполнение SH Update state/SHT HTTP в одном прогоне (auto-ветка входит в тот же конвейер):
#    потребители SHT Format/SH Format async/... должны читать ПОСЛЕДНЕЕ выполнение (.last()),
#    иначе .first() вернёт script_only-прогон → бесконечный цикл. Для существующих путей
#    (каждая нода выполняется 1 раз на прогон) .first()==.last() — изменения безопасны.
SH_LAST_FIXES = [
    # (node_name, old_fragment, new_fragment)
    ("SHT HTTP", "$('SH Update state').first().json", "$('SH Update state').last().json"),
    ("SHT Format", "$('SHT HTTP').first().json", "$('SHT HTTP').last().json"),
    ("SHT Format", "$('SH Update state').first().json", "$('SH Update state').last().json"),
    ("SH Format async", "$('SHT Format').first().json", "$('SHT Format').last().json"),
    ("SH Text async", "$('SHT Format').first().json", "$('SHT Format').last().json"),
    ("SH Build generation", "$('SHT Format').first().json", "$('SHT Format').last().json"),
    ("SH Build session", "$('SHT Format').first().json", "$('SHT Format').last().json"),
    ("SH Format rerr", "$('SHT Format').first().json", "$('SHT Format').last().json"),
]
for _n, _old, _new in SH_LAST_FIXES:
    _node = get(_n)
    _blob = json.dumps(_node['parameters'], ensure_ascii=False)
    assert _old in _blob, f"{_n}: фрагмент {_old!r} не найден"
    _js = _node.get('parameters', {}).get('jsCode')
    if _js is not None:
        _node['parameters']['jsCode'] = _js.replace(_old, _new)
    else:
        for _k, _v in list(_node['parameters'].items()):
            if isinstance(_v, str) and _old in _v:
                _node['parameters'][_k] = _v.replace(_old, _new)

add_node("SH AA Build", "n8n-nodes-base.code", 2, [600, 5600],
         {"mode": "runOnceForAllItems", "language": "javaScript",
          "jsCode": "const p = $('Parser').first().json;\nreturn [{ json: { sql: \"SELECT COALESCE(auto_approve, 0) AS auto_approve FROM users WHERE tg_user_id = ?\", params: [p.tg_user_id] } }];"})
add_node("SH AA HTTP", "n8n-nodes-base.httpRequest", 4.5, [880, 5600], dict(HTTP_PARAMS))
add_node("SH AA Check", "n8n-nodes-base.code", 2, [1160, 5600],
         {"mode": "runOnceForAllItems", "language": "javaScript",
          "jsCode": "const p = $('Parser').first().json;\nconst rows = $('SH AA HTTP').first().json.rows || [];\nconst aa = Number(rows[0] && rows[0].auto_approve) || 0;\nconst f = $('SHT Format').first().json;\nconst script = String(f.script || '').trim();\nlet topic = '';\nlet attempts = 1;\ntry { const u = $('SH Update state').first().json; topic = String(u.topic || ''); attempts = Number(u.attempts) || 1; } catch (e) {}\nif (aa === 1 && script) return [{ json: { mode: 'auto', chat_id: p.chat_id, script: script, topic: topic, attempts: attempts } }];\nreturn [{ json: { mode: 'verify', chat_id: p.chat_id } }];"})
add_node("Switch SH AA", "n8n-nodes-base.switch", 3.4, [1440, 5600],
         {"mode": "rules", "rules": {"values": [{"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"}, "conditions": [{"leftValue": "={{ $json.mode }}", "rightValue": "auto", "operator": {"type": "string", "operation": "equals"}}], "combinator": "and"}}]}, "options": {"fallbackOutput": "extra"}})

set_conn_target('Switch SH parse', 4, 'SH AA Build')
add_conn('SH AA Build', 0, 'SH AA HTTP')
add_conn('SH AA HTTP', 0, 'SH AA Check')
add_conn('SH AA Check', 0, 'Switch SH AA')
add_conn('Switch SH AA', 0, 'SH Update state')
add_conn('Switch SH AA', 1, 'SH Verify build')

# ---------------------------------------------------------------- 5b. AU AA chain (SCRIPT_AWAIT-skip)
add_node("AU AA Build", "n8n-nodes-base.code", 2, [600, 6200],
         {"mode": "runOnceForAllItems", "language": "javaScript",
          "jsCode": "const p = $('Parser').first().json;\nreturn [{ json: { sql: \"SELECT COALESCE(auto_approve, 0) AS auto_approve FROM users WHERE tg_user_id = ?\", params: [p.tg_user_id] } }];"})
add_node("AU AA HTTP", "n8n-nodes-base.httpRequest", 4.5, [880, 6200], dict(HTTP_PARAMS))
add_node("AU Verify route", "n8n-nodes-base.code", 2, [1760, 6400],
         {"mode": "runOnceForAllItems", "language": "javaScript",
          "jsCode": "const p = $('Parser').first().json;\nconst rows = $('AU AA HTTP').first().json.rows || [];\nconst aa = Number(rows[0] && rows[0].auto_approve) || 0;\nconst b = $('AU Verify build').first().json;\nif (aa === 1 && b.script) {\n  return [{ json: { mode: 'auto', chat_id: p.chat_id, script: String(b.script || ''),\n    script_full: (b.script_full && typeof b.script_full === 'object') ? b.script_full : { full_text: String(b.script || '') },\n    topic_id: Number(b.topic_id) || null, source_url: String(b.source_url || ''), video_length: Number(b.video_length) || 30 } }];\n}\nreturn [{ json: { mode: 'verify', chat_id: p.chat_id } }];"})
add_node("Switch AU verify", "n8n-nodes-base.switch", 3.4, [2040, 6400],
         {"mode": "rules", "rules": {"values": [{"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"}, "conditions": [{"leftValue": "={{ $json.mode }}", "rightValue": "auto", "operator": {"type": "string", "operation": "equals"}}], "combinator": "and"}}]}, "options": {"fallbackOutput": "extra"}})

set_conn_target('Switch AU parse', 0, 'AU AA Build')
add_conn('AU AA Build', 0, 'AU AA HTTP')
add_conn('AU AA HTTP', 0, 'AU Verify build')
set_conn_target('AU Verify HTTP', 0, 'AU Verify route')
add_conn('AU Verify route', 0, 'Switch AU verify')
add_conn('Switch AU verify', 0, 'SC Cont build')
add_conn('Switch AU verify', 1, 'AU Verify format')

# ---------------------------------------------------------------- 6. sc_*/vd_* при auto=1 → ✅
def patch_read(node_name):
    n = get(node_name)
    js = n['parameters']['jsCode']
    assert "SELECT state, quick_payload FROM sessions WHERE tg_user_id = ?" in js, f"{node_name}: read-SQL не найден"
    js = js.replace("SELECT state, quick_payload FROM sessions WHERE tg_user_id = ?", READ_SQL)
    js = js.replace("params: [p.tg_user_id]", "params: [p.tg_user_id, p.tg_user_id]")
    n['parameters']['jsCode'] = js

for rd in ('SC RG read', 'VD RG read', 'VD RJ read'):
    patch_read(rd)

# SC RG route: авто → как ✅
rg = get('SC RG route')
rg_js = rg['parameters']['jsCode']
anchor = "const state = (rows[0] && rows[0].state) || '';"
assert anchor in rg_js, "SC RG route: state-якорь не найден"
auto_block = (anchor + "\nconst aa = Number(rows[0] && rows[0].auto_approve) || 0;\n"
              "if (aa === 1 && state === 'SCRIPT_AWAIT' && qp.flow) {\n"
              "  const script = String(qp.script || '').trim();\n"
              "  if (!script) return [{ json: { mode: 'err', chat_id: p.chat_id, text: '⚠️ Сценарий не найден или устарел. Запусти генерацию заново.' } }];\n"
              "  if (qp.flow === 'au') {\n"
              "    return [{ json: { mode: 'au_video', chat_id: p.chat_id, script: script, topic_id: Number(qp.topic_id) || null, script_full: (qp.script_full && typeof qp.script_full === 'object') ? qp.script_full : { full_text: script }, source_url: String(qp.source_url || ''), video_length: Number(qp.video_length) || 30 } }];\n"
              "  }\n"
              "  return [{ json: { mode: 'sh_video', chat_id: p.chat_id, script: script, topic: String(qp.topic || '') } }];\n"
              "}")
rg_js = rg_js.replace(anchor, auto_block, 1)
rg['parameters']['jsCode'] = rg_js

# Switch SC RG += sh_video/au_video
srg = get('Switch SC RG')
srg['parameters']['rules']['values'].append({
    "conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                   "conditions": [{"leftValue": "={{ $json.mode }}", "rightValue": "sh_video",
                                   "operator": {"type": "string", "operation": "equals"}}], "combinator": "and"}})
srg['parameters']['rules']['values'].append({
    "conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                   "conditions": [{"leftValue": "={{ $json.mode }}", "rightValue": "au_video",
                                   "operator": {"type": "string", "operation": "equals"}}], "combinator": "and"}})
srg_main = conns['Switch SC RG']['main']
assert srg_main[-1] == [{"node": "AU Build alert", "type": "main", "index": 0}], "Switch SC RG fallback не AU Build alert"
fb = srg_main.pop(-1)
srg_main.append([{"node": "SH Update state", "type": "main", "index": 0}])
srg_main.append([{"node": "SC Cont build", "type": "main", "index": 0}])
srg_main.append(fb)

# VD RG route: авто → publish
vrg = get('VD RG route')
vrg_js = vrg['parameters']['jsCode']
assert anchor in vrg_js, "VD RG route: state-якорь не найден"
vrg_js = vrg_js.replace(anchor,
                        anchor + "\nconst aa = Number(rows[0] && rows[0].auto_approve) || 0;\n"
                        "if (aa === 1 && state === 'VIDEO_AWAIT' && String(qp.generation_id || '')) {\n"
                        "  return [{ json: { mode: 'publish', chat_id: p.chat_id, generation_id: String(qp.generation_id) } }];\n"
                        "}", 1)
vrg['parameters']['jsCode'] = vrg_js

# VD RJ route: авто → publish
vrj = get('VD RJ route')
vrj_js = vrj['parameters']['jsCode']
assert anchor in vrj_js, "VD RJ route: state-якорь не найден"
vrj_js = vrj_js.replace(anchor,
                        anchor + "\nconst aa = Number(rows[0] && rows[0].auto_approve) || 0;\n"
                        "if (aa === 1 && state === 'VIDEO_AWAIT' && String(qp.generation_id || '')) {\n"
                        "  return [{ json: { mode: 'publish', chat_id: p.chat_id, generation_id: String(qp.generation_id) } }];\n"
                        "}", 1)
vrj['parameters']['jsCode'] = vrj_js

# Switch VD RG / VD RJ += publish → VD OK Build session
for sw_name, fallback in (('Switch VD RG', 'VD RG Format err'), ('Switch VD RJ', 'VD RJ Format err')):
    sw = get(sw_name)
    sw['parameters']['rules']['values'].append({
        "conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                       "conditions": [{"leftValue": "={{ $json.mode }}", "rightValue": "publish",
                                       "operator": {"type": "string", "operation": "equals"}}], "combinator": "and"}})
    sw_main = conns[sw_name]['main']
    assert sw_main[-1] == [{"node": fallback, "type": "main", "index": 0}], f"{sw_name} fallback не {fallback}"
    fb = sw_main.pop(-1)
    sw_main.append([{"node": "VD OK Build session", "type": "main", "index": 0}])
    sw_main.append(fb)

# VD OK Build session: generation_id из item (VD OK route | VD RG/VD RJ publish)
vdok = get('VD OK Build session')
vdok_js = vdok['parameters']['jsCode']
assert "const r = $('VD OK route').first().json;" in vdok_js, "VD OK Build session: чтение VD OK route не найдено"
vdok_js = vdok_js.replace("const r = $('VD OK route').first().json;", "const r = $input.first().json || {};")
vdok['parameters']['jsCode'] = vdok_js

# ---------------------------------------------------------------- 7. SC ED: авто → ✅ (новая цепочка)
add_node("SC ED read", "n8n-nodes-base.code", 2, [600, 5200],
         {"mode": "runOnceForAllItems", "language": "javaScript",
          "jsCode": "const p = $('Parser').first().json;\nreturn [{ json: { sql: \"" + READ_SQL + "\", params: [p.tg_user_id, p.tg_user_id] } }];"})
add_node("SC ED HTTP", "n8n-nodes-base.httpRequest", 4.5, [880, 5200], dict(HTTP_PARAMS))
add_node("SC ED route", "n8n-nodes-base.code", 2, [1160, 5200],
         {"mode": "runOnceForAllItems", "language": "javaScript",
          "jsCode": "const p = $('Parser').first().json;\nconst rows = $('SC ED HTTP').first().json.rows || [];\nconst qp = (() => { try { return JSON.parse((rows[0] && rows[0].quick_payload) || '{}'); } catch (e) { return {}; } })();\nconst state = (rows[0] && rows[0].state) || '';\nconst aa = Number(rows[0] && rows[0].auto_approve) || 0;\nif (aa === 1 && state === 'SCRIPT_AWAIT' && qp.flow) {\n  const script = String(qp.script || '').trim();\n  if (!script) return [{ json: { mode: 'err', chat_id: p.chat_id, text: '⚠️ Сценарий не найден или устарел. Запусти генерацию заново.' } }];\n  if (qp.flow === 'au') {\n    return [{ json: { mode: 'au_video', chat_id: p.chat_id, script: script, topic_id: Number(qp.topic_id) || null, script_full: (qp.script_full && typeof qp.script_full === 'object') ? qp.script_full : { full_text: script }, source_url: String(qp.source_url || ''), video_length: Number(qp.video_length) || 30 } }];\n  }\n  return [{ json: { mode: 'sh_video', chat_id: p.chat_id, script: script, topic: String(qp.topic || '') } }];\n}\nreturn [{ json: { mode: 'edit', chat_id: p.chat_id } }];"})
add_node("Switch SC ED", "n8n-nodes-base.switch", 3.4, [1440, 5200],
         {"mode": "rules", "rules": {"values": [{"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"}, "conditions": [{"leftValue": "={{ $json.mode }}", "rightValue": "edit", "operator": {"type": "string", "operation": "equals"}}], "combinator": "and"}}]}, "options": {"fallbackOutput": "extra"}})

set_conn_target('SC ED answer', 0, 'SC ED read')
add_conn('SC ED read', 0, 'SC ED HTTP')
add_conn('SC ED HTTP', 0, 'SC ED route')
add_conn('SC ED route', 0, 'Switch SC ED')
add_conn('Switch SC ED', 0, 'SC ED format')
add_conn('Switch SC ED', 1, 'Switch SC OK')

# ---------------------------------------------------------------- write
out = json.dumps(wf, ensure_ascii=False, indent=1) + '\n'
open(PATH, 'w', encoding='utf-8').write(out)
print("OK nodes:", len(nodes))
