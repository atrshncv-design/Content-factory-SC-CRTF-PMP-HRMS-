#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Трансформер A2-auto-mode: ветвление цикла wf-tg-bot по settings.mode (auto).
База: fixes/wf-tg-bot.json (результат A1-fix2, 430 нод). Результат: тот же файл (перезапись).
Читает → мутирует → пишет (перезапускаемый, идемпотентный по именам новых нод).

Изменяемые существующие связи (5):
  1. SC HTTP wf-analytics out[0]: SC Build bridge prompt  → SC Check analytics (new)
  2. Switch SC parse out[1]:      TG no candidates        → AU2 Build settings (new)
  3. SC HTTP set topic out[0]:    SC Stage1 Format        → AU Build settings (new)
  4. PG HTTP session out[0]:      PG Stage4 Format        → AUP Build settings (new)
Изменяемый параметр (1):
  5. SC HTTP wf-analytics: options += response.response.neverError=true (Y6; auto-ошибки не виснут)

Новые ноды (56): три режимных трио (AU/AU2/AUP), SC Check analytics + Switch,
AU topic->script->generation chain (12), AU script->gen chain (17), error alert chain (4),
publish chain (13), switch-ы ветвления.
Сериализация: json.dumps(indent=1, ensure_ascii=False) БЕЗ trailing newline (как base).
"""
import json
import re
import sys
import uuid

BASE = "/Users/aleksandrtrisenkov/Desktop/PROGRAMMING/РАБОЧИЕ ПРОЕКТЫ/КОНТЕНТ-ЗАВОД-API-MVP/.scratch/review-full-14aug/fixes/wf-tg-bot.json"
TG = 941296693

with open(BASE, encoding="utf-8") as fh:
    data = json.load(fh)
wf = data[0] if isinstance(data, list) else data
nodes = wf["nodes"]
by_name = {n["name"]: n for n in nodes}
conns = wf.setdefault("connections", {})

# ---------- байт-точная esc-строка из GD Format (эталон) ----------
gd_js = by_name["GD Format"]["parameters"]["jsCode"]
esc_line = re.search(r"const esc = s =>[^\n]*", gd_js).group(0)

# ---------- шаблоны ----------
def code(name, js, x=0, y=0):
    return {
        "id": str(uuid.uuid4()), "name": name, "type": "n8n-nodes-base.code",
        "typeVersion": 2, "position": [x, y],
        "parameters": {"mode": "runOnceForAllItems", "language": "javaScript", "jsCode": js},
    }

def http_db(name, x=0, y=0):
    return {
        "id": str(uuid.uuid4()), "name": name, "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.5, "position": [x, y],
        "parameters": {
            "method": "POST", "url": "http://db-bridge:8787/query",
            "sendHeaders": True,
            "headerParameters": {"parameters": [{"name": "X-BRIDGE-TOKEN", "value": "={{ $env.FACTORY_DB_BRIDGE_TOKEN }}"}]},
            "sendBody": True, "contentType": "json", "specifyBody": "json",
            "jsonBody": "={{ $json }}", "options": {"timeout": 15000},
        },
    }

def http_bridge(name, x=0, y=0):
    return {
        "id": str(uuid.uuid4()), "name": name, "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.5, "position": [x, y],
        "parameters": {
            "method": "POST", "url": "http://host.docker.internal:8642/ask",
            "sendHeaders": True,
            "headerParameters": {"parameters": [{"name": "X-BRIDGE-TOKEN", "value": "={{ $env.HERMES_BRIDGE_TOKEN }}"}]},
            "sendBody": True, "contentType": "json", "specifyBody": "json",
            "jsonBody": "={{ $json }}", "options": {"timeout": 300000},
        },
    }

def http_webhook(name, url, timeout, x=0, y=0):
    return {
        "id": str(uuid.uuid4()), "name": name, "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.5, "position": [x, y],
        "parameters": {
            "method": "POST", "url": url,
            "sendBody": True, "contentType": "json", "specifyBody": "json",
            "jsonBody": "={{ $json }}",
            "options": {"timeout": timeout, "response": {"response": {"neverError": True}}},
        },
    }

def switch(name, left_value, right_value, op_type="string", x=0, y=0):
    return {
        "id": str(uuid.uuid4()), "name": name, "type": "n8n-nodes-base.switch",
        "typeVersion": 3.4, "position": [x, y],
        "parameters": {
            "mode": "rules",
            "rules": {"values": [{
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                    "conditions": [{
                        "leftValue": "={{ " + left_value + " }}",
                        "rightValue": right_value,
                        "operator": {"type": op_type, "operation": "equals"},
                    }],
                    "combinator": "and",
                }
            }]},
            "options": {"fallbackOutput": "extra"},
        },
    }

def tg_msg(name, x=0, y=0):
    return {
        "id": str(uuid.uuid4()), "name": name, "type": "n8n-nodes-base.telegram",
        "typeVersion": 1.2, "position": [x, y],
        "credentials": {"telegramApi": {"id": "10000000-0000-4000-8000-000000000004", "name": "telegram"}},
        "parameters": {
            "resource": "message", "operation": "sendMessage",
            "chatId": "={{ $('Parser').first().json.chat_id }}",
            "text": "={{ $json.text }}",
            "additionalFields": {"appendAttribution": False},
            "inlineKeyboard": {"rows": [{"row": {"buttons": [{"text": "📋 Меню", "additionalFields": {"callback_data": "cmd:menu"}}]}}]},
        },
    }

def out(node_name):
    return {"node": node_name}

new_nodes = []
def add(n):
    assert n["name"] not in by_name, "дубль имени: " + n["name"]
    new_nodes.append(n)
    by_name[n["name"]] = n

# ---------- jsCode-ы (esc — байт-точно из GD Format) ----------
js_au_settings = "\nreturn [{ json: { sql: \"SELECT key, value FROM settings WHERE key = 'mode'\", params: [] } }];\n"
js_au2_settings = "\nconst t = $json.text || '';\nreturn [{ json: { sql: \"SELECT key, value FROM settings WHERE key = 'mode'\", params: [], text: t } }];\n"
js_au_check = "\nconst rows = $('AU HTTP settings').first().json.rows || [];\nconst mode = (rows[0] && rows[0].value) || 'manual';\nreturn [{ json: { mode: mode } }];\n"
js_aup_check = "\nconst rows = $('AUP HTTP settings').first().json.rows || [];\nconst mode = (rows[0] && rows[0].value) || 'manual';\nreturn [{ json: { mode: mode } }];\n"
js_au2_check = "\nconst rows = $('AU2 HTTP settings').first().json.rows || [];\nconst mode = (rows[0] && rows[0].value) || 'manual';\nconst t = $('AU2 Build settings').first().json.text || '⚠️ Ошибка в автоматическом цикле';\nreturn [{ json: { mode: mode, text: t } }];\n"

js_sc_check_analytics = (
    "\nconst r = $('SC HTTP wf-analytics').first().json;\n"
    "const cands = (r && Array.isArray(r.candidates)) ? r.candidates : [];\n"
    "if (!r || r.error || !cands.length) {\n"
    "  return [{ json: { ok: false, text: '⚠️ Аналитика не ответила или кандидатов нет. Попробуй /start_cycle позже.' } }];\n"
    "}\n"
    "return [{ json: { ok: true } }];\n"
)

js_au_approve_topic = (
    "\nconst id = Number($('SC HTTP insert topic').first().json.lastInsertRowid);\n"
    "return [{ json: { sql: \"UPDATE topics SET status = 'approved', chosen = 1, approved_at = datetime('now'), approved_by = ? WHERE id = ?\", params: [941296693, id] } }];\n"
)
js_au_session = (
    "\nconst id = Number($('SC HTTP insert topic').first().json.lastInsertRowid);\n"
    "return [{ json: { sql: \"UPDATE sessions SET state = 'CYCLE_SCRIPT_PENDING', topic_id = ?, updated_at = datetime('now') WHERE tg_user_id = ?\", params: [id, 941296693] } }];\n"
)
js_au_prompt = (
    "\nconst topic = $('SC Parse topic').first().json;\n"
    "const prompt = 'Напиши сценарий короткого вертикального видео (30 сек, ~65 слов, русский) для клиента Robotec (промышленная робототехника, интегратор KUKA; тон: экспертно-деловой, ROI, окупаемость).\\nТема: ' + (topic.title || '') + '\\nИсточник: ' + (topic.source_url || '') + '\\nРационале: ' + (topic.rationale || '') + '\\n\\nВерни строго JSON: {\"hook\", \"body\", \"cta\", \"full_text\", \"target_length_sec\", \"estimated_words\", \"format_tag\", \"notes\"}. Без markdown.';\n"
    "return [{ json: { skill: 'scriptwriter', prompt: prompt } }];\n"
)
js_au_parse_script = by_name["CT Parse script"]["parameters"]["jsCode"].replace("$('CT HTTP bridge scriptwriter')", "$('AU HTTP bridge scriptwriter')")
js_au_insert_script = (
    "\nconst tid = Number($('SC HTTP insert topic').first().json.lastInsertRowid);\n"
    "const s = $('AU Parse script').first().json;\n"
    "return [{ json: { sql: \"INSERT INTO scripts (client_id, topic_id, hook, body, cta, target_length, format_tag, full_text, status) VALUES (1, ?, ?, ?, ?, ?, ?, ?, 'pending')\", params: [tid, s.hook, s.body, s.cta, s.target_length, s.format_tag, s.full_text] } }];\n"
)
js_au_set_script = (
    "\nconst id = Number($('AU HTTP insert script').first().json.lastInsertRowid);\n"
    "return [{ json: { sql: \"UPDATE sessions SET script_id = ?, updated_at = datetime('now') WHERE tg_user_id = ?\", params: [id, 941296693] } }];\n"
)
js_au_approve_script = (
    "\nconst id = Number($('AU HTTP insert script').first().json.lastInsertRowid);\n"
    "return [{ json: { sql: \"UPDATE scripts SET status = 'approved', approved_at = datetime('now'), approved_by = ? WHERE id = ?\", params: [941296693, id] } }];\n"
)
js_au_session_gen = (
    "\nconst id = Number($('AU HTTP insert script').first().json.lastInsertRowid);\n"
    "return [{ json: { sql: \"UPDATE sessions SET state = 'CYCLE_GENERATION_PENDING', script_id = ?, updated_at = datetime('now') WHERE tg_user_id = ?\", params: [id, 941296693] } }];\n"
)
js_au_link_body = (
    "\nconst t = $('SC Parse topic').first().json;\n"
    "const raw = String(t.source_url || '').trim();\n"
    "if (!raw || !/^https?:\\/\\/[^\\s]+$/i.test(raw)) {\n"
    "  return [{ json: { ok: false, text: '❌ У темы нет source_url (http/https) — генерация невозможна. Цикл остановлен.' } }];\n"
    "}\n"
    "return [{ json: { ok: true, valid: true, url: raw } }];\n"
)
js_au_check_link = (
    "\nconst r = $json;\n"
    "const b = (r.body && typeof r.body === 'object') ? r.body : r;\n"
    "const linkId = String(b.link_id || r.link_id || '');\n"
    "if (!linkId) return [{ json: { ok: false, text: '⚠️ creatify-link не вернул link_id. Цикл остановлен.' } }];\n"
    "return [{ json: { ok: true, link_id: linkId } }];\n"
)
js_au_prompt_json = (
    "\nconst linkId = $('AU Check link').first().json.link_id || '';\n"
    "const script = $('AU Parse script').first().json;\n"
    "const prompt = 'Собери валидный JSON для POST /api/link_to_videos (creatify) по сценарию.\\nСценарий: ' + (script.full_text || '') + ' (длина ' + (script.target_length || 30) + ' сек)\\nlink (UUID): ' + linkId + '\\nwebhook_url: __WEBHOOK_URL__/webhook/factory/creatify/6d8f2a41c9e7b3d5f0a1c4e8\\nvoice: русский экспертный; avatar: не задан; язык: ru; aspect_ratio: 9x16; target_platform: Instagram; model_version: aurora_v1_fast.\\nВерни ТОЛЬКО JSON payload (name, link, visual_style, script_style, aspect_ratio, video_length, language, target_audience, target_platform, model_version, override_script, webhook_url). Без markdown.';\n"
    "return [{ json: { skill: 'json-builder', prompt: prompt } }];\n"
)
js_au_parse_payload = by_name["AS Parse payload"]["parameters"]["jsCode"].replace("$('AS HTTP bridge json-builder')", "$('AU HTTP bridge json-builder')")
js_au_submit_body = (
    "\nconst sid = Number($('AU HTTP insert script').first().json.lastInsertRowid);\n"
    "const pl = $('AU Parse payload').first().json;\n"
    "const linkId = $('AU Check link').first().json.link_id || '';\n"
    "return [{ json: { script_id: sid, client_id: 1, json_payload: pl.payload, link_id: String(linkId) } }];\n"
)
js_au_check_submit = (
    "\nconst r = $json;\n"
    "const b = (r.body && typeof r.body === 'object') ? r.body : r;\n"
    "const creatifyId = String(b.creatify_id || r.creatify_id || '');\n"
    "const genId = String(b.generation_id || r.generation_id || '');\n"
    "if (!creatifyId || !genId) return [{ json: { ok: false, text: '⚠️ creatify-submit не вернул creatify_id. Цикл остановлен.' } }];\n"
    "return [{ json: { ok: true, creatify_id: creatifyId, generation_id: genId } }];\n"
)
js_au_alert = (
    "\nconst t = $json.text || $json.err || '⚠️ Ошибка в автоматическом цикле. Состояние сброшено в IDLE.';\n"
    "return [{ json: { sql: \"UPDATE sessions SET state = 'IDLE', topic_id = NULL, script_id = NULL, generation_id = NULL, selected_platforms = NULL, post_at = NULL, updated_at = datetime('now') WHERE tg_user_id = ?\", params: [941296693], text: t } }];\n"
)
js_au_format_alert = (
    "\nconst p = $('Parser').first().json;\n" + esc_line + "\n"
    "const t = $('AU Build alert').first().json.text || '⚠️ Ошибка в автоматическом цикле';\n"
    "return [{ json: { chat_id: p.chat_id, text: esc(t) } }];\n"
)
js_au_build_select = (
    "\nreturn [{ json: { sql: \"SELECT s.state, s.selected_platforms, s.post_at, s.generation_id, s.script_id, sc.full_text, g.video_output_url FROM sessions s LEFT JOIN scripts sc ON sc.id = s.script_id LEFT JOIN generations g ON g.id = s.generation_id WHERE s.tg_user_id = ?\", params: [941296693] } }];\n"
)
js_au_check_pub = (
    "\nconst rows = $('AU HTTP select').first().json.rows || [];\n"
    "const row = rows[0] || {};\n"
    "let platforms = [];\n"
    "try { platforms = JSON.parse(row.selected_platforms || '[]'); } catch (e) { platforms = []; }\n"
    "if (!Array.isArray(platforms)) platforms = [];\n"
    "if (!platforms.length) platforms = ['threads'];\n"
    "const postAt = row.post_at || new Date().toISOString();\n"
    "return [{ json: { allow: true, platforms: platforms, post_at: postAt, generation_id: row.generation_id || null, script_id: row.script_id || null, full_text: row.full_text || null, video_output_url: row.video_output_url || null } }];\n"
)
js_au_publish_body = (
    "\nconst c = $('AU Check pub').first().json;\n"
    "const fileIds = (typeof c.video_output_url === 'string' && c.video_output_url.length > 0) ? [c.video_output_url] : [];\n"
    "return [{ json: { platforms: c.platforms, captions: {}, post_at: c.post_at, generation_id: c.generation_id, content: (typeof c.full_text === 'string' ? c.full_text : ''), file_ids: fileIds } }];\n"
)
js_au_check_result = (
    "\nlet r = null;\n"
    "try { r = $('AU HTTP wf-publish').first().json; } catch (e) { r = null; }\n"
    "const resp = (r && typeof r.body === 'object' && r.body) ? r.body : (r || {});\n"
    "if (resp && resp.post_id !== undefined && resp.post_id !== null) {\n"
    "  return [{ json: { ok: true } }];\n"
    "}\n"
    "const e = resp.error;\n"
    "const msg = (typeof e === 'string' && e) ? e : (e && e.message) || 'сервис публикации не ответил';\n"
    "return [{ json: { ok: false, text: '❌ Ошибка публикации: ' + msg } }];\n"
)
js_au_final = (
    "\nreturn [{ json: { sql: \"UPDATE sessions SET state = 'IDLE', selected_platforms = NULL, post_at = NULL, generation_id = NULL, updated_at = datetime('now') WHERE tg_user_id = ?\", params: [941296693] } }];\n"
)

# ---------- создание нод ----------
Y = 0
def row():
    global Y
    Y += 80
    return Y

# --- A: трио режима (SC-ветка, после SC HTTP set topic) ---
add(code("AU Build settings", js_au_settings, 10000, row()))
add(http_db("AU HTTP settings", 10080, row() - 80))
add(code("AU Check", js_au_check, 10160, row() - 160))
add(switch("Switch AU topic", "$json.mode", "auto", "string", 10240, row() - 240))

# --- SC Check analytics (после SC HTTP wf-analytics, никогда+проверка) ---
add(code("SC Check analytics", js_sc_check_analytics, 10320, row()))
add(switch("Switch SC analytics", "$json.ok", True, "boolean", 10400, row() - 80))

# --- AU2: трио режима для no-candidates (после Switch SC parse fallback) ---
add(code("AU2 Build settings", js_au2_settings, 10480, row()))
add(http_db("AU2 HTTP settings", 10560, row() - 80))
add(code("AU2 Check", js_au2_check, 10640, row() - 160))
add(switch("Switch AU nocand", "$json.mode", "auto", "string", 10720, row() - 240))

# --- AU: topic->script chain (mode=auto) ---
add(code("AU Build approve topic", js_au_approve_topic, 10800, row()))
add(http_db("AU HTTP approve", 10880, row() - 80))
add(code("AU Build session", js_au_session, 10960, row() - 160))
add(http_db("AU HTTP session", 11040, row() - 240))
add(code("AU Build prompt", js_au_prompt, 11120, row() - 320))
add(http_bridge("AU HTTP bridge scriptwriter", 11200, row() - 400))
add(code("AU Parse script", js_au_parse_script, 11280, row() - 480))
add(switch("Switch AU parse", "$json.ok", True, "boolean", 11360, row() - 560))
add(code("AU Build insert script", js_au_insert_script, 11440, row() - 640))
add(http_db("AU HTTP insert script", 11520, row() - 720))
add(code("AU Build set script", js_au_set_script, 11600, row() - 800))
add(http_db("AU HTTP set script", 11680, row() - 880))

# --- AU: script->gen chain ---
add(code("AU Build approve script", js_au_approve_script, 11760, row() - 960))
add(http_db("AU HTTP approve script", 11840, row() - 1040))
add(code("AU Build session gen", js_au_session_gen, 11920, row() - 1120))
add(http_db("AU HTTP session gen", 12000, row() - 1200))
add(code("AU Build link body", js_au_link_body, 12080, row() - 1280))
add(switch("Switch AU link", "$json.ok", True, "boolean", 12160, row() - 1360))
add(http_webhook("AU HTTP creatify-link", "http://localhost:5678/webhook/factory/creatify-link", 60000, 12240, row() - 1440))
add(code("AU Check link", js_au_check_link, 12320, row() - 1520))
add(switch("Switch AU linkid", "$json.ok", True, "boolean", 12400, row() - 1600))
add(code("AU Build prompt json", js_au_prompt_json, 12480, row() - 1680))
# json-builder bridge c WEBHOOK_URL-подстановкой (эталон AS HTTP bridge json-builder)
add({
    "id": str(uuid.uuid4()), "name": "AU HTTP bridge json-builder", "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.5, "position": [12560, row() - 1760],
    "parameters": {
        "method": "POST", "url": "http://host.docker.internal:8642/ask",
        "sendHeaders": True,
        "headerParameters": {"parameters": [{"name": "X-BRIDGE-TOKEN", "value": "={{ $env.HERMES_BRIDGE_TOKEN }}"}]},
        "sendBody": True, "contentType": "json", "specifyBody": "json",
        "jsonBody": "={{ { skill: $json.skill, prompt: $json.prompt.split('__WEBHOOK_URL__').join(($env.WEBHOOK_URL || '').replace(/\\/$/, '')) } }}",
        "options": {"timeout": 300000, "response": {"response": {"neverError": True}}},
    },
})
add(code("AU Parse payload", js_au_parse_payload, 12640, row() - 1840))
add(switch("Switch AU payload", "$json.ok", True, "boolean", 12720, row() - 1920))
add(code("AU Build submit body", js_au_submit_body, 12800, row() - 2000))
add(http_webhook("AU HTTP creatify-submit", "http://localhost:5678/webhook/factory/creatify-submit", 300000, 12880, row() - 2080))
add(code("AU Check submit", js_au_check_submit, 12960, row() - 2160))
add(switch("Switch AU submit", "$json.ok", True, "boolean", 13040, row() - 2240))

# --- error alert chain (общая для всех auto-ошибок) ---
add(code("AU Build alert", js_au_alert, 13120, row() - 2320))
add(http_db("AU HTTP alert", 13200, row() - 2400))
add(code("AU Format alert", js_au_format_alert, 13280, row() - 2480))
add(tg_msg("TG AU alert", 13360, row() - 2560))

# --- C: publish chain (PG-ветка, после PG HTTP session) ---
add(code("AUP Build settings", js_au_settings.replace("AU HTTP settings", "AUP HTTP settings"), 13440, row() - 2640))
add(http_db("AUP HTTP settings", 13520, row() - 2720))
add(code("AUP Check", js_aup_check, 13600, row() - 2800))
add(switch("Switch AU pub", "$json.mode", "auto", "string", 13680, row() - 2880))
add(code("AU Build select", js_au_build_select, 13760, row() - 2960))
add(http_db("AU HTTP select", 13840, row() - 3040))
add(code("AU Check pub", js_au_check_pub, 13920, row() - 3120))
add(code("AU Build publish body", js_au_publish_body, 14000, row() - 3200))
add(http_webhook("AU HTTP wf-publish", "http://localhost:5678/webhook/factory/publish", 300000, 14080, row() - 3280))
add(code("AU Check result", js_au_check_result, 14160, row() - 3360))
add(switch("Switch AU pub result", "$json.ok", True, "boolean", 14240, row() - 3440))
add(code("AU Build final", js_au_final, 14320, row() - 3520))
add(http_db("AU HTTP final", 14400, row() - 3600))

# ---------- правки существующих связей ----------
def set_main(src, idx, target):
    arr = conns[src]["main"][idx]
    assert isinstance(arr, list), f"{src} main[{idx}] не список"
    arr[:] = [out(target)]

set_main("SC HTTP wf-analytics", 0, "SC Check analytics")
set_main("Switch SC parse", 1, "AU2 Build settings")
set_main("SC HTTP set topic", 0, "AU Build settings")
set_main("PG HTTP session", 0, "AUP Build settings")

# ---------- новые связи ----------
def link(src, target, out_idx=0):
    conns.setdefault(src, {"main": []})
    main = conns[src]["main"]
    while len(main) <= out_idx:
        main.append([])
    main[out_idx] = [out(target)]

link("SC Check analytics", "Switch SC analytics")
link("Switch SC analytics", "SC Build bridge prompt", 0)
link("Switch SC analytics", "AU2 Build settings", 1)

link("AU Build settings", "AU HTTP settings")
link("AU HTTP settings", "AU Check")
link("AU Check", "Switch AU topic")
link("Switch AU topic", "AU Build approve topic", 0)
link("Switch AU topic", "SC Stage1 Format", 1)

link("AU2 Build settings", "AU2 HTTP settings")
link("AU2 HTTP settings", "AU2 Check")
link("AU2 Check", "Switch AU nocand")
link("Switch AU nocand", "AU Build alert", 0)
link("Switch AU nocand", "TG no candidates", 1)

link("AU Build approve topic", "AU HTTP approve")
link("AU HTTP approve", "AU Build session")
link("AU Build session", "AU HTTP session")
link("AU HTTP session", "AU Build prompt")
link("AU Build prompt", "AU HTTP bridge scriptwriter")
link("AU HTTP bridge scriptwriter", "AU Parse script")
link("AU Parse script", "Switch AU parse")
link("Switch AU parse", "AU Build insert script", 0)
link("Switch AU parse", "AU Build alert", 1)
link("AU Build insert script", "AU HTTP insert script")
link("AU HTTP insert script", "AU Build set script")
link("AU Build set script", "AU HTTP set script")

link("AU HTTP set script", "AU Build approve script")
link("AU Build approve script", "AU HTTP approve script")
link("AU HTTP approve script", "AU Build session gen")
link("AU Build session gen", "AU HTTP session gen")
link("AU HTTP session gen", "AU Build link body")
link("AU Build link body", "Switch AU link")
link("Switch AU link", "AU HTTP creatify-link", 0)
link("Switch AU link", "AU Build alert", 1)
link("AU HTTP creatify-link", "AU Check link")
link("AU Check link", "Switch AU linkid")
link("Switch AU linkid", "AU Build prompt json", 0)
link("Switch AU linkid", "AU Build alert", 1)
link("AU Build prompt json", "AU HTTP bridge json-builder")
link("AU HTTP bridge json-builder", "AU Parse payload")
link("AU Parse payload", "Switch AU payload")
link("Switch AU payload", "AU Build submit body", 0)
link("Switch AU payload", "AU Build alert", 1)
link("AU Build submit body", "AU HTTP creatify-submit")
link("AU HTTP creatify-submit", "AU Check submit")
link("AU Check submit", "Switch AU submit")
link("Switch AU submit", "TG generating", 0)
link("Switch AU submit", "AU Build alert", 1)

link("AU Build alert", "AU HTTP alert")
link("AU HTTP alert", "AU Format alert")
link("AU Format alert", "TG AU alert")

link("AUP Build settings", "AUP HTTP settings")
link("AUP HTTP settings", "AUP Check")
link("AUP Check", "Switch AU pub")
link("Switch AU pub", "AU Build select", 0)
link("Switch AU pub", "PG Stage4 Format", 1)
link("AU Build select", "AU HTTP select")
link("AU HTTP select", "AU Check pub")
link("AU Check pub", "AU Build publish body")
link("AU Build publish body", "AU HTTP wf-publish")
link("AU HTTP wf-publish", "AU Check result")
link("AU Check result", "Switch AU pub result")
link("Switch AU pub result", "AU Build final", 0)
link("Switch AU pub result", "AU Build alert", 1)
link("AU Build final", "AU HTTP final")
link("AU HTTP final", "TG published")

# ---------- neverError для SC HTTP wf-analytics (Y6; auto-ошибки -> alert, не зависание) ----------
sc_http = by_name["SC HTTP wf-analytics"]["parameters"]["options"]
sc_http["response"] = {"response": {"neverError": True}}

# ---------- сериализация как base: indent=1, ensure_ascii=False, без trailing newline ----------
nodes.extend(new_nodes)
text = json.dumps(data, ensure_ascii=False, indent=1)
assert not text.endswith("\n"), "trailing newline!"
with open(BASE, "w", encoding="utf-8") as fh:
    fh.write(text)

print(f"OK: {len(nodes)} нод (было 430, +{len(new_nodes)}), connections sources: {len(conns)}")
print("Файл:", BASE)
