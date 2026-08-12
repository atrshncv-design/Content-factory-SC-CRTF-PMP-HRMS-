# Спека 13 — Новая архитектура: n8n как оркестратор, Hermes как LLM-движок

**Фаза:** P0 (КРИТИЧНОЕ архитектурное изменение) · **Статус:** к реализации
**Суперседит:** спеки 06 (TG-бот) и 12 (TG UX) в части «Hermes управляет TG»
**Основание:** живой тест 12.08 выявил — Hermes-gateway не пригоден как
client-facing Telegram-бот (служебные сообщения, встроенные slash-команды,
approvals ломают UX).

## 1. Принципиальное изменение

**Было** (спеки 06, 11, 12):
- Hermes-gateway принимает все TG-сообщения.
- Hermes-orchestrator-skill парсит команды, ведёт state machine, отправляет кнопки.
- n8n = «руки», вызывается Hermes через curl.

**Стало** (эта спека):
- **n8n принимает все TG-сообщения** через Telegram Trigger.
- **n8n парсит команды, ведёт state machine, отправляет кнопки** — детерминированно, без LLM.
- **Hermes = LLM-движок**, вызывается через `Execute Command` ноду ТОЛЬКО там, где нужен текстовый ответ LLM (4 сцены: онбординг, аналитик, сценарист, JSON-сборщик).
- Hermes-gateway **отключается**. systemd `hermes.service` — стоп. Telegram platform в config — отключить.

```
[TG юзер]
    │
    ▼
[n8n: Telegram Trigger] ◄─── весь UX здесь
    │
    ▼
[n8n: Code-парсер команд + State Machine в БД]
    │
    ├── /start, /help, /status, /cancel, /mode, /ping ──► детерминированный ответ
    │
    ├── /start_cycle ──► [wf-analytics HTTP] ──► [Execute Command: hermes -s analyst]
    │                                       ──► [Telegram: сообщение + кнопки этапа 1]
    │
    ├── callback approve:topic ──► [UPDATE topic] ──► [Execute Command: hermes -s scriptwriter]
    │                                                ──► [Telegram: этап 2]
    │
    ├── callback approve:script ──► [wf-creatify-link] ──► [Execute Command: hermes -s json-builder]
    │                                                  ──► [wf-creatify-submit]
    │
    ├── callback publish:gen ──► [wf-publish]
    │
    └── callback creatify готовности ──► [wf-creatify-webhook] ──► [Telegram: этап 3]
```

## 2. Почему это правильно

| Критерий | Hermes-gateway (было) | n8n (стало) |
|----------|----------------------|-------------|
| Predictable UX | ❌ служебные сообщения лезут | ✅ только то, что мы проектируем |
| State machine | ⚠️ через MEMORY.md (файл) | ✅ в таблице БД `sessions` |
| Inline-кнопки | ⚠️ reply_markup через gateway | ✅ нативная Telegram-нода |
| Slash-команды | ❌ конфликт с встроенными | ✅ наши команды = наш выбор |
| Гибкость | ⚠️ через правку промпта | ✅ визуально в n8n |
| Стабильность для клиента | ❌ low (LLM в каждом ответе) | ✅ high (детерминизм) |
| Роль LLM | везде | только 4 сцены (творчество) |

## 3. Что меняется технически

### 3.1 Telegram Trigger в n8n — РАЗРЕШЁН

Спека 11-amendments пункт «TG только в Hermes» — **отменён**. Теперь:
- n8n **Telegram Trigger** — основной приёмник сообщений.
- НО! Сначала **отключить Hermes-gateway** от Telegram, иначе два процесса будут конфликтовать за getUpdates (long polling) или webhook.

### 3.2 Hermes-gateway — ОСТАНОВИТЬ

```bash
sudo systemctl stop hermes
sudo systemctl disable hermes
# Опционально — убрать Telegram platform из config.yaml
hermes config set platforms.telegram.enabled false
```

### 3.3 Hermes остаётся как CLI

Hermes используется через `Execute Command` ноду в n8n. Каждый вызов — новый
процесс, без состояния. Команда:

```bash
hermes chat -q "<запрос>" --cli -Q -s content-factory/<skill>
```

- `-q "<запрос>"` — single query.
- `--cli -Q` — без TUI, тихий режим (только ответ).
- `-s content-factory/analyst` — preload конкретного skill.

**Важно:** путь к hermes внутри контейнера n8n. Два варианта:
- (A) Установить Hermes в контейнер n8n (через custom image или volume).
- (B) Выставить Hermes-CLI через HTTP-обёртку (быстрый сервер на Flask/FastAPI
  на хосте, listening на localhost:8642, делает subprocess `hermes chat ...` и
  возвращает ответ). n8n вызывает через HTTP Request ноду.

**Рекомендуется (B)** — чище, не требует custom-n8n image. См. раздел 4.

### 3.4 State machine — в БД

Новая таблица `sessions` в factory.db:
```sql
CREATE TABLE sessions (
  tg_user_id   INTEGER PRIMARY KEY,
  state        TEXT NOT NULL DEFAULT 'IDLE',
  -- IDLE | ONBOARDING_PENDING | CYCLE_ANALYTICS_PENDING | CYCLE_SCRIPT_PENDING
  -- | CYCLE_SCRIPT_EDITING | CYCLE_GENERATION_PENDING | CYCLE_VIDEO_PENDING
  -- | CYCLE_PUBLISH_PENDING | AUTO_CYCLE_RUNNING
  topic_id     INTEGER,
  script_id    INTEGER,
  generation_id INTEGER,
  selected_platforms TEXT,        -- JSON: ["instagram","youtube"]
  post_at      TEXT,
  updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
```

n8n читает/пишет через db-bridge. Между сообщениями оператора состояние сохраняется.

### 3.5 Команды — в Code-ноде n8n

Code-нода парсит входящее TG-сообщение:
```javascript
// Псевдокод в Code-ноде n8n
const text = $input.item.json.message.text.toLowerCase().trim();
const commands = {
  'start': 'menu', 'старт': 'menu', '/start': 'menu',
  'help': 'help', 'помощь': 'help', '/help': 'help',
  'status': 'status', 'статус': 'status',
  'cancel': 'cancel', 'стоп': 'cancel', 'отмена': 'cancel',
  'start_cycle': 'start_cycle', 'запуск цикла': 'start_cycle',
  // ... остальные из спеки 12
};
const cmd = commands[text] || commands[text.split(' ')[0] + ' ' + text.split(' ')[1]] || null;
if (cmd === 'onboard' && text.startsWith('onboard ')) {
  cmd = 'onboard';
  // extract URL
}
return { json: { command: cmd, args: extractArgs(text) } };
```

Затем Switch-нода разделяет по командам.

## 4. Hermes LLM-bridge (новый компонент)

Маленький HTTP-сервер на Flask/FastAPI на хосте (или в Docker):

```python
# ~/factory/hermes-bridge/server.py (упрощённо)
from flask import Flask, request, jsonify
import subprocess, os
app = Flask(__name__)
BRIDGE_TOKEN = os.environ['HERMES_BRIDGE_TOKEN']

@app.route('/ask', methods=['POST'])
def ask():
    auth = request.headers.get('X-BRIDGE-TOKEN')
    if auth != BRIDGE_TOKEN:
        return jsonify(error='unauthorized'), 401
    body = request.json
    skill = body['skill']  # 'analyst' | 'scriptwriter' | 'json-builder' | 'onboarding'
    prompt = body['prompt']
    result = subprocess.run(
        ['/home/ubuntu/hermes-agent/.venv/bin/hermes', 'chat',
         '-q', prompt, '--cli', '-Q', '-s', f'content-factory/{skill}'],
        capture_output=True, text=True, timeout=300, env={**os.environ, 'HERMES_HOME': '/home/ubuntu/.hermes'}
    )
    return jsonify(answer=result.stdout.strip(), stderr=result.stderr.strip(), returncode=result.returncode)
```

n8n вызывает через HTTP Request:
```
POST http://hermes-bridge:8642/ask
Headers: X-BRIDGE-TOKEN: {{ $env.HERMES_BRIDGE_TOKEN }}
Body: { "skill": "analyst", "prompt": "..." }
```

Этот сервер:
- Добавляется в `docker-compose.yml` как новый сервис `hermes-bridge`.
- Запускает Hermes CLI в subprocess для каждого запроса.
- Таймаут 300 сек (LLM может думать).
- Токен для авторизации.

## 5. План миграции (для разработчика)

### Этап 1 — Остановка Hermes-gateway
- `sudo systemctl stop hermes && sudo systemctl disable hermes`
- В config.yaml: `platforms.telegram.enabled: false`
- Удалить `register-tg-commands.sh` из systemd ExecStartPost (больше не нужно).

### Этап 2 — Новый компонент `hermes-bridge`
- Flask/FastAPI сервер, обёртка над `hermes chat`.
- Сервис в docker-compose, порт 8642 (внутренний, не публиковать).
- Токен в `.env` → `HERMES_BRIDGE_TOKEN`.
- Тест: `curl -X POST http://localhost:8642/ask -H "X-BRIDGE-TOKEN: ..." -d '{"skill":"analyst","prompt":"тест"}'`

### Этап 3 — Telegram Trigger в n8n
- Создать `wf-tg-bot` — главный воркфлоу приёма TG-сообщений.
- Telegram Trigger (_updates mode: long polling_ или _webhook_).
- Whitelist: проверка `message.from.id` в Code-ноде.
- Code-нода парсит команду.
- Switch по командам.
- Каждая команда → отдельный sub-workflow или ветка.

### Этап 4 — State machine в БД
- Миграция 002 — таблица `sessions`.
- Все операции через db-bridge.
- Перед каждым ответом — SELECT текущего state.
- После действия — UPDATE state.

### Этап 5 — Все команды и кнопки
- Реализовать `/start`, `/help`, `/status`, `/cancel`, `/mode`, `/ping` — детерминированно.
- `/onboard <url>` → wf-onboard + bridge (onboarding-skill).
- `/start_cycle` → wf-analytics + bridge (analyst-skill) + Telegram (кнопки).
- Callback approve/edit/reject → bridge + UPDATE state + следующее сообщение.
- Все inline-кнопки через Telegram-ноду `sendMessage` с `reply_markup`.

### Этап 6 — Тест live TG
- Команды `/start`, `/help`, `/status`, `/cancel` — должны работать без служебного мусора.
- «Напиши стих» — отказ.
- `/start_cycle` → цикл, кнопки, переходы состояний.

### Этап 7 — Документация
- Обновить DEPLOYMENT.md (новая архитектура).
- Обновить README.md на GitHub.
- Commit + push.

## 6. Что НЕ меняется

- Все 11 n8n-воркфлоу остаются.
- Скиллы Hermes (orchestrator, analyst, scriptwriter, json-builder, onboarding) — остаются. Теперь **вызываются через bridge**, а не внутри gateway-сессии.
- БД, db-bridge, cloudflared, mock-паттерн — без изменений.
- Спеки 00, 01, 02, 04, 05, 07, 08, 09 — без изменений.

## 7. Критерии готовности

1. `systemctl is-active hermes` → **inactive**.
2. `docker ps` содержит новый сервис `factory-hermes-bridge`.
3. Telegram-сообщение от оператора → приходит в n8n (видно в Executions), НЕ в Hermes.
4. `/status` в TG → наш шаблон из БД, без Session ID/tokens billed.
5. «Напиши стих» → канонический отказ.
6. `/start_cycle` → цикл идёт, bridge вызывает Hermes-skill для аналитика.
7. Inline-кнопки нажимаются, callback обрабатывается в n8n.
8. State machine хранится в `sessions` таблице.

## 8. Риски и облегчения

| Риск | Решение |
|------|---------|
| Long polling конфликт (если Hermes-gateway ещё активен) | Этап 1 — обязательно остановить Hermes ДО подключения TG Trigger в n8n |
| Hermes CLI медленный (subprocess startup) | Приемлемо для витринного режима; для P1 — кэш или долгоживущий процесс |
| Rate limit opencode zen (429) | Уже есть fallback (P-8); bridge просто передаст ошибку |
| Скилл orchestrator больше не нужен как active-skill | Оставить в `~/.hermes/skills/` — вызывается через `-s` флаг |

## 9. Итог для оператора

Оператор пишет команду в TG → **n8n** обрабатывает (детерминированно):
- видит ровно то, что мы спроектировали в спеке 12;
- никаких Session ID / tokens / approvals;
- LLM-творчество только на этапе выбора темы / написания сценария / сборки JSON;
- стабильность и предсказуемость.
