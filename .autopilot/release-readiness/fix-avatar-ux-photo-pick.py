#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix-avatar-ux-photo-pick.py — UX выбора аватара: имя → фото выбранного → ✅/🔁.

Проблема UX: выбор аватара слал 2 альбома по 8+7 фото (sendMediaGroup) —
«спам из чужих фото». Пользователь выбрал: кнопки с именами, после нажатия —
фото выбранного + «✅ Этот / 🔁 Другой».

Изменения в wf-tg-bot.json:
1. Убрать из цепочки TG avv preview1 / TG avv preview2 (массовые фото):
   AVV HTTP avatars -> AVV Build preview -> AVV Ask avatar (напрямую).
   В AVV Build preview убрать photos_1/photos_2 (не нужны).
2. Новая нода AVV Preview sel (Code): по avatar_id (entity_type) ищет аватара
   (сток — в STOCKS с фото; свой — в custom_avatars без фото) -> 
   {mode:'photo'|'text', chat_id, photo?, text, rows:[✅ Этот / 🔁 Другой / 🧹 Отмена / 📋 Меню]}.
3. Новая нода TG avv preview photo (sendPhoto, caption + кнопки).
4. Новая нода TG avv preview text (sendMessage, кнопки).
5. Новая нода Switch avv preview (mode: photo -> TG photo; text -> TG text; fallback -> AVV Ask avatar).
6. Parser: распознавать avv_ok / avv_again (entity_type = uuid для avv_ok).
7. Switch cb: avv_sel -> AVV Preview sel (вместо AVV Save avatar);
   + правило avv_ok -> AVV Save avatar (out[41]);
   + правило avv_again -> AVV Ask avatar (out[42]);
   fallback CB answer unknown сдвигается на out[43].
"""
import json

PATH = 'workflows/wf-tg-bot.json'
BS = chr(92)

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

with open(PATH, 'r', encoding='utf-8') as f:
    d = json.load(f)
wf = d[0] if isinstance(d, list) else d
nodes = wf['nodes']
conn = wf['connections']
by_name = {n['name']: n for n in nodes}

# ---------- 1. Переподключить AVV Build preview -> AVV Ask avatar (минуя TG avv preview1/2) ----------
conn['AVV Build preview'] = {'main': [[{'node': 'AVV Ask avatar', 'type': 'main', 'index': 0}]]}
# TG avv preview1/2 больше не в цепочке — удалить их ноды и связи
for nm in ('TG avv preview1', 'TG avv preview2'):
    if nm in conn:
        del conn[nm]
    nodes[:] = [n for n in nodes if n['name'] != nm]

# ---------- 2. AVV Build preview: убрать photos_1/photos_2 из вывода ----------
bp = by_name['AVV Build preview']
bp_js = bp['parameters']['jsCode']
bp_js = bp_js.replace(
    "photos_1: photos.slice(0, 8), photos_2: photos.slice(8)",
    "photos_1: [], photos_2: []"
)
bp['parameters']['jsCode'] = bp_js

# ---------- 3. Новая нода AVV Preview sel ----------
preview_sel_js = (
    "\n"
    "const p = $('Parser').first().json;\n"
    "const avatarId = String(p.entity_type || '').trim();\n"
    "const esc = s => String(s ?? '').replace(/([_*[" + BS + "]`])/g, '" + BS + "$1');\n"
    "const STOCKS = [\n"
    + ",\n".join(
        "  { id: '" + sid + "', name: '" + name + "', img: '" + img + "' }"
        for sid, name, img in STOCKS
    ) + "\n"
    "];\n"
    "const stock = STOCKS.find(s => s.id === avatarId);\n"
    "const ownRows = $('AVV HTTP avatars').first().json.rows || [];\n"
    "const own = ownRows.find(r => String(r.persona_id) === avatarId);\n"
    "const name = stock ? stock.name : (own ? String(own.creator_name || 'Аватар') : '');\n"
    "const okCb = '={{ \\'avv_ok:' + avatarId + '\\' }}';\n"
    "const againCb = '={{ \\'avv_again\\' }}';\n"
    "const rows = [\n"
    "  { row: { buttons: [\n"
    "    { text: '✅ Этот', additionalFields: { callback_data: okCb } },\n"
    "    { text: '🔁 Другой', additionalFields: { callback_data: againCb } }\n"
    "  ] } },\n"
    "  { row: { buttons: [\n"
    "    { text: '🧹 Отмена', additionalFields: { callback_data: '={{ \\'cmd:cancel\\' }}' } },\n"
    "    { text: '📋 Меню', additionalFields: { callback_data: '={{ \\'cmd:menu\\' }}' } }\n"
    "  ] } }\n"
    "];\n"
    "if (stock) {\n"
    "  return [{ json: { mode: 'photo', chat_id: p.chat_id, photo: stock.img, text: esc('🎭 Аватар: ' + name + '. Этот подходит?'), rows: rows } }];\n"
    "}\n"
    "return [{ json: { mode: 'text', chat_id: p.chat_id, text: esc('🎭 Свой аватар: ' + (name || avatarId) + '. Продолжить с этим аватаром?'), rows: rows } }];\n"
)

preview_sel = {
    'parameters': {'mode': 'runOnceForAllItems', 'language': 'javaScript', 'jsCode': preview_sel_js},
    'id': 'c1a2b3c4-0000-4000-8000-000000000001',
    'name': 'AVV Preview sel',
    'type': 'n8n-nodes-base.code',
    'typeVersion': 2,
    'position': [4620, 380],
}

# ---------- 4. TG avv preview photo (sendPhoto) ----------
tg_photo = {
    'parameters': {
        'resource': 'message',
        'operation': 'sendPhoto',
        'chatId': "={{ $('Parser').first().json.chat_id }}",
        'file': '={{ $json.photo }}',
        'additionalFields': {'caption': '={{ $json.text }}', 'appendAttribution': False},
        'replyMarkup': 'inlineKeyboard',
        'inlineKeyboard': {'rows': '={{ $json.rows }}'},
    },
    'id': 'c1a2b3c4-0000-4000-8000-000000000002',
    'name': 'TG avv preview photo',
    'type': 'n8n-nodes-base.telegram',
    'typeVersion': 1.2,
    'position': [4680, 380],
    'credentials': {'telegramApi': {'id': '10000000-0000-4000-8000-000000000004', 'name': 'telegram'}},
}

# ---------- 5. TG avv preview text (sendMessage) ----------
tg_text = {
    'parameters': {
        'resource': 'message',
        'operation': 'sendMessage',
        'chatId': "={{ $('Parser').first().json.chat_id }}",
        'text': '={{ $json.text }}',
        'additionalFields': {'appendAttribution': False},
        'replyMarkup': 'inlineKeyboard',
        'inlineKeyboard': {'rows': '={{ $json.rows }}'},
    },
    'id': 'c1a2b3c4-0000-4000-8000-000000000003',
    'name': 'TG avv preview text',
    'type': 'n8n-nodes-base.telegram',
    'typeVersion': 1.2,
    'position': [4740, 380],
    'credentials': {'telegramApi': {'id': '10000000-0000-4000-8000-000000000004', 'name': 'telegram'}},
}

# ---------- 6. Switch avv preview ----------
sw_preview = {
    'parameters': {
        'mode': 'rules',
        'rules': {
            'values': [
                {'conditions': {'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'strict'},
                                'conditions': [{'leftValue': '={{ $json.mode }}', 'rightValue': 'photo', 'operator': {'type': 'string', 'operation': 'equals'}}], 'combinator': 'and'}},
                {'conditions': {'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'strict'},
                                'conditions': [{'leftValue': '={{ $json.mode }}', 'rightValue': 'text', 'operator': {'type': 'string', 'operation': 'equals'}}], 'combinator': 'and'}},
            ],
            'options': {'fallbackOutput': 'extra'},
        },
    },
    'id': 'c1a2b3c4-0000-4000-8000-000000000004',
    'name': 'Switch avv preview',
    'type': 'n8n-nodes-base.switch',
    'typeVersion': 3.4,
    'position': [4620, 460],
}

# ---------- 7. Parser: avv_ok / avv_again ----------
parser = by_name['Parser']
parser_js = parser['parameters']['jsCode']
parser_js = parser_js.replace(
    "else if (action === 'avv_sel') cb = 'avv_sel';",
    "else if (action === 'avv_sel') cb = 'avv_sel';\n    else if (action === 'avv_ok') cb = 'avv_ok';\n    else if (action === 'avv_again') cb = 'avv_again';"
)
parser['parameters']['jsCode'] = parser_js

# ---------- 8. Switch cb: avv_sel -> AVV Preview sel; +avv_ok -> AVV Save avatar; +avv_again -> AVV Ask avatar ----------
sw_cb = by_name['Switch cb']
sw_cb_rules = sw_cb['parameters']['rules']['values']
# avv_sel таргет: меняем connection out[37]
outs_cb = conn['Switch cb']['main']
print('Switch cb выходов ДО:', len(outs_cb))
# out[37] (avv_sel) -> AVV Preview sel
outs_cb[37] = [{'node': 'AVV Preview sel', 'type': 'main', 'index': 0}]
# добавить правила avv_ok (41), avv_again (42)
def make_rule(rv):
    return {'conditions': {'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'strict'},
                           'conditions': [{'leftValue': '={{ $json.callback_action }}', 'rightValue': rv, 'operator': {'type': 'string', 'operation': 'equals'}}], 'combinator': 'and'}}
sw_cb_rules.append(make_rule('avv_ok'))
sw_cb_rules.append(make_rule('avv_again'))
# fallback CB answer unknown был out[41] -> становится out[43]
fallback_target = outs_cb[41][0]['node'] if len(outs_cb) > 41 else 'CB answer unknown'
# пересобрать выходы: out[41] -> AVV Save avatar, out[42] -> AVV Ask avatar, out[43] -> fallback
new_outs = outs_cb[:41]
new_outs.append([{'node': 'AVV Save avatar', 'type': 'main', 'index': 0}])
new_outs.append([{'node': 'AVV Ask avatar', 'type': 'main', 'index': 0}])
new_outs.append([{'node': fallback_target, 'type': 'main', 'index': 0}])
conn['Switch cb']['main'] = new_outs
print('Switch cb выходов ПОСЛЕ:', len(new_outs))

# ---------- 9. Connections для новых нод ----------
conn['AVV Preview sel'] = {'main': [[{'node': 'Switch avv preview', 'type': 'main', 'index': 0}]]}
conn['Switch avv preview'] = {'main': [
    [{'node': 'TG avv preview photo', 'type': 'main', 'index': 0}],
    [{'node': 'TG avv preview text', 'type': 'main', 'index': 0}],
    [{'node': 'AVV Ask avatar', 'type': 'main', 'index': 0}],
]}
conn['TG avv preview photo'] = {'main': []}
conn['TG avv preview text'] = {'main': []}

nodes.extend([preview_sel, tg_photo, tg_text, sw_preview])

with open(PATH, 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, indent=1)
print('OK: UX выбора аватара — имя -> фото/текст -> ✅ Этот / 🔁 Другой')
