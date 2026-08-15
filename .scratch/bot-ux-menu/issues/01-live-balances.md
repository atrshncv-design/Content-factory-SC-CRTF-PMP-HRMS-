# T1: Живые балансы creatify + SC (вместо протухших из БД)

Status: done
Blocked by: —
Файл: `.scratch/bot-ux-menu/fixes/wf-tg-bot.json` (база: `.scratch/bot-ux-menu/base/wf-tg-bot.json`)
Спека: `.scratch/bot-ux-menu/spec.md` §5.1

## Задача
Заменить показ балансов из протухших `settings.credits_remaining` на ЖИВЫЕ бесплатные GET-запросы в трёх ветках wf-tg-bot: старт (ST-ветка), статус (ST2-ветка), бюджет (BG-ветка).

## Что сделать (все правки — в JSON воркфлоу, исходники репо не трогать)

1. **ST-ветка** (Switch cmd out[0] → ST Build settings → ST HTTP settings → ST Build today → ST HTTP today → ST Format → TG start):
   - После `ST HTTP today` добавить: `ST LB creatify` (HTTP GET `https://api.creatify.ai/api/remaining_credits/`, typeVersion 4.5, authentication none, sendHeaders keypair: `X-API-ID: {{ $env.CREATIFY_API_ID }}`, `X-API-KEY: {{ $env.CREATIFY_API_KEY }}`, options.timeout 15000, options.response.response.neverError true) → `ST LB sc` (HTTP GET `https://api.scrapecreators.com/v1/account/credit-balance`, header `x-api-key: {{ $env.SCRAPECREATORS_API_KEY }}`, те же опции) → `ST LB parse` (Code: универсальный парсер, см. ниже) → `ST Format` (переписать чтение: `const lb = $('ST LB parse').first().json; const cr = lb.creatify; const sc = lb.sc;`).
2. **ST2-ветка** (status): аналогично, ноды `ST2 LB creatify`, `ST2 LB sc`, `ST2 LB parse` после `ST2 HTTP client`; `ST2 Format` показывает `💰 creatify: {cr} | SC: {sc}` (заменить строку с settings.credits_remaining).
3. **BG-ветка** (budget): ноды `BG LB creatify`, `BG LB sc`, `BG LB parse` после `BG HTTP`; `BG Format` — заменить `r.credits` на живой creatify, добавить строку `SC: {sc}`; сохранить сегодня/месяц/лимиты/прогноз из существующего SQL.
4. **Универсальный парсер баланса SC** (важно): ответ может прийти JSON-строкой в `$json.data`. Код: проверить `body.creditCount` → `raw.creditCount` → `JSON.parse(raw.data).creditCount` (try/catch). creatify: `body.remaining_credits` (объект в $json.body) → `raw.remaining_credits` → `JSON.parse(raw.data).remaining_credits`. Вывод: `{creatify: N, sc: N}` (числа; при ошибке — `null` → в тексте `?`).
5. **Защитный паттерн чтения ответа HTTP**: `($json.body && typeof $json.body === 'object') ? $json.body : $json`.
6. Тексты: `💰 creatify: {cr} | SC: {sc}` — без подчёркиваний; числа экранировать через esc() (эталон `MO Format` — КОПИРОВАТЬ строку, не перенабирать).

## Валидация перед сдачей
- `node --check` всех новых jsCode.
- BFS-достижимость от tg-trigger (все новые ноды соединены).
- `python3 scripts/lint-workflow-json.py` на результат — 0 НОВЫХ находок.
- `python3 scripts/sim-code-node.py` для `ST LB parse`/`ST2 LB parse`/`BG LB parse` с тремя вариантами входа (объект, JSON-строка в data, ошибка).
- НЕ вызывать никаких платных API (тесты — статические/симуляции).

## Вывод
Полный JSON воркфлоу → `.scratch/bot-ux-menu/fixes/wf-tg-bot.json` (перезаписать). В ответе: список новых нод с именами, результаты валидаций, diff-сводка.
