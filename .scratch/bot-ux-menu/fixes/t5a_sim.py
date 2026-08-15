#!/usr/bin/env python3
"""T5a sim harness: stubs $('Node'), $json AND $input; runs new/modified Code nodes."""
import json, subprocess, sys

WF = '.scratch/bot-ux-menu/fixes/wf-tg-bot.json'
data = json.load(open(WF))
wf = data[0] if isinstance(data, list) else data
by = {n['name']: n for n in wf['nodes']}

PARSER = {"kind": "message", "tg_user_id": 941296693, "chat_id": 42, "command": "shorts",
          "args": {"url": None, "value": "роботы", "id": None, "platform": None, "handle": None, "section": None},
          "raw": "shorts роботы", "callback_action": None, "entity_id": None}

def sim(name, nodes=None, json_=None, input_=None):
    js = by[name]['parameters']['jsCode']
    stub = "const __M = " + json.dumps(nodes or {}, ensure_ascii=False) + ";\n"
    stub += "const $ = (n) => ({ first: () => ({ json: __M[n] || {} }) });\n"
    stub += "const $json = " + json.dumps(json_ or {}, ensure_ascii=False) + ";\n"
    stub += "const $input = { first: () => ({ json: " + json.dumps(input_ or {}, ensure_ascii=False) + " }) };\n"
    code = stub + "const __R = (() => {\n" + js + "\n})();\nconsole.log(JSON.stringify(__R));"
    tmp = '/tmp/_t5a_sim.js'
    open(tmp, 'w', encoding='utf-8').write(code)
    r = subprocess.run(['node', tmp], capture_output=True, text=True)
    if r.returncode != 0:
        return {'ERROR': r.stderr[:500]}
    try:
        return json.loads(r.stdout.strip())[0]['json']
    except Exception as e:
        return {'PARSE_ERR': str(e), 'out': r.stdout[:300]}

results = []

# --- SH Topic ---
r = sim('SH Topic', nodes={'Parser': PARSER}, input_={'topic': 'роботы', 'mode': 'x'})
results.append(('SH Topic direct', r.get('topic') == 'роботы' and r.get('regen') is False, r))
p2 = dict(PARSER); p2['command'] = 'unknown'; p2['args'] = dict(PARSER['args'], value=None); p2['raw'] = 'тема текстом'
r = sim('SH Topic', nodes={'Parser': p2}, input_={'mode': 'quick_shorts_topic'})
results.append(('SH Topic gate-text', r.get('topic') == 'тема текстом' and r.get('regen') is False, r))
r = sim('SH Topic', nodes={'Parser': PARSER}, input_={'mode': 'rg_shorts', 'topic': 'роботы'})
results.append(('SH Topic regen', r.get('topic') == 'роботы' and r.get('regen') is True, r))

# --- SH Gate ---
r = sim('SH Gate', nodes={'SH LB parse': {'creatify': 5}, 'SH Topic': {'topic': 'роботы', 'regen': False}})
results.append(('SH Gate low', r.get('ok') is False and r.get('reason') == 'low', r))
r = sim('SH Gate', nodes={'SH LB parse': {'creatify': 100}, 'SH Topic': {'topic': 'роботы', 'regen': False}})
results.append(('SH Gate ok cost5', r.get('ok') is True and r.get('cost') == 5, r))
r = sim('SH Gate', nodes={'SH LB parse': {'creatify': 100}, 'SH Topic': {'topic': 'x' * 12000, 'regen': False}})
results.append(('SH Gate ok cost10', r.get('ok') is True and r.get('cost') == 10, r))
r = sim('SH Gate', nodes={'SH LB parse': {'creatify': 100}, 'SH Topic': {'topic': 'x' * 60001, 'regen': False}})
results.append(('SH Gate cap', r.get('ok') is False and r.get('reason') == 'cap', r))

# --- SHT Format ---
r = sim('SHT Format', nodes={'Parser': PARSER, 'SHT Build': {'valid': False, 'redirect': True, 'text': '🔗 x'}, 'SHT HTTP': {}})
results.append(('SHT Format redirect', r.get('mode') == 'redirect' and '🔗' in r.get('text', ''), r))
r = sim('SHT Format', nodes={'Parser': PARSER, 'SHT Build': {'valid': True, 'topic': 'роботы'},
                             'SHT HTTP': {'ok': True, 'status': 'done', 'video_output': 'https://cdn.x/v.mp4', 'shorts_id': 'abc'}})
results.append(('SHT Format done', r.get('mode') == 'done' and r.get('video_output') == 'https://cdn.x/v.mp4' and r.get('shorts_id') == 'abc', r))
r = sim('SHT Format', nodes={'Parser': PARSER, 'SHT Build': {'valid': True, 'topic': 'роботы'},
                             'SHT HTTP': {'ok': True, 'status': 'done', 'items': [{'video_output': 'https://y.mp4'}], 'shorts_id': 'abc'}})
results.append(('SHT Format done-items', r.get('mode') == 'done' and r.get('video_output') == 'https://y.mp4', r))
r = sim('SHT Format', nodes={'Parser': PARSER, 'SHT Build': {'valid': True}, 'SHT HTTP': {'ok': False, 'error': 'low_credits'}})
results.append(('SHT Format rlow', r.get('mode') == 'rlow', r))
r = sim('SHT Format', nodes={'Parser': PARSER, 'SHT Build': {'valid': True}, 'SHT HTTP': {'ok': False, 'error': 'boom'}})
results.append(('SHT Format rerr', r.get('mode') == 'rerr' and r.get('err') == 'boom', r))
r = sim('SHT Format', nodes={'Parser': PARSER, 'SHT Build': {'valid': True}, 'SHT HTTP': {'ok': True, 'status': 'queued', 'shorts_id': 'abc'}})
results.append(('SHT Format async', r.get('mode') == 'async' and r.get('shorts_id') == 'abc', r))
r = sim('SHT Format', nodes={'Parser': PARSER, 'SHT Build': {'valid': True}, 'SHT HTTP': {'ok': True, 'status': 'done', 'shorts_id': 'abc'}})
results.append(('SHT Format done-novideo', r.get('mode') == 'rerr', r))

# --- SH Format gen / low / cap / rlow / rerr / async ---
r = sim('SH Format gen', nodes={'Parser': PARSER, 'SH Gate': {'regen': False}})
results.append(('SH Format gen normal', 'Пишу сценарий' in r.get('text', ''), r))
r = sim('SH Format gen', nodes={'Parser': PARSER, 'SH Gate': {'regen': True}})
results.append(('SH Format gen regen', 'Перегенерирую' in r.get('text', ''), r))
r = sim('SH Format low', nodes={'Parser': PARSER, 'SH Gate': {'cr': 5}})
results.append(('SH Format low', 'Недостаточно кредитов creatify: 5' in r.get('text', ''), r))
r = sim('SH Format cap', nodes={'Parser': PARSER, 'SH Gate': {'cost': 55}})
results.append(('SH Format cap', '55' in r.get('text', ''), r))
r = sim('SH Format rlow', nodes={'Parser': PARSER})
results.append(('SH Format rlow', 'Недостаточно кредитов creatify' in r.get('text', ''), r))
r = sim('SH Format rerr', nodes={'Parser': PARSER, 'SHT Format': {'err': 'boom'}})
results.append(('SH Format rerr', 'Шортс не создан: boom' in r.get('text', ''), r))
r = sim('SH Format async', nodes={'Parser': PARSER, 'SHT Format': {'shorts_id': 'abc'}})
results.append(('SH Format async', 'abc' in r.get('text', ''), r))

# --- Build/SQL nodes ---
r = sim('SH Build generation', nodes={'SHT Format': {'video_output': 'v', 'shorts_id': 'abc'}, 'SH Topic': {'topic': 'роботы'}})
ok = 'INSERT INTO generations' in r.get('sql', '') and r.get('params', [])[0] == '{"topic":"роботы","type":"ai_shorts"}'
results.append(('SH Build generation', ok, r))
r = sim('SH Build session', nodes={'SH HTTP generation': {'lastInsertRowid': 42}, 'SH Topic': {'topic': 'роботы'}, 'SHT Format': {'shorts_id': 'abc'}})
ok = r.get('params', [])[0] == '42' and r.get('params', [])[1] == '{"topic":"роботы","shorts_id":"abc"}'
results.append(('SH Build session', ok, r))
r = sim('SH Build buttons', nodes={'Parser': PARSER, 'SH HTTP generation': {'lastInsertRowid': 42}})
results.append(('SH Build buttons', r.get('gen_id') == '42', r))
r = sim('SH Update state', nodes={'SH Topic': {'topic': 'роботы'}})
results.append(('SH Update state', 'QUICK_SHORTS_GENERATING' in r.get('sql', '') and r.get('params', [])[0] == '{"topic":"роботы","script":null}', r))
r = sim('SH Ask update', nodes={})
results.append(('SH Ask update', 'QUICK_SHORTS_AWAIT_TOPIC' in r.get('sql', ''), r))
r = sim('SH Reset state', nodes={})
results.append(('SH Reset state', "state='IDLE'" in r.get('sql', ''), r))

# --- DU Parse state (regen routing) ---
def du_state(qp, cb='regen_gen', state='CYCLE_VIDEO_PENDING', cmd=None):
    du_rows = [{'state': state, 'quick_payload': json.dumps(qp)}]
    p = dict(PARSER); p['callback_action'] = cb; p['command'] = cmd
    return sim('DU Parse state', nodes={'Parser': p, 'DU HTTP state': {'rows': du_rows}})
r = du_state({'topic': 'роботы', 'shorts_id': 'abc'})
results.append(('DU Parse state rg_shorts', r.get('mode') == 'rg_shorts' and r.get('topic') == 'роботы', r))
r = du_state({'url': 'u', 'duration': 30})
results.append(('DU Parse state rg_ok (url)', r.get('mode') == 'rg_ok', r))
r = du_state({})
results.append(('DU Parse state rg_cycle', r.get('mode') == 'rg_cycle', r))
r = du_state({}, state='QUICK_URL_AWAIT_DUR', cb=None, cmd='dur')
results.append(('DU Parse state dur_ok', r.get('mode') == 'dur_ok', r))

# --- Gate Check ---
def gate_check(state, cmd='unknown'):
    p = dict(PARSER); p['command'] = cmd
    return sim('Gate Check', nodes={'Parser': p, 'Gate HTTP': {'rows': [{'state': state}]}})
r = gate_check('QUICK_SHORTS_AWAIT_TOPIC')
results.append(('Gate Check shorts_topic', r.get('mode') == 'quick_shorts_topic', r))
r = gate_check('QUICK_SHORTS_GENERATING')
results.append(('Gate Check shorts_generating', r.get('mode') == 'quick_url_generating', r))
r = gate_check('IDLE')
results.append(('Gate Check idle', r.get('mode') == 'normal', r))

print('%-34s %-5s %s' % ('CASE', 'STATUS', 'RESULT'))
fails = 0
for name, ok, out in results:
    print('%-34s %-5s %s' % (name, 'PASS' if ok else 'FAIL', json.dumps(out, ensure_ascii=False)[:180]))
    if not ok:
        fails += 1
print('\nTOTAL:', len(results), 'FAILS:', fails)
sys.exit(1 if fails else 0)
