# C1-sc — low_credits-гейты ДО платных SC-вызовов (search / profile / content / transcripts-comments)

**Статус:** DONE 14.08, 0 кредитов (только статические проверки + sim).
**Тикет:** `.scratch/review-full-14aug/issues/C1-credit-gates.md` (Y1 из `docs/CODE-REVIEW-2026-08-14.md`, волна C «защита трат»).
**База:** `.scratch/review-full-14aug/base/` — live-экспорты 14.08 (search 25 нод / profile 20 / content 18 / transcripts-comments 37). НЕ репо `workflows/`.
**Результат:** `.scratch/review-full-14aug/fixes/` — search 29 нод / profile 24 / content 22 / transcripts-comments 45.

## Проблема (Y1)
У SC search/profile/content/transcripts mock/real-гейты есть (FIX-06), но **low_credits-гейта ДО вызова нет** —
только постфактум-обработка 402 в Normalize. При балансе ≤ 0 платный запрос (1–3 кред/шт) уходит в минус
или возвращает 402. wf-audience (26 кред/запрос) уже защищён гейтом 30 (FIX-05) — остальные 4 воркфлоу нет.

## Что сделано (паттерн — эталон wf-audience FIX-05 + тикет C1)

В каждый воркфлоу между mock-переключателем (**real-ветка**, output index 1) и платформенным Switch вставлена
цепочка из 4 нод:

```
... → Switch mock ──(0)──→ Code mock → Respond mock            (mock-ветка НЕ тронута)
                  └─(1)──→ HTTP Credit Balance → Code balance → IF low credits ──(true)→ Respond low credits
                                                                          └──(false)→ Switch platform → HTTP <платный SC> → …
```

1. **HTTP Credit Balance** (`httpRequest` v4.5) — бесплатный `GET https://api.scrapecreators.com/v1/account/credit-balance`,
   keypair-заголовок `x-api-key` из `$env.SCRAPECREATORS_API_KEY` (паттерн «ST LB sc» из wf-tg-bot),
   `options: {timeout: 15000, response: {response: {neverError: true}}}` — neverError ТОЛЬКО вложенный
   (top-level молча игнорируется в n8n 2.34.4). 0 кредитов.
2. **Code balance** (`code` v2, runOnceForAllItems) — универсальный парсер баланса: `body(объект) → raw → JSON.parse(data)`,
   `creditCount` ищется во всех местах; try/catch → `balance_unavailable: true` (баланс −1). Дополнительно
   **прокидывает входной item** (`Object.assign({}, $('Code validate'|'Detect …').first().json, …)`) —
   HTTP-ноды не прокидывают входной item, а платформенные Switch читают `$json.platform(s)`; без прокидывания
   Switch после гейта ушёл бы в fallback (сломало бы маршрутизацию). Существующие Switch/HTTP **не менялись**.
3. **IF low credits** (`if` v2.3, комбинатор `and`):
   - `{{ $json.balance }} < 5` (number/lt) **И** `{{ $json.balance_unavailable }} == false` (boolean/equals)
   → **true**: `Respond low credits` → `{ok: false, error: 'low_credits', balance}` БЕЗ платного вызова;
   → **false**: платная ветка как раньше (баланс ≥ порога **или** баланс не прочитался).
4. **Respond low credits** (`respondToWebhook` v1.5) — `={{ {ok: false, error: 'low_credits', balance: $('Code balance').first().json.balance} }}` (как в wf-audience).

**Порог 5** везде (задание: «порог 5; для wf-transcripts-comments можно 5»): max цена search/profile/content/transcripts
≈ 1–3 кред/запрос → порог 5 ≥ max разовой цены с запасом; ровно 5 проходит (sim T3).

## Решение по `balance_unavailable` (обоснование)
**Пропускаем** (fail-open): если баланс не прочитался (401/502/сеть/не-JSON) — IF уходит в платную ветку как раньше.
Обоснование: (а) гейт — защита от минуса, а не новая точка отказа; при сбое бесплатного balance-эндпоинта
рабочая цепочка (проверенная годами) не должна деградировать до «все запросы сломаны»; (б) платные вызовы и так
имеют постфактум-обработку 402 в Normalize — худший случай при fail-open = прежнее поведение базы;
(в) fail-closed (блокировать при недоступности) превратил бы эпизодический сбой balance-эндпоинта в полный
отказ сервиса. Сценарий подтверждён sim: `{balance: -1, balance_unavailable: true}` → IF false → платная ветка.

## Mock-режим
Во всех 4 воркфлоу mock-переключатель (`Switch mock` на `$env.SCRAPECREATORS_API_KEY == PLACEHOLDER_UNTIL_TOMORROW`)
стоит ДО гейта: гейт вставлен только в real-ветку (output 1) — mock-ветка (`Code mock → Respond mock`) не тронута.
В mock-режиме платный вызов и balance-запрос не выполняются (проверено по connections: `Switch mock main[0] → Code mock`,
`main[1] → HTTP Credit Balance`).

## Сводка по файлам

| Файл (fix) | Что вставлено | Порог | Валидация |
|---|---|---|---|
| `wf-creators-search.json` (25→29 нод) | 1 гейт: HTTP Credit Balance → Code balance → IF low credits → Respond low credits; real-ветка `Switch mock` → гейт → Switch IG/YouTube/TikTok (3 платных HTTP: search) | 5 | validate 0 issues (29 нод, 10/10 jsCode) · lint 0 находок · node --check OK · sim 6/6 |
| `wf-creator-profile.json` (20→24 нод) | 1 гейт (те же 4 ноды); real-ветка → Switch platform (4 платных HTTP: instagram/tiktok/youtube/twitter profile) | 5 | validate 0 issues (24 нод, 8/8 jsCode) · lint 0 находок · node --check OK · sim 1/1 |
| `wf-creator-content.json` (18→22 нод) | 1 гейт (те же 4 ноды); real-ветка → Switch platform (4 платных HTTP: reels/videos/channel-videos/user-tweets) | 5 | validate 0 issues (22 нод, 8/8 jsCode) · lint 0 находок · node --check OK · sim 1/1 |
| `wf-transcripts-comments.json` (37→45 нод) | **2 гейта**: transcript-цепочка (HTTP Credit Balance transcript → Code balance transcript → IF low credits transcript → Respond low credits transcript; → Switch transcript platform: TikTok/YouTube transcript) + comments-цепочка (аналогично, comments-суффиксы; → Switch comments platform: TikTok/YouTube/Instagram comments) | 5 (оба) | validate: 0 новых issues, 23 «недостижимых» — предсуществующее ложное срабатывание (см. ниже) · lint 0 находок · node --check OK (5/5 новых) · sim 4/4 |

Итого: **8 новых нод** (по 4 на гейт), платных SC-вызовов защищено: search 3, profile 4, content 4, transcripts+comments 5.

## Валидации (все статические, 0 кредитов)
- `validate-workflow-json.py` — search/profile/content: **0 issues**; transcripts-comments: единственный issue —
  «НЕДОСТИЖИМЫЕ (23)» — **предсуществующее ложное срабатывание** (задокументировано в `reports/04-sc-analytics-cluster.md`):
  в воркфлоу ДВА независимых триггера (`transcript-webhook` + `comments-webhook`), BFS валидатора идёт от первого;
  comments-ветка подключена к своему вебхуку корректно. В базе было 19, +4 = новые ноды comments-гейта (та же
  comments-ветка). Все остальные проверки файла (дубли имён/id, jsCode 14/14) — 0.
- `lint-workflow-json.py` — **0 находок** во всех 4 файлах.
- `node --check` — все новые парсеры OK (5 шт.), плюс 10/8/8/14 jsCode в валидаторе без ошибок.
- Sim `sim-code-node-both.py` (стабит и `$json`, и `$('Node')`) — **11/11 сценариев** на новых Code balance:
  balance 66 (body/direct/data-string/строкой «5»), 12.5, 3 (<5), 4 (<5), пустой ответ, 401 → −1+unavailable;
  во всех — pass-through `platform(s)/handle/limit/api_url` сохранён (Switch после гейта работает).
- IF-логика проверена симуляцией: `3 → LOW_CREDITS`, `5 → PAID`, `66 → PAID`, `unavailable → PAID`.
- Существующие ноды не изменены: diff параметров/type/typeVersion/credentials = 0 отличий от базы (только connections).
- Grep-ловушки: `={{ ` префиксы на месте (lint 0), neverError вложенный, `x-api-key` из `$env`, порог 5.

## Файлы
- **Фиксы:** `.scratch/review-full-14aug/fixes/wf-creators-search.json`, `wf-creator-profile.json`, `wf-creator-content.json`, `wf-transcripts-comments.json`
- **Отчёт:** `.scratch/review-full-14aug/fixes/C1-sc-credit-gates.md`
- База не изменялась. На сервер НЕ применено (паттерн волн фиксов — применение после «ок»).

## Остаётся вне этого фикса (из C1, отдельные тикеты)
- AS-цепочка wf-tg-bot (start_cycle → creatify-link/submit) — гейт 10/50 (Y2, второй пункт тикета C1 — не этот сабагент).
- Авторизация публичных webhook SC-кластера (Y12), доменный regex в Detect transcript/comments (отчёт 04, пункты 11–12) — вне объёма C1-sc.
