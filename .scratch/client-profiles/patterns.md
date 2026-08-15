# Паттерны работы с wf-tg-bot (для субагентов тикетов client-profiles)

Обязательные правила при любых правках `.scratch/client-profiles/fixes/wf-tg-bot.json`.

## Формат файла
- REST-снапшот n8n: JSON-массив из 1 элемента. `[0]` = workflow: {id, name, nodes, connections, active, activeVersionId, versionMetadata, ...}.
- Сохранять тот же формат: `json.dump(wf_list, f, ensure_ascii=False)` (indent 1 — как в base).
- Не трогать поля вне скоупа (versionMetadata, settings, meta...).

## typeVersion (n8n 2.34.4)
- telegram: `"1.2"` (НЕ 2.2 — не существует, активация падает)
- switch: `"3.4"` (НЕ 2.2)
- code: `"1"`
- httpRequest (db-bridge внутри бота): сверять с существующими — `"4.5"` или как у соседних db-bridge-нод

## Выражения
- ТОЛЬКО `={{ expr }}` (двойные скобки с `=`). НИКОГДА `={ ... }` (молча не работает).
- callback_data-литералы БЕЗ `=`: `"callback_data": "pf_new"`. Динамика: `"callback_data": "={{ 'pf_switch:' + $json.id }}"`.

## Кнопки TG
- `parameters.inlineKeyboard.rows[].row.buttons[]` → `{ "text": "...", "additionalFields": { "callback_data": "..." } }`.
- Кнопка меню на каждом экране: `{"text":"📋 Меню","callback_data":"cmd:menu"}` (литерал).
- answerCallbackQuery-ноды: `"operation": "answerQuery"` (НЕ `answerCallbackQuery`).

## esc() для TG-текстов (обязательно)
- КОПИРОВАТЬ дословно из ноды `MO Format` (base), НЕ перенабирать:
  `const esc = s => String(s ?? '').replace(/([_*[\]`])/g, '\\$1');`
- Всё динамическое в text — через esc(); статичные тексты не содержат `_` (или `\_`).
- esc() нужен и на ветках ошибок.

## Switch cmd
- В base: 35 правил `parameters.rules.values[]` (leftValue `={{ $json.command }}`, rightValue строка, string/equals) + fallback-выход (последний out_index = 35).
- Добавление правил: правила +1 → выходы +1 (fallback уезжает на новый индекс). СНАПШОТ `connections` ДО мутаций; пересчитать все `connections[switch_cmd].main` out_index.
- Switch cb (callback-действия): `callback_action` в leftValue.

## HTTP db-bridge (эталон: нода `ST HTTP settings`)
```json
{"method":"POST","url":"http://db-bridge:8787/query","sendHeaders":true,
 "headerParameters":{"parameters":[{"name":"X-BRIDGE-TOKEN","value":"={{ $env.FACTORY_DB_BRIDGE_TOKEN }}"}]},
 "sendBody":true,"contentType":"json","specifyBody":"json","jsonBody":"={{ $json }}",
 "options":{"timeout":15000}}
```
- Build-ноды (Code) возвращают `[{json: {sql: "...", params: [...]}}]`; HTTP шлёт `={{ $json }}`; ответ `{rows: [...]}` / `{lastInsertRowid: N}` / `{changes: N}`.
- Плейсхолдеры в SQL: `?` + params (prepared). `$env` в Code-нодах НЕ виден (только в HTTP-выражениях).
- DDL через db-bridge НЕЛЬЗЯ (только SELECT/INSERT/UPDATE/DELETE).

## Parser
- Нода `Parser` (Code, runOnceForAllItems): `const item = $input.first().json;` → map `C` {en: cmd, ru: cmd, '/slash': cmd} → парсинг `t.startsWith('... ')` для аргументов → возврат `{command, args{...}, tg_user_id, chat_id, message_id, query_id, raw, ...}`.
- Каждая новая команда — ОБЯЗАТЕЛЬНО слеш-форма в C-маппинге (`'/profile': 'profile'`) — автокомплит Telegram шлёт `/profile`.
- Документы: `if (item.message && item.message.document)` → до текстового парсинга.

## Валидация (после ЛЮБОЙ правки)
⚠️ Скрипты — в каталоге СКИЛЛА, не в репо (в репо `scripts/` НЕТ!). Используй АБСОЛЮТНЫЕ пути:
```bash
SK=/Users/aleksandrtrisenkov/.hermes/skills/software-development/content-factory-development/scripts
node --check <extracted jsCode>          # синтаксис
python3 $SK/validate-workflow-json.py .scratch/client-profiles/fixes/wf-tg-bot.json   # 0 issues
python3 $SK/lint-workflow-json.py .scratch/client-profiles/fixes/wf-tg-bot.json       # без новых находок
python3 $SK/extract-tg-ux-map.py .scratch/client-profiles/fixes/wf-tg-bot.json        # кнопки/BROKEN/NOROUTE
python3 $SK/sim-code-node-both.py <wf> <node> '<input>'   # поведение jsCode
```
- sim-вход: объект `{"nodes": {"<Имя>": <стаб json ноды>}, "json": <item>}`; ВСЕ `$('Node')`-ссылки стабить в nodes-мапе (иначе ReferenceError / state 'IDLE').
- Универсальные парсеры балансов читают `$json` И `$('Node')` → sim-code-node-both.py.

## Известные pitfalls
- Нода с `neverError` — только вложенный `options.response.response.neverError` (top-level не работает).
- Switch 3.4 boolean-выражение + string-оператор → exec error; сравнивать строки со строками.
- Битой active_client_id (999): резолв `users.active_client_id ?? settings.active_client_id` + валидация существования клиента → fallback первый active-клиент → 0 (гейт).
- `sessions`: PK = tg_user_id (колонки id НЕТ).
- tg-тексты, уходящие в JSON-промпты bridge (не в TG) — esc() НЕ нужен.

## Урок 15.08: connection-таргеты ОБЯЗАТЕЛЬНО с index/type

Каждый таргет в connections: `{"node": "...", "type": "main", "index": 0}`. Таргеты БЕЗ `index` n8n 2.34 МОЛЧА игнорирует — цепочка обрывается «без ошибки» (нода success, следующая не выполняется). Причина: CLI-экспорт (export:workflow) выкидывает index/type; apply_fix переносит файл в БД → live-рёбра ломаются. Симптом: исполнение success, lastNode = HTTP-нода, дальнейшие ноды не в runData. Валидатор скилла теперь это ловит (проверка index/type у таргетов). При правках connections — ВСЕГДА index: 0.

## Урок 15.08 (live-проверка): replyMarkup у telegram-нод v1.2

- n8n telegram v1.2 ИГНОРИРУЕТ параметр `inlineKeyboard` без `replyMarkup: "inlineKeyboard"` (кнопки молча не отправляются).
- Все новые TG-ноды создавать с обоими параметрами; валидатор теперь проверяет это.
- Симптом: сообщение уходит, кнопок нет, в данных исполнения нет reply_markup.
