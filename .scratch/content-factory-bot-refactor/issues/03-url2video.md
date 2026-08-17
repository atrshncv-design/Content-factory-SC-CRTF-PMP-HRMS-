# 03. Сценарий URL → видео

**Status:** ready-for-agent

Blocked by: 02-fsm-framework

## Goal

Перенести сценарий получения видео из ссылки из n8n в Python-бота, оставив генерацию в n8n job handler.

## Acceptance Criteria

- [ ] Пользователь вводит /url2video или нажимает кнопку.
- [ ] Бот запрашивает URL, валидирует его.
- [ ] Бот вызывает n8n job handler url2video через webhook с payload {url, user_id, client_id, duration}.
- [ ] Бот показывает статус генерации и итоговое видео с кнопками Меню/Отмена.
- [ ] Тесты на валидацию URL и FSM-переходы.

