# FIX-01+02+03a — wf-tg-bot: кнопки этапов 1–2, example.com, туннель

**Status:** ready-for-agent
**Blocked by:** —

## Задача
Исправить 3 критичных бага в `workflows/wf-tg-bot.json` (исходник — файл репо).
Результат: обновлённый JSON в `.scratch/review-content-factory/fixes/wf-tg-bot.json` (создать файл).

## Правки
1. **К2 — callback_data кнопок этапов 1–2 (4 TG-ноды):**
   - `TG stage1` (и `TG stage1 edit`): `callback_data: 'approve:topic:{{ $json.topic_id }}'` →
     `={{ 'approve:topic:' + $json.topic_id }}` (аналогично edit/reject/alt для topic).
   - `TG stage2` (и `TG script saved`): `callback_data: 'approve:script:{{ $json.script_id }}'` →
     `={{ 'approve:script:' + $json.script_id }}` (аналогично edit/reject).
   - Формат: параметр `inlineKeyboard` → `rows[].row.buttons[].additionalFields.callback_data`.
   - Эталон рабочей кнопки — в wf-creatify-webhook («Telegram stage3»): `={{ 'publish:gen:' + $json.gen_id }}`.
   - НЕ трогать кнопки stage4 (toggle:platform:instagram — статичные, работают).

2. **К4 — заглушка example.com:** нода `AS Build link body` (Code): `url: 'https://example.com'` →
   брать URL из входа (body.url) с валидацией http(s); если нет — `{ok:false, valid:false, text:'❌ Укажи URL...'}`.
   Не допускать ухода example.com в платный вызов.

3. **К5 — хардкод туннеля:** нода `AS Build bridge prompt` (Code): заменить
   `https://assessment-fossil-assignments-alice.trycloudflare.com` на `$env.WEBHOOK_URL`
   (конкатенация `$env.WEBHOOK_URL + '/webhook/factory/creatify/6d8f2a41c9e7b3d5f0a1c4e8'`).

## Ограничения
- Только чтение исходника + запись результата в `.scratch/review-content-factory/fixes/wf-tg-bot.json`.
- Исходный `workflows/wf-tg-bot.json` НЕ менять.
- Никаких сетевых вызовов/SSH. Секреты не выводить.
- В отчёте: список изменённых нод + что именно поменялось (было → стало).
- Язык: русский.
