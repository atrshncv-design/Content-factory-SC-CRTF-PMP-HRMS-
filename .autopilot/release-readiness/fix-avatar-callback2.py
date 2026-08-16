#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix-avatar-callback2.py — убрать лишний бэкслеш в callback_data аватарной кнопки.

Правильный формат (эталон gen_url2video): '={{ "cmd:gen_url2video" }}'
Сломанный: '={{ \\"cmd:avatar_video\\" }}' (бэкслеш перед кавычками ВНУТРИ
n8n-выражения -> Expression.renderExpression: invalid syntax -> нода падает).

Заменяем в каждой TG-ноде callback_data, содержащий 'cmd:avatar_video',
на эталонный формат без бэкслешей перед кавычками.
"""
import json

PATH = 'workflows/wf-tg-bot.json'
BS = chr(92)

GOOD = '={{ "' + 'cmd:avatar_video' + '" }}'
# возможные сломанные варианты: 1..4 бэкслеша перед кавычками
BAD_VARIANTS = []
for k in (1, 2, 3, 4):
    q = BS * k
    BAD_VARIANTS.append('={{ ' + q + '"cmd:avatar_video' + q + '" }}')

with open(PATH, 'r', encoding='utf-8') as f:
    d = json.load(f)
wf = d[0] if isinstance(d, list) else d

fixed_nodes = []
checked = 0
for n in wf['nodes']:
    if n['type'] != 'n8n-nodes-base.telegram':
        continue
    kb = n.get('parameters', {}).get('inlineKeyboard', {})
    rows = kb.get('rows', []) if isinstance(kb, dict) else []
    if isinstance(rows, str):
        continue
    changed = False
    for r in rows:
        row = r.get('row', {}) if isinstance(r, dict) else {}
        btns = row.get('buttons', []) if isinstance(row, dict) else []
        for b in btns:
            af = b.get('additionalFields') or {}
            cb = af.get('callback_data', '')
            if 'cmd:avatar_video' not in cb:
                continue
            checked += 1
            if cb == GOOD:
                continue
            if cb in BAD_VARIANTS:
                af['callback_data'] = GOOD
                changed = True
            else:
                print('НЕОЖИДАННЫЙ формат в', n['name'], ':', repr(cb))
    if changed:
        fixed_nodes.append(n['name'])

with open(PATH, 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, indent=1)

print('Проверено аватарных кнопок:', checked)
print('Исправлены ноды:', fixed_nodes)
