# Спека 11 — Поправки к спекам 03/06/10 после spike T-030

**Фаза:** P0 · **Статус:** СУПЕРСЕДИТ ранние спеки при конфликте
**Дата:** 2026-08-11
**Основание:** реальный smoke-тест Hermes Agent v0.20.0 на VM с opencode zen / deepseek-v4-flash-free.

> Эта спека — **список явных правок** к спекам 03 (агенты), 06 (TG-бот), 10
> (Hermes runtime). При любом конфликте — приоритет за ней. Спеки 00, 01, 02,
> 04, 05, 07, 08, 09 остаются в силе без изменений.

## Что подтверждено smoke-тестом

| Проверка | Результат |
|----------|-----------|
| `hermes chat -q "..."` с opencode zen | ✅ отвечает |
| Провайдер `opencode-zen` + env `OPENCODE_ZEN_API_KEY` | ✅ работает |
| `delegate_task` (тулсет `delegation`) | ✅ порождает субагента (`deleg_*` id) |
| `hermes gateway setup` — мастер подключения Telegram | ✅ существует |
| `hermes cronjob` — встроенный планировщик | ✅ существует |
| `hermes mcp` — Hermes как MCP-сервер/клиент | ✅ существует |
| **«OpenAI-compatible API на порту 8642 для вызовов из n8n»** | ❌ **НЕ существует** (я ошибся в спеке 10) |

---

## ПРАВКА 1 — Спека 10, раздел 3: API Hermes

### Было (неверно)
> «OpenAI-compatible API Server слушает на 8642, n8n стучится POST /v1/chat/completions»

### Стало (верно)

**Hermes НЕ экспонирует кастомный HTTP-API для оркестрации.** У него три режима работы:

| Команда | Что делает | Порт |
|---------|------------|------|
| `hermes chat -q "..."` | Один запрос к агенту, печатает ответ | — |
| `hermes chat` (интерактив) | TUI-сессия с агентом | — |
| `hermes gateway run` | Messaging gateway (Telegram/Slack/WhatsApp) — приём/отправка сообщений | — |
| `hermes serve` | JSON-RPC/WebSocket backend для desktop/remote клиентов | 9119 |
| `hermes proxy start` | OpenAI-compatible прокси к OAuth-провайдерам (не наш кейс) | 8645 |
| `hermes mcp serve` | Hermes как MCP-сервер (экспорт messaging-инструментов) | stdio |

### Реальная интеграция n8n ↔ Hermes

**Вариант A — Hermes сам оркестратор, вызывает n8n через `terminal`** (рекомендуется для P0):
- Hermes работает как долгоживущий процесс (`hermes gateway run` или `hermes chat` через TUI/скрипт).
- Когда нужно вызвать n8n-воркфлоу, агент использует toolset `terminal` → `curl http://n8n:5678/webhook/<wf>`.
- Telegram-бот целиком в Hermes (через `hermes gateway setup`).
- n8n не знает о Hermes — он просто получает HTTP-вызовы на свои webhook-ноды.

**Вариант B — Hermes подключает n8n как MCP-сервер** (чище, но +1 компонент):
- Пишем MCP-мост (Python/Node) —暴露 инструменты `run_analytics`, `submit_creatify`, `publish_post`.
- Каждый инструмент → HTTP к n8n webhook.
- `hermes mcp add factory_n8n --command node -- args/mcp-bridge.js`.
- Hermes-агент вызывает их через свой tool-loop.

**Для P0 — Вариант A** (меньше кода). Для P2/P3 — Вариант B.

### Где живёт состояние цикла

- **В памяти Hermes** (`~/.hermes/state.db` + `MEMORY.md`) — state агента, текущий шаг цикла, чего ждёт от оператора.
- **В нашей `factory.db`** — бизнес-артефакты (clients, topics, scripts, generations, posts).
- Разделение: agent-state в Hermes, business-data в factory.db.

---

## ПРАВКА 2 — Спека 03, раздел 7.1: «Эндпоинты Hermes»

### Было (неверно)
Таблица с 10 эндпоинтами: `/internal/start-cycle`, `/internal/onboard`, `/tg/handle`, `/internal/analytics-ready`, `/internal/decision`, `/internal/creatify-done`, `/internal/creatify-failed`, `/internal/publish-queued`, `/internal/performance-digest`, `GET /internal/status`.

### Стало (верно)

**Этих эндпоинтов НЕ существует.** Я их выдумал. У Hermes нет кастомных HTTP-эндпоинтов. Реальная модель:

| Точка входа в цикл | Как работает |
|--------------------|--------------|
| **Ручной запуск** | Оператор пишет в TG `/start_cycle` → Hermes (telegram-gateway) ловит → агент запускает цикл |
| **Авто-запуск** | `hermes cronjob add` — встроенный cron Hermes → в 09:00 будит агента → цикл |
| **Онбординг** | Команда `/onboard <url>` в TG → агент выполняет шаги через terminal/MCP |

### Что разработчику реализовать ВМЕСТО эндпоинтов

1. **Skill `orchestrator`** в `~/.hermes/skills/orchestrator.md` — системный промпт оркестратора.
2. **Skills субагентов** (`analyst.md`, `scriptwriter.md`, `json-builder.md`) — уже готовы в `~/factory/hermes/skills/`.
3. **MCP-мост к n8n** (вариант B) ИЛИ инструкция в skill'е оркестратора: «вызови n8n через `curl http://n8n:5678/webhook/<name>`» (вариант A).
4. **Встроенный cron** для авто-режима: `hermes cronjob add --schedule "0 9 * * *" --prompt "Запусти утренний цикл"`.

### Вызов n8n из Hermes — конкретные имена webhook'ов

n8n-воркфлоу должны иметь **Webhook-ноду** с путём:
- `wf-analytics` → `POST http://n8n:5678/webhook/factory/analytics` { client_id, niche, find_competitors }
- `wf-onboard` → `POST http://n8n:5678/webhook/factory/onboard` { url }
- `wf-creatify-link` → `POST http://n8n:5678/webhook/factory/creatify-link` { url, overrides? }
- `wf-creatify-submit` → `POST http://n8n:5678/webhook/factory/creatify-submit` { json_payload, link_id }
- `wf-publish` → `POST http://n8n:5678/webhook/factory/publish` { generation_id, platforms, post_at }

И обратные вызовы (n8n → Hermes) — **через `hermes send`** или через добавление в memory:
- n8n после генерации → `hermes send --platform telegram --message "Видео готово"` (через CLI в Execute Command ноде).
- Либо n8n пишет в `logs` таблицу → Hermes опрашивает.

**Рекомендация для P0:** n8n шлёт результат в TG напрямую через Telegram-ноду (тот же бот). Hermes в это время находится в ждущем режиме (после команды `/start_cycle`). После получения TG-сообщения от бота, Hermes продолжает цикл.

---

## ПРАВКА 3 — Спека 06: TG-бот

### Было (неверно)
> «n8n = транспорт, Hermes = логика. n8n держит Telegram Trigger, пересылает в Hermes /tg/handle, Hermes возвращает {method, params}»

### Стало (верно)

**n8n вообще не участвует в приёме TG-сообщений.** TG-бот целиком в Hermes:

1. `hermes gateway setup` → выбрать Telegram → ввести токен бота.
2. Hermes сам становится TG-клиентом: приём команд, callback_query, отправка сообщений, inline-кнопки.
3. Whitelist — через `allowed_users` в config.yaml (или через мастер setup).

### Что остаётся в n8n для TG

**Только односторонние алерты** от инфра-воркфлоу (creatify failed, postmypost error, кредиты < floor):
- n8n Workflow с Telegram-нодой (send message).
- Использует **тот же бот-токен** — это безопасно, потому что Telegram позволяет отправлять сообщения через токен без конфликта с long-polling/webhook Hermes.
- Получатель: `chat_id` оператора (941296693) или архив-канал.

> ⚠️ **Важно:** НЕ настраивать в n8n Telegram Trigger для приёма — он конфликтует с Hermes gateway. Только **Send** ноды.

### Ручной режим: 4 этапа верификации

Кнопки и сообщения рендерит **Hermes** (через gateway Telegram). Алгоритм:
1. Hermes-оркестратор завершает этап (например, выбор темы).
2. Hermes отправляет в TG сообщение с inline-кнопками через gateway.
3. Оператор жмёт кнопку → callback_query приходит в Hermes gateway → Hermes-агент продолжает цикл.
4. n8n в этом процессе не участвует вообще.

### Раньше в TICKETS были тикеты T-080/T-081 на wf-tg-incoming и wf-tg-send

- **T-080 (wf-tg-incoming)** — **УДАЛИТЬ**. Не нужен.
- **T-081 (wf-tg-send)** — **ОСТАВТЬ**, переименовать в «wf-tg-alerts»: односторонние алерты от n8n-воркфлоу.

---

## ПРАВКА 4 — Спека 00, раздел 2 (компоненты)

### Порты на VM
- 5678 — n8n (за cloudflared tunnel)
- 22 — SSH
- 80, 443 — были под Caddy, **теперь не нужны** (идём через cloudflared, сертификат не получался из-за firewall VK)
- 8642, 9119, 8645 — порты Hermes, **внутренние** (не экспонируются)

### Сервисы docker-compose (итог)
- `factory-n8n` — n8n (работа, вебхуки, HTTP-вызовы)
- `factory-cloudflared-n8n` — публичный HTTPS-доступ к n8n
- `factory-caddy` — можно **удалить** (не используется, сертификат не получался)
- Hermes — работает в venv (не Docker), как systemd-сервис или через `tmux`

### Hermes как сервис

Не собирать Docker-образ (Dockerfile в `~/factory/hermes/` устарел). Вместо этого — **systemd-юнит**:

```bash
# /etc/systemd/system/hermes.service
[Unit]
Description=Hermes Agent
After=network.target docker.service

[Service]
Type=simple
User=ubuntu
Environment="PATH=/home/ubuntu/.local/bin:/home/ubuntu/hermes-agent/.venv/bin:/usr/local/bin:/usr/bin"
WorkingDirectory=/home/ubuntu/hermes-agent
ExecStart=/home/ubuntu/hermes-agent/.venv/bin/hermes gateway run
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Запуск: `sudo systemctl enable --now hermes`.

---

## ПРАВКА 5 — Провайдер LLM в config.yaml

### Было (в `~/factory/hermes/config.yaml` — НЕВЕРНО)
```yaml
model:
  provider: openai
  base_url: ${LLM_BASE_URL}
  api_key_env: LLM_API_KEY
```

### Стало (верно, проверено smoke-тестом)
Файл `~/.hermes/config.yaml` (НЕ в `~/factory/hermes/`):
```yaml
model:
  provider: opencode-zen
  model: deepseek-v4-flash-free
```

Env в `~/.hermes/.env` (chmod 600):
```bash
OPENCODE_ZEN_API_KEY=sk-REDACTED_KEY
```

> Замечания:
> - Контекст модели урезан до 200K (free-тир opencode zen). Учитывать в `compression.threshold: 0.50`.
> - Free-модель — временная акция. Запасной вариант: `deepseek-v4-flash` (платный).
> - Не путать шлюзы: `opencode.ai/zen/v1` (free/pay-as-you-go) vs `opencode.ai/zen/go/v1` (подписка).

---

## Сводная таблица изменений для разработчика

| Документ | Что меняется |
|----------|--------------|
| `specs/03-agents.md`, раздел 7.1 | Удалить таблицу «Эндпоинты Hermes». Заменить на «Hermes запускает n8n через terminal/MCP» |
| `specs/06-telegram-bot.md` | Переписать: TG-бот целиком в Hermes (`hermes gateway setup`). n8n — только Telegram Send для алертов |
| `specs/10-hermes-runtime.md`, раздел 3 | Удалить «OpenAI API на 8642». Заменить на «Вариант A: terminal+curl; Вариант B: MCP-мост» |
| `specs/10-hermes-runtime.md`, раздел 5 (LLM) | `provider: opencode-zen`, env `OPENCODE_ZEN_API_KEY` |
| `specs/10-hermes-runtime.md`, раздел 8 (docker) | Hermes не в Docker, а в venv + systemd |
| `specs/TICKETS.md` T-030 | ✅ закрыт спайк (отчёт `10-validation-report.md`) |
| `specs/TICKETS.md` T-031 (Hermes Dockerfile) | Удалить. Заменить на T-031' «systemd-юнит Hermes» |
| `specs/TICKETS.md` T-032 (Hermes оркестратор) | Оркестратор = skill `orchestrator.md` + cronjob |
| `specs/TICKETS.md` T-033 (TG через Hermes) | `hermes gateway setup` + правка skills |
| `specs/TICKETS.md` T-035 (MCP-мост) | Опционально для P0 (можно через terminal+curl) |
| `specs/TICKETS.md` T-080 (wf-tg-incoming) | Удалить |
| `specs/TICKETS.md` T-081 (wf-tg-send) | Переименовать в wf-tg-alerts |
