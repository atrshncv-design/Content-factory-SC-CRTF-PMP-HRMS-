#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Фикс URL→видео v3: сессия не привязана к генерации (вебхук: 'Сессия не привязана к генерации #N').
DU success-ветка (Switch DU submit out0) была ПУСТОЙ — нет ни подтверждения, ни session-link.
Добавляем: DU Build gen link -> DU HTTP gen link (UPDATE sessions SET generation_id, script_id)
-> DU Format ok -> TG du ok.
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

# --- шаблоны ---
tg_du_gen = node('TG du gen')          # telegram-нода
du_format_gen = node('DU Format gen')  # code-форматтер (позиция)
du_parse_submit = node('DU Parse submit')
px, py = du_parse_submit['position']

# 1) DU Build gen link (Code)
build_link = {
    "parameters": {
        "mode": "runOnceForAllItems",
        "language": "javaScript",
        "jsCode": "\nconst p = $('Parser').first().json;\nconst sub = $('DU Parse submit').first().json;\nconst scriptId = Number($('DU HTTP script').first().json.lastInsertRowid) || 0;\nreturn [{ json: { sql: \"UPDATE sessions SET state='QUICK_URL_GENERATING', generation_id=?, script_id=COALESCE(script_id, ?), updated_at=datetime('now') WHERE tg_user_id=?\", params: [String(sub.generation_id), scriptId, p.tg_user_id] } }];\n"
    },
    "id": str(uuid.uuid4()),
    "name": "DU Build gen link",
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [px + 120, py],
}

# 2) DU HTTP gen link (HTTP, как SH HTTP gen link)
http_link = {
    "parameters": {
        "method": "POST",
        "url": "http://db-bridge:8787/query",
        "sendHeaders": True,
        "headerParameters": {"parameters": [
            {"name": "Content-Type", "value": "application/json"},
            {"name": "X-BRIDGE-TOKEN", "value": "={{ $env.FACTORY_DB_BRIDGE_TOKEN }}"}
        ]},
        "sendBody": True,
        "contentType": "json",
        "specifyBody": "json",
        "jsonBody": "={{ $json }}",
        "options": {"timeout": 15000, "response": {"response": {"neverError": True}}}
    },
    "id": str(uuid.uuid4()),
    "name": "DU HTTP gen link",
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.5,
    "position": [px + 180, py],
}

# 3) DU Format ok (Code)
format_ok = {
    "parameters": {
        "mode": "runOnceForAllItems",
        "language": "javaScript",
        "jsCode": "\nconst p = $('Parser').first().json;\nconst sub = $('DU Parse submit').first().json;\nconst esc = s => String(s ?? '').replace(/([_*[\\]`])/g, '\\\\$1');\nconst text = '✅ Генерация запущена (id ' + esc(sub.generation_id) + ', creatify ' + esc(String(sub.creatify_id).slice(0, 8)) + '…). Пришлю видео сюда, как creatify ответит.';\nreturn [{ json: { chat_id: p.chat_id, text: text } }];\n"
    },
    "id": str(uuid.uuid4()),
    "name": "DU Format ok",
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [px + 240, py],
}

# 4) TG du ok (Telegram — клон TG du gen)
tg_ok = {
    "parameters": json.loads(json.dumps(tg_du_gen['parameters'])),
    "id": str(uuid.uuid4()),
    "name": "TG du ok",
    "type": "n8n-nodes-base.telegram",
    "typeVersion": 1.2,
    "position": [px + 300, py],
    "credentials": json.loads(json.dumps(tg_du_gen['credentials'])),
}

for n in (build_link, http_link, format_ok, tg_ok):
    nodes.append(n)
    by_name[n['name']] = n
print("nodes added: DU Build gen link, DU HTTP gen link, DU Format ok, TG du ok")

# --- коммутация: Switch DU submit out0 (был пустой) ---
assert conn['Switch DU submit']['main'][0] == [], "Switch DU submit out0 не пуст!"
conn['Switch DU submit']['main'][0] = [{"node": "DU Build gen link", "type": "main", "index": 0}]
conn['DU Build gen link'] = {"main": [[{"node": "DU HTTP gen link", "type": "main", "index": 0}]]}
conn['DU HTTP gen link'] = {"main": [[{"node": "DU Format ok", "type": "main", "index": 0}]]}
conn['DU Format ok'] = {"main": [[{"node": "TG du ok", "type": "main", "index": 0}]]}
print("connections: OK (Switch DU submit out0 -> gen link -> format ok -> tg ok)")

out = json.dumps([data], ensure_ascii=False, indent=1) + '\n'
open(TGBOT, 'w', encoding='utf-8').write(out)
print('wf-tg-bot.json: OK')
