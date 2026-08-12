-- =============================================================================
--  Миграция 001: основная схема контент-завода
--  Спека 01 (БД).
--  Применяется скриптом db/migrate.sh. Идемпотентна (IF NOT EXISTS).
-- =============================================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 5000;

-- ─────────────────────── 版本管理 ───────────────────────
CREATE TABLE IF NOT EXISTS schema_version (
  version    INTEGER PRIMARY KEY,
  applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ─────────────────────── settings (ключ-значение) ───────────────────────
CREATE TABLE IF NOT EXISTS settings (
  key        TEXT PRIMARY KEY,
  value      TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ─────────────────────── users (разрешённые TG-пользователи) ───────────────────────
CREATE TABLE IF NOT EXISTS users (
  tg_user_id INTEGER PRIMARY KEY,
  username   TEXT,
  role       TEXT NOT NULL DEFAULT 'operator',  -- operator | admin
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ─────────────────────── clients (профили клиентов, спека 08) ───────────────────────
CREATE TABLE IF NOT EXISTS clients (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  name          TEXT NOT NULL,
  domain        TEXT,
  industry      TEXT,
  niche         TEXT,
  audience_json TEXT,
  tone          TEXT,
  profile_json  TEXT,
  confidence    REAL,
  status        TEXT NOT NULL DEFAULT 'draft',  -- draft | confirmed | active
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  onboarded_by  INTEGER REFERENCES users(tg_user_id)
);

CREATE TABLE IF NOT EXISTS client_socials (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  client_id  INTEGER NOT NULL REFERENCES clients(id),
  platform   TEXT NOT NULL,
  handle     TEXT,
  url        TEXT,
  found_from TEXT,               -- footer | scrapecreators | manual
  UNIQUE(client_id, platform, handle)
);

-- ─────────────────────── competitors ───────────────────────
CREATE TABLE IF NOT EXISTS competitors (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  client_id     INTEGER NOT NULL DEFAULT 1 REFERENCES clients(id),
  handle        TEXT NOT NULL,
  platform      TEXT NOT NULL,
  profile_data  TEXT,
  is_seed       INTEGER NOT NULL DEFAULT 0,
  discovered_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(handle, platform)
);

-- ─────────────────────── topics (темы дня, выход Аналитика) ───────────────────────
CREATE TABLE IF NOT EXISTS topics (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  client_id       INTEGER NOT NULL DEFAULT 1 REFERENCES clients(id),
  cycle_date      TEXT NOT NULL,
  title           TEXT NOT NULL,
  rationale       TEXT,
  source_url      TEXT,
  source_platform TEXT,
  source_metrics  TEXT,
  feasibility     TEXT,
  status          TEXT NOT NULL DEFAULT 'pending',
  chosen          INTEGER NOT NULL DEFAULT 0,
  created_at      TEXT NOT NULL DEFAULT (datetime('now')),
  approved_at     TEXT,
  approved_by     INTEGER REFERENCES users(tg_user_id)
);
CREATE INDEX IF NOT EXISTS idx_topics_cycle ON topics(cycle_date);
CREATE INDEX IF NOT EXISTS idx_topics_client ON topics(client_id);

-- ─────────────────────── scripts (сценарии, выход Сценариста) ───────────────────────
CREATE TABLE IF NOT EXISTS scripts (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  client_id     INTEGER NOT NULL DEFAULT 1 REFERENCES clients(id),
  topic_id      INTEGER NOT NULL REFERENCES topics(id),
  hook          TEXT,
  body          TEXT,
  cta           TEXT,
  target_length INTEGER NOT NULL DEFAULT 30,
  format_tag    TEXT,                   -- demo | myths | case | review (для аналитики P2)
  full_text     TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'pending',
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  approved_at   TEXT,
  approved_by   INTEGER REFERENCES users(tg_user_id)
);
CREATE INDEX IF NOT EXISTS idx_scripts_topic ON scripts(topic_id);

-- ─────────────────────── generations (задачи creatify) ───────────────────────
CREATE TABLE IF NOT EXISTS generations (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  client_id        INTEGER NOT NULL DEFAULT 1 REFERENCES clients(id),
  script_id        INTEGER NOT NULL REFERENCES scripts(id),
  creatify_id      TEXT UNIQUE,
  link_id          TEXT,
  request_payload  TEXT NOT NULL,
  status           TEXT NOT NULL DEFAULT 'pending',
  progress         REAL NOT NULL DEFAULT 0,
  video_output_url TEXT,
  local_path       TEXT,
  thumbnail_url    TEXT,
  failed_reason    TEXT,
  credits_spent    INTEGER NOT NULL DEFAULT 0,
  webhook_received INTEGER NOT NULL DEFAULT 0,
  created_at       TEXT NOT NULL DEFAULT (datetime('now')),
  completed_at     TEXT
);
CREATE INDEX IF NOT EXISTS idx_gen_status ON generations(status);
CREATE INDEX IF NOT EXISTS idx_gen_created ON generations(created_at);

-- ─────────────────────── posts (публикации postmypost) ───────────────────────
CREATE TABLE IF NOT EXISTS posts (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  client_id        INTEGER NOT NULL DEFAULT 1 REFERENCES clients(id),
  generation_id    INTEGER REFERENCES generations(id),
  cycle_date       TEXT NOT NULL,
  caption          TEXT,
  target_platforms TEXT NOT NULL,
  postmypost_id    INTEGER,
  post_at          TEXT NOT NULL,
  external_url     TEXT,                 -- публичная ссылка (для аналитики P2)
  status           TEXT NOT NULL DEFAULT 'draft',
  publish_result   TEXT,
  created_at       TEXT NOT NULL DEFAULT (datetime('now')),
  published_at     TEXT,
  approved_by      INTEGER REFERENCES users(tg_user_id)
);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);

-- ─────────────────────── social_accounts (кэш из GET /accounts) ───────────────────────
CREATE TABLE IF NOT EXISTS social_accounts (
  id                INTEGER PRIMARY KEY,   -- = postmypost account_id
  name              TEXT NOT NULL,
  platform          TEXT NOT NULL,
  login             TEXT,
  connection_status INTEGER NOT NULL DEFAULT 1,
  synced_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ─────────────────────── logs (ротация 7 дней) ───────────────────────
CREATE TABLE IF NOT EXISTS logs (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  ts        TEXT NOT NULL DEFAULT (datetime('now')),
  level     TEXT NOT NULL,
  component TEXT NOT NULL,
  event     TEXT NOT NULL,
  message   TEXT,
  payload   TEXT
);
CREATE INDEX IF NOT EXISTS idx_logs_ts ON logs(ts);

-- =============================================================================
--  СЕМЕНА (seed data)
-- =============================================================================

INSERT OR IGNORE INTO schema_version (version) VALUES (1);

INSERT OR IGNORE INTO settings (key, value) VALUES
  ('mode',                  'manual'),
  ('active_client_id',      '1'),
  ('daily_video_limit',     '3'),
  ('monthly_video_limit',   '100'),
  ('credit_floor',          '50'),
  ('cron_time',             '09:00'),
  ('client_name',           'Robotec'),
  ('client_niche',          'промышленная робототехника, интегратор KUKA'),
  ('client_tone',           'экспертно-деловой, ROI, окупаемость'),
  ('credits_remaining',     '500'),
  ('preferred_avatars',     '[]'),
  ('preferred_voices',      '[]');

-- Оператор (tg_user_id выдан заказчиком)
INSERT OR IGNORE INTO users (tg_user_id, username, role) VALUES
  (941296693, 'owner', 'admin');

-- Seed-клиент Robotec (для немедленного старта без онбординга)
INSERT OR IGNORE INTO clients (id, name, domain, industry, niche, tone, status, confidence)
VALUES (1, 'Robotec', 'robotec.ru', 'промышленная робототехника',
        'системный интегратор промышленных роботов KUKA под ключ',
        'экспертно-деловой, акцент на ROI и окупаемость 1-2 года',
        'active', 1.0);

-- Seed-конкуренты (fallback для аналитики)
INSERT OR IGNORE INTO competitors (client_id, handle, platform, is_seed) VALUES
  (1, 'KUKA Robotics',  'youtube',   1),
  (1, 'ABB Robotics',   'youtube',   1),
  (1, 'FANUC Robotics', 'youtube',   1),
  (1, '@robotec_tg',    'telegram',  1);

INSERT OR IGNORE INTO client_socials (client_id, platform, handle, url, found_from)
VALUES (1, 'telegram', '@robotec_tg', 'https://t.me/robotec_tg', 'manual');
