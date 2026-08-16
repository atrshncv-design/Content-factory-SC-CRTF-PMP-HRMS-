#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Тикет 15: бот-флоу «🎭 Видео с аватаром» (lipsync).
Команда avatar_video -> выбор аватара (custom_avatars approved) -> тема -> 30/60 ->
scriptwriter -> «Принять» (SC OK, flow=avv) -> factory/lipsync -> поколение + session link.
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

def add(n):
    nodes.append(n)
    by_name[n['name']] = n
    return n

def code(name, js, pos):
    return add({"parameters": {"mode": "runOnceForAllItems", "language": "javaScript", "jsCode": js},
                "id": str(uuid.uuid4()), "name": name, "type": "n8n-nodes-base.code", "typeVersion": 2, "position": pos})

def http(name, pos, extra=None):
    p = {"method": "POST", "url": "http://db-bridge:8787/query", "sendHeaders": True,
         "headerParameters": {"parameters": [{"name": "X-BRIDGE-TOKEN", "value": "={{ $env.FACTORY_DB_BRIDGE_TOKEN }}"}]},
         "sendBody": True, "contentType": "json", "specifyBody": "json", "jsonBody": "={{ $json }}",
         "options": {"timeout": 15000}}
    if extra: p.update(extra)
    return add({"parameters": p, "id": str(uuid.uuid4()), "name": name, "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.5, "position": pos})

def tg(name, pos, text_expr, rows, creds_from='TG du gen'):
    src = node(creds_from)
    p = {"resource": "message", "operation": "sendMessage", "chatId": "={{ $('Parser').first().json.chat_id }}",
         "text": text_expr, "additionalFields": {"appendAttribution": False},
         "replyMarkup": "inlineKeyboard", "inlineKeyboard": {"rows": rows}}
    return add({"parameters": p, "id": str(uuid.uuid4()), "name": name, "type": "n8n-nodes-base.telegram",
                "typeVersion": 1.2, "position": pos, "credentials": json.loads(json.dumps(src['credentials']))})

POS = [4200, 300]
def nxt(step=60):
    global POS
    POS = [POS[0] + step, POS[1]]
    return POS

# ========== 1) Parser: алиасы + avv_sel ==========
prs = node('Parser')
js = prs['parameters']['jsCode']
old = "    'gen_url2video': 'url2video', 'gen_shorts': 'shorts',"
new = "    'gen_url2video': 'url2video', 'gen_shorts': 'shorts',\n    'avatar_video': 'avatar_video', 'видео с аватаром': 'avatar_video', 'аватар видео': 'avatar_video', 'avv': 'avatar_video', 'gen_avatar_video': 'avatar_video',"
assert old in js, 'Parser: алиасы gen_shorts не найдены'
js = js.replace(old, new)
old = "    else if (action === 'vd_ok' || action === 'vd_regenerate' || action === 'vd_reject') cb = action;"
new = "    else if (action === 'vd_ok' || action === 'vd_regenerate' || action === 'vd_reject') cb = action;\n    else if (action === 'avv_sel') cb = 'avv_sel';"
assert old in js, 'Parser: vd-колбэки не найдены'
js = js.replace(old, new)
prs['parameters']['jsCode'] = js
print('Parser: avatar_video + avv_sel')

# ========== 2) Switch cmd: avatar_video -> AVV Start ==========
cmd_vals = node('Switch cmd')['parameters']['rules']['values']
cmd_main = conn['Switch cmd']['main']
avv_start = code('AVV Start', """
const p = $('Parser').first().json;
return [{ json: { sql: "UPDATE sessions SET state='AVATAR_VIDEO_AWAIT_AVATAR', quick_payload=NULL, updated_at=datetime('now') WHERE tg_user_id=?", params: [p.tg_user_id] } }];
""", nxt())
avv_http_state = http('AVV HTTP state', nxt())
avv_build_avatars = code('AVV Build avatars', """
const p = $('Parser').first().json;
return [{ json: { sql: "SELECT id, persona_id, creator_name FROM custom_avatars WHERE client_id = (SELECT COALESCE(active_client_id, 1) FROM users WHERE tg_user_id = ?) AND status = 'approved' ORDER BY id DESC", params: [p.tg_user_id] } }];
""", nxt())
avv_http_avatars = http('AVV HTTP avatars', nxt())
avv_ask = code('AVV Ask avatar', """
const p = $('Parser').first().json;
const rows = $('AVV HTTP avatars').first().json.rows || [];
const esc = s => String(s ?? '').replace(/([_*[\\]`])/g, '\\\\$1');
if (!rows.length) return [{ json: { mode: 'none', chat_id: p.chat_id, text: '🎭 Сначала создай аватар: /upload_avatar <url фото>. Потом вернись сюда.' } }];
const btns = rows.map(r => ({ text: String(r.creator_name || r.persona_id || 'Аватар').slice(0, 30), additionalFields: { callback_data: '={{ \\'avv_sel:' + String(r.id) + '\\' }}' } }));
return [{ json: { mode: 'list', chat_id: p.chat_id, text: '🎭 Выбери аватара для видео:', rows: [{ row: { buttons: btns } }] } }];
""", nxt())
tg_none = tg('TG avv none', nxt(), "={{ $json.text }}", [{"row": {"buttons": [{"text": "📋 Меню", "additionalFields": {"callback_data": "={{ \\\"cmd:menu\\\" }}"}}]}}])
tg_ask_avatar = tg('TG avv ask avatar', nxt(), "={{ $json.text }}", [{"row": {"buttons": [{"text": "🧹 Отмена", "additionalFields": {"callback_data": "={{ \\\"cmd:cancel\\\" }}"}}, {"text": "📋 Меню", "additionalFields": {"callback_data": "={{ \\\"cmd:menu\\\" }}"}}]}}])
avv_save = code('AVV Save avatar', """
const p = $('Parser').first().json;
const avatarId = String(p.entity_type || '').trim();
const esc = s => String(s ?? '').replace(/([_*[\\]`])/g, '\\\\$1');
const text = '🎭 Пришли тему для видео с аватаром (1–2 предложения). Разверну в сценарий и озвучу аватаром.';
return [{ json: { sql: "UPDATE sessions SET state='AVATAR_VIDEO_AWAIT_TOPIC', quick_payload=?, updated_at=datetime('now') WHERE tg_user_id=?", params: [JSON.stringify({ avatar_id: avatarId }), p.tg_user_id], chat_id: p.chat_id, text: esc(text) } }];
""", nxt())
tg_ask_topic = tg('TG avv ask topic', nxt(), "={{ $json.text }}", [{"row": {"buttons": [{"text": "🧹 Отмена", "additionalFields": {"callback_data": "={{ \\\"cmd:cancel\\\" }}"}}, {"text": "📋 Меню", "additionalFields": {"callback_data": "={{ \\\"cmd:menu\\\" }}"}}]}}])
avv_topic = code('AVV Topic', """
const p = $('Parser').first().json;
const topic = String(p.raw || '').trim();
const esc = s => String(s ?? '').replace(/([_*[\\]`])/g, '\\\\$1');
const text = '⏱ Длительность видео с аватаром: 30 сек — 5 кред · 60 сек — 10 кред';
return [{ json: { sql: "UPDATE sessions SET state='AVATAR_VIDEO_AWAIT_DUR', quick_payload=json_set(COALESCE(quick_payload,'{}'), '$.topic', ?), updated_at=datetime('now') WHERE tg_user_id=?", params: [topic, p.tg_user_id], chat_id: p.chat_id, text: esc(text) } }];
""", nxt())
tg_ask_dur = tg('TG avv ask dur', nxt(), "={{ $json.text }}", [
    {"row": {"buttons": [
        {"text": "⏱ 30 сек", "additionalFields": {"callback_data": "={{ \\\"cmd:dur_30\\\" }}"}},
        {"text": "⏱ 60 сек", "additionalFields": {"callback_data": "={{ \\\"cmd:dur_60\\\" }}"}}]}},
    {"row": {"buttons": [{"text": "🧹 Отмена", "additionalFields": {"callback_data": "={{ \\\"cmd:cancel\\\" }}"}}, {"text": "📋 Меню", "additionalFields": {"callback_data": "={{ \\\"cmd:menu\\\" }}"}}]}}])
avv_dur_apply = code('AVV Dur apply', """
const p = $('Parser').first().json;
const rows = $('SH HTTP dur state').first().json.rows || [];
let qp = {};
try { qp = JSON.parse((rows[0] && rows[0].quick_payload) || '{}'); } catch (e) { qp = {}; }
const dur = Number(p.args.value) || 30;
const topic = String(qp.topic || '');
const avatarId = String(qp.avatar_id || '');
return [{ json: { sql: "UPDATE sessions SET state='SCRIPT_AWAIT', quick_payload=json_set(COALESCE(quick_payload,'{}'), '$.video_length', ?), updated_at=datetime('now') WHERE tg_user_id=?", params: [dur, p.tg_user_id], topic: topic, video_length: dur, avatar_id: avatarId, chat_id: p.chat_id } }];
""", nxt())
avv_build_prompt = code('AVV Build prompt', """
const p = $('Parser').first().json;
const d = $('AVV Dur apply').first().json;
const dur = Number(d.video_length) || 30;
const words = Math.round(dur * 2);
const prompt = 'Напиши сценарий короткого вертикального видео с аватаром (' + dur + ' сек, ~' + words + ' слов, русский), экспертный тон.\\nТема: ' + (d.topic || '') + '\\n\\nВерни строго JSON: {\\"hook\\", \\"body\\", \\"cta\\", \\"full_text\\", \\"target_length_sec\\", \\"estimated_words\\", \\"format_tag\\", \\"notes\\"}. Без markdown.';
return [{ json: { skill: 'scriptwriter', prompt: prompt } }];
""", nxt())
avv_http_bridge = http('AVV HTTP bridge', nxt(), {"url": "http://host.docker.internal:8642/ask",
    "headerParameters": {"parameters": [{"name": "X-BRIDGE-TOKEN", "value": "={{ $env.HERMES_BRIDGE_TOKEN }}"}]},
    "options": {"timeout": 300000, "response": {"response": {"neverError": True}}}})
avv_parse = code('AVV Parse script', """
function extractJSON(s) {
  if (!s) return null;
  let t = String(s).trim();
  const m = t.match(/```(?:json)?\\s*([\\s\\S]*?)```/);
  if (m) t = m[1].trim();
  const start = t.indexOf('{');
  if (start >= 0) {
    let depth = 0, inStr = false, esc = false;
    for (let i = start; i < t.length; i++) {
      const c = t[i];
      if (inStr) { if (esc) esc = false; else if (c === '\\\\') esc = true; else if (c === '"') inStr = false; continue; }
      if (c === '"') inStr = true;
      else if (c === '{') depth++;
      else if (c === '}') { depth--; if (depth === 0) { try { return JSON.parse(t.slice(start, i + 1)); } catch (e) { return null; } } }
    }
  }
  try { return JSON.parse(t); } catch (e) { return null; }
}
const raw = $('AVV HTTP bridge').first().json.answer || '';
const j = extractJSON(raw);
if (!j) return [{ json: { ok: false, chat_id: $('Parser').first().json.chat_id, text: '⚠️ Сценарист не смог написать сценарий. Попробуй ещё раз.' } }];
return [{ json: { ok: true, hook: String(j.hook || ''), body: String(j.body || ''), cta: String(j.cta || ''), full_text: String(j.full_text || ''), target_length: Number(j.target_length_sec || 30), words: Number(j.estimated_words || 60), format_tag: String(j.format_tag || 'demo') } }];
""", nxt())
avv_verify = code('AVV Verify format', """
const p = $('Parser').first().json;
const s = $('AVV Parse script').first().json;
const d = $('AVV Dur apply').first().json;
const esc = s => String(s ?? '').replace(/([_*[\\]`])/g, '\\\\$1');
const sf = { hook: s.hook, body: s.body, cta: s.cta, full_text: s.full_text, target_length_sec: s.target_length };
const payload = JSON.stringify({ flow: 'avv', topic: String(d.topic || ''), video_length: Number(d.video_length) || 30, avatar_id: String(d.avatar_id || ''), script: s.full_text, script_full: sf, auto_approve: 0 });
const text = '📝 Сценарий готов (' + (Number(d.video_length) || 30) + ' сек, ~' + s.words + ' слов):\\n\\n' + esc(s.full_text);
return [{ json: { sql: "UPDATE sessions SET state='SCRIPT_AWAIT', quick_payload=?, updated_at=datetime('now') WHERE tg_user_id=?", params: [payload, p.tg_user_id], chat_id: p.chat_id, text: text } }];
""", nxt())
tg_verify = tg('TG AVV verify', nxt(), "={{ $json.text }}", [
    {"row": {"buttons": [
        {"text": "✅ Принять", "additionalFields": {"callback_data": "={{ 'sc_ok' }}"}},
        {"text": "🔁 Перегенерировать", "additionalFields": {"callback_data": "={{ 'sc_regenerate' }}"}}]}},
    {"row": {"buttons": [{"text": "🧹 Отмена", "additionalFields": {"callback_data": "={{ \\\"cmd:cancel\\\" }}"}}, {"text": "📋 Меню", "additionalFields": {"callback_data": "={{ \\\"cmd:menu\\\" }}"}}]}}])
avv_build_submit = code('AVV Build submit', """
const p = $('Parser').first().json;
const r = $('SC OK route').first().json;
return [{ json: { text: String(r.script || ''), creator: String(r.avatar_id || ''), video_length: Number(r.video_length) || 30, mode: 'video' } }];
""", nxt())
avv_http_submit = http('AVV HTTP submit', nxt(), {"url": "http://localhost:5678/webhook/factory/lipsync",
    "headerParameters": {"parameters": [{"name": "X-FACTORY-TOKEN", "value": "={{ $env.FACTORY_WEBHOOK_SECRET }}"}]},
    "options": {"timeout": 120000, "response": {"response": {"neverError": True}}}})
avv_parse_submit = code('AVV Parse submit', """
const r = $json;
const b = (r.body && typeof r.body === 'object') ? r.body : r;
const lid = String(b.lipsync_id || r.lipsync_id || '');
if (!lid) return [{ json: { ok: false, err: String((b.error && b.error.message) || b.error || 'пустой ответ'), chat_id: $('Parser').first().json.chat_id } }];
return [{ json: { ok: true, lipsync_id: lid, chat_id: $('Parser').first().json.chat_id } }];
""", nxt())
avv_build_gen = code('AVV Build generation', """
const p = $('Parser').first().json;
const s = $('AVV Parse submit').first().json;
return [{ json: { sql: "INSERT INTO generations (client_id, script_id, request_payload, status, creatify_id) VALUES ((SELECT COALESCE(active_client_id, 1) FROM users WHERE tg_user_id = ?), 0, ?, 'pending', ?)", params: [p.tg_user_id, JSON.stringify({ type: 'lipsync', topic: '' }), String(s.lipsync_id)] } }];
""", nxt())
avv_http_gen = http('AVV HTTP generation', nxt())
avv_build_link = code('AVV Build link', """
const p = $('Parser').first().json;
const g = $('AVV HTTP generation').first().json;
return [{ json: { sql: "UPDATE sessions SET state='AVATAR_VIDEO_GENERATING', generation_id=?, updated_at=datetime('now') WHERE tg_user_id=?", params: [String(g.lastInsertRowid || ''), p.tg_user_id] } }];
""", nxt())
avv_http_link = http('AVV HTTP link', nxt())
avv_format_ok = code('AVV Format ok', """
const p = $('Parser').first().json;
const s = $('AVV Parse submit').first().json;
const esc = s => String(s ?? '').replace(/([_*[\\]`])/g, '\\\\$1');
const text = '✅ Генерация запущена (id ' + esc(s.lipsync_id.slice(0, 8)) + '…). Пришлю видео сюда, как creatify ответит (обычно 1–3 мин).';
return [{ json: { chat_id: p.chat_id, text: esc(text) } }];
""", nxt())
tg_ok = tg('TG avv ok', nxt(), "={{ $json.text }}", [{"row": {"buttons": [{"text": "📋 Меню", "additionalFields": {"callback_data": "={{ \\\"cmd:menu\\\" }}"}}]}}])

# ========== 3) коммутация ==========
cmd_vals.append({"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
    "conditions": [{"leftValue": "={{ $json.command }}", "rightValue": "avatar_video", "operator": {"type": "string", "operation": "equals"}}], "combinator": "and"}})
cmd_main.append([{"node": "AVV Start", "type": "main", "index": 0}])
conn['AVV Start'] = {"main": [[{"node": "AVV HTTP state", "type": "main", "index": 0}]]}
conn['AVV HTTP state'] = {"main": [[{"node": "AVV Build avatars", "type": "main", "index": 0}]]}
conn['AVV Build avatars'] = {"main": [[{"node": "AVV HTTP avatars", "type": "main", "index": 0}]]}
conn['AVV HTTP avatars'] = {"main": [[{"node": "AVV Ask avatar", "type": "main", "index": 0}]]}
conn['AVV Ask avatar'] = {"main": [[{"node": "TG avv ask avatar", "type": "main", "index": 0}], [{"node": "TG avv none", "type": "main", "index": 0}]]}
# TG avv ask avatar: динамические кнопки из $json.rows
tg_ask_avatar['parameters']['inlineKeyboard'] = {"rows": "={{ $json.rows }}"}

# Switch cb: avv_sel -> AVV Save avatar
cb_vals = node('Switch cb')['parameters']['rules']['values']
cb_main = conn['Switch cb']['main']
for i, v in enumerate(cb_vals):
    rv = [c.get('rightValue','') for c in v['conditions']['conditions']]
    if rv and rv[0] == 'sc_edit':
        cb_main.insert(i + 1, [{"node": "AVV Save avatar", "type": "main", "index": 0}])
        cb_vals.insert(i + 1, {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
            "conditions": [{"leftValue": "={{ $json.callback_action }}", "rightValue": "avv_sel", "operator": {"type": "string", "operation": "equals"}}], "combinator": "and"}})
        break
conn['AVV Save avatar'] = {"main": [[{"node": "TG avv ask topic", "type": "main", "index": 0}]]}

# Gate Check: AVATAR_VIDEO_AWAIT_TOPIC -> avv_topic
gc = node('Gate Check')
js = gc['parameters']['jsCode']
old = "if (p.command === 'unknown' && state === 'QUICK_SHORTS_AWAIT_TOPIC') return [{ json: { mode: 'quick_shorts_topic' } }];"
new = old + "\nif (p.command === 'unknown' && state === 'AVATAR_VIDEO_AWAIT_TOPIC') return [{ json: { mode: 'avv_topic' } }];"
assert old in js, 'Gate Check: shorts_topic не найден'
gc['parameters']['jsCode'] = js.replace(old, new)
# Switch gate: avv_topic -> AVV Topic
gg_vals = node('Switch gate')['parameters']['rules']['values']
gg_main = conn['Switch gate']['main']
for i, v in enumerate(gg_vals):
    rv = [c.get('rightValue','') for c in v['conditions']['conditions']]
    if rv and rv[0] == 'quick_shorts_topic':
        gg_main.insert(i + 1, [{"node": "AVV Topic", "type": "main", "index": 0}])
        gg_vals.insert(i + 1, {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
            "conditions": [{"leftValue": "={{ $json.mode }}", "rightValue": "avv_topic", "operator": {"type": "string", "operation": "equals"}}], "combinator": "and"}})
        break
conn['AVV Topic'] = {"main": [[{"node": "TG avv ask dur", "type": "main", "index": 0}]]}

# SH Dur dispatch: AVATAR_VIDEO_AWAIT_DUR -> avv_dur/avv_wrong
sd = node('SH Dur dispatch')
js = sd['parameters']['jsCode']
old = "if (state === 'QUICK_SHORTS_AWAIT_DUR') {\n  return [{ json: { route: (dur === 30 || dur === 60) ? 'shorts_ok' : 'shorts_wrong', chat_id: p.chat_id, dur: dur } }];\n}"
new = old + "\nif (state === 'AVATAR_VIDEO_AWAIT_DUR') {\n  return [{ json: { route: (dur === 30 || dur === 60) ? 'avv_dur' : 'avv_wrong', chat_id: p.chat_id, dur: dur } }];\n}"
assert old in js, 'SH Dur dispatch: shorts-ветка не найдена'
sd['parameters']['jsCode'] = js.replace(old, new)
# Switch SH dur: добавить avv_dur/avv_wrong
sw_vals = node('Switch SH dur')['parameters']['rules']['values']
sw_main = conn['Switch SH dur']['main']
sw_main.insert(1, [{"node": "AVV Dur apply", "type": "main", "index": 0}])
sw_main.insert(1, [{"node": "TG avv ask dur", "type": "main", "index": 0}])
sw_vals.insert(1, {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
    "conditions": [{"leftValue": "={{ $json.route }}", "rightValue": "avv_wrong", "operator": {"type": "string", "operation": "equals"}}], "combinator": "and"}})
sw_vals.insert(2, {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
    "conditions": [{"leftValue": "={{ $json.route }}", "rightValue": "avv_dur", "operator": {"type": "string", "operation": "equals"}}], "combinator": "and"}})
conn['AVV Dur apply'] = {"main": [[{"node": "AVV Build prompt", "type": "main", "index": 0}]]}
conn['AVV Build prompt'] = {"main": [[{"node": "AVV HTTP bridge", "type": "main", "index": 0}]]}
conn['AVV HTTP bridge'] = {"main": [[{"node": "AVV Parse script", "type": "main", "index": 0}]]}
conn['AVV Parse script'] = {"main": [[{"node": "AVV Verify format", "type": "main", "index": 0}]]}
conn['AVV Verify format'] = {"main": [[{"node": "TG AVV verify", "type": "main", "index": 0}]]}

# SC OK route: flow=avv -> avv_video
sc = node('SC OK route')
js = sc['parameters']['jsCode']
old = "if (qp.flow === 'au') {"
new = "if (qp.flow === 'avv') {\n  return [{ json: { mode: 'avv_video', chat_id: p.chat_id, script: script, avatar_id: String(qp.avatar_id || ''), topic: String(qp.topic || ''), video_length: Number(qp.video_length) || 30 } }];\n}\nif (qp.flow === 'au') {"
assert old in js, 'SC OK route: au-ветка не найдена'
sc['parameters']['jsCode'] = js.replace(old, new)
# Switch SC OK: avv_video -> AVV Build submit
so_vals = node('Switch SC OK')['parameters']['rules']['values']
so_main = conn['Switch SC OK']['main']
for i, v in enumerate(so_vals):
    rv = [c.get('rightValue','') for c in v['conditions']['conditions']]
    if rv and rv[0] == 'sh_video':
        so_main.insert(i + 1, [{"node": "AVV Build submit", "type": "main", "index": 0}])
        so_vals.insert(i + 1, {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
            "conditions": [{"leftValue": "={{ $json.mode }}", "rightValue": "avv_video", "operator": {"type": "string", "operation": "equals"}}], "combinator": "and"}})
        break
conn['AVV Build submit'] = {"main": [[{"node": "AVV HTTP submit", "type": "main", "index": 0}]]}
conn['AVV HTTP submit'] = {"main": [[{"node": "AVV Parse submit", "type": "main", "index": 0}]]}
conn['AVV Parse submit'] = {"main": [[{"node": "AVV Build generation", "type": "main", "index": 0}], [{"node": "TG avv ok", "type": "main", "index": 0}]]}
conn['AVV Build generation'] = {"main": [[{"node": "AVV HTTP generation", "type": "main", "index": 0}]]}
conn['AVV HTTP generation'] = {"main": [[{"node": "AVV Build link", "type": "main", "index": 0}]]}
conn['AVV Build link'] = {"main": [[{"node": "AVV HTTP link", "type": "main", "index": 0}]]}
conn['AVV HTTP link'] = {"main": [[{"node": "AVV Format ok", "type": "main", "index": 0}]]}
conn['AVV Format ok'] = {"main": [[{"node": "TG avv ok", "type": "main", "index": 0}]]}
# AVV Parse submit out1 (fail) -> TG avv ok? нет — нужен fail-форматтер. Используем out1 -> TG avv ok как заглушку? Лучше fail -> отдельный текст.
# упрощение: out1 (ok:false) -> TG avv ok не подходит; перенаправим out1 в TG avv ask topic (переспросить)
conn['AVV Parse submit']['main'][1] = [{"node": "TG avv ask topic", "type": "main", "index": 0}]

# ========== 4) меню: кнопка «🎭 Видео с аватаром» ==========
n = node('TG menu gen')
kb = n['parameters']['inlineKeyboard']
first = kb['rows'][0]['row']['buttons']
first.append({"text": "🎭 Видео с аватаром", "additionalFields": {"callback_data": "={{ \\\"cmd:avatar_video\\\" }}"}})
print('TG menu gen: кнопка «Видео с аватаром»')

out = json.dumps([d], ensure_ascii=False, indent=1) + '\n'
open(F, 'w', encoding='utf-8').write(out)
print('wf-tg-bot.json: OK (тикет 15)')
