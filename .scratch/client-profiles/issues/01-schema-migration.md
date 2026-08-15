# 01 — Схема БД для профилей (миграция)

**What to build:** Расширить схему factory.db под профили клиентов: колонки контекста в `clients`, per-чат активный профиль в `users`, черновик интервью в `sessions`, сид владельца. Миграция идемпотентная, применяется на сервере при деплое (DDL через прямой sqlite3 — db-bridge DDL не выполняет).

**Blocked by:** None — can start immediately

**Status:** done (14.08, верифицировано оркестратором)

- [x] Скрипт миграции (python/sqlite3, идемпотентный: проверка существования колонок перед ALTER) добавляет: `clients.description TEXT`, `clients.context_links TEXT` (JSON-массив), `clients.context_docs TEXT` (JSON-массив {name,mime,text,chars}), `clients.context_refs TEXT` (JSON-массив), `users.active_client_id INTEGER NULL`, `sessions.profile_draft TEXT`
- [x] Сид: `INSERT OR IGNORE INTO users (tg_user_id, username, role) VALUES (941296693, 'owner', 'admin')`
- [x] `--dry-run` показывает план, без применения; применение — отдельным флагом (применяется на сервере только в деплой-тикете 12)
- [x] Проверка на копии live factory.db (локальная) — PRAGMA table_info показывает новые колонки (синтетическая живая схема + старая локальная копия: 6/6 ALTER, сид OK, повторный прогон no-op)

Артефакт: `.scratch/client-profiles/fixes/migrate-client-profiles.py`
