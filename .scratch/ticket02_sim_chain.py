#!/usr/bin/env python3
"""Тикет 02: симуляции мок-цепочки wf-analytics → link → submit (0 кредитов)."""
import json
import subprocess
import sys

def run_js(wf_path, node_name, nodes=None, json_=None, input_items=None):
    data = json.load(open(wf_path, encoding='utf-8'))
    wf = data[0] if isinstance(data, list) else data
    node = next(n for n in wf['nodes'] if n['name'] == node_name)
    js = node['parameters']['jsCode']
    stub = []
    stub.append("const __M = " + json.dumps(nodes or {}, ensure_ascii=False) + ";")
    stub.append("const $ = (n) => ({ first: () => ({ json: __M[n] || {} }) });")
    stub.append("const $json = " + json.dumps(json_ or {}, ensure_ascii=False) + ";")
    if input_items is not None:
        stub.append("const $input = { all: () => " + json.dumps([{"json": x} for x in input_items], ensure_ascii=False) + " };")
    code = "\n".join(stub) + "\nconst __R = (() => {\n" + js + "\n})();\nconsole.log(JSON.stringify(__R));"
    tmp = "/tmp/_t02_sim.js"
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(code)
    r = subprocess.run(['node', tmp], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  NODE ERROR {node_name}: {r.stderr[:500]}")
        sys.exit(1)
    return json.loads(r.stdout)

WF_A = 'workflows/wf-analytics.json'
WF_L = 'workflows/wf-creatify-link.json'
WF_S = 'workflows/wf-creatify-submit.json'
passed = 0

def check(name, cond, extra=''):
    global passed
    status = '✅' if cond else '❌'
    print(f"  {status} {name} {extra}")
    if not cond:
        sys.exit(1)
    passed += 1

# ---------- wf-analytics: Postprocess (мок Merge: 6 свежих записей) ----------
now = __import__('time').time()
H = 3600
mock_records = [
    {'title': 'KUKA welding arc', 'source_platform': 'instagram', 'source_url': 'https://www.instagram.com/reel/A1/', 'author': '@w', 'metrics': {'views': 120000, 'likes': 8000, 'shares': 1500, 'comments': 300}, 'ts_unix': now - 26 * H, 'transcript_excerpt': 'x', 'feasibility_hint': 'high'},
    {'title': 'Palletizer 40/min', 'source_platform': 'instagram', 'source_url': 'https://www.instagram.com/reel/A2/', 'author': '@p', 'metrics': {'views': 34000, 'likes': 2100, 'shares': 600, 'comments': 90}, 'ts_unix': now - 5 * H, 'transcript_excerpt': 'x', 'feasibility_hint': 'medium'},  # слишком свежий — отсеется
    {'title': 'Cobot picks parts', 'source_platform': 'instagram', 'source_url': 'https://www.instagram.com/reel/A3/', 'author': '@c', 'metrics': {'views': 45000, 'likes': 3200, 'shares': 400, 'comments': 120}, 'ts_unix': now - 50 * H, 'transcript_excerpt': 'x', 'feasibility_hint': 'high'},
    {'title': 'Six-axis sorts', 'source_platform': 'instagram', 'source_url': 'https://www.instagram.com/reel/A4/', 'author': '@w', 'metrics': {'views': 28000, 'likes': 1500, 'shares': 250, 'comments': 60}, 'ts_unix': now - 100 * H, 'transcript_excerpt': 'x', 'feasibility_hint': 'medium'},  # старый — отсеется
    {'title': 'KUKA tiktok', 'source_platform': 'tiktok', 'source_url': 'https://www.tiktok.com/video/1', 'author': '@r', 'metrics': {'views': 99000, 'likes': 6100, 'shares': 2100, 'comments': 180}, 'ts_unix': now - 30 * H, 'transcript_excerpt': 'x', 'feasibility_hint': 'high'},
    {'title': 'Cobot conveyor', 'source_platform': 'tiktok', 'source_url': 'https://www.tiktok.com/video/2', 'author': '@c', 'metrics': {'views': 89000, 'likes': 5100, 'shares': 2200, 'comments': 80}, 'ts_unix': now - 60 * H, 'transcript_excerpt': 'x', 'feasibility_hint': 'high'},
    {'title': 'YT breakdown', 'source_platform': 'youtube', 'source_url': 'https://www.youtube.com/watch?v=1', 'author': '@f', 'metrics': {'views': 210000, 'likes': 15000, 'shares': 900, 'comments': 700}, 'ts_unix': now - 20 * H, 'transcript_excerpt': 'x', 'feasibility_hint': 'high'},
    {'title': 'Welder vs human', 'source_platform': 'youtube', 'source_url': 'https://www.youtube.com/watch?v=2', 'author': '@w', 'metrics': {'views': 67000, 'likes': 4100, 'shares': 300, 'comments': 250}, 'ts_unix': now - 45 * H, 'transcript_excerpt': 'x', 'feasibility_hint': 'high'},
]
print('wf-analytics → Postprocess (мок-режим):')
r = run_js(WF_A, 'Postprocess', input_items=mock_records)
out = r[0]['json']
check('candidates — массив, непустой', isinstance(out.get('candidates'), list) and len(out['candidates']) > 0, f"({len(out.get('candidates', []))} шт)")
c = out['candidates'][0]
for fld in ['title', 'source_platform', 'source_url', 'author', 'metrics', 'age_hours', 'virality_index', 'transcript_excerpt', 'feasibility_hint']:
    check(f'candidate[{fld}]', fld in c)
check('метрики views/likes/shares', all(k in (c['metrics'] or {}) for k in ['views', 'likes', 'shares']))
check('meta.credits_spent=0', out.get('meta', {}).get('credits_spent') == 0)
# контракт бота: SC Check analytics читает r.candidates
check('контракт бота: r.candidates существует', 'candidates' in out)

print('wf-analytics → Code balance (мок HTTP credit-balance):')
r = run_js(WF_A, 'Code balance', json_={'body': {'creditCount': 500}})
check('balance=500, balance_unavailable=false', r[0]['json']['balance'] == 500 and r[0]['json']['balance_unavailable'] is False)

# ---------- wf-creatify-link ----------
print('wf-creatify-link → Code mock:')
r = run_js(WF_L, 'Code mock')
m = r[0]['json']
check('mock id/status/mock', isinstance(m.get('id'), str) and len(m['id']) >= 8 and m.get('status') == 'ok' and m.get('mock') is True)

print('wf-creatify-link → Code assemble (мок):')
r = run_js(WF_L, 'Code assemble', json_={'id': '11111111-2222-3333-4444-555555555555', 'status': 'ok', 'mock': True})
check('link_id из мока', r[0]['json']['link_id'] == '11111111-2222-3333-4444-555555555555')
check('raw сохранён', 'raw' in r[0]['json'])

print('wf-creatify-link → Code assemble (форма {link:{id}}):')
r = run_js(WF_L, 'Code assemble', json_={'link': {'id': 'LINK-REAL-1'}})
check('link_id из link.id', r[0]['json']['link_id'] == 'LINK-REAL-1')

print('wf-creatify-link → Code assemble (форма {data:{id}}):')
r = run_js(WF_L, 'Code assemble', json_={'data': {'id': 'LINK-REAL-2'}})
check('link_id из data.id', r[0]['json']['link_id'] == 'LINK-REAL-2')

# ---------- wf-creatify-submit ----------
good_payload = {
    'name': 'robotec-welding-20260816',
    'link': 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
    'visual_style': 'DynamicProductTemplate',
    'script_style': 'ProblemSolutionV2',
    'aspect_ratio': '9x16',
    'video_length': 30,
    'language': 'ru',
    'target_audience': 'директора заводов',
    'target_platform': 'Instagram',
    'model_version': 'aurora_v1_fast',
    'override_script': 'Заводы теряют миллионы на браке сварки. KUKA варит идеальный шов каждые 30 секунд.',
    'background_music_volume': 0.15,
    'voiceover_volume': 1.0,
    'no_background_music': False,
    'no_caption': False,
    'no_cta': False,
    'webhook_url': 'https://factory.example.com/webhook/factory/creatify/6d8f2a41c9e7b3d5f0a1c4e8',
}
env_payload = {'script_id': 42, 'client_id': 1, 'json_payload': good_payload, 'link_id': 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'}

print('wf-creatify-submit → Code validate (валидный payload):')
r = run_js(WF_S, 'Code validate', json_=env_payload)
check('valid=1, errors=[]', r[0]['json']['valid'] == 1 and r[0]['json']['errors'] == [], str(r[0]['json']['errors']))

print('wf-creatify-submit → Code validate (нет link):')
bad = json.loads(json.dumps(env_payload)); bad['json_payload'] = json.loads(json.dumps(good_payload)); del bad['json_payload']['link']
r = run_js(WF_S, 'Code validate', json_=bad)
check('valid=0, missing link', r[0]['json']['valid'] == 0 and 'missing link' in r[0]['json']['errors'])

print('wf-creatify-submit → Code validate (override_script c TG-разметкой):')
bad2 = json.loads(json.dumps(env_payload)); bad2['json_payload'] = json.loads(json.dumps(good_payload)); bad2['json_payload']['override_script'] = '**Заводы** теряют миллионы `на браке` сварки.'
r = run_js(WF_S, 'Code validate', json_=bad2)
check('valid=0, markup', r[0]['json']['valid'] == 0 and 'markup' in ' '.join(r[0]['json']['errors']))

print('wf-creatify-submit → Code validate (override_script объект):')
bad3 = json.loads(json.dumps(env_payload)); bad3['json_payload'] = json.loads(json.dumps(good_payload)); bad3['json_payload']['override_script'] = {'text': 'x'}
r = run_js(WF_S, 'Code validate', json_=bad3)
check('valid=0, not string', r[0]['json']['valid'] == 0 and 'must be string' in ' '.join(r[0]['json']['errors']))

print('wf-creatify-submit → Code validate (video_length вне enum):')
bad4 = json.loads(json.dumps(env_payload)); bad4['json_payload'] = json.loads(json.dumps(good_payload)); bad4['json_payload']['video_length'] = 90
r = run_js(WF_S, 'Code validate', json_=bad4)
check('valid=0, video_length', r[0]['json']['valid'] == 0 and 'video_length' in ' '.join(r[0]['json']['errors']))

print('wf-creatify-submit → Code validate (DU: пустой override_script — допустимо):')
du = json.loads(json.dumps(env_payload)); du['json_payload'] = json.loads(json.dumps(good_payload)); du['json_payload']['override_script'] = ''
r = run_js(WF_S, 'Code validate', json_=du)
check('valid=1 (DU пустой override_script)', r[0]['json']['valid'] == 1)

print('wf-creatify-submit → Code mock:')
r = run_js(WF_S, 'Code mock')
m = r[0]['json']
check('mock pending', isinstance(m.get('id'), str) and m.get('status') == 'pending' and m.get('mock') is True)

print('wf-creatify-submit → Code extract (мок INSERT generation):')
r = run_js(WF_S, 'Code extract', json_={'id': 'video-1111', 'status': 'pending', 'progress': 0, 'mock': True},
           nodes={'INSERT generation': {'lastInsertRowid': 77}})
check('creatify_id + generation_id', r[0]['json']['creatify_id'] == 'video-1111' and r[0]['json']['generation_id'] == 77)

print('wf-creatify-submit → Build update body:')
r = run_js(WF_S, 'Build update body', json_={'creatify_id': 'video-1111', 'generation_id': 77})
b = r[0]['json']
check('sql UPDATE generations', 'UPDATE generations SET creatify_id' in b.get('sql', '') and b['params'] == ['video-1111', 77])

print('wf-creatify-submit → Code balance (достаточно):')
r = run_js(WF_S, 'Code balance', json_={'body': {'remaining_credits': 120}})
check('balance=120', r[0]['json']['balance'] == 120)

print('wf-creatify-submit → Code balance (мало):')
r = run_js(WF_S, 'Code balance', json_={'body': {'remaining_credits': 30}})
check('balance=30 (< 50 → гейт low_credits)', r[0]['json']['balance'] == 30)

print(f"\n🟢 Все симы зелёные: {passed} проверок, 0 кредитов")
