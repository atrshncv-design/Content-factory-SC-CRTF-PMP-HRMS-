-- =============================================================================
--  Миграция 002: таблица sessions (state machine диалога оператора в БД)
--  Спека 13 §3.4.
--  Применяется скриптом db/migrate.sh. Идемпотентна (IF NOT EXISTS).
-- =============================================================================

-- ─────────────────────── sessions (state machine оператора) ───────────────────────
CREATE TABLE IF NOT EXISTS sessions (
  tg_user_id         INTEGER PRIMARY KEY,
  state              TEXT NOT NULL DEFAULT 'IDLE',
  topic_id           INTEGER,
  script_id          INTEGER,
  generation_id      INTEGER,
  selected_platforms TEXT,
  post_at            TEXT,
  updated_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Семя: оператор в IDLE
INSERT OR IGNORE INTO sessions (tg_user_id, state) VALUES (941296693, 'IDLE');

-- ─────────────────────── 版本管理 ───────────────────────
INSERT OR IGNORE INTO schema_version (version) VALUES (2);
