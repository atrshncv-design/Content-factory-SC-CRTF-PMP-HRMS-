# 06. Сценарий работы с аватарами

**Status:** ready-for-agent

Blocked by: 02-fsm-framework

## Goal

Перенести загрузку BYOA-аватара и список моих аватаров из n8n в Python-бота.

## Acceptance Criteria

- [ ] Команда /upload_avatar: бот запрашивает фото/видео аватара, сохраняет file_id и metadata.
- [ ] Команда /my_avatars: список с кнопками выбора.
- [ ] Интеграция с db-bridge для хранения creator_id/persona_id.
- [ ] Тесты на FSM и хранение аватаров.

