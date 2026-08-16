# 14 — Новый воркфлоу wf-creatify-lipsync (AI Avatar) + поллинг

**Спека:** spec-3formats.md §6
**Blocked by:** —
**Status:** ready-for-agent

## Что сделать

Новый файл `workflows/wf-creatify-lipsync.json` (по образцу wf-creatify-shorts.json):

1. Webhook `factory/lipsync` (headerAuth X-FACTORY-TOKEN): body `{text, creator, video_length (30|60), mode, webhook_url?}`.
2. `Code validate`: text непустой (60–120 слов под длительность), creator UUID, video_length ∈ {30, 60}, вычистка меток (как cleanText в shorts).
3. Гейт кредитов: GET /api/remaining_credits/ + Code balance (порог ≥ 10), как в shorts.
4. POST `https://api.creatify.ai/api/lipsyncs/` body `{name: 'Ролик из сценария', text: <чистый текст>, creator: <UUID>, aspect_ratio: '9x16', model_version: 'standard'}` (keypair X-API-ID/X-API-KEY; НЕ aurora).
5. `Code Normalize`: `{ok, lipsync_id: id, status, video_output, duration, credits_used}` → Respond ok.
6. INSERT generations: в wf-tg-bot (как DU gen link — сессия), request_payload.type='lipsync'.

Поллинг (wf-creatify-poll.json):
- Для поколений с `request_payload` type=lipsync → GET `/api/lipsyncs/?ids=<creatify_id>` вместо link_to_videos; при done → video_output_url записать + доставить (см. тикет 15/16, механизм stage3: download + Telegram sendVideo с кнопками).

**Контракт lipsync (офиц. docs):** POST /api/lipsyncs/ — `{name?, text|audio, creator (id из /api/personas), model_version: standard|aurora_v1|aurora_v1_fast (standard = 5 кред/30с), aspect_ratio: 16x9|1x1|9x16, green_screen?, transparent_background?}`. НЕТ video_length и webhook_url → длительность = длине текста, доставка только поллингом.

## Критерии приёмки

- JSON валиден, валидатор 0 issues.
- Сим/mock-проверка: гейт, валидация text, normalize — зелёные (0 кредитов).
- Поллер корректно маршрутизирует lipsync-поколения.
