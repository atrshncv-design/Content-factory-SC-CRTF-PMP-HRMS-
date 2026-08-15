# 13 — Миграция v2: publish_platforms + profile_questions

**What to build:** Расширить схему под волну 2: колонка дефолтных платформ публикации в `clients` и редактируемый список вопросов интервью в `settings` (с сидом дефолтных 8 вопросов). Идемпотентная миграция, применяется на сервере при деплое.

**Blocked by:** None — can start immediately (disjoint: python-скрипт)

**Status:** done (15.08, верифицировано оркестратором)

- [ ] Скрипт миграции v2 (расширить `.scratch/client-profiles/fixes/migrate-client-profiles.py` или новый файл `migrate-client-profiles-v2.py`, тот же стиль: --dry-run/--apply, идемпотентно через PRAGMA table_info): `ALTER TABLE clients ADD COLUMN publish_platforms TEXT` (JSON-массив дефолтных платформ), `INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES ('profile_questions', '<JSON 8 дефолтных вопросов волны 1>', datetime('now'))` (дефолт = текущие вопросы интервью: название, ниша, что делает компания, ЦА, ссылки, документы, тон, конкуренты/референсы)
- [ ] Бэкап БД перед apply; повторный прогон — no-op
- [ ] Тесты: синтетическая живая схема (clients с колонками волны 1, settings, users, sessions) — apply дважды (второй no-op); старая схема без новых колонок — не падает

Примечания: дефолтные вопросы взять из текущего PFN Qlist (файл `.scratch/client-profiles/fixes/wf-tg-bot.json`). НЕ применять к data/factory.db в репо и на сервере (применение — в деплой-тикете 21).
