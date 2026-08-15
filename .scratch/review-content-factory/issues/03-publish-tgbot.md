# REVIEW-03 — Publish-кластер (PM) + wf-tg-bot

**Status:** done (13.08.2026, см. docs/CODE-REVIEW-2026-08-13.md)
**Blocked by:** —

## Задача
Полный построчный разбор воркфлоу n8n из файлов репо
`/Users/aleksandrtrisenkov/Desktop/PROGRAMMING/РАБОЧИЕ ПРОЕКТЫ/КОНТЕНТ-ЗАВОД-API-MVP/workflows/`:

- `wf-publish.json` (PM-1/PM-2/PM-3, id ...010, 26 нод)
- `wf-publish-status.json` (id ...011, cron)
- `wf-sync-accounts.json` (id ...012, cron)
- `wf-tg-alerts.json` (id ...00a)
- `wf-tg-bot.json` (id ...013, 278 нод)

## Чек-лист (по каждому файлу)
1. Контракт входа/выхода против `specs/API-REFERENCES.md` + TICKETS-EXPANSION.md
   (разделы 18/18a/21, PM-1/PM-2/PM-3; UX-1 раздел 26).
2. wf-publish: details[] под все платформы, publication_type enum (POST=1/STORY=2/REELS=4),
   publication_status=5, account_ids из актуального маппинга (tiktok=106, НЕ 103).
3. PM-3: caption-адаптация через hermes-bridge (host.docker.internal:8642/ask,
   X-BRIDGE-TOKEN $env, timeout 300s, `<CAPTION>` контракт, fallback=исходный текст).
4. Mock/real-переключатели ($env.POSTMYPOST_TOKEN === 'PLACEHOLDER_UNTIL_TOMORROW').
5. Ветки валидации ошибок: 422 «аккаунт не подключён» обрабатывается, не уходит в платный POST.
6. Авторизация postmypost (Bearer $env), тип ноды ≥4.5.
7. jsonBody паттерн (Code-нода Build body → `={{ $json }}` или `={{ {sql, params} }}`).
8. Идемпотентность/повторы: publish-status (pending_publication → published, IF any? корректно),
   sync-accounts (UPSERT, loop Split In Batches).
9. wf-tg-bot: парсер команд (28 команд), Switch правила, callback-обработчики,
   whitelist (941296693), esc()-экранирование Telegram Markdown, answerCallbackQuery,
   валидации: невалидный аргумент НЕ уходит в платный webhook (Switch обязателен).
10. Секреты: нет inline-ключей.
11. Error-handling: retry/backoff, neverError на HTTP к webhook'ам, fallbackOutput.

## Формат отчёта (markdown)
- Таблица находок: | # | Воркфлоу | Severity (🔴/🟠/🟡/🟢) | path:line (node name) | Описание | Рекомендация |
- Раздел «Проверенные контракты».
- Раздел «Непроверенное».
- Для wf-tg-bot: отдельная таблица «28 команд: ветка есть / отвечает / риск платного вызова».

## Ограничения
- ТОЛЬКО чтение файлов репо. Никаких сетевых вызовов, никакого SSH, никаких API.
- Секреты не выводить. Код НЕ менять. Отчёт — в ответе (не файл).
- Язык отчёта: русский.
