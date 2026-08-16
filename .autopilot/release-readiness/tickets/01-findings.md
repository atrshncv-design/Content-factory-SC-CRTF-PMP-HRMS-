# 01 — находки и результаты приёмки

## Исправлено в рамках тикета 01

- `workflows/wf-tg-bot.json`: 294 `callback_data` inline-кнопок завёрнуты в формат `={{ "..." }}`.
- `workflows/wf-creatify-webhook.json`: 2 `callback_data` (кнопка «Меню» в sendVideo/fallback) завёрнуты в формат `={{ "..." }}`.
- `workflows/wf-tg-bot.json`: 4 HTTP-ноды, вызывающие внутренние webhook `factory/creatify-link` и `factory/creatify-submit` (`DU HTTP link`, `DU HTTP submit`, `AS HTTP creatify-link`, `AS HTTP creatify-submit`), приведены к `typeVersion 4.5` + `authentication: none` + keypair-заголовкам `X-API-ID` / `X-API-KEY` из `$env`.

## Проверки (0 платных вызовов)

1. **Валидатор проекта** (`/tmp/validate_01.py`):
   - Все 35 команд из `tg-commands-35.json` покрыты в `Switch cmd` `wf-tg-bot`.
   - Все `callback_data` в `wf-tg-bot` и `wf-creatify-webhook` имеют формат `={{ }}`.
   - `neverError` в HTTP Request только вложенный (`options.response.response.neverError`).
   - Telegram-ноды: `typeVersion` 1.2; Switch-ноды: 3.4; HTTP Request: 4.5.
   - BFS от триггера доходит до всех Telegram Send Message / Send Video / HTTP Request.
   - `wf-creatify-webhook` sendVideo: `resource='message'`, параметр `file`, `caption` в `additionalFields`.

2. **Sim-прогон wf-creatify-webhook** (`/tmp/sim_webhook.py`, `node` v22.23.1):
   - `Code done build` со статусом `done` + `video_output_url` → формирует payload с видео.
   - `Build stage3` → `chat_id`, `video`, `text` корректны.
   - `Build update failed` → `alert_text` с `failed_reason` отправляется оператору.
   - Итог: 0 fails.

## Найдено вне тикета

- Вне зоны тикета 01 (`wf-tg-bot`, `wf-creatify-webhook`, `tg-commands-35.json`) дыр не выявлено.
- Прочие workflow проверены на формат `callback_data`: все валидны.

## Примечания / наблюдения

- В `Switch cmd` `wf-tg-bot` есть ветви, не входящие в `tg-commands-35.json`: `auto`, `dur`, `durc`, `hint`, `profile_doc`, `profile_photo`, `profile_video`, `questions`, `remove_operator`, `text_post`. Это внутренние callback/обработчики медиа; они корректно обрабатываются и не являются дефектом.
- В репо присутствуют незакоммиченные изменения в других файлах (видны в `git diff --stat`); тикет 01 затронул только `workflows/wf-tg-bot.json` и `workflows/wf-creatify-webhook.json`.
