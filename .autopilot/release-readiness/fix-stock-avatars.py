#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix-stock-avatars.py — стоковые аватары creatify в ветке AVV wf-tg-bot.json.

Правки:
1. Новая Code-нода AVV Build preview (между AVV HTTP avatars и TG-нодами):
   - свои (approved) первыми (кнопки avv_sel:<persona_id> — ФИКС бага с локальным id),
   - стоковые 15 (кнопки avv_sel:<stock id>) ниже,
   - photos_1/photos_2 = 8+7 URL превью (preview_image_9_16).
2. Новые TG-ноды TG avv preview1 / TG avv preview2 (sendMediaGroup, 8 и 7 фото).
3. AVV Ask avatar — проксирует $('AVV Build preview').first().json (mode/text/rows).
4. Connections: AVV HTTP avatars -> AVV Build preview -> TG avv preview1 ->
   TG avv preview2 -> AVV Ask avatar -> (как было: TG avv ask avatar / TG avv none).
"""
import json
import re
import sys

PATH = 'workflows/wf-tg-bot.json'

STOCKS = [
    ('009f502d-3649-4624-a438-80b126f1fa30', 'Camila',   'https://cdn.creatify.ai/creator/009f502d-3649-4624-a438-80b126f1fa30/p_rs__0917.png'),
    ('018a97ef-4fba-4a34-8097-5e60e6e36ffe', 'Chloé',    'https://cdn.creatify.ai/creator/018a97ef-4fba-4a34-8097-5e60e6e36ffe/p.png'),
    ('285923a8-25b1-4ad1-a5ea-40ad8cbcaf9d', 'Bianca',   'https://cdn.creatify.ai/creator/285923a8-25b1-4ad1-a5ea-40ad8cbcaf9d/p.png'),
    ('745fef08-8eee-4e3b-873d-c39b9791c4cd', 'Sylvia',   'https://cdn.creatify.ai/creator/745fef08-8eee-4e3b-873d-c39b9791c4cd/p_rs__0917.png'),
    ('74686a1c-040c-4783-a2e2-a54367fbf998', 'Olivia',   'https://cdn.creatify.ai/creator/74686a1c-040c-4783-a2e2-a54367fbf998/p.png'),
    ('e40f0f2f-c280-4a35-af40-54ffaee3c67b', 'Priya',    'https://cdn.creatify.ai/creator/e40f0f2f-c280-4a35-af40-54ffaee3c67b/p_rs__0917.png'),
    ('fb40e95f-c907-45f9-a0ef-2d2ab981aa00', 'Carmen',   'https://cdn.creatify.ai/creator/fb40e95f-c907-45f9-a0ef-2d2ab981aa00/p_rs__0917.png'),
    ('6fdf53cb-ac28-4487-96d2-3eae073ece26', 'Lily',     'https://cdn.creatify.ai/creator/6fdf53cb-ac28-4487-96d2-3eae073ece26/p.png'),
    ('0251876f-0da4-4c61-8320-8955d8be1f98', 'Diego',    'https://cdn.creatify.ai/creator/0251876f-0da4-4c61-8320-8955d8be1f98/p.png'),
    ('0587591d-54cc-4d8d-867d-cc82de168f61', 'Sam',      'https://cdn.creatify.ai/creator/0587591d-54cc-4d8d-867d-cc82de168f61/p.png'),
    ('5a711072-4cef-49de-b82c-282e4f1e5a7d', 'Leo',      'https://cdn.creatify.ai/media_file/2161659/8f0b29818f35c355a5f0bb39129d84d0.png'),
    ('85ff68b3-2a6f-4e5c-9534-db0fbc18fdb9', 'Quentin',  'https://cdn.creatify.ai/creator/85ff68b3-2a6f-4e5c-9534-db0fbc18fdb9/p_rs__0917.png'),
    ('bf384605-a98d-4bad-828a-f3fd8825f5f6', 'Santiago', 'https://cdn.creatify.ai/creator/bf384605-a98d-4bad-828a-f3fd8825f5f6/p.png'),
    ('f8b1e966-f8df-4441-b426-66c0e61fb6cf', 'Kaito',    'https://cdn.creatify.ai/creator/f8b1e966-f8df-4441-b426-66c0e61fb6cf/p_rs__0917.png'),
    ('7b9482cd-7717-4202-9fc0-69b9c635b785', 'Aryan',    'https://cdn.creatify.ai/creator/7b9482cd-7717-4202-9fc0-69b9c635b785/p.png'),
]

BS = chr(92)  # backslash

# ---------- jsCode для новых нод ----------

BUILD_PREVIEW_JS = (
    "\n"
    "const p = $('Parser').first().json;\n"
    "const rows = $('AVV HTTP avatars').first().json.rows || [];\n"
    "const esc = s => String(s ?? '').replace(/([_*[" + BS + "]`])/g, '" + BS + "$1');\n"
    "const STOCKS = [\n"
    + ",\n".join(
        "  { id: '" + sid + "', name: '" + name + "', img: '" + img + "' }"
        for sid, name, img in STOCKS
    ) + "\n"
    "];\n"
    "const btnsOwn = rows.map(r => ({ text: String(r.creator_name || r.persona_id || '\u0410\u0432\u0430\u0442\u0430\u0440').slice(0, 30), additionalFields: { callback_data: '={{ \\'avv_sel:' + String(r.persona_id) + '\\' }}' } }));\n"
    "const btnsStock = STOCKS.map(s => ({ text: s.name, additionalFields: { callback_data: '={{ \\'avv_sel:' + s.id + '\\' }}' } }));\n"
    "const all = btnsOwn.concat(btnsStock);\n"
    "const photos = STOCKS.map(s => s.img);\n"
    "const header = btnsOwn.length ? '\u0421\u0432\u043e\u0438 \u2014 \u043f\u0435\u0440\u0432\u044b\u043c\u0438 \u043a\u043d\u043e\u043f\u043a\u0430\u043c\u0438, \u0441\u0442\u043e\u043a\u043e\u0432\u044b\u0435 creatify \u2014 \u043d\u0438\u0436\u0435 (\u0444\u043e\u0442\u043e \u0432\u044b\u0448\u0435).' : '\u0421\u0442\u043e\u043a\u043e\u0432\u044b\u0435 \u0430\u0432\u0430\u0442\u0430\u0440\u044b creatify (\u0444\u043e\u0442\u043e \u0432\u044b\u0448\u0435).';\n"
    "const text = '\U0001F3AD \u0412\u044b\u0431\u0435\u0440\u0438 \u0430\u0432\u0430\u0442\u0430\u0440\u0430 \u0434\u043b\u044f \u0432\u0438\u0434\u0435\u043e: ' + esc(header);\n"
    "return [{ json: { mode: 'list', chat_id: p.chat_id, text: text, rows: [{ row: { buttons: all } }], photos_1: photos.slice(0, 8), photos_2: photos.slice(8) } }];\n"
)

# ---------- загрузка ----------

with open(PATH, 'r', encoding='utf-8') as f:
    d = json.load(f)
wf = d[0] if isinstance(d, list) else d

nodes = wf['nodes']
conn = wf['connections']
by_name = {n['name']: n for n in nodes}

# ---------- 1. Новая Code-нода AVV Build preview ----------

build_preview = {
    'parameters': {
        'mode': 'runOnceForAllItems',
        'language': 'javaScript',
        'jsCode': BUILD_PREVIEW_JS,
    },
    'id': 'b1a2c3d4-0000-4000-8000-000000000001',
    'name': 'AVV Build preview',
    'type': 'n8n-nodes-base.code',
    'typeVersion': 2,
    'position': [4470, 300],
}

# ---------- 2. TG-ноды sendMediaGroup (8 и 7 фото) ----------

def media_group_node(name, node_id, idx_expr_prefix, count, pos_x):
    """media: fixedCollection {media: [ {type:'photo', media:'={{ $json.<prefix>[i] }}'} x count ]}"""
    media_list = []
    for i in range(count):
        media_list.append({
            'type': 'photo',
            'media': '={{ $json.%s[%d] }}' % (idx_expr_prefix, i),
            'additionalFields': {},
        })
    return {
        'parameters': {
            'resource': 'message',
            'operation': 'sendMediaGroup',
            'chatId': "={{ $('Parser').first().json.chat_id }}",
            'media': {'media': media_list},
            'additionalFields': {'disable_notification': False},
        },
        'id': node_id,
        'name': name,
        'type': 'n8n-nodes-base.telegram',
        'typeVersion': 1.2,
        'position': [4540, pos_x],
        'credentials': {
            'telegramApi': {
                'id': '10000000-0000-4000-8000-000000000004',
                'name': 'telegram',
            }
        },
    }

tg_preview1 = media_group_node('TG avv preview1', 'b1a2c3d4-0000-4000-8000-000000000002', 'photos_1', 8, 380)
tg_preview2 = media_group_node('TG avv preview2', 'b1a2c3d4-0000-4000-8000-000000000003', 'photos_2', 7, 460)

# ---------- 3. Правка AVV Ask avatar: прокси из AVV Build preview ----------

ask_node = by_name['AVV Ask avatar']
ask_node['parameters']['jsCode'] = (
    "\n"
    "const b = $('AVV Build preview').first().json;\n"
    "return [{ json: { mode: b.mode || 'list', chat_id: b.chat_id, text: b.text, rows: b.rows } }];\n"
)

# ---------- 4. Connections ----------

# AVV HTTP avatars -> AVV Build preview (вместо AVV Ask avatar)
conn['AVV HTTP avatars'] = {'main': [[{'node': 'AVV Build preview', 'type': 'main', 'index': 0}]]}
# AVV Build preview -> TG avv preview1
conn['AVV Build preview'] = {'main': [[{'node': 'TG avv preview1', 'type': 'main', 'index': 0}]]}
# TG avv preview1 -> TG avv preview2
conn['TG avv preview1'] = {'main': [[{'node': 'TG avv preview2', 'type': 'main', 'index': 0}]]}
# TG avv preview2 -> AVV Ask avatar
conn['TG avv preview2'] = {'main': [[{'node': 'AVV Ask avatar', 'type': 'main', 'index': 0}]]}
# AVV Ask avatar -> TG avv ask avatar / TG avv none (без изменений, но проверим)

nodes.extend([build_preview, tg_preview1, tg_preview2])

# ---------- 5. Запись ----------

with open(PATH, 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, indent=1)

print('OK: добавлены AVV Build preview, TG avv preview1, TG avv preview2')
print('Правка AVV Ask avatar: прокси из AVV Build preview (persona_id в кнопках — фикс)')
print('Connections: HTTP avatars -> Build preview -> preview1 -> preview2 -> Ask avatar')
