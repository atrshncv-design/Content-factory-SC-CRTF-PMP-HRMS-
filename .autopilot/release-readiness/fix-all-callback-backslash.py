#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix-all-callback-backslash.py — убрать бэкслеш после '{{ ' во всех callback_data.

Баг: callback_data вида '={{ \\"cmd:xxx\\" }}' (бэкслеш 92 перед кавычкой 34)
-> n8n Expression.renderExpression: invalid syntax -> нода падает молча.
Рабочий эталон: '={{ "cmd:xxx" }}' (кавычка сразу после пробела).

Исправляем в каждой TG-ноде: если callback_data начинается с '={{ ' и сразу
за ним идёт бэкслеш(и) перед кавычкой, заменяем на эталон без бэкслешей.
"""
import json

PATH = 'workflows/wf-tg-bot.json'
BS = chr(92)

with open(PATH, 'r', encoding='utf-8') as f:
    d = json.load(f)
wf = d[0] if isinstance(d, list) else d

fixed_nodes = []
fixed_total = 0
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
            if not cb.startswith('={{ '):
                continue
            checked += 1
            # эталон: '={{ "' — после пробела сразу кавычка (34)
            if len(cb) > 5 and ord(cb[4]) == 34:
                continue  # уже рабочий
            # ищем: '={{ ' + бэкслеши + '"...'
            rest = cb[4:]  # после '={{ '
            k = 0
            while k < len(rest) and rest[k] == BS:
                k += 1
            if k > 0 and k < len(rest) and rest[k] == '"':
                # '={{ "' + хвост (кавычка уже в rest[k])
                good = '={{ "' + rest[k+1:]
                af['callback_data'] = good
                changed = True
                fixed_total += 1
            else:
                print('НЕОЖИДАННОЕ в', n['name'], ':', repr(cb))
    if changed:
        fixed_nodes.append(n['name'])

with open(PATH, 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, indent=1)

print('Проверено кнопок с callback:', checked)
print('Исправлено кнопок:', fixed_total)
print('Ноды:', fixed_nodes)
