# C2-B3 финальные правки wf-tg-bot (14.08.2026) — отчёт

База: `fixes/wf-tg-bot.json` (результат B2, 500 нод, 0 issues, lint 0).
Трансформер: `.scratch/review-full-14aug/transform-C2-B3-final-tgbot.py` (перезапускаемый, контроль
`reserialized == raw` на исходнике). Результат: **505 нод** (+5), `fixes/wf-tg-bot.json` перезаписан.

## Что → было → стало

| # | Что | Было | Стало |
|---|-----|------|-------|
| 1 | **DU Gate** (Y4) | `const cost = Math.round(5 * dur / 30);` — округление ВНИЗ, занижало оценку стоимости | `const cost = 5 * Math.ceil(dur / 30);` — округление ВВЕРХ, **идентичный паттерн `SH Gate`** (`5 * Math.ceil(dur / 30)`) — как реально списывает creatify (5 кред / 30с) |
| 2 | **Parser** (Y10) | C-маппинг: `'instruction': 'instruction', 'инструкция': 'instruction', 'инструкции': 'instruction', '/инструкция': 'instruction'` — **нет `/instruction`** (единственная из 31 команда без латинского слеш-варианта; setMyCommands предлагает `/instruction` → «Не понял») | Добавлен ключ `'/instruction': 'instruction'` рядом с `'инструкции'` (перед `/инструкция`) — теперь `/instruction` парсится в `command = 'instruction'` |
| 3 | **AS-кредитный гейт** (Y2) | Путь `approve:script → … → AS Build link body → AS HTTP creatify-link` — **БЕЗ проверки баланса creatify** (гейты 10/50 были только у UV/DU/SH); `AS Check link` ловил ошибку ПОСЛЕ вызова | Вставлен гейт ДО платного вызова: `AS Build link body → AS LB creatify → AS LB parse → AS Gate → Switch AS gate → (ok) AS HTTP creatify-link` / `(low) AS Format low → TG AS fail`. См. раздел «Решение по AS-гейту» |

## Решение по AS-гейту (Y2)

**Проверка B1-нод:** `AS Check link` и `AS Check submit` на месте и работают (sim-подтверждено):
- `AS Check link` при `{ok:false, error:'low_credits'}` от wf-creatify-link → `{ok:false, text:'❌ Не удалось создать ссылку creatify: low\_credits'}` → `Switch AS link` fallback → `AS Build err` (сброс в IDLE).
- `AS Check submit` при `low_credits` → `{ok:false, text:'❌ Запуск генерации не удался: Недостаточно кредитов creatify'}`.

**Но это НЕ защита трат:** Check'и срабатывают ПОСЛЕ вызова `AS HTTP creatify-link` — защищают только от зависания/молчаливой ошибки. Для защиты от списания нужен гейт ДО (задача: «гейт ДО вызова защищает от списания, Check ПОСЛЕ — только от зависания»). Гейта ДО на AS-пути не было → **добавлен минимальный**, по LB-паттерну DU/SH:

Новая цепочка (5 нод):
1. **`AS LB creatify`** (httpRequest 4.5): `GET https://api.creatify.ai/api/remaining_credits/`, keypair `X-API-ID`/`X-API-KEY` из `$env`, `timeout: 15000`, `neverError` вложенный — параметры байт-в-байт с `DU LB creatify`.
2. **`AS LB parse`** (code 2): body→raw→`JSON.parse(data)` → `creatify`; **pass-through** upstream-элемента `AS Build link body` (`Object.assign({}, src, {creatify})`) — критично: `AS HTTP creatify-link` шлёт `jsonBody = {{ $json }}` и нужен `url`.
3. **`AS Gate`** (code 2): `cr == null || cr < 10` → `{ok:false, reason:'low', cr, url}`; иначе `{ok:true, cr, url}`. Fail-closed на недоступном балансе — **идентично `DU Gate`/`SH Gate`** (в этом воркфлоу конвенция fail-closed, в отличие от SC-кластера с fail-open).
4. **`Switch AS gate`** (switch 3.4): правило `$json.ok` == `true` (**boolean/equals**, эталон `Switch CL allow` — НЕ строковый `'true'`, питфолл A2/Y11) → main[0] = `AS HTTP creatify-link`; fallback (`fallbackOutput: extra`) → main[1] = `AS Format low`.
5. **`AS Format low`** (code 2): esc-эталон из `MO Format` (байт-точно), текст **«❌ Недостаточно кредитов creatify (N). Минимум 10.»** → `TG AS fail` (переиспользована существующая нода, multi-input разрешён — эталон B1).

Проверка единственности входа: `n8n-backward-reach.py` — `AS HTTP creatify-link` имеет ровно одного предка (`Switch AS gate`); обход через сохранённый payload невозможен (вход в AS-цепочку один — callback `approve:script`).

## Валидация

| Проверка | Результат |
|----------|-----------|
| `validate-workflow-json.py` (BFS все ноды достижимы, дубли имён/id, node --check 228 jsCode) | ✅ 0 issues (505 нод) |
| `lint-workflow-json.py` | ✅ 0 находок |
| node --check новых Code-нод (AS LB parse / AS Gate / AS Format low / DU Gate / Parser) | ✅ через валидатор + явно |
| Сериализация: `indent=1, ensure_ascii=False`, без trailing newline, `reserialized == raw` | ✅ |

## Sim-прогоны (все rc=0)

| Нода | Вход | Результат |
|------|------|-----------|
| DU Gate | dur=45, cr=100 | `cost=10, ok:true` ✅ (ceil(45/30)=2 → 5·2) |
| DU Gate | dur=30, cr=100 | `cost=5, ok:true` ✅ |
| DU Gate | dur=25, cr=100 | `cost=5, ok:true` ✅ (ceil(25/30)=1) |
| Parser | текст `/instruction` | `command='instruction'` ✅ |
| Parser | `/инструкция`, `инструкция`, `instruction` | `command='instruction'` ✅ (регрессий нет) |
| Parser | `/menu` | `command='menu'` ✅ |
| AS LB parse | `{body:{data:'{"remaining_credits":20}'}}` + src с url | `{creatify:20, url:'https://x.com/v', ok:true, valid:true}` ✅ (pass-through) |
| AS Gate | balance=5 | `{ok:false, reason:'low', cr:5, url}` ✅ (отказ) |
| AS Gate | balance=20 | `{ok:true, cr:20, url}` ✅ (ok) |
| AS Format low | AS Gate.cr=5, Parser.chat_id=123 | `text:'❌ Недостаточно кредитов creatify (5). Минимум 10.'` ✅ |
| Switch AS gate (node -e) | ok:true / ok:false / ok:'true' / {} | main[0] / fallback / fallback / fallback ✅ |
| AS Check link (B1, не менялась) | API `{ok:false,error:'low_credits'}` / `{link_id}` | ловит ПОСЛЕ → ошибка / ok:true ✅ |
| AS Check submit (B1, не менялась) | `{ok:false,error:'low_credits'}` / `{creatify_id}` | «Недостаточно кредитов creatify» / ok:true ✅ |

## Остатки (вне скоупа этой волны)

1. **AU-цепочка (auto-режим)** — `AU Build link body → Switch AU link → AU HTTP creatify-link` тоже без кредитного гейта. Требование Y2 касалось только AS (approve:script → link → submit); для симметрии можно добавить такой же гейт на AU-путь отдельной волной.
2. **Y11** — 12 существующих Switch с `string/equals 'true'` (SC allow, OB/CT/ET/AS parse, CP allow, UV parse, DU gate/link/submit, SH gate) остаются как есть; новый `Switch AS gate` уже по корректному boolean-паттерну.
3. **Y3** — хардкод `tg_user_id` 941296693 НЕ трогался (тикет D2 — следующий в очереди, база = этот файл).
4. **Y5/Y12/Y13/Y14** — secret_token, публичные webhook, FACTORY_WEBHOOK_SECRET, DEPLOYMENT.md — вне скоупа.
5. `TG AS fail` теперь имеет 3 входов (Switch AS parse, AS Format err, AS Format low) — multi-input подтверждён (каждый источник пишет своё ребро).

## Файлы

- Изменён: `/Users/aleksandrtrisenkov/Desktop/PROGRAMMING/РАБОЧИЕ ПРОЕКТЫ/КОНТЕНТ-ЗАВОД-API-MVP/.scratch/review-full-14aug/fixes/wf-tg-bot.json` (505 нод, 0 issues, lint 0)
- Создан: `/Users/aleksandrtrisenkov/Desktop/PROGRAMMING/РАБОЧИЕ ПРОЕКТЫ/КОНТЕНТ-ЗАВОД-API-MVP/.scratch/review-full-14aug/transform-C2-B3-final-tgbot.py`
- Отчёт: `/Users/aleksandrtrisenkov/Desktop/PROGRAMMING/РАБОЧИЕ ПРОЕКТЫ/КОНТЕНТ-ЗАВОД-API-MVP/.scratch/review-full-14aug/fixes/C2-B3-final-tgbot.md`
