# 01. Bootstrap Python-бота и core-обработчики

**Status:** ready-for-agent

Blocked by: none

## Goal

Создать структуру сервиса factory-tg-bot, Docker-конфигурацию, подключение к config/.env, db-bridge, и реализовать /start, главное меню, статус.

## Acceptance Criteria

- [ ] Создан каталог apps/factory-tg-bot с pyproject.toml, aiogram 3, pydantic, aiosqlite, pytest.
- [ ] Dockerfile и docker-compose.yml для сервиса factory-tg-bot рядом с factory-n8n.
- [ ] Конфигурация через pydantic-settings из .env (TELEGRAM_BOT_TOKEN, FACTORY_DB_BRIDGE_TOKEN, WEBHOOK_HOST и т.д.).
- [ ] Роутер core: /start, /menu, /status, обработка callback cmd:menu, cmd:cancel.
- [ ] Подключение к db-bridge для SELECT/UPDATE sessions и users.
- [ ] Бот запускается локально в polling режиме; webhook endpoint готов.

