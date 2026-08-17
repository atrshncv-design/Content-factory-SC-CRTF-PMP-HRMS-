# Спека: рефакторинг Telegram-бота контент-завода

## 1. Цель

Вынести UI/UX логику Telegram-бота из n8n в отдельный Python-сервис на aiogram. n8n сохраняется только как оркестратор тяжёлых job'ов (Creatify, ScrapeCreators, Post My Post). Это устраняет причину «правка 1 бага → 10 новых багов» и делает сценарии понятными, тестируемыми и версионируемыми.

## 2. Проблема текущей архитектуры

- `workflows/wf-tg-bot.json` содержит ~972 ноды.
- Каждый экран, inline-кнопка и callback — отдельные ноды.
- Состояние пользователя тащится через SQLite `sessions.state` + `quick_payload`, что требует отдельных нод на каждый шаг.
- Логика сценариев размазана по связям нод, поэтому изменение Switch cmd или Parser ломает несвязанные на первый взгляд места.
- Отладка возможна только через разворачивание `execution_data` в SQLite.
- Деплой требует direct DB edit и учёта `workflow_history[activeVersionId]`.

## 3. Архитектура целевого решения

```
┌─────────────────┐      webhook/callback      ┌────────────────────────┐
│   Telegram      │ ◄──────────────────────────► │   factory-tg-bot       │
│   (Bot API)     │                               │   Python + aiogram 3   │
└─────────────────┘                               │   FSM + SQLite         │
                                                  └──────────┬─────────────┘
                                                             │ HTTP job request
                                                             ▼
                                                  ┌────────────────────────┐
                                                  │   n8n job handlers     │
                                                  │   - generate_video     │
                                                  │   - fetch_analytics    │
                                                  │   - publish_post       │
                                                  └──────────┬─────────────┘
                                                             │ result / status
                                                             ▼
                                                  ┌────────────────────────┐
                                                  │   factory.db (SQLite)  │
                                                  │   + db-bridge          │
                                                  └────────────────────────┘
```

### Разделение ответственности

| Что делает бот | Что делает n8n |
|---|---|
| Меню, inline-кнопки, карусели, FSM | Генерация видео через Creatify |
| Валидация ввода пользователя | Сбор аналитики через ScrapeCreators |
| Запуск job'ов и показ прогресса | Автопостинг через Post My Post |
| Хранение состояния сессии в SQLite | Конвертация URL → скрипт / шортс |
| Показ результатов пользователю | — |

## 4. Сценарии (MVP — первый этап)

### Обязательные к переносу

1. `/start`, главное меню, статус
2. URL → видео (ручной режим)
3. AI Shorts
4. Видео с аватаром + карусель
5. Работа с аватарами (загрузка, список моих аватаров)
6. Профили / клиенты
7. Сбор аналитики из ScrapeCreators
8. Автопостинг в Post My Post
9. Режим авто: парсинг → выбор темы → сценарий → генерация → автопостинг
10. Режим ручной: каждый шаг с верификацией пользователя

### Сценарии фиксируются в коде явно

Каждый сценарий — отдельный Python-модуль с FSM (Finite State Machine):

```
bot/scenarios/
  start.py
  menu.py
  url2video.py
  shorts.py
  avatar_video.py
  avatars.py
  profiles.py
  analytics.py
  autopost.py
  auto_mode.py
  manual_mode.py
```

## 5. Интерфейс между ботом и n8n

Бот вызывает n8n workflow через webhook с `respondMode: responseNode`. n8n отвечает синхронно, если операция быстрая, или ставит job в очередь и сообщает `job_id`.

### Job-запрос

```json
{
  "job": "generate_avatar_video",
  "user_id": 941296693,
  "client_id": "robotec",
  "payload": {
    "avatar_id": "uuid",
    "topic": "текст темы",
    "duration": 30
  }
}
```

### Job-ответ (синхронный)

```json
{
  "ok": true,
  "video_url": "https://...",
  "credits_spent": 5
}
```

### Job-ответ (асинхронный)

```json
{
  "ok": true,
  "job_id": "abc-123",
  "status": "queued"
}
```

Бот сохраняет `job_id` и ожидает callback от n8n (или опрашивает status endpoint).

## 6. База данных

Оставляем SQLite `factory.db` + db-bridge. Бот пишет состояние в таблицу `sessions` через тот же db-bridge или напрямую (read-only аналитика, read-write состояние).

Таблица сессий расширяется полями FSM:

```sql
ALTER TABLE sessions ADD COLUMN fsm_state TEXT;
ALTER TABLE sessions ADD COLUMN fsm_data TEXT;  -- JSON
```

## 7. Технический стек

- **Python 3.11+**
- **aiogram 3.x** — Telegram Bot API, FSM, inline-кнопки, webhooks
- **FastAPI / aiohttp** — webhook endpoint для Telegram и callback'ов от n8n
- **SQLite + aiosqlite** — состояние и данные
- **Pydantic** — валидация payload'ов
- **pytest + pytest-asyncio** — тесты
- **Docker** — `factory-tg-bot` сервис рядом с `factory-n8n`

## 8. Критерии приёмки

- [ ] Все сценарии из раздела 4 работают без n8n-нод UI.
- [ ] n8n workflow для job'ов содержат не более 20 нод каждый.
- [ ] Любая правка сценария не затрагивает другие сценарии (pytest + code review).
- [ ] Деплой происходит через `git pull` + `docker compose up -d`, без direct DB edit.
- [ ] В GitHub создана отдельная рабочая ветка с новой версией.
- [ ] Есть тесты на core-логику (FSM переходы, callback routing).

## 9. Out of scope

- Переход с SQLite на Postgres.
- Смена сервера `factory`.
- Редизайн интерфейса Telegram (тексты и кнопки остаются текущими, если не согласовано иное).
- Интеграции, которых нет в текущем n8n (например, новые соцсети).

## 10. Риски

- **Параллельная работа**: пока идёт переезд, старый wf-tg-bot должен оставаться работоспособным.
- **Job-интерфейс**: нужно чётко зафиксировать контракт между ботом и n8n, иначе будут те же проблемы, что сейчас.
- **Секреты**: Telegram Bot Token, API-ключи остаются в `.env`, бот читает их через переменные окружения.
