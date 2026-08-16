# 07 — Клиентские профили, роли и hermes-bridge

**Требования:** G05 (операторский доступ), G04 (Robotec), R01 (доводка до идеала)
**Blocked by:** —
**Зона:** `workflows/wf-tg-bot.json` (ревью), `hermes-bridge/server.py`, `infra/db/migrate-client-profiles*.py`
**Волна:** 1
**Status:** done

## Что должно заработать

Клиентские профили и ролевой доступ работают корректно: per-chat active_client_id, интервью, документы (PDF/DOCX/TXT), OCR фото, редактирование вопросов, мягкое удаление.

## Из брифа / манифеста, дословно

> «Только я (оператор)»
> «Robotec остаётся»

## Разделы спецификации

История 5.

## Критерии приёмки

- [x] Резолв active_client_id per-чат (users.active_client_id → settings.active_client_id fallback) без битого значения 999.
- [x] Профиль Robotec (id=1) — активен, контекст используется в промптах.
- [x] hermes-bridge /doc-text и /img-text живы и не ломают /ask.
- [x] Миграции v1/v2 воспроизводимы из репо; v3 отсутствует в репо — восстановить файл миграции.
- [x] Команды add_operator/operators/whitelist работают, нет tg_user_id хардкода 941296693.
- [x] Валидатор + sim зелёные; 0 платных вызовов.
