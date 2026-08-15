# REVIEW-02 — Creatify-кластер (CR + базовый контур генерации)

**Status:** done (13.08.2026, см. docs/CODE-REVIEW-2026-08-13.md)
**Blocked by:** —

## Задача
Полный построчный разбор воркфлоу n8n из файлов репо
`/Users/aleksandrtrisenkov/Desktop/PROGRAMMING/РАБОЧИЕ ПРОЕКТЫ/КОНТЕНТ-ЗАВОД-API-MVP/workflows/`:

- `wf-creatify-link.json` (id ...00c)
- `wf-creatify-submit.json` (id ...00d)
- `wf-creatify-webhook.json` (id ...00e)
- `wf-creatify-poll.json`
- `wf-creatify-text.json` (CR-2, ...020)
- `wf-creatify-avatar.json` (CR-1, ...019)
- `wf-creatify-asset.json` (CR-3, ...021)
- `wf-creatify-adclone.json` (CR-4, ...022)
- `wf-creatify-shorts.json` (CR-5, ...023)
- `wf-creatify-product.json` (CR-6, ...024)
- `wf-creatify-banner.json` (CR-7, ...025)

## Чек-лист (по каждому файлу)
1. Контракт входа/выхода webhook против `specs/API-REFERENCES.md` + TICKETS-EXPANSION.md
   (разделы 20–24, CR-1..CR-7). Пути реальные: `/api/ai_scripts/`, `/api/asset_generator/`,
   `/api/ads_clone/`, `/api/ai_shorts/`, `/api/product_to_videos/gen_image/`, `/api/iab_images/`,
   `/api/inspiration_jobs/`, `/api/personas/`, `/api/remaining_credits/`.
2. Mock/real-переключатели (Switch `$env.CREATIFY_API_ID === 'PLACEHOLDER_UNTIL_TOMORROW'`).
3. Ветки валидации ошибок: невалидный вход → осмысленная ошибка, НЕ уход в платный HTTP.
4. low_credits-гейты (пороги: floor 50, shorts 30, adclone 20, banner 10 — соответствуют ли).
5. Авторизация: keypair-заголовки из $env, typeVersion ≥4.5, contentType json, authentication:"none".
6. jsonBody = `={{ $json.payload }}` (payload в Code-ноде), без вложенных `{{ }}`.
7. Идемпотентность: creatify-webhook (creatify_id, duplicate), UPDATE sessions, LEFT JOIN scripts.
8. webhookId в нодах (cr4-adclone, cr5-shorts, cr6-product, cr7-banner, cr7-inspiration).
9. Секреты: нет inline-ключей.
10. Error-handling: retry/backoff (maxTries 3), fallbackOutput extra, timeout ≥120s на генерацию.
11. Критичные цены: adclone 84 кред (НЕ 12!), ai_shorts 5/30с отложенное списание, asset 1,
    product 1+3 — стоят ли гейты/предупреждения в воркфлоу; риск непреднамеренной траты.
12. Списание отложенное: webhook-ветка обрабатывает done/duplicate/failed корректно.

## Формат отчёта (markdown)
- Таблица находок: | # | Воркфлоу | Severity (🔴/🟠/🟡/🟢) | path:line (node name) | Описание | Рекомендация |
- Раздел «Проверенные контракты» (вход/выход, соответствие спеке).
- Раздел «Непроверенное» (живые вызовы запрещены).

## Ограничения
- ТОЛЬКО чтение файлов репо. Никаких сетевых вызовов, никакого SSH, никаких API.
- Секреты не выводить. Код НЕ менять. Отчёт — в ответе (не файл).
- Язык отчёта: русский.
