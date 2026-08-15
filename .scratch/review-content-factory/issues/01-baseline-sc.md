# REVIEW-01 — Базовый контур + SC-кластер

**Status:** done (13.08.2026, см. docs/CODE-REVIEW-2026-08-13.md)
**Blocked by:** —

## Задача
Полный построчный разбор воркфлоу n8n из файлов репо
`/Users/aleksandrtrisenkov/Desktop/PROGRAMMING/РАБОЧИЕ ПРОЕКТЫ/КОНТЕНТ-ЗАВОД-API-MVP/workflows/`:

- `wf-onboard.json` (id 0dbb4ea9...)
- `wf-analytics.json` (id ...00b)
- `wf-creators-search.json` (SC-1, ...015)
- `wf-creator-profile.json` (SC-2, ...016)
- `wf-creator-content.json` (SC-3, ...014)
- `wf-audience.json` (SC-4, ...017)
- `wf-transcripts-comments.json` (SC-5, ...018)
- `zz-test-sqlite.json` (служебный)

## Чек-лист (по каждому файлу)
1. Контракт входа/выхода webhook против `specs/API-REFERENCES.md` и `specs/TICKETS-EXPANSION.md`.
2. Mock/real-переключатели (Switch `$env.<KEY> === 'PLACEHOLDER_UNTIL_TOMORROW'`).
3. Ветки валидации ошибок: невалидный вход → осмысленная ошибка, НЕ уход в платный HTTP.
4. low_credits-гейты и защита от трат (SC: баланс/кэш, audience = 26 кред — есть ли предупреждение?).
5. Авторизация: httpHeaderAuth/keypair, $env-заголовки, тип ноды HTTP ≥4.5, contentType json.
6. jsonBody без вложенных `{{ }}` (паттерн Code-нода Build body → `={{ $json.payload }}`).
7. Идемпотентность (INSERT OR IGNORE в competitors и т.п.).
8. webhookId / имена нод без пробелов.
9. Секреты: нет inline-ключей в JSON.
10. SSRF-защита (onboard: запрет 10/8, 172.16/12, 192.168/16, 127/8).
11. Error-handling: retry/backoff, fallbackOutput на Switch, neverError.
12. Для SC-кластера: кэш-поведение эндпоинтов, trim=true, цены (audience 26 кред!) — соответствует ли воркфлоу правилам бюджета из скилла.

## Формат отчёта (markdown)
- Таблица находок: | # | Воркфлоу | Severity (🔴/🟠/🟡/🟢) | path:line (node name) | Описание | Рекомендация |
- Раздел «Проверенные контракты»: для каждого воркфлоу — вход/выход, совпадает ли со спекой (да/нет/частично).
- Раздел «Непроверенное» (что требует живого вызова — запрещено).

## Ограничения
- ТОЛЬКО чтение файлов репо. Никаких сетевых вызовов, никакого SSH, никаких API.
- Секреты не выводить; при находке — маскированный фрагмент.
- Код НЕ менять. Отчёт — в ответе (не файл).
- Язык отчёта: русский.
