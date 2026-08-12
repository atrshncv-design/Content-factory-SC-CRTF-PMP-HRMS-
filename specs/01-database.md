# Спека 01 — БД и модель данных (SQLite)

**Фаза:** P0 · **Статус:** к реализации

## 1. Почему SQLite

- Нулевая нагрузка на RAM (файл на SSD, in-process).
- Достаточно для витринного варианта (1 клиент, низкий трафик).
- Нет отдельного сервера БД — проще деплой и бэкап (один файл).
- WAL-mode решает проблему блокировок при конкурентных записях из n8n/Hermes.

**Путь к файлу:** `FACTORY_DB_PATH=/var/data/factory.db`
**Бэкап:** ежедневное копирование файла в `/var/backups/factory-YYYYMMDD.db`
(cron в n8n, хранение 7 копий).

## 2. Схема (таблицы)

### 2.1 `settings` — ключ-значение, глобальные настройки завода

```sql
CREATE TABLE settings (
  key          TEXT PRIMARY KEY,
  value        TEXT NOT NULL,
  updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
```

Семена (seed):
- `client_name` = `Robotec`
- `client_niche` = `промышленная робототехника, интегратор KUKA`
- `client_tone` = `экспертно-деловой, ROI, окупаемость`
- `mode` = `manual` (manual | auto)
- `daily_video_limit` = `3`
- `monthly_video_limit` = `100`
- `credit_floor` = `50`
- `cron_time` = `09:00`

### 2.2 `users` — разрешённые Telegram-пользователи

```sql
CREATE TABLE users (
  tg_user_id   INTEGER PRIMARY KEY,
  username     TEXT,
  role         TEXT NOT NULL DEFAULT 'operator',  -- operator | admin
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 2.3 `competitors` — отслеживаемые конкуренты (найдены или ручные)

```sql
CREATE TABLE competitors (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  handle       TEXT NOT NULL,          -- @handle или URL
  platform     TEXT NOT NULL,          -- instagram | tiktok | youtube | ...
  profile_data TEXT,                   -- JSON: follower_count, bio, ...
  is_seed      INTEGER NOT NULL DEFAULT 0,  -- 1 = ручной seed, 0 = найден заводом
  discovered_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(handle, platform)
);
```

**Seed для robotec** (фолбэк, если автопоиск не сработает):
- KUKA Russia, ABB Robotics, FANUC — профили в IG/YT.
- Полный список — в спеке 02, раздел «поиск конкурентов».

### 2.4 `topics` — темы дня (выход аналитика)

```sql
CREATE TABLE topics (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  cycle_date    TEXT NOT NULL,          -- YYYY-MM-DD (день цикла)
  title         TEXT NOT NULL,
  rationale     TEXT,                   -- почему выбрали (тренд/метрики/ниша)
  source_url    TEXT,                   -- URL трендового ролика-источника
  source_platform TEXT,                 -- instagram | tiktok | youtube
  source_metrics TEXT,                  -- JSON: views, likes, shares, age_hours
  feasibility   TEXT,                   -- оценка: можно ли сделать через creatify
  status        TEXT NOT NULL DEFAULT 'pending',
                -- pending | approved | rejected | superseded
  chosen        INTEGER NOT NULL DEFAULT 0,  -- 1 = выбран как тема дня
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  approved_at   TEXT,
  approved_by   INTEGER REFERENCES users(tg_user_id)
);
CREATE INDEX idx_topics_cycle ON topics(cycle_date);
```

### 2.5 `scripts` — сценарии (выход сценариста)

```sql
CREATE TABLE scripts (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  topic_id      INTEGER NOT NULL REFERENCES topics(id),
  hook          TEXT,                   -- цепляющее начало (3 сек)
  body          TEXT,                   -- основной текст сценария
  cta           TEXT,                   -- призыв к действию
  target_length INTEGER NOT NULL DEFAULT 30,  -- 15 | 30 | 45 | 60 (сек)
  full_text     TEXT NOT NULL,          -- полный текст для озвучки
  status        TEXT NOT NULL DEFAULT 'pending',
                -- pending | approved | rejected
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  approved_at   TEXT,
  approved_by   INTEGER REFERENCES users(tg_user_id)
);
CREATE INDEX idx_scripts_topic ON scripts(topic_id);
```

### 2.6 `generations` — задачи генерации в creatify

```sql
CREATE TABLE generations (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  script_id       INTEGER NOT NULL REFERENCES scripts(id),
  creatify_id     TEXT UNIQUE,          -- UUID задачи creatify (для вебхука/поллинга)
  link_id         TEXT,                 -- UUID link в creatify (POST /api/links/)
  request_payload TEXT NOT NULL,        -- JSON: отправленный в link_to_videos
  status          TEXT NOT NULL DEFAULT 'pending',
                  -- pending | running | done | failed | rejected
  progress        REAL NOT NULL DEFAULT 0,   -- 0..1
  video_output_url TEXT,                -- URL MP4 от creatify (временный!)
  local_path      TEXT,                 -- /var/media/<id>.mp4 (скачанный)
  thumbnail_url   TEXT,
  failed_reason   TEXT,
  credits_spent   INTEGER NOT NULL DEFAULT 0,
  webhook_received INTEGER NOT NULL DEFAULT 0,  -- 1 = callback пришёл
  created_at      TEXT NOT NULL DEFAULT (datetime('now')),
  completed_at    TEXT
);
CREATE INDEX idx_gen_status ON generations(status);
CREATE INDEX idx_gen_created ON generations(created_at);
```

> **Контроль бюджета:** `COUNT(*) WHERE status='done' AND created_at >= начало месяца`
> ≤ `monthly_video_limit`. `COUNT(*) WHERE date=сегодня` ≤ `daily_video_limit`.

### 2.7 `posts` — публикации в соцсети (postmypost)

```sql
CREATE TABLE posts (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  generation_id    INTEGER REFERENCES generations(id),  -- NULL для текстовых постов
  cycle_date       TEXT NOT NULL,
  caption          TEXT,                 -- подпись к посту
  target_platforms TEXT NOT NULL,        -- JSON: ["instagram","youtube","tiktok",...]
  postmypost_id    INTEGER,              -- ID публикации в postmypost
  post_at          TEXT NOT NULL,        -- запланированное время ISO 8601
  status           TEXT NOT NULL DEFAULT 'draft',
                   -- draft | pending_publication | publishing | published | error
  publish_result   TEXT,                 -- JSON результата/ошибки
  created_at       TEXT NOT NULL DEFAULT (datetime('now')),
  published_at     TEXT,
  approved_by      INTEGER REFERENCES users(tg_user_id)
);
CREATE INDEX idx_posts_status ON posts(status);
```

### 2.8 `social_accounts` — кэш подключённых аккаунтов (из GET /accounts)

```sql
CREATE TABLE social_accounts (
  id               INTEGER PRIMARY KEY,   -- = postmypost account_id
  name             TEXT NOT NULL,
  platform         TEXT NOT NULL,         -- instagram | youtube | ...
  login            TEXT,
  connection_status INTEGER NOT NULL DEFAULT 1,  -- 1 ok | 2 auth_required
  synced_at        TEXT NOT NULL DEFAULT (datetime('now'))
);
```

> Обновляется раз в час n8n-воркфлоу `sync-accounts` (вызов `GET /accounts`).
> При `connection_status=2` — алерт в TG («нужно перелогиниться в кабинете postmypost»).

### 2.9 `logs` — журнал событий (ротация 7 дней)

```sql
CREATE TABLE logs (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  ts         TEXT NOT NULL DEFAULT (datetime('now')),
  level      TEXT NOT NULL,           -- info | warn | error
  component  TEXT NOT NULL,           -- n8n | hermes | creatify | scrapecreators | postmypost
  event      TEXT NOT NULL,           -- short event name
  message    TEXT,
  payload    TEXT                     -- JSON детали
);
CREATE INDEX idx_logs_ts ON logs(ts);
```

**Ротация:** `DELETE FROM logs WHERE ts < datetime('now', '-7 days');` — cron 03:00.

## 3. Прагматы и миграции

```sql
PRAGMA journal_mode = WAL;       -- конкурентные чтения/запись
PRAGMA foreign_keys = ON;        -- проверка ссылок
PRAGMA synchronous = NORMAL;     -- баланс скорости/надёжности (WAL это позволяет)
PRAGMA busy_timeout = 5000;      -- ждать 5 сек при блокировке
```

**Миграции:** папка `db/migrations/` с пронумерованными файлами
`001_init.sql`, `002_*.sql`. Применяются при старте контейнера Hermes (скрипт
`migrate.sh` пробегает по файлам, если версия в `schema_version` ниже).

```sql
CREATE TABLE schema_version (
  version    INTEGER PRIMARY KEY,
  applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

## 4. Доступ к БД

- **Из n8n:** нода `SQLite` (community node `n8n-nodes-base` имеет встроенную).
  Configure: `Database File = /var/data/factory.db`.
- **Из Hermes:** простая обёртка (подробнее в спеке 03) — read/write через
  thin-layer (REST от Hermes к n8n, либо прямое подключение sqlite3 в рантайме
  Hermes, т.к. они на одном хосте).
- **Принцип:** writes делает та сторона, которая «владеет» артефактом:
  - n8n пишет `generations.status` после вебхука (он принял вебхук).
  - Hermes пишет `topics/scripts` (он их генерит).
  - Чтобы избежать гонок — каждая таблица имеет чёткого «писца».

## 5. Размер и производительность

При витринной нагрузке (≤3 видео/день) объём БД — десятки KB/день. Индексы
покрывают все запросы по статусам и датам. `VACUUM` еженедельно. Никаких
особых мер по производительности не требуется.
