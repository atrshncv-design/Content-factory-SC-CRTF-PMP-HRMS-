#!/usr/bin/env python3
"""Оркестраторский валидатор wf-tg-bot после каждого тикета UX-реворка.
Запуск: python3 .scratch/bot-ux-menu/validate_workflow.py <wf.json> [--expect-<feature>]
Проверки: JSON валиден, BFS-достижимость от tg-trigger, сломанные callback_data
({{ без =), дубли id, node --check всех jsCode (требует node в PATH), lint."""
import json, subprocess, sys, tempfile, os, re

path = sys.argv[1]
data = json.load(open(path))
wf = data[0] if isinstance(data, list) else data
nodes = wf['nodes']
conns = wf.get('connections', {})
by_name = {n['name']: n for n in nodes}
issues = []
warns = []

# 1. duplicate node names / ids
seen = {}
for n in nodes:
    if n['name'] in seen:
        issues.append(f"ДУБЛЬ имени ноды: {n['name']}")
    seen[n['name']] = 1
ids = [n.get('id') for n in nodes]
if len(set(ids)) != len(ids):
    issues.append(f"ДУБЛЬ id нод: {len(ids) - len(set(ids))}")

# 2. BFS от tg-trigger
adj = {}
for src, cm in conns.items():
    for arrs in cm.get('main', []):
        if isinstance(arrs, list):
            for a in arrs:
                if isinstance(a, dict):
                    adj.setdefault(src, []).append(a['node'])
start = 'tg-trigger' if 'tg-trigger' in by_name else next(iter(by_name))
visited, stack = set(), [start]
while stack:
    x = stack.pop()
    if x in visited: continue
    visited.add(x)
    stack.extend(adj.get(x, []))
unreach = [n['name'] for n in nodes if n['name'] not in visited]
if unreach:
    issues.append(f"НЕДОСТИЖИМЫЕ ноды ({len(unreach)}): {unreach[:10]}...")

# 3. broken callback_data: содержит '{{' без префикса '='
for n in nodes:
    if n['type'] != 'n8n-nodes-base.telegram': continue
    kb = n.get('parameters', {}).get('inlineKeyboard', {})
    rows_val = kb.get('rows', [])
    if isinstance(rows_val, str):  # expression-клавиатура (динамические кнопки) — пропускаем
        continue
    for r in rows_val:
        if not isinstance(r, dict): continue
        for b in (r.get('row', {}) if isinstance(r.get('row'), dict) else {}).get('buttons', []):
            cb = (b.get('additionalFields') or {}).get('callback_data', '')
            if '{{' in cb and not cb.lstrip().startswith('={{'):
                issues.append(f"СЛОМАННЫЙ callback_data в {n['name']}: {cb[:60]}")

# 4. node --check всех jsCode
code_nodes = [n for n in nodes if n['type'] == 'n8n-nodes-base.code']
for n in code_nodes:
    js = n['parameters'].get('jsCode', '')
    if not js.strip(): continue
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as f:
        f.write(js)
        tmp = f.name
    r = subprocess.run(['node', '--check', tmp], capture_output=True, text=True)
    os.unlink(tmp)
    if r.returncode != 0:
        issues.append(f"node --check FAIL {n['name']}: {r.stderr.strip()[:200]}")

# 5. Парсер/команды: наличие ожидаемых веток (если --expect передано)
expect = [a[len('--expect-'):] for a in sys.argv[2:] if a.startswith('--expect-')]
scmd = by_name.get('Switch cmd')
if scmd:
    rules = [r['conditions']['conditions'][0]['rightValue'] for r in scmd['parameters']['rules']['values']]
    for e in expect:
        if e not in rules:
            warns.append(f"Нет правила Switch cmd для: {e}")

print(f"Файл: {path}")
print(f"Нод: {len(nodes)} | Связей-источников: {len(conns)}")
print(f"Проверка callback_data: {'OK' if not any('СЛОМАННЫЙ' in i for i in issues) else 'ЕСТЬ ПОЛОМКИ'}")
print(f"Проверка jsCode: {sum(1 for i in issues if 'node --check FAIL' in i)} ошибок")
if expects := [i for i in issues if 'НЕДОСТИЖИМЫЕ' in i]:
    print(expects[0])
print("\n=== ISSUES ===")
for i in issues: print("❌", i)
print("\n=== WARNS ===")
for w in warns: print("⚠️", w)
if not issues:
    print("\n✅ ВАЛИДАЦИЯ ПРОЙДЕНА (0 issues)")
sys.exit(1 if issues else 0)
