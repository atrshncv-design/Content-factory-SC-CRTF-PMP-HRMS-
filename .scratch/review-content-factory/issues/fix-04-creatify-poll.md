# FIX-04 — wf-creatify-poll: real-режим

**Status:** ready-for-agent
**Blocked by:** —

## Задача
Исправить wf-creatify-poll (cron */5) — сейчас неработоспособен в real-режиме.
Результат: обновлённый JSON в `.scratch/review-content-factory/fixes/wf-creatify-poll.json`.

## Правки (по CODE-REVIEW К3)
1. **Switch mock** (нода `Switch mock`): добавить `"fallbackOutput": "extra"` в options →
   при real-ключах поток идёт в real-ветку (out[1]), а не обрывается молча.
   Правило: `$env.CREATIFY_API_ID === 'PLACEHOLDER_UNTIL_TOMORROW'` → mock (out[0]); иначе real (out[1]).

2. **HTTP GET creatify** (real-ветка): сейчас `authentication:"genericCredentialType"` +
   `genericAuthType:"httpMultipleHeadersAuth"` — НЕ работает (заголовки не доставляются).
   Заменить на эталон: `authentication:"none"`, `sendHeaders:true`, `specifyHeaders:"keypair"`,
   `headerParameters:{parameters:[{name:"X-API-ID", value:"={{ $env.CREATIFY_API_ID }}"},{name:"X-API-KEY", value:"={{ $env.CREATIFY_API_KEY }}"}]}`,
   typeVersion 4.5, contentType json (если POST) / query для GET.
   URL: `GET /api/link_to_videos/?ids=...` (сохранить как есть, если не верифицировано — не менять URL).

3. **Обработка результата GET:** после HTTP добавить Code-ноду (или расширить существующую):
   при status done/failed → UPDATE generations (через db-bridge: `UPDATE generations SET status=?, video_output_url=? WHERE creatify_id=?`)
   + опционально вызвать wf-creatify-webhook логику (или tg-alert). Промежуточные статусы — без UPDATE.

## Ограничения
- Только чтение исходника + запись результата в `.scratch/review-content-factory/fixes/wf-creatify-poll.json`.
- Исходный `workflows/wf-creatify-poll.json` НЕ менять.
- Никаких сетевых вызовов/SSH. Секреты не выводить.
- В отчёте: изменённые ноды, было → стало; схема новых нод (полный JSON параметров).
- Язык: русский.
