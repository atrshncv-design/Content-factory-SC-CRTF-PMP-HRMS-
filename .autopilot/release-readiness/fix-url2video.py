#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Фикс URL→видео: NOT NULL constraint failed: scripts.topic_id.
Все 3 места INSERT в scripts с возможным NULL topic_id -> 0-сентинель
(прецедент: generations.script_id=0; FK в SQLite off по умолчанию).
1) DU Build script  — VALUES (?, NULL, ...) -> VALUES (?, 0, ...)
2) GE Build insert  — SELECT 1, topic_id ... -> COALESCE(topic_id, 0)
3) SC Cont build    — Number(item.topic_id) || null -> || 0
"""
import json

TGBOT = 'workflows/wf-tg-bot.json'

raw = open(TGBOT, encoding='utf-8').read()
data = json.loads(raw)
data = data[0] if isinstance(data, list) else data

def node(name):
    return next(n for n in data['nodes'] if n['name'] == name)

# 1) DU Build script
n = node('DU Build script')
js = n['parameters']['jsCode']
old = "INSERT INTO scripts (client_id, topic_id, hook, body, cta, target_length, format_tag, full_text, status) VALUES (?, NULL, '', '', '', ?, 'user', ?, 'pending')"
assert old in js, 'DU Build script: SQL не найден'
js = js.replace(old, "INSERT INTO scripts (client_id, topic_id, hook, body, cta, target_length, format_tag, full_text, status) VALUES (?, 0, '', '', '', ?, 'user', ?, 'pending')")
n['parameters']['jsCode'] = js
print('DU Build script: OK')

# 2) GE Build insert
n = node('GE Build insert')
js = n['parameters']['jsCode']
old = "SELECT 1, topic_id, '', '', '', 30, 'user', ?, 'pending' FROM sessions WHERE tg_user_id = ?"
assert old in js, 'GE Build insert: SQL не найден'
js = js.replace(old, "SELECT 1, COALESCE(topic_id, 0), '', '', '', 30, 'user', ?, 'pending' FROM sessions WHERE tg_user_id = ?")
n['parameters']['jsCode'] = js
print('GE Build insert: OK')

# 3) SC Cont build
n = node('SC Cont build')
js = n['parameters']['jsCode']
old = "const topicId = Number(item.topic_id) || null;"
assert old in js, 'SC Cont build: topicId не найден'
js = js.replace(old, "const topicId = Number(item.topic_id) || 0;")
n['parameters']['jsCode'] = js
print('SC Cont build: OK')

out = json.dumps([data], ensure_ascii=False, indent=1) + '\n'
open(TGBOT, 'w', encoding='utf-8').write(out)
print('wf-tg-bot.json: OK')
