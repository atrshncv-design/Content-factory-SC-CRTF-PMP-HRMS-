#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix-inline-keyboard-expression.py — чиним rows-выражение в inlineKeyboard.

Баг: паттерн "inlineKeyboard": {"rows": "={{ $json.rows }}"} НЕ работает в n8n
2.34.4 — выражение внутри fixedCollection не вычисляется, addReplyMarkup делает
for (const row of keyboardData.rows) по СТРОКЕ (символам) -> пустая клавиатура,
кнопок нет (пользователь: «КУДА МНЕ НАЖИМАТЬ БЕЗ КНОПОК»).

Фикс: передавать ВСЮ inlineKeyboard выражением:
"inlineKeyboard": "={{ {rows: $json.rows} }}"
Тогда getNodeParameter('inlineKeyboard') возвращает вычисленный объект
{rows: [...]} и addReplyMarkup нормально его итерирует.

Меняем во всех TG-нодах, где rows — строка-выражение.
"""
import json

PATH = 'workflows/wf-tg-bot.json'

with open(PATH, 'r', encoding='utf-8') as f:
    d = json.load(f)
wf = d[0] if isinstance(d, list) else d

changed = []
for n in wf['nodes']:
    if n['type'] != 'n8n-nodes-base.telegram':
        continue
    kb = n.get('parameters', {}).get('inlineKeyboard', {})
    if isinstance(kb, dict) and isinstance(kb.get('rows'), str):
        # заменяем на выражение-объект
        n['parameters']['inlineKeyboard'] = '={{ {rows: $json.rows} }}'
        changed.append(n['name'])

with open(PATH, 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, indent=1)

print('Исправлены ноды:', changed)
