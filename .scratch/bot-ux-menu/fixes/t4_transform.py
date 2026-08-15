#!/usr/bin/env python3
"""T4: Быстрый сценарий URL→видео для wf-tg-bot (fixes-версия).
Работает только с файлом .scratch/bot-ux-menu/fixes/wf-tg-bot.json.
Добавляет: ветку url2video (UV), ветку dur (DU), регенерацию (RG),
gate QUICK_URL_* правила, esc() во всех новых Format, CN Build quick_payload=NULL.
"""
import json, re, sys, uuid

PATH = '.scratch/bot-ux-menu/fixes/wf-tg-bot.json'
data = json.load(open(PATH, encoding='utf-8'))
wf = data[0] if isinstance(data, list) else data
nodes = wf['nodes']
conns = wf.setdefault('connections', {})
by_name = {n['name']: n for n in nodes}
TG = 941296693

# ---------- esc line verbatim from MO Format ----------
mo_js = by_name['MO Format']['parameters']['jsCode']
m = re.search(r"const esc = .*?;", mo_js)
assert m, "esc line not found in MO Format"
ESC_LINE = m.group(0)

def new_id():
    return str(uuid.uuid4())

def mk_node(name, ntype, params, tv, pos):
    assert name not in by_name, f"duplicate node {name}"
    n = {"parameters": params, "id": new_id(), "name": name, "type": ntype,
         "typeVersion": tv, "position": pos}
    nodes.append(n)
    by_name[name] = n
    return n

def mk_code(name, js, pos):
    return mk_node(name, 'n8n-nodes-base.code',
                   {"mode": "runOnceForAllItems", "language": "javaScript", "jsCode": js}, 2, pos)

def mk_http_db(name, pos):
    return mk_node(name, 'n8n-nodes-base.httpRequest', {
        "method": "POST", "url": "http://db-bridge:8787/query",
        "sendHeaders": True,
        "headerParameters": {"parameters": [{"name": "X-BRIDGE-TOKEN", "value": "={{ $env.FACTORY_DB_BRIDGE_TOKEN }}"}]},
        "sendBody": True, "contentType": "json", "specifyBody": "json",
        "jsonBody": "={{ $json }}", "options": {"timeout": 15000}
    }, 4.5, pos)

def mk_http_lb_creatify(name, pos):
    return mk_node(name, 'n8n-nodes-base.httpRequest', {
        "method": "GET", "url": "https://api.creatify.ai/api/remaining_credits/",
        "authentication": "none", "sendHeaders": True, "specifyHeaders": "keypair",
        "headerParameters": {"parameters": [
            {"name": "X-API-ID", "value": "={{ $env.CREATIFY_API_ID }}"},
            {"name": "X-API-KEY", "value": "={{ $env.CREATIFY_API_KEY }}"}
        ]},
        "options": {"timeout": 15000, "response": {"response": {"neverError": True}}}
    }, 4.5, pos)

LB_PARSE_JS = by_name['ST LB parse']['parameters']['jsCode']

def mk_switch(name, rules, pos, n_out):
    """rules: list of (leftValue, rightValue) string-equals; fallback extra."""
    values = []
    for lv, rv in rules:
        values.append({"conditions": {
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
            "conditions": [{"leftValue": lv, "rightValue": rv,
                            "operator": {"type": "string", "operation": "equals"}}],
            "combinator": "and"}})
    return mk_node(name, 'n8n-nodes-base.switch',
                   {"mode": "rules", "rules": {"values": values},
                    "options": {"fallbackOutput": "extra"}}, 3.4, pos)

def mk_tg(name, buttons_rows, pos):
    rows = []
    for row in buttons_rows:
        btns = [{"text": t, "additionalFields": {"callback_data": cb}} for t, cb in row]
        rows.append({"row": {"buttons": btns}})
    return mk_node(name, 'n8n-nodes-base.telegram', {
        "resource": "message", "operation": "sendMessage",
        "chatId": "={{ $('Parser').first().json.chat_id }}", "text": "={{ $json.text }}",
        "additionalFields": {"appendAttribution": False},
        "replyMarkup": "inlineKeyboard", "inlineKeyboard": {"rows": rows}
    }, 1.2, pos)

def conn(src, out_idx, dst):
    main = conns.setdefault(src, {}).setdefault('main', [])
    while len(main) <= out_idx:
        main.append([])
    main[out_idx].append({"node": dst, "type": "main", "index": 0})

# snapshot of Switch cmd outputs BEFORE any mutations
ORIG_CMD_MAIN = [list(arr) for arr in conns['Switch cmd']['main']]
ORIG_GATE_MAIN = [list(arr) for arr in conns['Switch gate']['main']]

# =========================================================
# 1) Switch cmd: append rules url2video(31), dur(32); fallback -> out[33]
# =========================================================
scmd = by_name['Switch cmd']
scmd['parameters']['rules']['values'].append(json.loads(json.dumps(
    scmd['parameters']['rules']['values'][0]).replace('"start"', '"url2video"')))
scmd['parameters']['rules']['values'].append(json.loads(json.dumps(
    scmd['parameters']['rules']['values'][0]).replace('"start"', '"dur"')))

# =========================================================
# 2) UV branch (url2video)
# =========================================================
X = 1500
mk_code('UV Build state', f"""
return [{json.dumps({'json': {'sql': 'SELECT state, quick_payload FROM sessions WHERE tg_user_id = ?', 'params': [TG]}})}];
""", [X, -500])
mk_http_db('UV HTTP state', [X + 60, -500])
mk_code('UV Check busy', f"""
const p = $('Parser').first().json;
const rows = $('UV HTTP state').first().json.rows || [];
const state = (rows[0] && rows[0].state) || 'IDLE';
let url = String((p.args && p.args.url) || '').trim();
if (!url && p.command === 'url2video' && p.args && p.args.value) url = String(p.args.value).trim();
let mode = 'busy';
if (state === 'IDLE') mode = url ? 'parse' : 'ask';
return [{{ json: {{ mode: mode, state: state, url: url }} }}];
""", [X + 120, -500])
mk_switch('Switch UV busy',
          [('={{ $json.mode }}', 'parse'), ('={{ $json.mode }}', 'ask')], [X + 180, -500], 3)
mk_code('UV Parse url', """
const p = $('Parser').first().json;
let raw = String((p.args && p.args.url) || '').trim();
if (!raw && p.command === 'url2video' && p.args && p.args.value) raw = String(p.args.value).trim();
if (!raw) raw = String(p.raw || '').trim();
if (!/^https?:\\/\\//i.test(raw)) return [{ json: { ok: false, url: raw } }];
return [{ json: { ok: true, url: raw } }];
""", [X + 260, -540])
mk_switch('Switch UV parse', [('={{ $json.ok }}', 'true')], [X + 320, -540], 2)
mk_code('UV Save url', f"""
const u = $('UV Parse url').first().json;
return [{{ json: {{ sql: "UPDATE sessions SET state='QUICK_URL_AWAIT_DUR', quick_payload=?, updated_at=datetime('now') WHERE tg_user_id = ?", params: [JSON.stringify({{ url: u.url }}), {TG}] }} }}];
""", [X + 400, -540])
mk_http_db('UV HTTP save', [X + 460, -540])
mk_http_lb_creatify('UV LB creatify', [X + 520, -540])
mk_code('UV LB parse', LB_PARSE_JS, [X + 580, -540])
mk_code('UV Ask dur', f"""
const p = $('Parser').first().json;
const lb = $('UV LB parse').first().json;
{ESC_LINE}
const cr = lb.creatify != null ? lb.creatify : '?';
const text = '⏱ Длительность ролика: 30 сек — 5 кред · 60 сек — 10 кред · 90 сек — 15 кред. Остаток creatify: ' + esc(cr);
return [{{ json: {{ chat_id: p.chat_id, text: text }} }}];
""", [X + 640, -540])
mk_tg('TG uv ask dur', [
    [('⏱ 30 сек', 'cmd:dur_30'), ('⏱ 60 сек', 'cmd:dur_60'), ('⏱ 90 сек', 'cmd:dur_90')],
    [('🧹 Отмена', 'cmd:cancel'), ('📋 Меню', 'cmd:menu')],
], [X + 700, -540])

mk_code('UV Build ask link', f"""
return [{{ json: {{ sql: "UPDATE sessions SET state='QUICK_URL_AWAIT_LINK', quick_payload=NULL, updated_at=datetime('now') WHERE tg_user_id = ?", params: [{TG}] }} }}];
""", [X + 260, -420])
mk_http_db('UV HTTP ask link', [X + 320, -420])
mk_code('UV Ask link', f"""
const p = $('Parser').first().json;
{ESC_LINE}
const text = esc('🔗 Пришли ссылку на материал для ролика. Например: https://robotec.ru/news/123');
return [{{ json: {{ chat_id: p.chat_id, text: text }} }}];
""", [X + 380, -420])
mk_tg('TG uv ask link', [[('🧹 Отмена', 'cmd:cancel'), ('📋 Меню', 'cmd:menu')]], [X + 440, -420])

mk_code('UV Format busy', f"""
const p = $('Parser').first().json;
{ESC_LINE}
const text = esc('⏳ Сейчас выполняется другой шаг. Заверши его или отправь: отмена');
return [{{ json: {{ chat_id: p.chat_id, text: text }} }}];
""", [X + 260, -300])
mk_tg('TG uv busy', [[('🧹 Отмена', 'cmd:cancel'), ('📋 Меню', 'cmd:menu')]], [X + 320, -300])

mk_code('UV Format bad url', f"""
const p = $('Parser').first().json;
{ESC_LINE}
const text = esc('❌ Это не похоже на ссылку. Пришли URL вида https://…');
return [{{ json: {{ chat_id: p.chat_id, text: text }} }}];
""", [X + 400, -660])
mk_tg('TG uv bad url', [[('🧹 Отмена', 'cmd:cancel'), ('📋 Меню', 'cmd:menu')]], [X + 460, -660])

# connections UV
conn('Switch cmd', 31, 'UV Build state')
conn('UV Build state', 0, 'UV HTTP state')
conn('UV HTTP state', 0, 'UV Check busy')
conn('UV Check busy', 0, 'Switch UV busy')
conn('Switch UV busy', 0, 'UV Parse url')
conn('Switch UV busy', 1, 'UV Build ask link')
conn('Switch UV busy', 2, 'UV Format busy')
conn('UV Format busy', 0, 'TG uv busy')
conn('UV Build ask link', 0, 'UV HTTP ask link')
conn('UV HTTP ask link', 0, 'UV Ask link')
conn('UV Ask link', 0, 'TG uv ask link')
conn('UV Parse url', 0, 'Switch UV parse')
conn('Switch UV parse', 0, 'UV Save url')
conn('Switch UV parse', 1, 'UV Format bad url')
conn('UV Format bad url', 0, 'TG uv bad url')
conn('UV Save url', 0, 'UV HTTP save')
conn('UV HTTP save', 0, 'UV LB creatify')
conn('UV LB creatify', 0, 'UV LB parse')
conn('UV LB parse', 0, 'UV Ask dur')
conn('UV Ask dur', 0, 'TG uv ask dur')

# =========================================================
# 3) Gate: Gate Check jsCode + Switch gate rules + gate messages
# =========================================================
by_name['Gate Check']['parameters']['jsCode'] = """
const p = $('Parser').first().json;
const rows = $('Gate HTTP').first().json.rows || [];
const state = (rows[0] && rows[0].state) || 'IDLE';
if (p.command === 'unknown' && state === 'CYCLE_SCRIPT_EDITING') return [{ json: { mode: 'script_edit' } }];
if (p.command === 'unknown' && state === 'QUICK_URL_AWAIT_LINK') return [{ json: { mode: 'quick_url_link' } }];
if (p.command === 'unknown' && state === 'QUICK_URL_AWAIT_DUR') return [{ json: { mode: 'quick_url_dur' } }];
if (p.command === 'unknown' && state === 'QUICK_URL_GENERATING') return [{ json: { mode: 'quick_url_generating' } }];
return [{ json: { mode: 'normal' } }];
"""
sgate = by_name['Switch gate']
for rv in ('quick_url_link', 'quick_url_dur', 'quick_url_generating'):
    rule = json.loads(json.dumps(sgate['parameters']['rules']['values'][0]))
    rule['conditions']['conditions'][0]['rightValue'] = rv
    sgate['parameters']['rules']['values'].append(rule)

mk_code('GD Format', f"""
const p = $('Parser').first().json;
{ESC_LINE}
const text = esc('⏱ Выбери длительность кнопкой выше');
return [{{ json: {{ chat_id: p.chat_id, text: text }} }}];
""", [X + 40, -80])
mk_tg('TG gd wait', [[('📋 Меню', 'cmd:menu')]], [X + 100, -80])
mk_code('GG Format', f"""
const p = $('Parser').first().json;
{ESC_LINE}
const text = esc('⏳ Генерируется, жди ответа');
return [{{ json: {{ chat_id: p.chat_id, text: text }} }}];
""", [X + 40, 0])
mk_tg('TG gg wait', [[('📋 Меню', 'cmd:menu')]], [X + 100, 0])

# Switch gate connections: out[0] GE Build insert, out[1] UV Parse url, out[2] GD Format, out[3] GG Format, out[4] TG unknown
old_gate_main = ORIG_GATE_MAIN  # [[GE],[TG unknown]]
conns['Switch gate']['main'] = [
    old_gate_main[0],
    [{"node": "UV Parse url", "type": "main", "index": 0}],
    [{"node": "GD Format", "type": "main", "index": 0}],
    [{"node": "GG Format", "type": "main", "index": 0}],
    old_gate_main[1],
]
conn('GD Format', 0, 'TG gd wait')
conn('GG Format', 0, 'TG gg wait')

# =========================================================
# 4) DU branch (dur)
# =========================================================
Y = 120
mk_code('DU Check state', f"""
return [{{ json: {{ sql: 'SELECT state, quick_payload FROM sessions WHERE tg_user_id = ?', params: [{TG}] }} }}];
""", [X, Y])
mk_http_db('DU HTTP state', [X + 60, Y])
mk_code('DU Parse state', """
const p = $('Parser').first().json;
const rows = $('DU HTTP state').first().json.rows || [];
const state = (rows[0] && rows[0].state) || 'IDLE';
let qp = {};
try { qp = JSON.parse((rows[0] && rows[0].quick_payload) || '{}'); } catch (e) { qp = {}; }
const url = String(qp.url || '');
const dur = Number(p.args.value) || Number(qp.duration) || 0;
const quick = !!(url && dur);
let mode = 'dur_wrong';
if (state === 'QUICK_URL_AWAIT_DUR' && p.command === 'dur') mode = 'dur_ok';
else if (p.callback_action === 'regen_gen' && quick) mode = 'rg_ok';
else if (p.callback_action === 'regen_gen') mode = 'rg_cycle';
return [{ json: { mode: mode, state: state, url: url, dur: dur, quick: quick } }];
""", [X + 120, Y])
mk_switch('Switch DU route',
          [('={{ $json.mode }}', 'dur_ok'), ('={{ $json.mode }}', 'dur_wrong'),
           ('={{ $json.mode }}', 'rg_ok'), ('={{ $json.mode }}', 'rg_cycle')], [X + 180, Y], 5)

mk_code('DU Format wrong', f"""
const p = $('Parser').first().json;
{ESC_LINE}
const text = esc('⏱ Сначала начни сценарий: кнопка «URL → видео»');
return [{{ json: {{ chat_id: p.chat_id, text: text }} }}];
""", [X + 260, Y + 240])
mk_tg('TG du wrong', [[('📋 Меню', 'cmd:menu')]], [X + 320, Y + 240])

mk_http_lb_creatify('DU LB creatify', [X + 260, Y - 40])
mk_code('DU LB parse', LB_PARSE_JS, [X + 320, Y - 40])
mk_code('DU Gate', """
const lb = $('DU LB parse').first().json;
const st = $('DU Parse state').first().json;
const cr = lb.creatify != null ? Number(lb.creatify) : null;
const dur = Number(st.dur) || 0;
const cost = Math.round(5 * dur / 30);
const url = String(st.url || '');
if (cr == null || cr < 10) return [{ json: { ok: false, reason: 'low', cr: cr, cost: cost, dur: dur, url: url } }];
if (cost > 50) return [{ json: { ok: false, reason: 'cap', cr: cr, cost: cost, dur: dur, url: url } }];
return [{ json: { ok: true, cr: cr, cost: cost, dur: dur, url: url } }];
""", [X + 380, Y - 40])
mk_switch('Switch DU gate',
          [('={{ $json.ok }}', 'true'), ('={{ $json.reason }}', 'low')], [X + 440, Y - 40], 3)

mk_code('DU Format gen', f"""
const p = $('Parser').first().json;
const g = $('DU Gate').first().json;
{ESC_LINE}
const text = '⏳ Создаю ролик из ссылки на ' + esc(g.dur) + ' сек (~' + esc(g.cost) + ' кред). Пришлю сюда, как будет готово.';
return [{{ json: {{ chat_id: p.chat_id, text: text }} }}];
""", [X + 520, Y - 100])
mk_tg('TG du gen', [[('🧹 Отмена', 'cmd:cancel'), ('📋 Меню', 'cmd:menu')]], [X + 580, Y - 100])
mk_code('DU Format low', f"""
const p = $('Parser').first().json;
const g = $('DU Gate').first().json;
{ESC_LINE}
const cr = g.cr != null ? g.cr : '?';
const text = '⛔ Недостаточно кредитов creatify: ' + esc(cr) + '. Нужно минимум 10 для генерации.';
return [{{ json: {{ chat_id: p.chat_id, text: text }} }}];
""", [X + 520, Y - 20])
mk_tg('TG du low', [[('💰 Бюджет', 'cmd:budget'), ('📋 Меню', 'cmd:menu')]], [X + 580, Y - 20])
mk_code('DU Format cap', f"""
const p = $('Parser').first().json;
const g = $('DU Gate').first().json;
{ESC_LINE}
const text = '⛔ Стоимость генерации (~' + esc(g.cost) + ' кред) превышает лимит 50.';
return [{{ json: {{ chat_id: p.chat_id, text: text }} }}];
""", [X + 520, Y + 60])
mk_tg('TG du cap', [[('📋 Меню', 'cmd:menu')]], [X + 580, Y + 60])

# --- generation chain (shared with RG) ---
mk_code('DU Update state', f"""
const st = $('DU Parse state').first().json;
return [{{ json: {{ sql: "UPDATE sessions SET state='QUICK_URL_GENERATING', quick_payload=?, updated_at=datetime('now') WHERE tg_user_id = ?", params: [JSON.stringify({{ url: st.url, duration: Number(st.dur) }}), {TG}] }} }}];
""", [X + 660, Y - 100])
mk_http_db('DU HTTP update', [X + 720, Y - 100])
mk_code('DU Build settings', """
return [{ json: { sql: "SELECT key, value FROM settings WHERE key IN ('active_client_id')", params: [] } }];
""", [X + 780, Y - 100])
mk_http_db('DU HTTP settings', [X + 840, Y - 100])
mk_code('DU Build script', f"""
const st = $('DU Parse state').first().json;
const s = $('DU HTTP settings').first().json;
let clientId = 1;
for (const r of (s.rows || [])) {{ if (r.key === 'active_client_id') {{ clientId = Number(r.value) || 1; }} }}
const fullText = 'Ролик из ссылки: ' + st.url;
return [{{ json: {{ sql: "INSERT INTO scripts (client_id, topic_id, hook, body, cta, target_length, format_tag, full_text, status) VALUES (?, NULL, '', '', '', ?, 'user', ?, 'pending')", params: [clientId, Number(st.dur), fullText] }} }}];
""", [X + 900, Y - 100])
mk_http_db('DU HTTP script', [X + 960, Y - 100])
mk_code('DU Build link body', """
const st = $('DU Parse state').first().json;
return [{ json: { url: st.url, aspect_ratio: '9x16', video_length: Number(st.dur), language: 'ru' } }];
""", [X + 1020, Y - 100])
mk_node('DU HTTP link', 'n8n-nodes-base.httpRequest', {
    "method": "POST", "url": "http://localhost:5678/webhook/factory/creatify-link",
    "sendBody": True, "contentType": "json", "specifyBody": "json", "jsonBody": "={{ $json }}",
    "options": {"timeout": 60000, "response": {"response": {"neverError": True}}}
}, 4.5, [X + 1080, Y - 100])
mk_code('DU Parse link', """
const r = $json;
const b = (r.body && typeof r.body === 'object') ? r.body : r;
const linkId = String(b.link_id || r.link_id || '');
if (!linkId) return [{ json: { ok: false, err: String((r.error && r.error.message) || r.error || 'пустой ответ') } }];
return [{ json: { ok: true, link_id: linkId } }];
""", [X + 1140, Y - 100])
mk_switch('Switch DU link', [('={{ $json.ok }}', 'true')], [X + 1200, Y - 100], 2)
mk_code('DU Build submit', f"""
const st = $('DU Parse state').first().json;
const l = $('DU Parse link').first().json;
const s = $('DU HTTP settings').first().json;
const scriptId = Number($('DU HTTP script').first().json.lastInsertRowid);
let clientId = 1;
for (const r of (s.rows || [])) {{ if (r.key === 'active_client_id') {{ clientId = Number(r.value) || 1; }} }}
const dur = Number(st.dur) || 0;
return [{{ json: {{
  script_id: scriptId,
  client_id: clientId,
  json_payload: {{
    name: 'Ролик из ссылки',
    link: l.link_id,
    visual_style: 'default',
    script_style: 'informative',
    aspect_ratio: '9x16',
    video_length: dur,
    language: 'ru',
    target_platform: 'Instagram',
    model_version: 'aurora_v1_fast',
    override_script: ''
  }},
  link_id: String(l.link_id)
}} }}];
""", [X + 1280, Y - 100])
mk_node('DU HTTP submit', 'n8n-nodes-base.httpRequest', {
    "method": "POST", "url": "http://localhost:5678/webhook/factory/creatify-submit",
    "sendBody": True, "contentType": "json", "specifyBody": "json", "jsonBody": "={{ $json }}",
    "options": {"timeout": 300000, "response": {"response": {"neverError": True}}}
}, 4.5, [X + 1340, Y - 100])
mk_code('DU Parse submit', """
const r = $json;
const b = (r.body && typeof r.body === 'object') ? r.body : r;
const creatifyId = String(b.creatify_id || r.creatify_id || '');
const genId = String(b.generation_id || r.generation_id || '');
if (!creatifyId || !genId) return [{ json: { ok: false, err: String((r.error && r.error.message) || r.error || 'пустой ответ') } }];
return [{ json: { ok: true, creatify_id: creatifyId, generation_id: genId } }];
""", [X + 1400, Y - 100])
mk_switch('Switch DU submit', [('={{ $json.ok }}', 'true')], [X + 1460, Y - 100], 2)

mk_code('DU Format fail link', f"""
const p = $('Parser').first().json;
const l = $('DU Parse link').first().json;
{ESC_LINE}
const text = '😕 Не удалось создать ссылку: ' + esc(l.err);
return [{{ json: {{ chat_id: p.chat_id, text: text }} }}];
""", [X + 1280, Y + 120])
mk_tg('TG du fail link', [[('📋 Меню', 'cmd:menu')]], [X + 1340, Y + 120])
mk_code('DU Format fail submit', f"""
const p = $('Parser').first().json;
const s = $('DU Parse submit').first().json;
{ESC_LINE}
const text = '😕 Не удалось запустить генерацию: ' + esc(s.err);
return [{{ json: {{ chat_id: p.chat_id, text: text }} }}];
""", [X + 1520, Y + 120])
mk_tg('TG du fail submit', [[('📋 Меню', 'cmd:menu')]], [X + 1580, Y + 120])
mk_code('DU Build reset', f"""
return [{{ json: {{ sql: "UPDATE sessions SET state='IDLE', quick_payload=NULL, updated_at=datetime('now') WHERE tg_user_id = ?", params: [{TG}] }} }}];
""", [X + 1640, Y + 120])
mk_http_db('DU HTTP reset', [X + 1700, Y + 120])

# connections DU
conn('Switch cmd', 32, 'DU Check state')
conn('DU Check state', 0, 'DU HTTP state')
conn('DU HTTP state', 0, 'DU Parse state')
conn('DU Parse state', 0, 'Switch DU route')
conn('Switch DU route', 0, 'DU LB creatify')
conn('Switch DU route', 1, 'DU Format wrong')
conn('Switch DU route', 2, 'RG Format gen')
conn('Switch DU route', 3, 'TG regen')
conn('DU Format wrong', 0, 'TG du wrong')
conn('DU LB creatify', 0, 'DU LB parse')
conn('DU LB parse', 0, 'DU Gate')
conn('DU Gate', 0, 'Switch DU gate')
conn('Switch DU gate', 0, 'DU Format gen')
conn('Switch DU gate', 1, 'DU Format low')
conn('Switch DU gate', 2, 'DU Format cap')
conn('DU Format gen', 0, 'TG du gen')
conn('DU Format low', 0, 'TG du low')
conn('DU Format cap', 0, 'TG du cap')
conn('TG du gen', 0, 'DU Update state')
conn('DU Update state', 0, 'DU HTTP update')
conn('DU HTTP update', 0, 'DU Build settings')
conn('DU Build settings', 0, 'DU HTTP settings')
conn('DU HTTP settings', 0, 'DU Build script')
conn('DU Build script', 0, 'DU HTTP script')
conn('DU HTTP script', 0, 'DU Build link body')
conn('DU Build link body', 0, 'DU HTTP link')
conn('DU HTTP link', 0, 'DU Parse link')
conn('DU Parse link', 0, 'Switch DU link')
conn('Switch DU link', 0, 'DU Build submit')
conn('Switch DU link', 1, 'DU Format fail link')
conn('DU Format fail link', 0, 'TG du fail link')
conn('TG du fail link', 0, 'DU Build reset')
conn('DU Build reset', 0, 'DU HTTP reset')
conn('DU Build submit', 0, 'DU HTTP submit')
conn('DU HTTP submit', 0, 'DU Parse submit')
conn('DU Parse submit', 0, 'Switch DU submit')
conn('Switch DU submit', 1, 'DU Format fail submit')
conn('DU Format fail submit', 0, 'TG du fail submit')
conn('TG du fail submit', 0, 'DU Build reset')

# =========================================================
# 5) RG branch (regen): RG answer -> DU Check state (shared chain)
# =========================================================
conns['RG answer']['main'] = [[{"node": "DU Check state", "type": "main", "index": 0}]]
mk_code('RG Format gen', f"""
const p = $('Parser').first().json;
{ESC_LINE}
const text = esc('🔁 Перегенерирую...');
return [{{ json: {{ chat_id: p.chat_id, text: text }} }}];
""", [X + 260, Y + 340])
mk_tg('TG rg gen', [[('📋 Меню', 'cmd:menu')]], [X + 320, Y + 340])
conn('RG Format gen', 0, 'TG rg gen')
conn('TG rg gen', 0, 'DU Update state')

# =========================================================
# 6) CN Build: + quick_payload=NULL
# =========================================================
by_name['CN Build']['parameters']['jsCode'] = f"""
return [{{ json: {{ sql: "UPDATE sessions SET state = 'IDLE', topic_id = NULL, script_id = NULL, generation_id = NULL, selected_platforms = NULL, post_at = NULL, quick_payload = NULL, updated_at = datetime('now') WHERE tg_user_id = ?", params: [{TG}] }} }}];
"""

# =========================================================
# 7) Switch cmd connections: rebuild main (34 outputs)
# =========================================================
old_main = ORIG_CMD_MAIN  # 32 entries, out[31]=Gate Build
assert len(old_main) == 32, f"expected 32 outputs, got {len(old_main)}"
gate_build_entry = old_main[31]
new_main = old_main[:31] + [
    [{"node": "UV Build state", "type": "main", "index": 0}],
    [{"node": "DU Check state", "type": "main", "index": 0}],
    gate_build_entry,
]
conns['Switch cmd']['main'] = new_main

# =========================================================
# write back (indent=1, ensure_ascii=False, no trailing newline)
# =========================================================
with open(PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=1, ensure_ascii=False)

print(f"OK: {len(nodes)} nodes")
