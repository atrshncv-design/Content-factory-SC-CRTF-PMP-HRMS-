#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Фикс URL→видео v2: FK constraint (db-bridge включает foreign_keys, в отличие от CLI!).
0-сентинель для scripts.topic_id НЕ работает (REFERENCES topics(id) enforced).
Решение: новый узел DU Build topic + DU HTTP topic (INSERT INTO topics), DU Build script
читает lastInsertRowid темы. GE/SC откатываются к исходным формам (у них темы гарантированы потоком).
"""
import json, uuid

TGBOT = 'workflows/wf-tg-bot.json'

raw = open(TGBOT, encoding='utf-8').read()
data = json.loads(raw)
data = data[0] if isinstance(data, list) else data
nodes = data['nodes']
conn = data['connections']
by_name = {n['name']: n for n in nodes}

def node(name):
    return by_name[name]

# ---------- 1) DU Build topic (Code) + DU HTTP topic (HTTP) ----------
build_script = node('DU Build script')
http_script = node('DU HTTP script')
px, py = build_script['position']

build_topic = {
    "parameters": {
        "mode": "runOnceForAllItems",
        "language": "javaScript",
        "jsCode": "\nconst st = $('DU Parse state').first().json;\nconst s = $('DU HTTP settings').first().json;\nconst row = (s.rows || [])[0] || {};\nconst clientId = Number(row.ac_id) || 0;\nconst url = String(st.url || '').trim();\nreturn [{ json: { sql: \"INSERT INTO topics (client_id, cycle_date, title, source_url, status) VALUES (?, date('now'), ?, ?, 'pending')\", params: [clientId, url, url] } }];\n"
    },
    "id": str(uuid.uuid4()),
    "name": "DU Build topic",
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [px - 120, py],
}

http_topic = {
    "parameters": json.loads(json.dumps(http_script['parameters'])),
    "id": str(uuid.uuid4()),
    "name": "DU HTTP topic",
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.5,
    "position": [px - 60, py],
}

nodes.append(build_topic)
nodes.append(http_topic)
by_name['DU Build topic'] = build_topic
by_name['DU HTTP topic'] = http_topic
print('nodes added: DU Build topic, DU HTTP topic')

# ---------- 2) DU Build script: читать topic_id из DU HTTP topic ----------
js = build_script['parameters']['jsCode']
old = "const s = $('DU HTTP settings').first().json;\nconst row = (s.rows || [])[0] || {};\nconst clientId = Number(row.ac_id) || 0;\nconst fullText = 'Ролик из ссылки: ' + st.url;\nreturn [{ json: { sql: \"INSERT INTO scripts (client_id, topic_id, hook, body, cta, target_length, format_tag, full_text, status) VALUES (?, 0, '', '', '', ?, 'user', ?, 'pending')\", params: [clientId, Number(st.dur), fullText] } }];"
new = "const s = $('DU HTTP settings').first().json;\nconst t = $('DU HTTP topic').first().json;\nconst row = (s.rows || [])[0] || {};\nconst clientId = Number(row.ac_id) || 0;\nconst topicId = Number(t.lastInsertRowid) || 0;\nconst fullText = 'Ролик из ссылки: ' + st.url;\nreturn [{ json: { sql: \"INSERT INTO scripts (client_id, topic_id, hook, body, cta, target_length, format_tag, full_text, status) VALUES (?, ?, '', '', '', ?, 'user', ?, 'pending')\", params: [clientId, topicId, Number(st.dur), fullText] } }];"
assert old in js, 'DU Build script: jsCode не найден'
build_script['parameters']['jsCode'] = js.replace(old, new)
print('DU Build script: OK (topic_id из DU HTTP topic)')

# ---------- 3) перекоммутация: settings -> Build topic -> HTTP topic -> Build script ----------
conn['DU HTTP settings']['main'][0][0]['node'] = 'DU Build topic'
conn['DU Build topic'] = {"main": [[{"node": "DU HTTP topic", "type": "main", "index": 0}]]}
conn['DU HTTP topic'] = {"main": [[{"node": "DU Build script", "type": "main", "index": 0}]]}
print('connections: OK')

# ---------- 4) откат GE/SC (0-сентинель падает с FK; у них темы гарантированы) ----------
ge = node('GE Build insert')
js = ge['parameters']['jsCode']
old = "SELECT 1, COALESCE(topic_id, 0), '', '', '', 30, 'user', ?, 'pending' FROM sessions WHERE tg_user_id = ?"
assert old in js, 'GE Build insert: SQL не найден'
ge['parameters']['jsCode'] = js.replace(old, "SELECT 1, topic_id, '', '', '', 30, 'user', ?, 'pending' FROM sessions WHERE tg_user_id = ?")
print('GE Build insert: revert OK')

sc = node('SC Cont build')
js = sc['parameters']['jsCode']
old = "const topicId = Number(item.topic_id) || 0;"
assert old in js, 'SC Cont build: topicId не найден'
sc['parameters']['jsCode'] = js.replace(old, "const topicId = Number(item.topic_id) || null;")
print('SC Cont build: revert OK')

out = json.dumps([data], ensure_ascii=False, indent=1) + '\n'
open(TGBOT, 'w', encoding='utf-8').write(out)
print('wf-tg-bot.json: OK')
