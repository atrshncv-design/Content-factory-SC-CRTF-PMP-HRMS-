#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix-avatar-callback.py — починить callback_data кнопки «Видео с аватаром».

Проблема: callback_data = '={{ \\"cmd:avatar_video\\" }}' (ДВА бэкслеша в строке)
-> n8n Expression.renderExpression падает 'invalid syntax' на ноде с этой кнопкой.
Эталон рабочих кнопок: '={{ "cmd:gen_url2video" }}' (ОДИН бэкслеш = просто
экранирование кавычки для n8n-выражения).

Чиним во ВСЕХ TG-нодах: заменяем callback_data со значением, содержащим
двойной бэкслеш перед кавычками внутри 'cmd:avatar_video', на одинарный.
"""
import json

PATH = 'workflows/wf-tg-bot.json'
BS = chr(92)  # один бэкслеш

with open(PATH, 'r', encoding='utf-8') as f:
    d = json.load(f)
wf = d[0] if isinstance(d, list) else d

BAD_1 = '={{ ' + BS + BS + '"cmd:avatar_video' + BS + BS + '" }}'   # два бэкслеша
BAD_2 = '={{ ' + BS + BS + BS + BS + '"cmd:avatar_video' + BS + BS + BS + BS + '" }}'  # четыре (если где-то утроилось)
GOOD = '={{ ' + BS + '"cmd:avatar_video' + BS + '" }}'              # один бэкслеш

fixed_nodes = []
total_buttons = 0
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
            total_buttons += 1
            af = b.get('additionalFields') or {}
            cb = af.get('callback_data', '')
            if 'cmd:avatar_video' in cb and cb != GOOD:
                if BAD_1 in cb or BAD_2 in cb:
                    af['callback_data'] = GOOD
                    changed = True
    if changed:
        fixed_nodes.append(n['name'])

with open(PATH, 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, indent=1)

print('Проверено кнопок:', total_buttons)
print('Исправлены ноды:', fixed_nodes)
