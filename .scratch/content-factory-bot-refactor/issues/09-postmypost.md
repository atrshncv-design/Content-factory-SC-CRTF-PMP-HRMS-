# 09. Интеграция с Post My Post: автопостинг

**Status:** ready-for-agent

Blocked by: 02-fsm-framework

## Goal

Перенести логику автопостинга из n8n в Python-бота.

## Acceptance Criteria

- [ ] Команда /publish_type и связанные кнопки работают в боте.
- [ ] Бот запрашивает дату/время поста, платформу, текст/медиа.
- [ ] Бот вызывает n8n job handler publish_post.
- [ ] Показ запланированных постов и статуса.
- [ ] Тесты на FSM и валидацию.

