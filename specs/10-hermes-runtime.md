# Спека 10 — Runtime Hermes

**Фаза:** P0 · **Статус:** к реализации · **Критическая зависимость**

> ⚠️ Эта спека описывает, КАК реально работает Hermes Agent (Nous Research),
> и фиксирует архитектурное решение «Hermes-native + n8n как руки». Она частично
> **перекрывает** спеки 03 и 06 — при конфликте **эта спека приоритетнее**.

## 0. TL;DR решения

Hermes Agent — это **полноценный автономный агентский фреймворк** (не LLM, не
обёртка). У него уже есть: субагенты с изоляцией контекста, встроенная память
(SQLite + markdown), нативный Telegram-тулсет, расписание, OpenAI-compatible
API. Мы используем эту мощь, а не переписываем её.

**Распределение ролей:**
- **Hermes** — мозг: субагенты, решения, TG-бот, agent-memory.
- **n8n** — руки: HTTP-вызовы к scrapecreators/creatify/postmypost, приём
  вебхуков creatify, cron-триггеры, визуальная история исполнений.
- **Наша SQLite** (`factory.db`) — бизнес-данные (клиенты, темы, генерации,
  посты). **Не** дублирует agent-memory Hermes.

## 1. Что такое Hermes Agent (факты из документации)

- Репозиторий: `github.com/NousResearch/hermes-agent`, MIT, v0.20.0.
- Полноценный agent-loop: выбор провайдера, промпт, инструменты, повторы,
  fallback, сжатие контекста, персистентность сессий.
- **Требует внешнюю LLM** (нет встроенной модели).
- Установка: `curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash`
  (ставит `uv`, Python 3.11, Node.js). Для headless/VPS: флаг `--skip-browser`.
- Каталог данных: `~/.hermes/` (переопределяется через `HERMES_HOME`).
- **PyPI-пакета НЕТ**, публичного Docker-образа НЕТ — собираем из клона репо.

## 2. Подключение LLM (opencode zen → deepseek v4)

В `~/.hermes/config.yaml`:
```yaml
model:
  provider: openai          # любой OpenAI-compatible
  model: deepseek-v4-flash-free
  base_url: ${LLM_BASE_URL} # URL провайдера opencode zen
  api_key_env: LLM_API_KEY  # имя env-переменной с ключом
```

> `base_url` переопределяет всё — указывает на любой OpenAI-compatible endpoint.
> `${VAR}`-подстановка работает в YAML. Ключи в `~/.hermes/.env` (chmod 600).

## 3. API Hermes (для вызовов из n8n)

### OpenAI-compatible API Server — порт 8642
- Запуск: `hermes gateway` (поднимает API Server).
- Base URL: `http://localhost:8642/v1`.
- Авторизация: `Authorization: Bearer ${API_SERVER_KEY}` (env).
- Эндпоинты:
  - `POST /v1/chat/completions` — stateless, OpenAI-формат. Дефолтная модель
    `hermes-agent` (сам агент как «модель»).
  - `POST /v1/responses` — **stateful**, серверное сохранение состояния,
    чейн через `previous_response_id`. Tool-calls исполняются серверно.
  - `GET /v1/models`, `GET /health`.
  - `POST /v1/runs` + `GET /v1/runs/{run_id}` — асинхронные задачи с поллингом.
- Multi-user memory: заголовок `X-Hermes-Session-Key`.

> ⚠️ **Расхождение в доках:** страница api-server говорит про порт 8642 и
> `hermes gateway`, CLI-референс — про `hermes serve` на 9119 (это dashboard,
> не OpenAI API). **Spike (T-030) должен подтвердить**, какой командой и портом
> поднимается OpenAI-compatible API.

### Вызов из n8n
```json
// n8n HTTP-нода: POST http://hermes:8642/v1/chat/completions
Headers: { "Authorization": "Bearer ${API_SERVER_KEY}",
           "Content-Type": "application/json" }
Body: { "model": "hermes-agent",
        "messages": [{"role":"user","content":"Выбери тему из кандидатов: ..."}] }
```

## 4. Субагенты — нативная `delegate_task`

НЕ пишем свой код субагентов. Используем встроенный инструмент `delegate_task`
(тулсет `delegation`):

```yaml
# config.yaml
delegation:
  orchestrator_enabled: true
  max_spawn_depth: 2          # оркестратор → субагенты, не глубже
  max_concurrent_children: 3
```

Агент-оркестратор вызывает:
```python
# концептуально (агент делает это сам через tool-call)
delegate_task(
  goal="Из топ-20 трендов выбери 1 тему для B2B-робототехники...",
  context="Ниша: промышленные роботы KUKA. Аудитория: директора заводов...",
  role="leaf",                 # субагент не плодит детей
  max_iterations=20
)
```

**Гарантии изоляции:**
- Субагент стартует с **нулевым знанием** истории родителя.
- Знает только то, что родитель передал в `goal`/`context`.
- Родителю возвращается **только финальная сводка**.
- До 3 параллельных (через массив `tasks`).

> Это **ровно** наша спека 03 (Аналитик → Сценарист → JSON-сборщик), но без
> нашего кода. Промпты субагентов (см. спеку 03, разделы 3-5) кладутся в
> `~/.hermes/skills/` или передаются через `context` делегирования.

## 5. Telegram-бот — нативный тулсет `hermes-telegram`

**Не пишем TG-логику в n8n.** Hermes сам работает с TG через встроенный тулсет:
- Приём сообщений, команд, callback_query.
- Отправка sendMessage/sendVideo с inline-кнопками.
- Allowlist по platform user IDs (наша `TELEGRAM_ALLOWED_USER_IDS`).

```yaml
# config.yaml → platforms
platforms:
  telegram:
    enabled: true
    token_env: TELEGRAM_BOT_TOKEN
    allowed_users: [941296693]
```

> n8n TG-ноды остаются **только** для исходящих алертов от инфра-воркфлоу
> (creatify failed, credit floor) — через `wf-tg-send`. Входящие сообщения и
> интерактивный бот (команды, inline-кнопки) — целиком в Hermes.

## 6. Память — встроенная, не дублируем

Hermes хранит agent-state сам:
- `~/.hermes/state.db` (SQLite + FTS5) — сессии, lineage.
- `~/.hermes/memories/MEMORY.md` — заметки агента (~2200 символов).
- `~/.hermes/memories/USER.md` — профиль (~1375 символов).

**Наша `factory.db`** хранит только **бизнес-сущности**:
clients, topics, scripts, generations, posts, competitors, logs.

> **Правило разделения:** state цикла агента (на каком шаге, чего ждёт от
> оператора) — в Hermes memory. Бизнес-артефакты (выбранная тема, готовый
> сценарий, ID задачи creatify) — в `factory.db`. Перекрытия нет.

## 7. Как Hermes вызывает n8n («руки»)

Агент не делает HTTP-запросы к scrapecreators/creatify/postmypost напрямую —
это работа n8n (визуально, с retry, с вебхуками). Два механизма:

### Вариант A — MCP-сервер (рекомендуется для P0)
Hermes подключает n8n как MCP-сервер:
```yaml
# config.yaml → mcp_servers
mcp_servers:
  factory_n8n:
    url: "http://localhost:5678/mcp"   # если n8n отдаёт MCP
    # ИЛИ stdio-обёртка
    command: "node"
    args: ["./mcp-bridge.js"]          # тонкий мост к n8n REST API
```
Агент вызывает инструменты `run_analytics`, `submit_creatify`, `publish_post`
— а MCP-мост дёргает соответствующие n8n-воркфлоу через `POST /api/v1/workflows/{id}/execute`.

### Вариант B — `terminal` тулсет (fallback)
Агент исполняет `curl` к n8n webhook'ам:
```bash
curl -X POST http://localhost:5678/webhook/factory-analytics -d '{...}'
```
Грубее, но работает без MCP-моста. Для spike — достаточно.

## 8. docker-compose (обновлённый под Hermes)

```yaml
services:
  n8n:
    image: n8nio/n8n:latest
    ports: ["5678:5678"]
    env_file: .env
    volumes:
      - n8n-data:/home/node/.n8n
      - ./data:/var/data
      - ./media:/var/media
    restart: unless-stopped

  hermes:
    build: ./hermes          # Dockerfile из клона hermes-agent + наш config
    ports: ["8642:8642"]     # OpenAI API (только localhost в проде)
    env_file: .env
    environment:
      - HERMES_HOME=/hermes-home
      - API_SERVER_KEY=${API_SERVER_KEY}
    volumes:
      - hermes-data:/hermes-home
      - ./data:/var/data     # read-write к factory.db
      - ./media:/var/media
    restart: unless-stopped
    depends_on: [n8n]

  caddy:
    image: caddy:2
    ports: ["80:80", "443:443"]
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy-data:/data
    restart: unless-stopped
    depends_on: [n8n, hermes]

volumes: { n8n-data: {}, hermes-data: {}, caddy-data: {} }
```

> `hermes/Dockerfile` собирается из клона `github.com/NousResearch/hermes-agent`
> + копирует наш `config.yaml`, `skills/`, `mcp-bridge.js` (если вариант A).

## 9. ⚠️ Spike-валидация (КРИТИЧНО, делается первым)

Документация Hermes содержит расхождения и пробелы. **До** commits в архитектуру,
разработчик выполняет spike (T-030, 1-2 часа):

1. Клонировать `hermes-agent`, собрать Docker-образ.
2. Поднять, подключить opencode zen как LLM-провайдер.
3. Проверить: `GET /health` → 200 на порту 8642.
4. Проверить: `POST /v1/chat/completions` → осмысленный ответ.
5. Проверить: `delegate_task` действительно порождает субагента.
6. Проверить: тулсет `hermes-telegram` принимает сообщения.
7. Зафиксировать реальные порт/команду/config в `specs/10-validation-report.md`.

**Если spike провалился** (доки врут, фичи нет) — откат на **fallback-режим**:

### Fallback: Hermes как LLM-сервис (опция 2 из интервью)
- Используем ТОЛЬКО `POST /v1/chat/completions` как «умный текстовый генератор».
- ВСЯ оркестрация (субагенты как отдельные промпты, TG-бот, state) — в n8n
  по спекам 03/06 как они были до этой спеки.
- Больше ручной работы, но предсказуемо и знакомо.
- В этом случае спеки 03/06 **не правятся** (остаются в исходном виде).

> Разработчик фиксирует результат spike в `specs/10-validation-report.md` и
> решает: native (правим 03/06 по этой спеке) или fallback (03/06 как есть).

## 10. Что меняется в других спеках (после spike-native)

| Спека | Что меняется |
|-------|--------------|
| 03 | Субагенты — нативная `delegate_task`, не наш код. Промпты в skills/. Эндпоинты `/internal/*` исчезают — их заменяет MCP/terminal вызов n8n. |
| 06 | TG-бот — целиком в Hermes (тулсет hermes-telegram). n8n оставляет только `wf-tg-send` для алертов. |
| 00 | docker-compose обновляется (см. раздел 8). Порты: 8642 (Hermes API), 5678 (n8n), 80/443 (Caddy). |
| 01 | Без изменений — `factory.db` остаётся для бизнес-данных. |

## 11. Критерии готовности (native-режим)

1. Spike-отчёт `10-validation-report.md` подтверждает: Hermes стартует, API 8642
   отвечает, delegate_task работает, hermes-telegram принимает сообщения.
2. Hermes оркестратор (через промпт) прогоняет цикл: analytics → topic → script
   → JSON, порождая субагентов.
3. Бот в TG отвечает на команды (/start, /status, /onboard) через Hermes.
4. n8n-воркфлоу (analytics, creatify-submit, publish) вызываются из Hermes
   через MCP-мост или terminal.
5. `factory.db` наполняется бизнес-артефактами, agent-state в `~/.hermes/`.
6. При отказе spike — fallback-режим работает по спекам 03/06 без правок.
