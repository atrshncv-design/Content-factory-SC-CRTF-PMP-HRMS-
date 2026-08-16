#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Тикет 13: выбор длительности 30/60 для AI Shorts.
wf-tg-bot: SH Ask dur (после темы) -> кнопки 30/60 -> SH Dur apply -> цепочка генерации.
Switch cmd 'dur' перехватывается SH Dur check/dispatch (по состоянию QUICK_SHORTS_AWAIT_DUR).
SH Update state/SHT HTTP/SC OK route — проброс video_length.
wf-creatify-shorts: video_length {30,60}, Exp prompt слова = vl*2.
"""
import json, uuid

F = 'workflows/wf-tg-bot.json'
d = json.load(open(F))
d = d[0] if isinstance(d, list) else d
nodes = d['nodes']
conn = d['connections']
by_name = {n['name']: n for n in nodes}

def node(name):
    return by_name[name]

# ---------- 1) SC OK route: sh_video + video_length ----------
n = node('SC OK route')
js = n['parameters']['jsCode']
old = "return [{ json: { mode: 'sh_video', chat_id: p.chat_id, script: script, topic: String(qp.topic || '') } }];"
new = "return [{ json: { mode: 'sh_video', chat_id: p.chat_id, script: script, topic: String(qp.topic || ''), video_length: Number(qp.video_length) || 30 } }];"
assert old in js, 'SC OK route: sh_video не найден'
n['parameters']['jsCode'] = js.replace(old, new)
print('SC OK route: video_length добавлен')

# ---------- 2) SH Update state: video_length + topic fallback ----------
n = node('SH Update state')
js = n['parameters']['jsCode']
old = """const p = $('Parser').first().json;
const item = $input.first().json || {};
let topic = String(item.topic || '').trim();
if (!topic) {
  try { const t = $('SH Topic').first().json; topic = String(t.topic || '').trim(); } catch (e) {}
}
const script = (item.script !== undefined && item.script !== null && String(item.script).trim() !== '')
  ? String(item.script).trim() : null;
const attempts = Number(item.attempts) || 1;
const mode = script ? 'video' : 'script_only';
const payload = { topic: topic, script: script, mode: mode, attempts: attempts, auto_approve: 0 };
return [{ json: { sql: "UPDATE sessions SET state='QUICK_SHORTS_GENERATING', quick_payload=json_set(?, '$.auto_approve', COALESCE((SELECT auto_approve FROM users WHERE tg_user_id = ?), 0)), updated_at=datetime('now') WHERE tg_user_id = ?", params: [JSON.stringify(payload), p.tg_user_id, p.tg_user_id], topic: topic, script: script, mode: mode, attempts: attempts } }];"""
new = """const p = $('Parser').first().json;
const item = $input.first().json || {};
let topic = String(item.topic || '').trim();
if (!topic) {
  try { const t = $('SH Topic').first().json; topic = String(t.topic || '').trim(); } catch (e) {}
}
if (!topic) {
  try { const dd = $('SH Dur apply').first().json; topic = String(dd.topic || '').trim(); } catch (e) {}
}
const script = (item.script !== undefined && item.script !== null && String(item.script).trim() !== '')
  ? String(item.script).trim() : null;
const attempts = Number(item.attempts) || 1;
const mode = script ? 'video' : 'script_only';
const videoLength = Number(item.video_length) || (() => { try { return Number($('SH Dur apply').first().json.video_length) || 30; } catch (e) { return 30; } })();
const payload = { topic: topic, script: script, mode: mode, attempts: attempts, auto_approve: 0, video_length: videoLength };
return [{ json: { sql: "UPDATE sessions SET state='QUICK_SHORTS_GENERATING', quick_payload=json_set(?, '$.auto_approve', COALESCE((SELECT auto_approve FROM users WHERE tg_user_id = ?), 0)), updated_at=datetime('now') WHERE tg_user_id = ?", params: [JSON.stringify(payload), p.tg_user_id, p.tg_user_id], topic: topic, script: script, mode: mode, attempts: attempts, video_length: videoLength } }];"""
assert old in js, 'SH Update state: jsCode не найден'
n['parameters']['jsCode'] = js.replace(old, new)
print('SH Update state: video_length/topic-fallback')

# ---------- 3) SHT HTTP jsonBody: video_length ----------
n = node('SHT HTTP')
jb = n['parameters']['jsonBody']
old = "  const script = String((u && u.script) || '').trim();\n  if (script) return { script: script, aspect_ratio: '9:16', style: 'auto', webhook_url: webhook };\n  return { topic: String((u && u.topic) || ''), mode: 'script_only' };"
new = "  const script = String((u && u.script) || '').trim();\n  const vl = Number((u && u.video_length) || 30);\n  if (script) return { script: script, aspect_ratio: '9:16', style: 'auto', webhook_url: webhook, video_length: vl };\n  return { topic: String((u && u.topic) || ''), mode: 'script_only', video_length: vl };"
assert old in jb, 'SHT HTTP: jsonBody не найден'
n['parameters']['jsonBody'] = jb.replace(old, new)
print('SHT HTTP: video_length')

# ---------- 4) новые узлы ----------
sh_topic = node('SH Topic')
tg_uv = node('TG uv ask dur')  # шаблон кнопок (уже без 90)
du_check = node('DU Check state')

ask_dur = {
    "parameters": {"mode": "runOnceForAllItems", "language": "javaScript",
        "jsCode": "\nconst p = $('Parser').first().json;\nconst item = $input.first().json || {};\nlet topic = String(item.topic || '').trim();\nif (!topic) { try { const t = $('SH Topic').first().json; topic = String(t.topic || '').trim(); } catch (e) {} }\nconst esc = s => String(s ?? '').replace(/([_*[\\]`])/g, '\\\\$1');\nconst text = '⏱ Длительность шортса: 30 сек — 5 кред · 60 сек — 10 кред';\nreturn [{ json: { sql: \"UPDATE sessions SET state='QUICK_SHORTS_AWAIT_DUR', quick_payload=?, updated_at=datetime('now') WHERE tg_user_id=?\", params: [JSON.stringify({ topic: topic }), p.tg_user_id], chat_id: p.chat_id, text: esc(text) } }];\n"},
    "id": str(uuid.uuid4()), "name": "SH Ask dur", "type": "n8n-nodes-base.code", "typeVersion": 2,
    "position": [sh_topic['position'][0] + 60, sh_topic['position'][1] + 400],
}
tg_ask = {
    "parameters": json.loads(json.dumps(tg_uv['parameters'])),
    "id": str(uuid.uuid4()), "name": "TG sh ask dur", "type": "n8n-nodes-base.telegram", "typeVersion": 1.2,
    "position": [ask_dur['position'][0] + 60, ask_dur['position'][1]],
    "credentials": json.loads(json.dumps(tg_uv['credentials'])),
}
dur_check = {
    "parameters": {"mode": "runOnceForAllItems", "language": "javaScript",
        "jsCode": "\nconst p = $('Parser').first().json;\nreturn [{ json: { sql: 'SELECT state, quick_payload FROM sessions WHERE tg_user_id = ?', params: [p.tg_user_id] } }];\n"},
    "id": str(uuid.uuid4()), "name": "SH Dur check", "type": "n8n-nodes-base.code", "typeVersion": 2,
    "position": [du_check['position'][0] - 700, du_check['position'][1] + 500],
}
dur_state = {
    "parameters": {"method": "POST", "url": "http://db-bridge:8787/query", "sendHeaders": True,
        "headerParameters": {"parameters": [{"name": "X-BRIDGE-TOKEN", "value": "={{ $env.FACTORY_DB_BRIDGE_TOKEN }}"}]},
        "sendBody": True, "contentType": "json", "specifyBody": "json", "jsonBody": "={{ $json }}",
        "options": {"timeout": 15000}},
    "id": str(uuid.uuid4()), "name": "SH HTTP dur state", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.5,
    "position": [dur_check['position'][0] + 60, dur_check['position'][1]],
}
dur_dispatch = {
    "parameters": {"mode": "runOnceForAllItems", "language": "javaScript",
        "jsCode": "\nconst p = $('Parser').first().json;\nconst rows = $('SH HTTP dur state').first().json.rows || [];\nconst state = (rows[0] && rows[0].state) || 'IDLE';\nconst dur = Number(p.args.value) || 0;\nif (state === 'QUICK_SHORTS_AWAIT_DUR') {\n  return [{ json: { route: (dur === 30 || dur === 60) ? 'shorts_ok' : 'shorts_wrong', chat_id: p.chat_id, dur: dur } }];\n}\nreturn [{ json: { route: 'du', chat_id: p.chat_id } }];\n"},
    "id": str(uuid.uuid4()), "name": "SH Dur dispatch", "type": "n8n-nodes-base.code", "typeVersion": 2,
    "position": [dur_state['position'][0] + 60, dur_state['position'][1]],
}
switch_dur = {
    "parameters": {"mode": "rules", "rules": {"values": [
        {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
            "conditions": [{"leftValue": "={{ $json.route }}", "rightValue": "shorts_ok", "operator": {"type": "string", "operation": "equals"}}], "combinator": "and"}},
        {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
            "conditions": [{"leftValue": "={{ $json.route }}", "rightValue": "shorts_wrong", "operator": {"type": "string", "operation": "equals"}}], "combinator": "and"}},
    ]}, "options": {"fallbackOutput": "extra"}},
    "id": str(uuid.uuid4()), "name": "Switch SH dur", "type": "n8n-nodes-base.switch", "typeVersion": 3.4,
    "position": [dur_dispatch['position'][0] + 60, dur_dispatch['position'][1]],
}
dur_apply = {
    "parameters": {"mode": "runOnceForAllItems", "language": "javaScript",
        "jsCode": "\nconst p = $('Parser').first().json;\nconst rows = $('SH HTTP dur state').first().json.rows || [];\nlet qp = {};\ntry { qp = JSON.parse((rows[0] && rows[0].quick_payload) || '{}'); } catch (e) { qp = {}; }\nconst dur = Number(p.args.value) || 30;\nconst topic = String(qp.topic || '').trim();\nreturn [{ json: { sql: \"UPDATE sessions SET state='QUICK_SHORTS_GENERATING', quick_payload=json_set(?, '$.video_length', ?), updated_at=datetime('now') WHERE tg_user_id=?\", params: [JSON.stringify({ topic: topic, video_length: dur }), dur, p.tg_user_id], topic: topic, video_length: dur, chat_id: p.chat_id } }];\n"},
    "id": str(uuid.uuid4()), "name": "SH Dur apply", "type": "n8n-nodes-base.code", "typeVersion": 2,
    "position": [switch_dur['position'][0] + 60, switch_dur['position'][1]],
}
for n in (ask_dur, tg_ask, dur_check, dur_state, dur_dispatch, switch_dur, dur_apply):
    nodes.append(n)
    by_name[n['name']] = n
print('nodes added: SH Ask dur, TG sh ask dur, SH Dur check, SH HTTP dur state, SH Dur dispatch, Switch SH dur, SH Dur apply')

# ---------- 5) коммутация ----------
conn['SH Topic']['main'][0][0]['node'] = 'SH Ask dur'
conn['SH Ask dur'] = {"main": [[{"node": "TG sh ask dur", "type": "main", "index": 0}]]}
conn['SH Dur check'] = {"main": [[{"node": "SH HTTP dur state", "type": "main", "index": 0}]]}
conn['SH HTTP dur state'] = {"main": [[{"node": "SH Dur dispatch", "type": "main", "index": 0}]]}
conn['SH Dur dispatch'] = {"main": [[{"node": "Switch SH dur", "type": "main", "index": 0}]]}
conn['Switch SH dur'] = {"main": [
    [{"node": "SH Dur apply", "type": "main", "index": 0}],
    [{"node": "TG sh ask dur", "type": "main", "index": 0}],
    [{"node": "DU Check state", "type": "main", "index": 0}],
]}
conn['SH Dur apply'] = {"main": [[{"node": "SH LB creatify", "type": "main", "index": 0}]]}
# Switch cmd 'dur' -> SH Dur check
cmd_vals = node('Switch cmd')['parameters']['rules']['values']
cmd_main = conn['Switch cmd']['main']
for i, v in enumerate(cmd_vals):
    rv = [c.get('rightValue','') for c in v['conditions']['conditions']]
    if rv and rv[0] == 'dur':
        cmd_main[i][0]['node'] = 'SH Dur check'
        print('Switch cmd: dur -> SH Dur check')
        break
print('connections: OK')

out = json.dumps([d], ensure_ascii=False, indent=1) + '\n'
open(F, 'w', encoding='utf-8').write(out)
print('wf-tg-bot.json: OK (тикет 13)')
