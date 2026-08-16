#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix-avatar-preview-text.py — текст выбора аватара без «(фото выше)».

После удаления массовых фото (8+7) текст остался со старой версией:
«Стоковые аватары creatify (фото выше).» — фото больше нет, пользователь
справедливо возмущён. Новый текст: подсказка «нажми на имя — покажу фото».
"""
import json

PATH = 'workflows/wf-tg-bot.json'

with open(PATH, 'r', encoding='utf-8') as f:
    d = json.load(f)
wf = d[0] if isinstance(d, list) else d

for n in wf['nodes']:
    if n['name'] != 'AVV Build preview':
        continue
    js = n['parameters']['jsCode']
    old = "const header = btnsOwn.length ? '\u0421\u0432\u043e\u0438 \u2014 \u043f\u0435\u0440\u0432\u044b\u043c\u0438 \u043a\u043d\u043e\u043f\u043a\u0430\u043c\u0438, \u0441\u0442\u043e\u043a\u043e\u0432\u044b\u0435 creatify \u2014 \u043d\u0438\u0436\u0435 (\u0444\u043e\u0442\u043e \u0432\u044b\u0448\u0435).' : '\u0421\u0442\u043e\u043a\u043e\u0432\u044b\u0435 \u0430\u0432\u0430\u0442\u0430\u0440\u044b creatify (\u0444\u043e\u0442\u043e \u0432\u044b\u0448\u0435).';"
    new = "const header = btnsOwn.length ? '\u0421\u0432\u043e\u0438 \u2014 \u043f\u0435\u0440\u0432\u044b\u043c\u0438 \u043a\u043d\u043e\u043f\u043a\u0430\u043c\u0438, \u0441\u0442\u043e\u043a\u043e\u0432\u044b\u0435 creatify \u2014 \u043d\u0438\u0436\u0435.' : '\u0421\u0442\u043e\u043a\u043e\u0432\u044b\u0435 \u0430\u0432\u0430\u0442\u0430\u0440\u044b creatify.';\nconst hint = ' \u041d\u0430\u0436\u043c\u0438 \u043d\u0430 \u0438\u043c\u044f \u2014 \u043f\u043e\u043a\u0430\u0436\u0443 \u0444\u043e\u0442\u043e \u0430\u0432\u0430\u0442\u0430\u0440\u0430.';"
    new2 = "const text = '\U0001F3AD \u0412\u044b\u0431\u0435\u0440\u0438 \u0430\u0432\u0430\u0442\u0430\u0440\u0430 \u0434\u043b\u044f \u0432\u0438\u0434\u0435\u043e: ' + esc(header) + hint;"
    assert old in js, 'старый текст не найден'
    js = js.replace(old, new)
    old2 = "const text = '\U0001F3AD \u0412\u044b\u0431\u0435\u0440\u0438 \u0430\u0432\u0430\u0442\u0430\u0440\u0430 \u0434\u043b\u044f \u0432\u0438\u0434\u0435\u043e: ' + esc(header);"
    assert old2 in js, 'текст-строка не найдена'
    js = js.replace(old2, new2)
    n['parameters']['jsCode'] = js
    print('AVV Build preview: текст исправлен')

with open(PATH, 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, indent=1)
print('OK')
