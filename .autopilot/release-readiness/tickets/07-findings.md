# 07 — Клиентские профили, роли и hermes-bridge: находки

Тикет: `07-client-profiles-and-access.md`  
Дата аудита: 2026-08-16  
Scope: `hermes-bridge/server.py`, `infra/db/migrate-client-profiles*.py`, `workflows/wf-tg-bot.json`.

## Критерии приёмки — статус

| Критерий | Статус | Примечание |
|---|---|---|
| Резолв active_client_id per-чат | ✅ | Паттерн `COALESCE(users.active_client_id, settings.active_client_id)` с валидацией `clients.status='active'` и fallback на первого active-клиента используется во всех SQL-нодах. |
| Профиль Robotec (id=1) активен | ✅ | `clients.status='active'` для id=1 в 001_init.sql + seeds; резолв fallback вернёт id=1 при отсутствии per-чат значения. |
| hermes-bridge /doc-text и /img-text живы | ✅ | Эндпоинты реализованы, auth через X-BRIDGE-TOKEN, не ломают /ask. Smoke /health OK. |
| Миграции v1/v2/v3 воспроизводимы | ✅ | Файлы добавлены в `infra/db/`, `migrate.sh` запускает их в порядке. Dry-run на копии live БД показал no-op. |
| Команды profile/profiles/add_operator/operators | ✅ | Есть в Parser, Switch cmd, tg-commands-35.json; доступ проверяется через `users.role`. |
| Нет tg_user_id хардкода 941296693 в wf-tg-bot.json | ✅ | Удалён мёртвый `const TG = 941296693;` из Parser. |
| Валидатор + sim зелёные | ✅ | `validate_workflow.py` — 0 issues; `tests/` — 25/25 passed. |
| 0 платных вызовов | ✅ | Только static analysis, моки, бесплатные smoke (health, auth, schema dry-run). |

## Исправлено в рамках тикета

### 1. `workflows/wf-tg-bot.json` — SQL-синтаксис в профильных нодах

**Найдено:** две SQL-ошибки в нодах профиля:
- `PDL Build`: `(SELECT SELECT COALESCE(...)` → исправлено на `(SELECT COALESCE(...)`.
- `PPM Build done`: `c.id = SELECT COALESCE(...)` → исправлено на `c.id = (SELECT COALESCE(...)`.

**Влияние:** без исправления команды `profiles` (список/переключение) и настройка `publish_platforms` в карточке профиля падали бы с SQL-ошибкой.

**Проверка:** `node --check` для всех jsCode + `validate_workflow.py` — 0 issues.

### 2. `workflows/wf-tg-bot.json` — мёртвый хардкод `const TG = 941296693;` в Parser

**Найдено:** переменная объявлялась, но не использовалась ни в access-логике, ни в маршрутизации.

**Исправление:** удалена строка. Доступ к боту реализован через `users.role` (`Access build` → `Access check`).

## Найдено вне тикета (записано, не исправлено)

| ID | Severity | Файл:нода/строка | Доказательство | Гипотеза фикса | Платный риск |
|---|---|---|---|---|---|
| 07-F01 | 🟡 | `workflows/wf-creatify-webhook.json` | Хардкод `chat_id: 941296693` и fallback `uid = r.tg_user_id \|\| 941296693` в 4 местах (TODO D2) | Заменить fallback на извлечение tg_user_id из generations/clients/sessions; либо сделать явный owner-recv только для админа | нет |
| 07-F02 | 🟡 | `workflows/wf-sync-accounts.json:228` | `chat_id: 941296693` при уведомлении о перелогине | Передавать chat_id из соответствующего пользователя/сессии | нет |
| 07-F03 | 🟡 | `workflows/wf-creatify-avatar.json:601,704` | `chat_id: 941296693` в уведомлениях об одобрении/отклонении аватара | Передавать chat_id заявителя | нет |
| 07-F04 | 🟡 | `workflows/wf-publish-status.json:282,428` | `chat_id: 941296693` в статусах публикации | Передавать chat_id оператора, запустившего публикацию | нет |

**Примечание:** хардкоды вне `wf-tg-bot.json` помечены как TODO D2 / уведомления владельцу. Они не блокируют командный профильный доступ из тикета 07.

## Проверки

- `python3 .scratch/bot-ux-menu/validate_workflow.py workflows/wf-tg-bot.json` → 0 issues.
- `python3 -m pytest tests/ -v` → 25 passed.
- `python3 infra/db/migrate-client-profiles*.py /tmp/server-factory.db --dry-run` (копия live) → все no-op, схема совпадает.
- `curl http://127.0.0.1:8642/health` (на сервере) → `{"ok": true}`.
- `curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:8642/ask` (без токена) → 401.
