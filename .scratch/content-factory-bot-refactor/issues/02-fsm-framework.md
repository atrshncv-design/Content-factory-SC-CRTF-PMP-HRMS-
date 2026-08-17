# 02. FSM framework и базовые абстракции сценариев

**Status:** ready-for-agent

Blocked by: 01-bootstrap-core

## Goal

Внедрить aiogram FSM, generic-обработчики inline-кнопок и модули для сценариев, чтобы добавление нового сценария не требовало изменения core.

## Acceptance Criteria

- [ ] Настроен Storage для FSM на SQLite (aiosqlite).
- [ ] Создан декоратор/роутер для сценариев: каждый сценарий = отдельный файл в bot/scenarios/.
- [ ] Generic-клавиатуры: menu_button(), cancel_button(), confirm_keyboard().
- [ ] Единая точка входа для callback-запросов с routing по префиксу (avv_*, sh_*, url_*, etc.).
- [ ] Unit-тесты на FSM-переходы.

