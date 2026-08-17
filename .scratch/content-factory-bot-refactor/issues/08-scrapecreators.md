# 08. Интеграция со ScrapeCreators: сбор аналитики

**Status:** ready-for-agent

Blocked by: 02-fsm-framework

## Goal

Вынести запуск сбора аналитики из n8n в Python-бота, оставив сам платный вызов в n8n job handler.

## Acceptance Criteria

- [ ] Пользователь выбирает тип аналитики (creator, audience, comments, transcript и т.д.).
- [ ] Бот собирает параметры (handle, platform, url).
- [ ] Бот вызывает n8n job handler analytics с payload.
- [ ] По завершении бот показывает результат или ошибку.
- [ ] Тесты на валидацию параметров.

