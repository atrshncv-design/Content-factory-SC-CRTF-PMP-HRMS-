# 10 — Ревью-фиксы: безопасность webhook'ов и хардкоды (кросс-ревью волн 1+2)

**Требования:** R01 (довести до идеала), R09i (без известных багов), История 10 спеки («все находки 🔴/🟠 закрыты или осознанно deferred»)
**Blocked by:** —
**Зона:** `workflows/*.json` (webhook-ноды и их вызывающие), `hermes-bridge/*.py`, `DEPLOYMENT.md`, `*.sh`
**Волна:** 3 (финальные фиксы после кросс-ревью)
**Status:** done (16.08, агент)

## Находки кросс-ревью (верифицированы статически 16.08)

1. 🔴 **22 webhook-ноды `factory/*` без аутентификации** (wf-tg-alerts, wf-publish, wf-creatify-{submit,asset,shorts,product,banner,adclone,avatar,link,text}, wf-analytics, wf-audience, wf-creators-search, wf-creator-profile, wf-creator-content, wf-transcripts-comments ×2, wf-onboard). n8n доступен через публичный cloudflared-туннель, пути задокументированы в DEPLOYMENT.md → при реальных ключах удалённый слив кредитов creatify/SC и спам от имени TG-бота (factory/tg-alert пишет в произвольный chat_id).
2. 🟠 **wf-creatify-webhook (колбэк Creatify): fail-open авторизация** — `$env.FACTORY_WEBHOOK_SECRET ? (header===secret) : true`: при незаданной переменной ЛЮБОЙ запрос проходит. Секретный суффикс пути (6d8f2a41c9e7b3d5f0a1c4e8) закоммичен — не считать его секретом.
3. 🟡 **wf-tg-bot.json: висячие ссылки** `$('DU LB sc')`, `$('SH LB sc')`, `$('UV LB sc')` — таких нод нет (есть 'DU/SH/UV LB creatify'); try/catch молча глотает → SC-баланс в quick-флоу всегда пустой.
4. 🟡 **wf-creatify-webhook.json: хардкод tg_user_id 941296693** — 5 мест, fallback `|| 941296693` (TODO D2): при отсутствии session-link видео/алерты уходят оператору-хардкоду вместо ошибки.
5. 🟡 **DEPLOYMENT.md: реальный chat_id 941296693** в curl-примере (строка ~50) и в whitelist-примере (§13).

## Критерии приёмки

- [x] 1. Все 21 внутренний webhook `factory/*` (кроме `factory/creatify/<suffix>` — внешний колбэк) получают header-auth: `authentication: headerAuth`, имя заголовка `X-FACTORY-TOKEN`, значение `={{ $env.FACTORY_WEBHOOK_SECRET }}`.
- [x] 2. Все внутренние вызывающие (HTTP-ноды в workflows/*.json, чей URL содержит `/webhook/factory/`; hermes-bridge/*.py; register-скрипты; curl-примеры в DEPLOYMENT.md) отправляют заголовок `X-FACTORY-TOKEN` из env. Полный список вызывающих собрать grep'ом. Статическая проверка: НЕТ ни одного вызова factory/* без заголовка.
- [x] 3. `factory/creatify/<suffix>` (внешний колбэк Creatify): fail-closed — FACTORY_WEBHOOK_SECRET не задан/пуст → 403; задан → сравнение заголовка, не совпал → 403. Суффикс пути остаётся доп.защитой (n8n не поддерживает выражения в path).
- [x] 4. wf-creatify-webhook: убрать все 5 fallback-хардкодов 941296693 — при отсутствии привязки сессии не отправлять, вернуть ошибку (критерий: grep '941296693' по workflows/wf-creatify-webhook.json = 0).
- [x] 5. wf-tg-bot: висячие `LB sc`-ссылки — добавлены недостающие ноды `DU/SH/UV LB sc` по образцу `ST LB sc` (вариант «добавить по образцу»: сохраняет поведение — SC-баланс реально запрашивается, parse-ноды не трогались).
- [x] 6. DEPLOYMENT.md: chat_id 941296693 в примерах → `<CHAT_ID>` (критерий: grep '941296693' по DEPLOYMENT.md = 0).
- [x] 7. Валидатор 0 issues по всем тронутым воркфлоу; pytest tests/ зелёный; sim-прогоны затронутых Code-нод; 0 платных вызовов; секреты — только имена переменных.

## Исполнение (16.08, агент)

### Схема n8n 2.34.4 (сверено с исходниками `n8n@2.34.4`, Webhook.node.ts/description.ts/utils.ts)
- `authentication: "headerAuth"` в n8n 2.34.4 требует **credential типа `httpHeaderAuth`** (поля `name` = имя заголовка, `value` = значение; хранится в vault), НЕ параметров `httpHeader`/`httpHeaderValue`. Без credential webhook отвечает 500 (fail-closed).
- Поэтому каждая из 21 ноды: `parameters.authentication: "headerAuth"` + `credentials.httpHeaderAuth` (один общий credential «Factory Webhook Auth», id `f0000000-...-a`). Значение секрета — НЕ в репо: на сервере создаётся credential с name=`X-FACTORY-TOKEN`, value=значение `FACTORY_WEBHOOK_SECRET` из `.env` (**deploy-гейт**, задокументирован в DEPLOYMENT.md §2).

### 1. Header-auth на 21 webhook `factory/*`
- Файлы: wf-tg-alerts, wf-publish, wf-creatify-{submit,asset,shorts,product,banner(×2),adclone,avatar(×2),link,text}, wf-analytics, wf-audience, wf-creators-search, wf-creator-profile, wf-creator-content, wf-transcripts-comments(×2), wf-onboard — 21 нода, `authentication: headerAuth` + credential-ссылка. Поведение (responseMode, пути, options) не менялось.
- Вне скоупа (осознанно): `zz-test-sqlite` (`factory/_test`, служебный тестовый воркфлоу, не в списке находки) и `factory/creatify/<suffix>` (внешний колбэк — обработан находкой 2).

### 2. Все 30 внутренних вызывающих шлют `X-FACTORY-TOKEN: {{ $env.FACTORY_WEBHOOK_SECRET }}`
- wf-tg-bot.json (23 HTTP-ноды: SC/OB/AS×2/CP/CRS/CRP/CRC/AUD/TR/CMT/AVA/AVL/AST/SHT/PRD/BNR/DU×2/TX/AU×3), wf-creatify-avatar (2), wf-creatify-webhook (2: tg-alert failed/unknown), wf-publish-status (2), wf-sync-accounts (1).
- hermes-bridge/*.py и register-tg-commands*.sh вызовов `factory/*` не содержат (проверено grep'ом: только skill-path и пути ~/factory).
- DEPLOYMENT.md: все curl-примеры (включая §2 и демо-тест audience) получили `-H 'X-FACTORY-TOKEN: $FACTORY_WEBHOOK_SECRET'`.
- Статическая проверка №2 (скрипт): 30/30 вызывающих с заголовком, 0 пропусков.

### 3. wf-creatify-webhook: fail-closed
- `IF auth`: `... : true }}` → `... : false }}` — секрет не задан → 403; задан и заголовок `x-factory-secret` (фактическое имя, под которым Creatify шлёт секрет — по .env.example и прежнему коду) не совпал → 403.
- `Respond unauthorized`: добавлен `responseCode: 403`.
- Суффикс пути `factory/creatify/6d8f2a41c9e7b3d5f0a1c4e8` сохранён; header-auth на ноду НЕ вешался (внешняя сторона его не знает).

### 4. Хардкод 941296693 убран (5 мест, grep = 0)
- `Build session update`: `uid = r.tg_user_id || null` — без session-link UPDATE не затронет строк.
- `Build stage3`: `uid = ... || null` + `if (!uid) throw new Error('Сессия не привязана к генерации #' + id + ' (нет session-link) — видео не отправлено')` — видео не уходит никому, вебхук возвращает ошибку.
- `Build session reset`: `uid = r.tg_user_id || null` (безвредный no-op без сессии).
- `HTTP tg-alert failed/unknown`: jsonBody без fallback + новые IF-ноды `IF alert failed`/`IF alert unknown` (leftValue `tg_user_id ?? ''`, string/notEquals ''): при отсутствии сессии алерт НЕ отправляется, поток идёт мимо (`→ Build session reset` / `→ Respond unknown`), Respond failed/unknown возвращается как раньше. `?? ''` гарантирует строку (fail-closed и при undefined).

### 5. wf-tg-bot: висячие LB sc-ссылки
- Добавлены 3 ноды-копии `ST LB sc` (HTTP GET scrapecreators credit-balance, keypair x-api-key, neverError): `DU LB sc` [1780,80], `SH LB sc` [1080,3840], `UV LB sc` [2050,-540]; connections переведены на паттерн `X LB creatify → X LB sc → X LB parse` (как ST/ST2/BG/MU). Parse-ноды не менялись — SC-баланс снова реально запрашивается.

### 6. DEPLOYMENT.md
- 941296693 → `<CHAT_ID>` в curl-примере tg-alert, whitelist (§Воркфлоу), `sessions: <CHAT_ID>|IDLE`, упоминании хардкода TG= (§профили) — grep = 0.
- Добавлен deploy-гейт: создание credential httpHeaderAuth (X-FACTORY-TOKEN = FACTORY_WEBHOOK_SECRET) и привязка к 21 ноде.

### Проверки (все зелёные)
- `python3 .scratch/bot-ux-menu/validate_workflow.py` по всем 22 тронутым воркфлоу → 0 issues (wf-creatify-banner/avatar/transcripts показывают недостижимые ноды — существующее поведение BFS на многотриггерных воркфлоу, подтверждено прогоном на HEAD-версиях: те же 11/25/23).
- `python3 -m pytest tests/ -q` → 25 passed.
- `python3 -m pytest tests/test_wf_tg_bot.py -v` → 10 passed.
- Статическая проверка №2: 30/30 вызывающих factory/* с X-FACTORY-TOKEN; 21/21 webhook с headerAuth (кроме внешнего колбэка и zz-test).
- `grep 941296693`: wf-creatify-webhook.json = 0, DEPLOYMENT.md = 0.
- Sim-прогоны (sim-code-node-both.py): Build session update/разreset — uid есть → params [uid], нет → [null]; Build stage3 — uid есть → chat_id, нет → throw с понятным текстом.
- Платных HTTP-вызовов не выполнялось; секреты — только имена переменных (FACTORY_WEBHOOK_SECRET, X-FACTORY-TOKEN).

### Осталось на deploy-гейт (не в репо)
- Создать credential n8n «Factory Webhook Auth» (httpHeaderAuth: name=`X-FACTORY-TOKEN`, value=значение FACTORY_WEBHOOK_SECRET из .env) и привязать к 21 ноде `factory/*` при импорте; проверить live: вызов без заголовка → 403/500, с заголовком → ок.
- Платные тесты (creatify/SC) — как обычно, отдельно с согласованием бюджета.

## Правила

- 0 кредитов: никаких реальных HTTP-вызовов (даже localhost) — только статика, симы. ✅ соблюдено.
- НЕ деплой (сервер ~/factory не трогать), НЕ git commit/add. Не трогать .autopilot/state.js, PROGRESS.md, dashboard.html, spec.md, interfaces.md, чужие тикеты. ✅ соблюдено (правки только в workflows/*.json, DEPLOYMENT.md, этот тикет).
- Секреты — только имена переменных (FACTORY_WEBHOOK_SECRET, X-FACTORY-TOKEN); НЕ читать .env. ✅
- Правила n8n: никогдаError вложенный; switch строковые сравнения; callback_data ={{ }}; HTTP платных вызовов typeVersion 4.5 + keypair. ✅ (правки не затрагивали эти аспекты).
- Webhook-нода в n8n: для header-auth параметры `authentication: "headerAuth"`, `httpHeader`/`headerName` + `headerValue` (проверить точные имена полей по схеме ноды в соседних воркфлоу или документации n8n 2.34.4; если нода использует другие ключи — использовать фактические, проверив пример в wf-creatify-webhook, если там уже есть auth-подобные настройки). ⚠️ Уточнено по исходникам n8n 2.34.4: headerAuth использует credential `httpHeaderAuth` (name/value), а не параметры ноды — применён фактический формат сериализации.
