#!/usr/bin/env python3
"""Тикет 09: E2E smoke-симуляция цепочки /start → publish (0 кредитов).
Стабит $('Node'), $json и $input (по образцу .scratch/ticket02_sim_chain.py +
sim_combined.py). Каждая проверка — реальный jsCode из workflows/*.json.
"""
import json, subprocess, sys, os, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)
WF_TG = 'workflows/wf-tg-bot.json'
WF_WEB = 'workflows/wf-creatify-webhook.json'
WF_SUB = 'workflows/wf-creatify-submit.json'
WF_LINK = 'workflows/wf-creatify-link.json'
WF_AN = 'workflows/wf-analytics.json'
WF_PUB = 'workflows/wf-publish.json'

passed = 0
fails = []

def load_wf(p):
    data = json.load(open(p, encoding='utf-8'))
    return data[0] if isinstance(data, list) else data

def run_js(wf_path, node_name, nodes=None, json_=None, input_items=None):
    wf = load_wf(wf_path)
    node = next(n for n in wf['nodes'] if n['name'] == node_name)
    js = node['parameters']['jsCode']
    stub = []
    stub.append("const __M = " + json.dumps(nodes or {}, ensure_ascii=False) + ";")
    stub.append("const $ = (n) => ({ first: () => ({ json: __M[n] || {} }) });")
    stub.append("const $json = " + json.dumps(json_ or {}, ensure_ascii=False) + ";")
    if input_items is not None:
        stub.append("const $input = { all: () => " + json.dumps([{"json": x} for x in input_items], ensure_ascii=False) + ", first: () => ({ json: " + json.dumps(input_items[0], ensure_ascii=False) + " }) };")
    else:
        stub.append("const $input = { all: () => [], first: () => ({ json: {} }) };")
    code = "\n".join(stub) + "\nconst __R = (() => {\n" + js + "\n})();\nconsole.log(JSON.stringify(__R));"
    tmp = "/tmp/_t09_sim.js"
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(code)
    r = subprocess.run(['node', tmp], capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise RuntimeError(f"NODE ERROR {node_name}: {r.stderr[:400]}")
    return json.loads(r.stdout)

def check(name, cond, extra=''):
    global passed
    status = '✅' if cond else '❌'
    print(f"  {status} {name} {extra}")
    if not cond:
        fails.append(name)
    passed += 1

# ============ ЗВЕНО 1: /start → Parser ============
print("=== 1. TG /start → Parser → Switch cmd ===")
r = run_js(WF_TG, 'Parser', input_items=[{'message': {'text': '/start', 'from': {'id': 941296693}, 'chat': {'id': 941296693}, 'message_id': 1}}])
out = r[0]['json']
check('Parser: /start → command=start', out.get('command') == 'start', f"({out.get('command')})")
check('Parser: tg_user_id проброшен', out.get('tg_user_id') == 941296693)
check('Parser: kind=message', out.get('kind') == 'message')

# ============ ЗВЕНО 2: Профиль (GPF, клиентские профили) ============
print("=== 2. Профиль (GPF) ===")
r = run_js(WF_TG, 'GPF Build', nodes={'Parser': {'tg_user_id': 941296693}})
sql = r[0]['json']['sql']
check('GPF Build: SQL читает профиль', 'client_profile' in sql or 'profile_draft' in sql or 'SELECT' in sql)

# ============ ЗВЕНО 3: Аналитика (SC) ============
print("=== 3. Аналитика (SC) ===")
r = run_js(WF_TG, 'SC Build analytics body', nodes={'Parser': {'tg_user_id': 941296693}}, json_={'rows': [{'ac_id': 1}]})
check('SC Build analytics body: client_id=1', r[0]['json']['client_id'] == 1)
check('SC Build analytics body: find_competitors=false', r[0]['json']['find_competitors'] is False)

# SC Check analytics с мок-ответом wf-analytics (контракт candidates[])
now = time.time(); H = 3600
cands = [
    {'title': 'KUKA welding arc', 'source_platform': 'instagram', 'source_url': 'https://www.instagram.com/reel/A1/', 'author': '@w', 'metrics': {'views': 120000, 'likes': 8000, 'shares': 1500, 'comments': 300}, 'ts_unix': now - 26*H, 'transcript_excerpt': 'x', 'feasibility_hint': 'high', 'age_hours': 26, 'virality_index': 8.4},
]
r = run_js(WF_TG, 'SC Check analytics', nodes={'SC HTTP wf-analytics': {'candidates': cands}})
check('SC Check analytics: ok=true', r[0]['json']['ok'] is True)
r = run_js(WF_TG, 'SC Check analytics', nodes={'SC HTTP wf-analytics': {'error': 'no credits'}})
check('SC Check analytics: ошибка → понятный текст', r[0]['json']['ok'] is False and 'Попробуй' in r[0]['json']['text'])

# SC Build bridge prompt
r = run_js(WF_TG, 'SC Build bridge prompt', nodes={'SC HTTP wf-analytics': {'candidates': cands}, 'SC CTX Format': {'ctx': 'Клиент: Robotec, ниша: сварка'}})
p = r[0]['json']['prompt']
check('SC Build bridge prompt: skill=analyst', r[0]['json']['skill'] == 'analyst')
check('SC Build bridge prompt: кандидаты в промпте', 'KUKA welding arc' in p and 'Кандидаты трендов' in p)

# SC Parse topic (мок ответа LLM-аналитика)
r = run_js(WF_TG, 'SC Parse topic', nodes={'SC HTTP bridge analyst': {'answer': '{"chosen": {"title": "Сварка роботом KUKA", "source_url": "https://www.instagram.com/reel/A1/", "source_platform": "instagram", "rationale": "высокий охват", "feasibility": "high", "adaptation_for_client": "для Robotec", "target_length_sec": 30}}'}})
t = r[0]['json']
check('SC Parse topic: ok=true, title', t.get('ok') is True and t.get('title') == 'Сварка роботом KUKA')
check('SC Parse topic: target_length=30', t.get('target_length') == 30)

# SC Build insert topic
r = run_js(WF_TG, 'SC Build insert topic', nodes={'SC Parse topic': t})
check('SC Build insert topic: INSERT INTO topics', 'INSERT INTO topics' in r[0]['json']['sql'])
check('SC Build insert topic: client_id=1 (Robotec)', r[0]['json']['params'][0] == 'Сварка роботом KUKA')

# ============ ЗВЕНО 4: Сценарий (AU Parse script) ============
print("=== 4. Сценарий (AU) ===")
r = run_js(WF_TG, 'AU Parse script', nodes={'AU HTTP bridge scriptwriter': {'answer': '{"hook": "Заводы теряют миллионы", "body": "Робот KUKA варит идеальный шов каждые 30 секунд. Это в 4 раза быстрее человека и без брака.", "cta": "Узнайте, как внедрить роботизированную сварку на вашем заводе.", "full_text": "Заводы теряют миллионы на браке сварки. Робот KUKA варит идеальный шов каждые 30 секунд. Это в 4 раза быстрее человека и без брака. Узнайте, как внедрить роботизированную сварку на вашем заводе.", "target_length_sec": 30, "estimated_words": 45, "format_tag": "demo"}'}})
s = r[0]['json']
check('AU Parse script: ok=true, full_text чистый', s.get('ok') is True and 'Заводы теряют' in s.get('full_text',''))
check('AU Parse script: без markdown-разметки', '**' not in s.get('full_text','') and '`' not in s.get('full_text',''))
check('AU Parse script: target_length=30', s.get('target_length') == 30)

# ============ ЗВЕНО 5: link ============
print("=== 5. link (wf-creatify-link) ===")
r = run_js(WF_LINK, 'Code assemble', json_={'link': {'id': 'LINK-REAL-1'}})
check('link: Code assemble link.id → link_id', r[0]['json']['link_id'] == 'LINK-REAL-1')

# ============ ЗВЕНО 6: submit (wf-creatify-submit) ============
print("=== 6. submit (wf-creatify-submit) ===")
good_payload = {
    'name': 'robotec-welding-20260816', 'link': 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
    'visual_style': 'DynamicProductTemplate', 'script_style': 'ProblemSolutionV2',
    'aspect_ratio': '9x16', 'video_length': 30, 'language': 'ru',
    'target_audience': 'директора заводов', 'target_platform': 'Instagram',
    'model_version': 'aurora_v1_fast',
    'override_script': 'Заводы теряют миллионы на браке сварки. KUKA варит идеальный шов каждые 30 секунд.',
    'background_music_volume': 0.15, 'voiceover_volume': 1.0,
    'no_background_music': False, 'no_caption': False, 'no_cta': False,
    'webhook_url': 'https://factory.example.com/webhook/factory/creatify/6d8f2a41c9e7b3d5f0a1c4e8',
}
env_payload = {'script_id': 42, 'client_id': 1, 'json_payload': good_payload, 'link_id': 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'}
r = run_js(WF_SUB, 'Code validate', json_=env_payload)
check('submit: Code validate валидный', r[0]['json']['valid'] == 1)

# ============ ЗВЕНО 7: Webhook done → видео в чат ============
print("=== 7. webhook done (wf-creatify-webhook) ===")
select_row = {'id': 99, 'script_id': 42, 'full_text': 'Заводы теряют миллионы на браке сварки.', 'script_excerpt': 'Заводы теряют…', 'topic_id': 7, 'session_qp': '{"flow":"sh"}', 'tg_user_id': 941296693}
r = run_js(WF_WEB, 'Code done build', json_={'rows': [select_row]},
           nodes={'Webhook': {'body': {'video_output_url': 'https://cdn.example.com/v1.mp4'}}})
d = r[0]['json']
check('webhook: Code done build id/video', d['id'] == '99' and 'v1.mp4' in d['video_output_url'])
check('webhook: Code done build flow=sh', d['flow'] == 'sh')
check('webhook: auto_approve=false', d['auto_approve'] is False)

r = run_js(WF_WEB, 'Build update done', json_=d)
check('webhook: Build update done → UPDATE generations status=done', 'UPDATE generations SET status=\'done\'' in r[0]['json']['sql'] and 'webhook_received=1' in r[0]['json']['sql'])

r = run_js(WF_WEB, 'Build session update', nodes={'Code done build': d, 'HTTP SELECT': {'rows': [select_row]}})
check('webhook: Build session update → VIDEO_AWAIT', 'VIDEO_AWAIT' in r[0]['json']['sql'])

r = run_js(WF_WEB, 'Build stage3', nodes={'Code done build': d, 'HTTP SELECT': {'rows': [select_row]}, 'Webhook': {'body': {'video_output_url': 'https://cdn.example.com/v1.mp4'}}})
st = r[0]['json']
check('webhook: stage3 chat_id=оператор', st['chat_id'] == 941296693)
check('webhook: stage3 video есть', 'v1.mp4' in st['video'])
check('webhook: stage3 текст «Этап 3/4»', 'Этап 3/4' in st['text'])

# ============ ЗВЕНО 8: Публикация (wf-publish) ============
print("=== 8. publish (wf-publish) ===")
r = run_js(WF_TG, 'AU Build publish body', nodes={'AU Check pub': {'allow': True, 'platforms': ['instagram'], 'post_at': '2026-08-16T12:00:00Z', 'generation_id': 99, 'script_id': 42, 'full_text': 'Заводы теряют миллионы', 'video_output_url': 'https://cdn.example.com/v1.mp4'}})
pb = r[0]['json']
check('AU Build publish body: platforms+video', pb['platforms'] == ['instagram'] and pb['file_ids'] == ['https://cdn.example.com/v1.mp4'])

r = run_js(WF_TG, 'AU Check result', nodes={'AU HTTP wf-publish': {'body': {'post_id': 12345}}})
check('AU Check result: post_id → ok', r[0]['json']['ok'] is True)
r = run_js(WF_TG, 'AU Check result', nodes={'AU HTTP wf-publish': {'body': {'error': {'message': 'no account'}}}})
check('AU Check result: ошибка → понятный текст', r[0]['json']['ok'] is False and 'no account' in r[0]['json']['text'])

print(f"\n{'🟢' if not fails else '🔴'} Симы: {passed} проверок, фейлов: {len(fails)}")
if fails:
    for f in fails: print("  FAIL:", f)
    sys.exit(1)
