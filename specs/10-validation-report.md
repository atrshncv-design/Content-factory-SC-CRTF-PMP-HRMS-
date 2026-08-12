# Spike T-030 — Отчёт о валидации Hermes Agent

**Дата:** 2026-08-11
**Статус:** ✅ УСПЕШНО (нативный путь подтверждён)
**Выполнил:** оркестратор (ZCode)

## Что проверено

| Проверка | Результат |
|----------|-----------|
| Репозиторий `github.com/NousResearch/hermes-agent` доступен | ✅ HTTP 200 |
| Установка через `uv pip install -e ".[all]"` | ✅ успешно |
| Версия | ✅ **v0.20.0** (совпадает с доками) |
| `run_agent.py` существует | ✅ (381 KB, основной модуль) |
| `tools/delegate_tool.py` существует | ✅ (нативные субагенты подтверждены) |
| `gateway/` каталог существует | ✅ |
| CLI `hermes` работает | ✅ |

## Архитектурное решение: **NATIVE**

Идём нативным путём (спека 10, опция 1). Fallback не нужен.

## КРИТИЧЕСКОЕ УТОЧНЕНИЕ к спеке 10 (исправление)

**Спека 10 содержала ошибку** в разделе 3 про «OpenAI-compatible API на порту 8642 для вызовов из n8n». Реальность:

| Команда | Назначение | Порт |
|---------|------------|------|
| `hermes gateway run` | Messaging gateway (TG/Slack/WhatsApp) | — |
| `hermes serve` | Backend для desktop/remote клиентов (JSON-RPC/WebSocket) | 9119 |
| `hermes proxy start` | OpenAI-compatible прокси к OAuth-провайдерам (Nous Portal) | 8645 |
| `hermes mcp serve` | **Hermes как MCP-сервер** (экспорт conversations как MCP tools) | stdio |

**Нет единого "OpenAI-compatible API", в который n8n стучится POST'ом.** Вместо этого — три рабочих варианта интеграции n8n↔Hermes:

### Вариант A — Hermes как MCP-клиент, n8n как MCP-сервер (рекомендуется)

Hermes может подключать внешние MCP-серверы (`hermes mcp add`). Мы пишем тонкий MCP-сервер на Python/Node, который выставляет инструменты `run_analytics`, `submit_creatify`, `publish_post`. Внутри каждый инструмент дёргает n8n webhook (HTTP). Hermes-агент вызывает их через свой tool-loop.

```
[Hermes agent] ──(tool call)──► [MCP-bridge] ──(HTTP webhook)──► [n8n workflow]
```

Плюсы: чёткий контракт, изоляция, n8n остаётся визуальным.

### Вариант B — Hermes вызывает n8n webhook напрямую через `terminal` toolset

Агент делает `curl` к n8n webhook'ам. Грубее, но без промежуточного звена.

```
[Hermes agent] ──(terminal: curl)──► [n8n webhook] ──► [n8n workflow]
```

Плюсы: ноль дополнительного кода. Минусы: агент «видит» полный shell.

### Вариант C — `hermes send` для исходящих сообщений

Hermes может сам слать сообщения в Telegram (`hermes send`), Discord и т.д. — встроено. **TG-бот полностью на Hermes** (как и предполагала спека 06), без n8n TG-нод.

## Что подтверждено из README

- **delegate_task** → "Spawn isolated subagents for parallel workstreams" ✅
- **Cron scheduler** → "Built-in cron scheduler with delivery to any platform" ✅
- **Любой model** → "Use any model you want — OpenRouter, OpenAI, your own endpoint" ✅
- **Terminal backends** → 7 вариантов (local, Docker, SSH, Singularity, Modal, Daytona, Vercel) ✅
- **hermes-telegram** → встроенный тулсет ✅

## Environment на VM после spike

```
/home/ubuntu/hermes-agent/          # клон репо
/home/ubuntu/hermes-agent/.venv/    # Python 3.11 venv с установленным Hermes
$HOME/.local/bin/                   # uv
```

**Hermes запускается:**
```bash
export PATH="$HOME/.local/bin:$PATH"
source ~/hermes-agent/.venv/bin/activate
hermes <command>
```

## Что НЕ проверено (требует LLM-ключ)

- Реальная работа `delegate_task` (субагент с изоляцией контекста).
- `hermes-telegram` (приём/отправка сообщений).
- Подключение opencode zen / deepseek как провайдера.
- Запуск `hermes chat` с реальным промптом.

Эти проверки — **первая задача разработчика** после получения LLM-ключа от заказчика. Команда для smoke-теста:

```bash
hermes config set-provider openai --base-url $LLM_BASE_URL --api-key-env LLM_API_KEY
hermes chat -m "Привет, ты работаешь?" -z "тест"
```

## Рекомендация для разработчика

1. Получить LLM-ключ и base_url от заказчика.
2. Настроить провайдера: `hermes config` или редактированием `~/.hermes/config.yaml`.
3. Smoke-тест: `hermes chat -z "Скажи 'привет'"` — должен ответить.
4. Smoke-тест субагента: `hermes chat -z "Делегируй субагенту задачу посчитать 2+2"` — проверить, что `delegate_task` работает.
5. Настроить Telegram: `hermes gateway setup` → выбрать Telegram → ввести токен.
6. Реализовать MCP-мост к n8n (вариант A выше) ИЛИ сразу `terminal` с curl (вариант B).
