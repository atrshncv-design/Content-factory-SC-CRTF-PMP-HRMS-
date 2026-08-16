#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Тикеты 11+12: убрать премиум (asset/product/banner) + строгие секунды {30,60}.
Только wf-tg-bot.json — правки строковые/структурные, раундтрип ensure_ascii=False indent=1.
"""
import json, uuid

F = 'workflows/wf-tg-bot.json'
d = json.load(open(F))
d = d[0] if isinstance(d, list) else d
nodes = d['nodes']
conn = d['connections']
by_name = {n['name']: n for n in nodes}

def node(name):
    return by_name[name]

# ============ ТИКЕТ 11: убрать премиум ============
# 11.1 меню-кнопки (TG menu gen): убрать Ассет/Product/Баннеры
n = node('TG menu gen')
kb = n['parameters']['inlineKeyboard']
new_rows = []
for r in kb['rows']:
    btns = r['row']['buttons']
    keep = [b for b in btns if not any(x in b['additionalFields']['callback_data'] for x in ('hint_asset', 'hint_product', 'hint_banner'))]
    if keep:
        new_rows.append({'row': {'buttons': keep}})
kb['rows'] = new_rows
print('TG menu gen: премиум-кнопки убраны ->', len(new_rows), 'рядов')

# 11.2 текст меню (MU gen Format): убрать строки asset/product/banner
n = node('MU gen Format')
js = n['parameters']['jsCode']
old = "\\nДополнительно (требуют аргумент — пример в скобках):\\n👤 Аватар из видео (upload_avatar <url>)\\n🖼️ Изображение (asset <промпт>)\\n📦 Product-видео (product <url фото>)\\n🪧 Баннеры (banner <url фото>)'"
new = "\\n🎭 Видео с аватаром — аватар озвучивает твой текст (5 кред за 30 сек)\\n👤 Создать аватар: upload_avatar <url фото>'"
assert old in js, 'MU gen Format: блок не найден'
n['parameters']['jsCode'] = js.replace(old, new)
print('MU gen Format: текст обновлён')

# 11.3 GPF Route: asset/product/banner -> новая TG premium off
# добавить ноду TG premium off (клон TG du gen)
tg_du = node('TG du gen')
prem_off = {
    "parameters": json.loads(json.dumps(tg_du['parameters'])),
    "id": str(uuid.uuid4()),
    "name": "TG premium off",
    "type": "n8n-nodes-base.telegram",
    "typeVersion": 1.2,
    "position": [tg_du['position'][0] - 600, tg_du['position'][1] + 400],
    "credentials": json.loads(json.dumps(tg_du['credentials'])),
}
prem_off['parameters']['text'] = "={{ $json.text }}"
nodes.append(prem_off)
by_name['TG premium off'] = prem_off
# форматтер Premium off Format (Code) — текст
pf = {
    "parameters": {
        "mode": "runOnceForAllItems",
        "language": "javaScript",
        "jsCode": "\nconst p = $('Parser').first().json;\nconst esc = s => String(s ?? '').replace(/([_*[\\]`])/g, '\\\\$1');\nconst text = '⚠️ Формат отключён. Доступны: 🔗 URL→видео, 🎬 AI Shorts, 🎭 Видео с аватаром, 🔄 Запустить цикл (все по 5 кред за 30 сек).';\nreturn [{ json: { chat_id: p.chat_id, text: esc(text) } }];\n"
    },
    "id": str(uuid.uuid4()),
    "name": "Premium off Format",
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [prem_off['position'][0] - 60, prem_off['position'][1]],
}
nodes.append(pf)
by_name['Premium off Format'] = pf
conn['Premium off Format'] = {"main": [[{"node": "TG premium off", "type": "main", "index": 0}]]}

gpf = node('GPF Route')
vals = gpf['parameters']['rules']['values']
main = conn['GPF Route']['main']
off_branch = {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"}, "conditions": [{"leftValue": "={{ $json.command }}", "rightValue": "__OFF__", "operator": {"type": "string", "operation": "equals"}}], "combinator": "and"}}
for i, v in enumerate(vals):
    rv = [c.get('rightValue','') for c in v['conditions']['conditions']]
    if rv and rv[0] in ('asset', 'product', 'banner'):
        main[i][0]['node'] = 'Premium off Format'
        print(f'GPF Route: {rv[0]} -> Premium off Format')
print('GPF Route: премиум-ветки отключены')

# ============ ТИКЕТ 12: строгие секунды {30,60} ============
# 12.1 UV Ask dur текст
n = node('UV Ask dur')
js = n['parameters']['jsCode']
old = "'⏱ Длительность ролика: 30 сек — 5 кред · 60 сек — 10 кред · 90 сек — 15 кред. Остаток creatify: '"
new = "'⏱ Длительность ролика: 30 сек — 5 кред · 60 сек — 10 кред. Остаток creatify: '"
assert old in js, 'UV Ask dur: текст не найден'
n['parameters']['jsCode'] = js.replace(old, new)
print('UV Ask dur: 90 убрано')

# 12.2 TG uv ask dur кнопки: убрать 90
n = node('TG uv ask dur')
kb = n['parameters']['inlineKeyboard']
for r in kb['rows']:
    r['row']['buttons'] = [b for b in r['row']['buttons'] if 'dur_90' not in b['additionalFields']['callback_data']]
print('TG uv ask dur: кнопка 90 убрана')

# 12.3 DU Parse state: durValid только {30,60}
n = node('DU Parse state')
js = n['parameters']['jsCode']
old = "const durValid = dur >= 15 && dur <= 300;"
new = "const durValid = (dur === 30 || dur === 60);"
assert old in js, 'DU Parse state: durValid не найден'
js = js.replace(old, new)
# сообщение «только 30 или 60» — DU Format wrong
n['parameters']['jsCode'] = js
print('DU Parse state: durValid {30,60}')

n = node('DU Format wrong')
js = n['parameters']['jsCode']
old = "'⏱ Сначала начни сценарий: кнопка «URL → видео». Длительность ролика — 15–300 секунд.'"
new = "'⚠️ Только 30 или 60 секунд. Начни сценарий: кнопка «URL → видео».'"
assert old in js, 'DU Format wrong: текст не найден'
n['parameters']['jsCode'] = js.replace(old, new)
print('DU Format wrong: текст {30,60}')

# 12.4 DR Parse (цикл): dur_ok только {30,60}
n = node('DR Parse')
js = n['parameters']['jsCode']
old = "mode = (dur >= 15 && dur <= 300) ? 'dur_ok' : 'dur_wrong';"
new = "mode = (dur === 30 || dur === 60) ? 'dur_ok' : 'dur_wrong';"
assert old in js, 'DR Parse: условие не найдено'
n['parameters']['jsCode'] = js.replace(old, new)
print('DR Parse: {30,60}')

# 12.5 кнопки цикла: TG DR ask / TG DR wrong — убрать 90 и custom
for nm in ('TG DR ask', 'TG DR wrong'):
    n = node(nm)
    kb = n['parameters']['inlineKeyboard']
    new_rows = []
    for r in kb['rows']:
        btns = [b for b in r['row']['buttons'] if not any(x in b['additionalFields']['callback_data'] for x in ('durc_90', 'durc_custom'))]
        if btns:
            new_rows.append({'row': {'buttons': btns}})
    kb['rows'] = new_rows
    print(f'{nm}: 90/custom убраны')

out = json.dumps([d], ensure_ascii=False, indent=1) + '\n'
open(F, 'w', encoding='utf-8').write(out)
print('wf-tg-bot.json: OK (тикеты 11+12)')
