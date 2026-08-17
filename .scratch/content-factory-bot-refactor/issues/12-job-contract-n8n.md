# 12. Job-контракт и рефактор n8n job handlers

**Status:** ready-for-agent

Blocked by: 03-url2video

## Goal

Зафиксировать HTTP-контракт между ботом и n8n и превратить wf-tg-bot в тонкие job-only workflow.

## Acceptance Criteria

- [ ] Создан документ docs/job-contract.md с payload/status форматами.
- [ ] Каждый job handler в n8n не содержит UI-логики, только вызов API + запись в БД.
- [ ] wf-tg-bot больше не обрабатывает Telegram-команды (или отключен).
- [ ] Бот и n8n используют единый auth-token для webhook.

