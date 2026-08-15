#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T5a: AI Shorts quick scenario for wf-tg-bot (374 -> ~404 nodes)."""
import json, re, uuid, copy, sys

PATH = '.scratch/bot-ux-menu/fixes/wf-tg-bot.json'

d = json.load(open(PATH))
if isinstance(d, list):
    assert len(d) == 1
    wf = d[0].get('workflow', d[0])
else:
    wf = d.get('workflow', d)
nodes = wf['nodes']
conns = wf['connections']
by_name = {n['name']: n for n in nodes}

# ---- snapshot connections BEFORE mutations (T4 pitfall) ----
ORIG = copy.deepcopy(conns)

# ---- esc() line extracted byte-exact from MO Format (T1 pitfall) ----
MO_JS = by_name['MO Format']['parameters']['jsCode']
ESC_LINE = re.search(r"const esc = .*?;", MO_JS).group(0)
assert ESC_LINE.startswith('const esc = '), ESC_LINE
print('ESC_LINE:', repr(ESC_LINE))

def esc_js(tpl):
    assert '__ESC_LINE__' in tpl
    return tpl.replace('__ESC_LINE__', ESC_LINE)

TG_CRED = {"telegramApi": {"id": "10000000-0000-4000-8000-000000000004", "name": "telegram"}}

def mk_code(name, js, pos):
    return {"parameters": {"mode": "runOnceForAllItems", "language": "javaScript", "jsCode": js},
            "id": str(uuid.uuid4()), "name": name, "type": "n8n-nodes-base.code",
            "typeVersion": 2, "position": pos}

def mk_http_db(name, pos):
    return {"parameters": {"method": "POST", "url": "http://db-bridge:8787/query",
            "sendHeaders": True,
            "headerParameters": {"parameters": [{"name": "X-BRIDGE-TOKEN", "value": "={{ $env.FACTORY_DB_BRIDGE_TOKEN }}"}]},
            "sendBody": True, "contentType": "json", "specifyBody": "json",
            "jsonBody": "={{ $json }}", "options": {"timeout": 15000}},
            "id": str(uuid.uuid4()), "name": name, "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.5, "position": pos}

def mk_http_lb_creatify(name, pos):
    return {"parameters": {"method": "GET", "url": "https://api.creatify.ai/api/remaining_credits/",
            "authentication": "none", "sendHeaders": True, "specifyHeaders": "keypair",
            "headerParameters": {"parameters": [
                {"name": "X-API-ID", "value": "={{ $env.CREATIFY_API_ID }}"},
                {"name": "X-API-KEY", "value": "={{ $env.CREATIFY_API_KEY }}"}]},
            "options": {"timeout": 15000, "response": {"response": {"neverError": True}}}},
            "id": str(uuid.uuid4()), "name": name, "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.5, "position": pos}

def mk_tg(name, params, pos, cred=True):
    n = {"parameters": params, "id": str(uuid.uuid4()), "name": name,
         "type": "n8n-nodes-base.telegram", "typeVersion": 1.2, "position": pos}
    if cred:
        n["credentials"] = copy.deepcopy(TG_CRED)
    return n

def mk_switch(name, rules, pos):
    return {"parameters": {"mode": "rules", "rules": {"values": rules},
            "options": {"fallbackOutput": "extra"}},
            "id": str(uuid.uuid4()), "name": name, "type": "n8n-nodes-base.switch",
            "typeVersion": 3.4, "position": pos}

def rule(left, right):
    return {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
            "conditions": [{"leftValue": left, "rightValue": right,
                            "operator": {"type": "string", "operation": "equals"}}],
            "combinator": "and"}}

def conn_one(target):
    return [{"node": target, "type": "main", "index": 0}]

def set_conn(src, outs):
    conns[src] = {"main": outs}

# ============ 1. Parser: shorts URL -> args.url ============
P_JS = by_name['Parser']['parameters']['jsCode']
OLD_P = "  else if (C[words[0]]) { command = C[words[0]]; args.value = words.slice(1).join(' ') || null; }\n  return { command: command, args: args };"
NEW_P = ("  else if (C[words[0]]) { command = C[words[0]]; args.value = words.slice(1).join(' ') || null; }\n"
         "  if (command === 'shorts' && args.value && /^https?:\\/\\//i.test(args.value)) args.url = args.value;\n"
         "  return { command: command, args: args };")
assert OLD_P in P_JS, 'Parser anchor not found'
by_name['Parser']['parameters']['jsCode'] = P_JS.replace(OLD_P, NEW_P)

# ============ 2. SHT Build rewrite ============
by_name['SHT Build']['parameters']['jsCode'] = r'''
const p = $('Parser').first().json;
const url = String((p.args && (p.args.url || p.args.value)) || '').trim();
if (/^https?:\/\//i.test(url)) return [{ json: { valid: false, redirect: true, chat_id: p.chat_id, text: '🔗 Для ссылок есть сценарий «URL → видео». Нажми кнопку или напиши: url2video' } }];
const topic = String((p.args && (p.args.value || p.args.url)) || '').trim();
if (topic) return [{ json: { valid: true, direct: true, topic: topic, chat_id: p.chat_id } }];
return [{ json: { valid: false, ask: true, chat_id: p.chat_id, text: '🎬 Пришли тему для шортса (1–2 предложения). Я разверну её в сценарий и сгенерирую вертикальное видео (5 кред за 30 сек).' } }];
'''

# ============ 3. SHT Switch: 2 rules (valid, ask) + fallback = 3 outputs ============
by_name['SHT Switch']['parameters']['rules']['values'] = [
    rule('={{ String($json.valid) }}', 'true'),
    rule('={{ String($json.ask) }}', 'true'),
]
set_conn('SHT Switch', [conn_one('SH Topic'), conn_one('TG sh ask'), conn_one('SHT Format')])

# ============ 4. SHT HTTP: topic body + 300000 timeout ============
by_name['SHT HTTP']['parameters']['jsonBody'] = "={{ {topic: $('SH Topic').first().json.topic, aspect_ratio: '9:16', style: 'auto'} }}"
by_name['SHT HTTP']['parameters']['options'] = {"timeout": 300000, "response": {"response": {"neverError": True}}}
by_name['SHT HTTP']['position'] = [1540, 3800]

# ============ 5. SHT Format rewrite ============
by_name['SHT Format']['parameters']['jsCode'] = esc_js(r'''
const p = $('Parser').first().json;
const b = $('SHT Build').first().json;
__ESC_LINE__
if (!b.valid) return [{ json: { mode: 'redirect', chat_id: p.chat_id, text: esc(b.text) } }];
let r = {};
try { r = $('SHT HTTP').first().json; } catch (e) {}
const body = (r && r.body && typeof r.body === 'object') ? r.body : (r || {});
if (!body || body.ok !== true) {
  const e = body && body.error;
  let msg = (typeof e === 'string' && e) ? e : (e && e.message) || 'генерация шортса не удалась';
  return [{ json: { mode: (msg === 'low_credits') ? 'rlow' : 'rerr', chat_id: p.chat_id, err: msg } }];
}
const video = String(body.video_output || ((body.items && body.items[0] && body.items[0].video_output) || ''));
const shortsId = String(body.shorts_id || '?');
if (body.status === 'done') {
  if (video) return [{ json: { mode: 'done', chat_id: p.chat_id, video_output: video, shorts_id: shortsId } }];
  return [{ json: { mode: 'rerr', chat_id: p.chat_id, err: 'нет video_output в ответе' } }];
}
return [{ json: { mode: 'async', chat_id: p.chat_id, shorts_id: shortsId } }];
''')
by_name['SHT Format']['position'] = [1600, 3800]
set_conn('SHT Format', [conn_one('Switch SH parse')])

# ============ 6. Gate Check: QUICK_SHORTS states ============
GC_JS = by_name['Gate Check']['parameters']['jsCode']
OLD_GC = "if (p.command === 'unknown' && state === 'QUICK_URL_GENERATING') return [{ json: { mode: 'quick_url_generating' } }];"
NEW_GC = (OLD_GC + "\n"
          "if (p.command === 'unknown' && state === 'QUICK_SHORTS_GENERATING') return [{ json: { mode: 'quick_url_generating' } }];\n"
          "if (p.command === 'unknown' && state === 'QUICK_SHORTS_AWAIT_TOPIC') return [{ json: { mode: 'quick_shorts_topic' } }];")
assert OLD_GC in GC_JS, 'Gate Check anchor not found'
by_name['Gate Check']['parameters']['jsCode'] = GC_JS.replace(OLD_GC, NEW_GC)

# ============ 7. Switch gate: + rule quick_shorts_topic (fallback -> out[5]) ============
by_name['Switch gate']['parameters']['rules']['values'].append(rule('={{ $json.mode }}', 'quick_shorts_topic'))
set_conn('Switch gate', [conn_one('GE Build insert'), conn_one('UV Parse url'),
                         conn_one('GD Format'), conn_one('GG Format'),
                         conn_one('SH Topic'), conn_one('TG unknown')])

# ============ 8. DU Parse state: rg_shorts mode + topic out ============
DU_JS = by_name['DU Parse state']['parameters']['jsCode']
OLD_DU = """const quick = !!(url && dur);
let mode = 'dur_wrong';
if (state === 'QUICK_URL_AWAIT_DUR' && p.command === 'dur') mode = 'dur_ok';
else if (p.callback_action === 'regen_gen' && quick) mode = 'rg_ok';
else if (p.callback_action === 'regen_gen') mode = 'rg_cycle';
return [{ json: { mode: mode, state: state, url: url, dur: dur, quick: quick } }];"""
NEW_DU = """const quick = !!(url && dur);
const topic = String(qp.topic || '');
let mode = 'dur_wrong';
if (state === 'QUICK_URL_AWAIT_DUR' && p.command === 'dur') mode = 'dur_ok';
else if (p.callback_action === 'regen_gen' && topic) mode = 'rg_shorts';
else if (p.callback_action === 'regen_gen' && quick) mode = 'rg_ok';
else if (p.callback_action === 'regen_gen') mode = 'rg_cycle';
return [{ json: { mode: mode, state: state, url: url, dur: dur, quick: quick, topic: topic } }];"""
assert OLD_DU in DU_JS, 'DU Parse state anchor not found'
by_name['DU Parse state']['parameters']['jsCode'] = DU_JS.replace(OLD_DU, NEW_DU)

# ============ 9. Switch DU route: + rule rg_shorts (fallback stays last) ============
by_name['Switch DU route']['parameters']['rules']['values'].append(rule('={{ $json.mode }}', 'rg_shorts'))
set_conn('Switch DU route', [conn_one('DU LB creatify'), conn_one('DU Format wrong'),
                             conn_one('DU LB creatify'), conn_one('TG regen'),
                             conn_one('SH Topic'), []])

# ============ 10. esc() for GE/PG Stage4/TP Stage4/SCH Stage4 Format ============
by_name['GE Format']['parameters']['jsCode'] = esc_js(r'''
const p = $('Parser').first().json;
const id = Number($('GE HTTP insert').first().json.lastInsertRowid);
__ESC_LINE__
return [{ json: { chat_id: p.chat_id, text: esc('✍️ Сценарий сохранён (твой текст). Проверь и подтверди:'), script_id: id } }];
''')
by_name['PG Stage4 Format']['parameters']['jsCode'] = esc_js(r'''
const p = $('Parser').first().json;
__ESC_LINE__
const text = '📤 Этап 4/4 — Куда публикуем?\n\n☐ Instagram Reels\n☐ YouTube Shorts\n☐ TikTok\n☐ Telegram\n☐ Threads (текст)\n☐ X (текст)\n\n⏰ Время: не выбрано\n\nВыбери площадки (toggle), время (schedule), затем «📤 Запланировать».';
return [{ json: { chat_id: p.chat_id, text: esc(text) } }];
''')
by_name['TP Stage4 Format']['parameters']['jsCode'] = esc_js(r'''
const p = $('Parser').first().json;
const pl = $('TP Toggle').first().json.platforms || [];
const rows = $('TP HTTP select').first().json.rows || [];
const postAt = (rows[0] && rows[0].post_at) || 'не выбрано';
const all = [['instagram', 'Instagram Reels'], ['youtube', 'YouTube Shorts'], ['tiktok', 'TikTok'], ['telegram', 'Telegram'], ['threads', 'Threads (текст)'], ['x', 'X (текст)']];
const lines = ['📤 Этап 4/4 — Куда публикуем?', ''];
for (const a of all) lines.push((pl.indexOf(a[0]) >= 0 ? '☑️' : '☐') + ' ' + a[1]);
lines.push('', '⏰ Время: ' + postAt);
__ESC_LINE__
return [{ json: { chat_id: p.chat_id, text: esc(lines.join('\n')) } }];
''')
by_name['SCH Stage4 Format']['parameters']['jsCode'] = esc_js(r'''
const p = $('Parser').first().json;
const rows = $('SCH HTTP select').first().json.rows || [];
let platforms = [];
try { platforms = JSON.parse(rows[0] && rows[0].selected_platforms || '[]'); } catch (e) { platforms = []; }
const postAt = (rows[0] && rows[0].post_at) || 'не выбрано';
const all = [['instagram', 'Instagram Reels'], ['youtube', 'YouTube Shorts'], ['tiktok', 'TikTok'], ['telegram', 'Telegram'], ['threads', 'Threads (текст)'], ['x', 'X (текст)']];
const lines = ['📤 Этап 4/4 — Куда публикуем?', ''];
for (const a of all) lines.push((platforms.indexOf(a[0]) >= 0 ? '☑️' : '☐') + ' ' + a[1]);
lines.push('', '⏰ Время: ' + postAt);
__ESC_LINE__
return [{ json: { chat_id: p.chat_id, text: esc(lines.join('\n')) } }];
''')

# ============ 11. New nodes ============
NEW = []

# --- common generation chain ---
NEW.append(mk_code('SH Topic', r'''
const p = $('Parser').first().json;
const src = $input.first().json;
let topic = String((src && src.topic) || '').trim();
if (!topic) topic = String((p.args && (p.args.value || p.args.url)) || '').trim();
if (!topic) topic = String(p.raw || '').trim();
const regen = !!(src && src.mode === 'rg_shorts');
return [{ json: { topic: topic, chat_id: p.chat_id, regen: regen } }];
''', [1000, 3840]))
NEW.append(mk_http_lb_creatify('SH LB creatify', [1060, 3840]))
NEW.append(mk_code('SH LB parse', r'''
const r = $json;
const body = (r.body && typeof r.body === 'object') ? r.body : r;
const data = (body && typeof body.data === 'string') ? body.data : (typeof r.data === 'string' ? r.data : null);
let sc = null;
try {
  if (body.creditCount != null) sc = Number(body.creditCount);
  else if (r.creditCount != null) sc = Number(r.creditCount);
  else if (data) sc = Number(JSON.parse(data).creditCount);
} catch (e) {}
let cr = null;
try {
  if (body.remaining_credits != null) cr = Number(body.remaining_credits);
  else if (r.remaining_credits != null) cr = Number(r.remaining_credits);
  else if (data) cr = Number(JSON.parse(data).remaining_credits);
} catch (e) {}
return [{ json: { creatify: cr, sc: sc } }];
''', [1120, 3840]))
NEW.append(mk_code('SH Gate', r'''
const lb = $('SH LB parse').first().json;
const t = $('SH Topic').first().json;
const cr = lb.creatify != null ? Number(lb.creatify) : null;
const chars = String(t.topic || '').length;
const dur = Math.max(30, Math.ceil(chars / 200));
const cost = 5 * Math.ceil(dur / 30);
if (cr == null || cr < 10) return [{ json: { ok: false, reason: 'low', cr: cr, cost: cost, topic: t.topic, regen: t.regen } }];
if (cost > 50) return [{ json: { ok: false, reason: 'cap', cr: cr, cost: cost, topic: t.topic, regen: t.regen } }];
return [{ json: { ok: true, cr: cr, cost: cost, topic: t.topic, regen: t.regen } }];
''', [1180, 3840]))
NEW.append(mk_switch('Switch SH gate', [
    rule('={{ $json.ok }}', 'true'),
    rule('={{ $json.reason }}', 'low'),
], [1240, 3840]))
NEW.append(mk_code('SH Format gen', esc_js(r'''
const p = $('Parser').first().json;
const g = $('SH Gate').first().json;
__ESC_LINE__
const text = g.regen ? esc('🔁 Перегенерирую...') : esc('⏳ Пишу сценарий и генерирую шортс...');
return [{ json: { chat_id: p.chat_id, text: text } }];
'''), [1300, 3800]))
NEW.append(mk_tg('TG sh gen', {"resource": "message", "operation": "sendMessage",
    "chatId": "={{ $('Parser').first().json.chat_id }}", "text": "={{ $json.text }}",
    "additionalFields": {"appendAttribution": False}, "replyMarkup": "inlineKeyboard",
    "inlineKeyboard": {"rows": [{"row": {"buttons": [
        {"text": "🧹 Отмена", "additionalFields": {"callback_data": "cmd:cancel"}},
        {"text": "📋 Меню", "additionalFields": {"callback_data": "cmd:menu"}}]}}]}}, [1360, 3800]))
NEW.append(mk_code('SH Update state', r'''
const t = $('SH Topic').first().json;
return [{ json: { sql: "UPDATE sessions SET state='QUICK_SHORTS_GENERATING', quick_payload=?, updated_at=datetime('now') WHERE tg_user_id = ?", params: [JSON.stringify({ topic: t.topic, script: null }), 941296693] } }];
''', [1420, 3800]))
NEW.append(mk_http_db('SH HTTP update', [1480, 3800]))

# --- gate fail paths ---
NEW.append(mk_code('SH Format low', esc_js(r'''
const p = $('Parser').first().json;
const g = $('SH Gate').first().json;
__ESC_LINE__
const cr = g.cr != null ? g.cr : '?';
const text = '⛔ Недостаточно кредитов creatify: ' + esc(cr) + '. Нужно минимум 10 для генерации.';
return [{ json: { chat_id: p.chat_id, text: text } }];
'''), [1300, 3880]))
NEW.append(mk_tg('TG sh low', {"resource": "message", "operation": "sendMessage",
    "chatId": "={{ $('Parser').first().json.chat_id }}", "text": "={{ $json.text }}",
    "additionalFields": {"appendAttribution": False}, "replyMarkup": "inlineKeyboard",
    "inlineKeyboard": {"rows": [{"row": {"buttons": [
        {"text": "💰 Бюджет", "additionalFields": {"callback_data": "cmd:budget"}},
        {"text": "📋 Меню", "additionalFields": {"callback_data": "cmd:menu"}}]}}]}}, [1780, 3900]))
NEW.append(mk_code('SH Format cap', esc_js(r'''
const p = $('Parser').first().json;
const g = $('SH Gate').first().json;
__ESC_LINE__
const text = '⛔ Стоимость генерации (~' + esc(g.cost) + ' кред) превышает лимит 50.';
return [{ json: { chat_id: p.chat_id, text: text } }];
'''), [1300, 3920]))
NEW.append(mk_tg('TG sh err', {"resource": "message", "operation": "sendMessage",
    "chatId": "={{ $('Parser').first().json.chat_id }}", "text": "={{ $json.text }}",
    "additionalFields": {"appendAttribution": False}, "replyMarkup": "inlineKeyboard",
    "inlineKeyboard": {"rows": [{"row": {"buttons": [
        {"text": "📋 Меню", "additionalFields": {"callback_data": "cmd:menu"}}]}}]}}, [1780, 3940]))
NEW.append(mk_code('SH Reset state', r'''
return [{ json: { sql: "UPDATE sessions SET state='IDLE', quick_payload=NULL, updated_at=datetime('now') WHERE tg_user_id = ?", params: [941296693] } }];
''', [1840, 3920]))
NEW.append(mk_http_db('SH HTTP reset', [1900, 3920]))

# --- response paths (async / rlow / rerr) ---
NEW.append(mk_code('SH Format async', esc_js(r'''
const p = $('Parser').first().json;
const f = $('SHT Format').first().json;
__ESC_LINE__
const text = '⏳ Шортс генерируется (id ' + esc(f.shorts_id) + '). Пришлю видео, как creatify ответит.';
return [{ json: { chat_id: p.chat_id, text: text } }];
'''), [1720, 3860]))
NEW.append(mk_tg('TG sh async', {"resource": "message", "operation": "sendMessage",
    "chatId": "={{ $('Parser').first().json.chat_id }}", "text": "={{ $json.text }}",
    "additionalFields": {"appendAttribution": False}, "replyMarkup": "inlineKeyboard",
    "inlineKeyboard": {"rows": [{"row": {"buttons": [
        {"text": "📋 Меню", "additionalFields": {"callback_data": "cmd:menu"}}]}}]}}, [1780, 3860]))
NEW.append(mk_code('SH Format rlow', esc_js(r'''
const p = $('Parser').first().json;
__ESC_LINE__
return [{ json: { chat_id: p.chat_id, text: esc('😕 Недостаточно кредитов creatify') } }];
'''), [1720, 3900]))
NEW.append(mk_code('SH Format rerr', esc_js(r'''
const p = $('Parser').first().json;
const f = $('SHT Format').first().json;
__ESC_LINE__
const text = '😕 Шортс не создан: ' + esc(f.err);
return [{ json: { chat_id: p.chat_id, text: text } }];
'''), [1720, 3940]))

# --- delivery chain (done) ---
NEW.append(mk_code('SH Build generation', r'''
const f = $('SHT Format').first().json;
const t = $('SH Topic').first().json;
return [{ json: { sql: "INSERT INTO generations (client_id, request_payload, status, video_output_url, local_path, webhook_received, completed_at, creatify_id) VALUES (1, ?, 'done', ?, ?, 1, datetime('now'), ?)", params: [JSON.stringify({ topic: t.topic, type: 'ai_shorts' }), f.video_output, f.video_output, String(f.shorts_id)] } }];
''', [1720, 3760]))
NEW.append(mk_http_db('SH HTTP generation', [1780, 3760]))
NEW.append(mk_code('SH Build session', r'''
const g = $('SH HTTP generation').first().json;
const t = $('SH Topic').first().json;
const f = $('SHT Format').first().json;
return [{ json: { sql: "UPDATE sessions SET state='CYCLE_VIDEO_PENDING', generation_id=?, quick_payload=?, updated_at=datetime('now') WHERE tg_user_id = ?", params: [String(g.lastInsertRowid), JSON.stringify({ topic: t.topic, shorts_id: f.shorts_id }), 941296693] } }];
''', [1840, 3760]))
NEW.append(mk_http_db('SH HTTP session', [1900, 3760]))
NEW.append(mk_tg('TG sh video', {"resource": "video", "operation": "sendVideo",
    "chatId": "={{ $('Parser').first().json.chat_id }}",
    "video": "={{ $('SHT Format').first().json.video_output }}",
    "additionalFields": {"appendAttribution": False, "caption": "🎬 Шортс готов"}}, [1960, 3760]))
NEW.append(mk_code('SH Build buttons', r'''
const p = $('Parser').first().json;
const g = $('SH HTTP generation').first().json;
return [{ json: { chat_id: p.chat_id, gen_id: String(g.lastInsertRowid) } }];
''', [2020, 3760]))
NEW.append(mk_tg('TG sh buttons', {"resource": "message", "operation": "sendMessage",
    "chatId": "={{ $('Parser').first().json.chat_id }}", "text": "={{ '🎬 Шортс готов' }}",
    "additionalFields": {"appendAttribution": False}, "replyMarkup": "inlineKeyboard",
    "inlineKeyboard": {"rows": [{"row": {"buttons": [
        {"text": "📤 Опубликовать", "additionalFields": {"callback_data": "={{ 'publish:gen:' + $json.gen_id }}"}},
        {"text": "🔁 Перегенерировать", "additionalFields": {"callback_data": "={{ 'regen:gen:' + $json.gen_id }}"}},
        {"text": "❌ Отклонить", "additionalFields": {"callback_data": "={{ 'reject:gen:' + $json.gen_id }}"}},
        {"text": "📋 Меню", "additionalFields": {"callback_data": "cmd:menu"}}]}}]}}, [2080, 3760]))

# --- ask path ---
NEW.append(mk_tg('TG sh ask', {"resource": "message", "operation": "sendMessage",
    "chatId": "={{ $('Parser').first().json.chat_id }}",
    "text": "={{ '🎬 Пришли тему для шортса (1–2 предложения). Я разверну её в сценарий и сгенерирую вертикальное видео (5 кред за 30 сек).' }}",
    "additionalFields": {"appendAttribution": False}, "replyMarkup": "inlineKeyboard",
    "inlineKeyboard": {"rows": [{"row": {"buttons": [
        {"text": "🧹 Отмена", "additionalFields": {"callback_data": "cmd:cancel"}},
        {"text": "📋 Меню", "additionalFields": {"callback_data": "cmd:menu"}}]}}]}}, [1000, 3900]))
NEW.append(mk_code('SH Ask update', r'''
return [{ json: { sql: "UPDATE sessions SET state='QUICK_SHORTS_AWAIT_TOPIC', quick_payload=NULL, updated_at=datetime('now') WHERE tg_user_id = ?", params: [941296693] } }];
''', [1060, 3900]))
NEW.append(mk_http_db('SH Ask HTTP', [1120, 3900]))

# --- response router ---
NEW.append(mk_switch('Switch SH parse', [
    rule('={{ $json.mode }}', 'done'),
    rule('={{ $json.mode }}', 'async'),
    rule('={{ $json.mode }}', 'rlow'),
    rule('={{ $json.mode }}', 'rerr'),
], [1660, 3800]))

# ============ 12. Connections for new nodes ============
set_conn('SH Topic', [conn_one('SH LB creatify')])
set_conn('SH LB creatify', [conn_one('SH LB parse')])
set_conn('SH LB parse', [conn_one('SH Gate')])
set_conn('SH Gate', [conn_one('Switch SH gate')])
set_conn('Switch SH gate', [conn_one('SH Format gen'), conn_one('SH Format low'), conn_one('SH Format cap')])
set_conn('SH Format gen', [conn_one('TG sh gen')])
set_conn('TG sh gen', [conn_one('SH Update state')])
set_conn('SH Update state', [conn_one('SH HTTP update')])
set_conn('SH HTTP update', [conn_one('SHT HTTP')])
set_conn('SH Format low', [conn_one('TG sh low')])
set_conn('SH Format cap', [conn_one('TG sh err')])
set_conn('TG sh low', [conn_one('SH Reset state')])
set_conn('TG sh err', [conn_one('SH Reset state')])
set_conn('SH Reset state', [conn_one('SH HTTP reset')])
set_conn('SH HTTP reset', [])
set_conn('SH Format async', [conn_one('TG sh async')])
set_conn('TG sh async', [])
set_conn('SH Format rlow', [conn_one('TG sh low')])
set_conn('SH Format rerr', [conn_one('TG sh err')])
set_conn('SH Build generation', [conn_one('SH HTTP generation')])
set_conn('SH HTTP generation', [conn_one('SH Build session')])
set_conn('SH Build session', [conn_one('SH HTTP session')])
set_conn('SH HTTP session', [conn_one('TG sh video')])
set_conn('TG sh video', [conn_one('SH Build buttons')])
set_conn('SH Build buttons', [conn_one('TG sh buttons')])
set_conn('TG sh buttons', [])
set_conn('TG sh ask', [conn_one('SH Ask update')])
set_conn('SH Ask update', [conn_one('SH Ask HTTP')])
set_conn('SH Ask HTTP', [])
set_conn('Switch SH parse', [conn_one('SH Build generation'), conn_one('SH Format async'),
                             conn_one('SH Format rlow'), conn_one('SH Format rerr'),
                             conn_one('TG shorts')])

# ============ 13. Append nodes ============
for n in NEW:
    assert n['name'] not in by_name, n['name']
    nodes.append(n)
    by_name[n['name']] = n

# ============ 14. Save (same format as source) ============
out = json.dumps(d, indent=1, ensure_ascii=False)
with open(PATH, 'w', encoding='utf-8') as f:
    f.write(out)
print('nodes:', len(nodes), '| new:', len(NEW))
print('saved OK, bytes:', len(out))
