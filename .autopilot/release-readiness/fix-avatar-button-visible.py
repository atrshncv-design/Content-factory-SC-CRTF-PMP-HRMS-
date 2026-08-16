#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix-avatar-button-visible.py — кнопка «🎭 Видео с аватаром» на всех экранах + команда.

Правки:
1. wf-tg-bot.json: TG start / TG gen rejected / TG published — добавить кнопку
   «🎭 Видео с аватаром» (cmd:avatar_video) в первый ряд (после URL→видео/AI Shorts).
2. tg-commands-35.json: добавить команду avatar_video (32 -> 33).
3. register-tg-commands-35.sh: want-set + total 32 -> 33.
"""
import json
import re

BS = chr(92)

# ---------- 1. wf-tg-bot.json ----------
PATH = 'workflows/wf-tg-bot.json'
with open(PATH, 'r', encoding='utf-8') as f:
    d = json.load(f)
wf = d[0] if isinstance(d, list) else d

TARGETS = {
    'TG start': 'первый ряд с gen_url2video/gen_shorts',
    'TG gen rejected': 'ряд с gen_url2video/gen_shorts',
    'TG published': 'ряд с gen_url2video/gen_shorts',
}

BUTTON_JSON = '{"text": "🎭 Видео с аватаром", "additionalFields": {"callback_data": "={{ \\\\"cmd:avatar_video\\\\" }}"}}'

changed = []
for n in wf['nodes']:
    if n['type'] != 'n8n-nodes-base.telegram' or n['name'] not in TARGETS:
        continue
    p = n['parameters']
    kb = p.get('inlineKeyboard', {})
    if not isinstance(kb, dict):
        continue
    rows = kb.get('rows', [])
    if isinstance(rows, str):
        continue
    # найти первый ряд с кнопкой gen_url2video или gen_shorts
    target_row = None
    for r in rows:
        row = r.get('row', {})
        btns = row.get('buttons', [])
        texts = json.dumps(btns, ensure_ascii=False)
        if 'gen_url2video' in texts or 'gen_shorts' in texts:
            target_row = r
            break
    if target_row is None:
        print('WARN: не найден ряд в', n['name'])
        continue
    btns = target_row['row']['buttons']
    # уже есть?
    if any(json.dumps(b, ensure_ascii=False).find('avatar_video') >= 0 for b in btns):
        print('уже есть в', n['name'])
        continue
    # вставить после последней кнопки gen_* в ряду
    insert_at = len(btns)
    for i, b in enumerate(btns):
        if 'gen_url2video' in json.dumps(b, ensure_ascii=False) or 'gen_shorts' in json.dumps(b, ensure_ascii=False):
            insert_at = i + 1
    new_btn = {
        'text': '🎭 Видео с аватаром',
        'additionalFields': {
            'callback_data': '={{ \\"cmd:avatar_video\\" }}',
        },
    }
    btns.insert(insert_at, new_btn)
    changed.append(n['name'])

with open(PATH, 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, indent=1)
print('wf-tg-bot: кнопка добавлена в:', changed)

# ---------- 2. tg-commands-35.json ----------
P2 = 'tg-commands-35.json'
with open(P2, 'r', encoding='utf-8') as f:
    cmds = json.load(f)
if isinstance(cmds, dict):
    cmds = cmds.get('commands', [])
names = [c.get('command') for c in cmds]
print('до:', len(names), '| avatar_video есть:', 'avatar_video' in names)
if 'avatar_video' not in names:
    cmds.append({
        'command': 'avatar_video',
        'description': 'Видео с аватаром (5 кред/30с)',
    })
with open(P2, 'w', encoding='utf-8') as f:
    json.dump(cmds, f, ensure_ascii=False, indent=1)
print('после:', len(cmds))

# ---------- 3. register-tg-commands-35.sh ----------
P3 = 'register-tg-commands-35.sh'
with open(P3, 'r', encoding='utf-8') as f:
    sh = f.read()
# want-set: добавить avatar_video
sh = sh.replace(
    'want = {"start","menu","instruction","help","status","mode","onboard","start_cycle","url2video","shorts","cancel","topics","competitors","accounts","budget","client","clients","reload_skills","ping","creators","creator","creator_content","audience","transcript","comments","upload_avatar","my_avatars","publish_type","profile","profiles","add_operator","operators"}',
    'want = {"start","menu","instruction","help","status","mode","onboard","start_cycle","url2video","shorts","cancel","topics","competitors","accounts","budget","client","clients","reload_skills","ping","creators","creator","creator_content","audience","transcript","comments","upload_avatar","my_avatars","publish_type","profile","profiles","add_operator","operators","avatar_video"}'
)
# total 32 -> 33
sh = sh.replace('[ "$total" = "32" ]', '[ "$total" = "33" ]')
# тексты
sh = sh.replace('all 32 factory commands', 'all 33 factory commands')
sh = sh.replace('verify на 32', 'verify на 33')
sh = sh.replace('регистрирует 32 команды', 'регистрирует 33 команды')
with open(P3, 'w', encoding='utf-8') as f:
    f.write(sh)
print('register-tg-commands-35.sh: want-set+total 33')
