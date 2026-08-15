# D2 — хардкод tg_user_id 941296693, secret_token, AU-гейт (фикс-волна 14.08.2026)

База: `.scratch/review-full-14aug/fixes/wf-tg-bot.json` (505 нод) + `.scratch/review-full-14aug/fixes/wf-creatify-webhook.json` (25 нод).
Результат: `wf-tg-bot.json` **510 нод** (+5 AU-гейт), `wf-creatify-webhook.json` 25 нод. 0 кредитов — только статические проверки + sim.

## 1. wf-tg-bot: замена хардкода 941296693 → динамический tg_user_id

Метод: forward-BFS от Parser по `connections` (out-граф) → 503/505 нод достижимы. Дополнительно проверено обратным условием: **все 54 ноды-кандидата требуют Parser на КАЖДОМ пути от триггера** (BFS от tg-trigger с заблокированным Parser достигает только 2 ноды: tg-trigger, Whitelist) — `$('Parser')` в них гарантированно выполнен, риск ReferenceError отсутствует.

Паттерн: `const p = $('Parser').first().json;` (добавлена первой строкой, если нода её ещё не имела) + `params: [..., p.tg_user_id]` вместо `941296693`.

### Таблица: нода → было → стало (53 ноды, все в Parser-контексте)

Общий случай (52 ноды): `params: [..., 941296693]` → `params: [..., p.tg_user_id]` + `const p = $('Parser').first().json;`
(у 8 нод `const p` уже была — только замена литерала). Ноды:

| Нода | Было | Стало |
|---|---|---|
| CN Build | `params: [941296693]` | `params: [p.tg_user_id]` |
| SC Build state | `params: [941296693]` | `params: [p.tg_user_id]` |
| SC Build setstate | `params: [941296693]` | `params: [p.tg_user_id]` |
| SC Build set topic | `params: [id, 941296693]` | `params: [id, p.tg_user_id]` |
| OB Build state | `params: [941296693]` | `params: [p.tg_user_id]` |
| OB Build insert client | SQL-литерал `VALUES (..., 'active', 941296693)` | `VALUES (..., 'active', ?)` + `params: [..., t.confidence, p.tg_user_id]` |
| OB Build session idle | `params: [941296693]` | `params: [p.tg_user_id]` |
| Gate Build | `params: [941296693]` | `params: [p.tg_user_id]` |
| GE Build insert | `params: [p.raw, 941296693]` | `params: [p.raw, p.tg_user_id]` (const p была) |
| GE Build session | `params: [id, 941296693]` | `params: [id, p.tg_user_id]` |
| CT Build approve | `params: [941296693, String(p.entity_id)]` | `params: [p.tg_user_id, String(p.entity_id)]` (const p была) |
| CT Build session | `params: [String(p.entity_id), 941296693]` | `params: [String(p.entity_id), p.tg_user_id]` (const p была) |
| CT Build set script | `params: [id, 941296693]` | `params: [id, p.tg_user_id]` |
| ET Build session | `params: [id, 941296693]` | `params: [id, p.tg_user_id]` |
| RT Build session | `params: [941296693]` | `params: [p.tg_user_id]` |
| AS Build approve | `params: [941296693, String(p.entity_id)]` | `params: [p.tg_user_id, String(p.entity_id)]` (const p была) |
| AS Build session | `params: [String(p.entity_id), 941296693]` | `params: [String(p.entity_id), p.tg_user_id]` (const p была) |
| ES Build session | `params: [941296693]` | `params: [p.tg_user_id]` |
| RS Build session | `params: [941296693]` | `params: [p.tg_user_id]` |
| PG Build session | `params: [String(p.entity_id), 941296693]` | `params: [String(p.entity_id), p.tg_user_id]` (const p была) |
| JG Build session | `params: [941296693]` | `params: [p.tg_user_id]` |
| TP Build select | `params: [941296693]` | `params: [p.tg_user_id]` |
| TP Build update | `params: [JSON.stringify(pl), 941296693]` | `params: [JSON.stringify(pl), p.tg_user_id]` |
| SCH Build update | `params: [v, 941296693]` | `params: [v, p.tg_user_id]` |
| SCH Build select | `params: [941296693]` | `params: [p.tg_user_id]` |
| CP Build select | `params: [941296693]` | `params: [p.tg_user_id]` |
| CP Build final | `params: [941296693]` | `params: [p.tg_user_id]` |
| UV Build state | `params: [941296693]` (однострочный стиль) | `params: [p.tg_user_id]` |
| UV Save url | `params: [JSON.stringify(...), 941296693]` | `params: [JSON.stringify(...), p.tg_user_id]` |
| UV Build ask link | `params: [941296693]` | `params: [p.tg_user_id]` |
| DU Check state | `params: [941296693]` (single-quote стиль) | `params: [p.tg_user_id]` |
| DU Update state | `params: [JSON.stringify(...), 941296693]` | `params: [JSON.stringify(...), p.tg_user_id]` |
| DU Build reset | `params: [941296693]` | `params: [p.tg_user_id]` |
| SH Update state | `params: [JSON.stringify(...), 941296693]` | `params: [JSON.stringify(...), p.tg_user_id]` |
| SH Reset state | `params: [941296693]` | `params: [p.tg_user_id]` |
| SH Build session | `params: [String(...), JSON.stringify(...), 941296693]` | `params: [String(...), JSON.stringify(...), p.tg_user_id]` |
| SH Ask update | `params: [941296693]` | `params: [p.tg_user_id]` |
| TX Build | `params: [941296693]` | `params: [p.tg_user_id]` |
| TX Save text | `params: [JSON.stringify({text}), 941296693]` | `params: [JSON.stringify({text}), p.tg_user_id]` (const p была) |
| TX Toggle select | `params: [941296693]` | `params: [p.tg_user_id]` |
| TX Toggle | `params: [JSON.stringify(payload), 941296693]` | `params: [JSON.stringify(payload), p.tg_user_id]` (const p была) |
| TX Build select | `params: [941296693]` | `params: [p.tg_user_id]` |
| TX Reset | `params: [941296693]` | `params: [p.tg_user_id]` |
| AU Build approve topic | `params: [941296693, id]` | `params: [p.tg_user_id, id]` |
| AU Build session | `params: [id, 941296693]` | `params: [id, p.tg_user_id]` |
| AU Build set script | `params: [id, 941296693]` | `params: [id, p.tg_user_id]` |
| AU Build approve script | `params: [941296693, id]` | `params: [p.tg_user_id, id]` |
| AU Build session gen | `params: [id, 941296693]` | `params: [id, p.tg_user_id]` |
| AU Build alert | `params: [941296693], text: t` | `params: [p.tg_user_id], text: t` |
| AU Build select | `params: [941296693]` | `params: [p.tg_user_id]` |
| AU Build final | `params: [941296693]` | `params: [p.tg_user_id]` |
| CP Build pub err | `params: [941296693], text: t` | `params: [p.tg_user_id], text: t` |
| AS Build err | `params: [941296693], text: t` | `params: [p.tg_user_id], text: t` |

### Ноды ВНЕ Parser-контекста (хардкод оставлен + комментарий)

| Нода | Было | Стало |
|---|---|---|
| Whitelist | `const TG = 941296693;` | `const TG = 941296693; // TODO D2: вне Parser-контекста` |

Обоснование: Whitelist стоит МЕЖДУ tg-trigger и Parser (`tg-trigger → Whitelist → Parser`) — он исполняется ДО Parser, ссылаться на `$('Parser')` нельзя (это whitelist-гейт админа). Хардкод здесь семантически корректен (список допущенных операторов).

## 2. wf-creatify-webhook: session update/reset + chat_id (approve/reject-уведомления)

Схема `sessions` (infra/db/002_sessions.sql): **PK `tg_user_id` INTEGER, колонка `generation_id` INTEGER ЕСТЬ**. НО подзапрос `SELECT tg_user_id FROM sessions WHERE generation_id = ?` для основного цикла **структурно невозможен (курица-яйцо)**: единственный, кто пишет `sessions.generation_id` в основном цикле (approve:script → creatify-submit → callback) — это сам вебхук (`Build session update`). На момент колбэка у сессии `generation_id = NULL` → подзапрос вернул бы NULL → UPDATE 0 строк → сломанный state machine (сессия навсегда в CYCLE_GENERATION_PENDING, generation_id не сохраняется → ломается публикация).

Рабочее решение — **script_id-цепочка**: в основном цикле `sessions.script_id` == `generations.script_id` (AS Build session пишет script_id=approved script; AS Build submit body шлёт `script_id: Number(p.entity_id)`; AU — тот же id из `AU HTTP insert script`). Расширен `HTTP SELECT`:

```sql
SELECT g.id, g.status, substr(s.full_text, 1, 120) AS script_excerpt,
       (SELECT tg_user_id FROM sessions WHERE script_id = g.script_id) AS tg_user_id
FROM generations g LEFT JOIN scripts s ON s.id=g.script_id WHERE g.creatify_id = ?
```

Все 4 потребителя читают `tg_user_id` из `$('HTTP SELECT').first().json.rows[0]` (HTTP SELECT исполняется на КАЖДОМ пути вебхука — безопасно). Для путей, где session-link не резолвится (DU quick url2video: создаёт НОВЫЙ script через `DU HTTP script`, session-link отсутствует; легаси) — **fallback на 941296693 с комментарием** (сохраняет поведение как сегодня, контракт ответа не ломается: chat_id никогда null):

| Нода | Было | Стало |
|---|---|---|
| HTTP SELECT | SELECT без tg_user_id | + `(SELECT tg_user_id FROM sessions WHERE script_id = g.script_id) AS tg_user_id` |
| Build session update | `params: [String(d.id), 941296693]` | `params: [String(d.id), uid]`, uid = `r.tg_user_id \|\| 941296693` (TODO D2 fallback) |
| Build session reset | `params: [941296693]` | `params: [uid]`, uid = `r.tg_user_id \|\| 941296693` (TODO D2 fallback) |
| Build stage3 (уведомление «Видео готово» с approve/reject/regen кнопками) | `chat_id: 941296693` | `chat_id: uid`, uid из HTTP SELECT `\|\| 941296693` (TODO D2 fallback) |
| HTTP tg-alert failed (алерт при failure) | `jsonBody {chat_id: 941296693, ...}` | `jsonBody {chat_id: (($('HTTP SELECT').first().json.rows \|\| [{}])[0] \|\| {}).tg_user_id \|\| 941296693, ...}` |

Контракт ответа НЕ тронут: все `Respond *` ноды и IF-ветки без изменений (проверено: дифф параметров существующих нод — только 5 ожидаемых правок выше; `{ok:true}` / `{ok:true,status:'failed'}` / `{ok:false,error:...}` сохранены). SQL-инъекции нет — значение приходит параметром `?`, не конкатенацией.

Примечание: «Build alert approve/reject» из ТЗ в воркфлоу соответствует пара `Build stage3` (успех, кнопки approve/regen/reject) + `HTTP tg-alert failed` (алерт об ошибке) — обе покрыты.

## 3. tg-trigger: secret_token (Y5)

**Решение: оставить как есть (`additionalFields: {}`), НЕ задавать.** Обоснование:
- n8n 2.34.4 telegramTrigger: параметр `additionalFields.secretToken` читается с дефолтом `''`; при пустом значении `secret_token` **опускается** из setWebhook (стандартный паттерн узла: `...(secretToken ? { secret_token: secretToken } : {})`) — пустой токен безопасен, узел не падает, Telegram регистрирует вебхук без токена.
- Задать из env (`={{ $env.TELEGRAM_BOT_SECRET }}`) при FIX-10 (переменная НЕ задана на сервере) рискованно: undefined в выражении на активации = fail-closed, который сломает весь бот — запрещено условием задачи.
- Статичный токен в JSON = секрет в репо-файле без конвенции ротации; текущая защита уже есть: URL вебхука (uuid, не содержит bot token) + Whitelist-гейт (исполняется ДО Parser).
- Файл изменён только в части Y3/AU (tg-trigger node байт-в-байт не тронут).
- **Когда понадобится**: задать env `TELEGRAM_BOT_SECRET` на сервере и поменять `additionalFields` → `{"secretToken": "={{ $env.TELEGRAM_BOT_SECRET }}"}` + переактивировать воркфлоу (перерегистрация setWebhook). Одна строка.

## 4. AU-цепочка: кредитный гейт ДО creatify-link (остаток Y2)

Фактическая цепочка оказалась `AU Build link body → Switch AU link (ok-гейт URL) → AU HTTP creatify-link`. Гейт вставлен между Switch AU link и AU HTTP creatify-link — **копия паттерна AS** (C2, fail-closed, как DU/SH/AS-гейты wf-tg-bot):

```
Switch AU link main[0] → AU LB creatify (НОВ) → AU LB parse (НОВ) → AU Gate (НОВ) → Switch AU gate (НОВ)
    main[0] → AU HTTP creatify-link (как раньше)
    main[1] → AU Format low (НОВ) → TG AU alert (существующая, multi-input)
```

- `AU LB creatify` (httpRequest 4.5): GET `https://api.creatify.ai/api/remaining_credits/`, keypair X-API-ID/X-API-KEY из `$env`, timeout 15000, neverError вложенный — байт-в-байт с AS LB creatify.
- `AU LB parse` (code 2): body→raw→JSON.parse(data) → `creatify`; **pass-through** `Object.assign({}, $('AU Build link body').first().json, {creatify: cr})` — AU HTTP creatify-link шлёт `jsonBody = {{ $json }}`, без url сломается.
- `AU Gate` (code 2): **fail-closed** `cr == null || cr < 10` → low (конвенция wf-tg-bot: недоступный баланс БЛОКИРУЕТ генерацию).
- `Switch AU gate` (switch 3.4): boolean/equals `$json.ok == true` (эталон Switch CL allow / Switch AS gate, НЕ строковый 'true'), `fallbackOutput: extra`.
- `AU Format low` (code 2): esc из MO Format, текст «❌ Недостаточно кредитов creatify (N). Минимум 10.», `{chat_id: p.chat_id, text}`.
- `TG AU alert` — переиспользована (multi-input: второй источник пишет ребро в своём connections; параметры не менялись).
- Проверка wiring: прямые предки `AU HTTP creatify-link` = ровно 1 (`Switch AU gate`); `Switch AU link` main[0] → `AU LB creatify`; `Switch AU gate` main[0]→AU HTTP creatify-link, main[1]→AU Format low; `TG AU alert` = 2 предка (AU Format alert, AU Format low).

## 5. Валидация и sim

- `validate-workflow-json.py`: wf-tg-bot → **0 issues** (510 нод, BFS, node --check 231 jsCode); wf-creatify-webhook → **0 issues** (25 нод).
- `lint-workflow-json.py`: оба → **0 находок**.
- `node --check` всех jsCode обоих файлов: OK (231 + 6).
- Ресериализация: `json.dumps(ensure_ascii=False, indent=1)` без trailing newline — байт-в-байт (оба файла).
- sim-code-node-both.py (12 прогонов, все rc=0):
  - `AU LB parse`: balance 5 (body.data-строка) → `{ok, valid, url, creatify: 5}` — **pass-through url подтверждён**.
  - `AU Gate`: 5 → low; 20 → ok; null → low (fail-closed).
  - `AU Format low`: cr=5 → текст «❌ Недостаточно кредитов creatify (5). Минимум 10.», chat_id 777; cr=null → «(?)».
  - Динамика: `CT Build approve` → params `[555, "7"]`; `UV Build state`/`DU Check state` (стили однострочный/single-quote) → `[555]`; `OB Build insert client` → SQL с `?` + 9-й параметр `555`; `AU Build alert` → `[555]` + text passthrough; `Gate Build` → `[555]`.
  - Webhook: `Build session update` → `["42", 555]` и fallback `["42", 941296693]`; `Build session reset` → `[555]` / `[941296693]`; `Build stage3` → `chat_id: 555` / fallback `941296693`, текст и gen_id без изменений.
  - Выражение `HTTP tg-alert failed` проверено node -e: резолв `{chat_id: 555}`, fallback `{chat_id: 941296693}`.

## 6. Остатки

- **Parser**: `const TG = 941296693;` — мёртвая константа (не используется в jsCode), не трогалась (Parser — источник `tg_user_id`). Удалить при следующей правке Parser.
- **DU quick url2video** (и легаси-пути): session-link по script_id не резолвится (DU создаёт новый script) → вебхук использует fallback 941296693 (поведение как сегодня). Полный фикс: писать `sessions.generation_id`/session-link при submit в DU-цепочке — отдельный тикет, вне скоупа D2.
- **tg-trigger**: secret_token не задан (решение выше); включение — одна строка после провижининга env.
- **wf-creatify-webhook**: статичный path-token `factory/creatify/6d8f2a41c9e7b3d5f0a1c4e8` (issue С10) и fail-open авторизация (FIX-10/Y13) — вне скоупа D2, задокументировано в review.

## Файлы

- `/Users/aleksandrtrisenkov/Desktop/PROGRAMMING/РАБОЧИЕ ПРОЕКТЫ/КОНТЕНТ-ЗАВОД-API-MVP/.scratch/review-full-14aug/fixes/wf-tg-bot.json` (510 нод, 0 issues, lint 0)
- `/Users/aleksandrtrisenkov/Desktop/PROGRAMMING/РАБОЧИЕ ПРОЕКТЫ/КОНТЕНТ-ЗАВОД-API-MVP/.scratch/review-full-14aug/fixes/wf-creatify-webhook.json` (25 нод, 0 issues, lint 0)
- этот отчёт
