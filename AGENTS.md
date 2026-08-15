# AGENTS.md

Проект: контент-завод — фабрика коротких вертикальных видео (n8n 2.34.4 в Docker + Hermes Agent + SQLite factory.db).

## Agent skills

### Issue tracker

Local markdown: one feature per directory `.scratch/<feature-slug>/` with `spec.md` and one file per ticket in `issues/`. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: `CONTEXT.md` (глоссарий и инварианты) + `docs/adr/` (решения). Спеки проекта — в `specs/`. See `docs/agents/domain.md`.

## Правила работы

- Источник правды для воркфлоу — сервер `~/factory/`; репо `workflows/` синхронизируется при деплое. Новейшую версию воркфлоу искать по всем `.scratch/*/fixes/`.
- Платные вызовы (creatify/scrapecreators) — только с явного согласия пользователя; тесты «до точки списания».
- TG-тексты: экранирование Markdown (`esc()`), статика без `_`, callback_data только `={{ expr }}`.
- Секреты — только имена переменных; значения в `.env` сервера (никогда в коде/чате/коммитах).
- Telegram-ноды: typeVersion telegram v1.2, switch v3.4; neverError — вложенный `options.response.response.neverError`; HTTP-ноды платных вызовов — typeVersion 4.5 + keypair-заголовки.
