# 04. Сценарий AI Shorts

**Status:** ready-for-agent

Blocked by: 02-fsm-framework

## Goal

Перенести генерацию шортс по теме из n8n в Python-бота.

## Acceptance Criteria

- [ ] Пользователь вводит тему или выбирает из предложенных.
- [ ] Бот запрашивает длительность (30/60 сек) кнопками.
- [ ] Бот вызывает n8n job handler shorts с payload {topic, duration, user_id, client_id}.
- [ ] После генерации показывает видео и кнопки Меню/Отмена/Сгенерировать ещё.
- [ ] Тесты на FSM и callback routing.

