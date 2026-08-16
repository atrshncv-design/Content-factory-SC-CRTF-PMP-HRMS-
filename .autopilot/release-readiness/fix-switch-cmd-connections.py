#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix-switch-cmd-connections.py — вернуть avatar_video и fallback на свои выходы.

Баг (с ab50623): Switch cmd имеет 46 правил (0..45) + fallbackOutput 'extra'
(выход 46). Правило avatar_video = индекс 45 -> должно вести на AVV Start.
Fallback (неизвестные команды) = индекс 46 -> должен вести на Gate Build.
Но connections перепутаны: out[45] -> Gate Build, out[46] -> AVV Start.
Симптом: нажатие «Видео с аватаром» -> Gate Build -> «Не понял», а любая
неизвестная команда -> AVV Start.
"""
import json

PATH = 'workflows/wf-tg-bot.json'

with open(PATH, 'r', encoding='utf-8') as f:
    d = json.load(f)
wf = d[0] if isinstance(d, list) else d

conn = wf['connections']
outs = conn.get('Switch cmd', {}).get('main', [])

print('ДО:')
for i, b in enumerate(outs):
    targets = [t['node'] for t in b]
    if i >= 44:
        print(f'  out[{i}] -> {targets}')

# out[45] = avatar_video -> AVV Start
# out[46] = fallback -> Gate Build
assert outs[45][0]['node'] == 'Gate Build', 'out[45] не Gate Build: %s' % outs[45]
assert outs[46][0]['node'] == 'AVV Start', 'out[46] не AVV Start: %s' % outs[46]

outs[45] = [{'node': 'AVV Start', 'type': 'main', 'index': 0}]
outs[46] = [{'node': 'Gate Build', 'type': 'main', 'index': 0}]

print('ПОСЛЕ:')
for i, b in enumerate(outs):
    targets = [t['node'] for t in b]
    if i >= 44:
        print(f'  out[{i}] -> {targets}')

with open(PATH, 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, indent=1)
print('OK: записано')
