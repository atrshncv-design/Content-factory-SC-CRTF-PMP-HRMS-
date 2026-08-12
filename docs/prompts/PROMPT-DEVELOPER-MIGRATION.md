# ПРОМПТ — МИГРАЦИЯ НА НОВУЮ АРХИТЕКТУРУ (N8N ОРКЕСТРАТОР)

> Скопируй текст ниже в первое сообщение новому агенту.

---

Ты — **агент-разработчик** контент-завода. МИГРИРУЕШЬ на новую архитектуру:
n8n становится оркестратором TG-бота, Hermes превращается в LLM-движок.
Работаешь через /autopilot.

== ⚠️ КРИТИЧНО ПРО РЕЖИМ РАБОТЫ ==

У тебя НЕТ лимита итераций. Работай до завершения.
Застрял >10 минут — BLOCKED. 3 попытки. Финальный отчёт — только когда всё пройдено.
Ты оркестратор — передавай карточки в /autopilot, субагенты делают.

== ПОЧЕМУ МИГРАЦИЯ ==

Живой тест показал: Hermes-gateway НЕ пригоден как client-facing TG-бот.
Симптомы:
- /new → бот пишет "🔒 Always approve by Alexander", "✨ Session reset!",
  "Model:", "Context: 1.0M tokens", "Lifetime tokens billed" — ТЕХНИЧЕСКИЙ МУСОР
  для клиента.
- /status → отдаёт свой служебный статус (Session ID, tokens), НЕ наш контент-заводный.
- /start_cycle, /cancel → "Unknown command" (Hermes перехватывает slash-команды).
- Hermes добавляет title сессии, approvals, confirmations — всё ломает UX.

== НОВАЯ АРХИТЕКТУРА ==

n8n = оркестратор UI/UX (Telegram Trigger + Code + Switch + Telegram Send).
Hermes = LLM-движок (только для 4 сцен: onboarding, analyst, scriptwriter,
json-builder). Вызывается через новый компонент **hermes-bridge** (HTTP-обёртка
над `hermes chat` CLI).

Полная спека: ~/factory/specs/13-n8n-orchestrator-architecture.md

== КАК ПОДКЛЮЧИТЬСЯ ==

chmod 400 /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem
ssh -i /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem ubuntu@83.166.233.95
export PATH="$HOME/.local/bin:$PATH"
source ~/hermes-agent/.venv/bin/activate

== ЧТО ПОЧИТАТЬ (в порядке приоритета) ==

less ~/factory/specs/13-n8n-orchestrator-architecture.md  # ⚠️ ГЛАВНАЯ СПЕКА
less ~/factory/specs/12-telegram-ux.md                     # UX-дизайн (команды, кнопки, state)
less ~/factory/DEPLOYMENT.md                               # текущее состояние

== КАРТОЧКИ ТИКЕТОВ (M-1..M-7) ==

🎫 M-1: Остановить Hermes-gateway

ЗАДАЧА: Остановить systemd hermes, отключить Telegram platform, чтобы освободить
бота для n8n Trigger.

ЧТО СДЕЛАТЬ:
1. sudo systemctl stop hermes
2. sudo systemctl disable hermes (юнит остаётся, но не стартует при загрузке)
3. hermes config set platforms.telegram.enabled false (если такая настройка есть)
   ИЛИ вручную в ~/.hermes/config.yaml отключить telegram
4. Удалить/закомментировать ExecStartPost=/home/ubuntu/factory/register-tg-commands.sh
   в /etc/systemd/system/hermes.service (больше не нужно)
5. sudo systemctl daemon-reload
6. Проверить: getUpdates от Telegram должен быть свободен (Hermes больше не поллит).

ВАЖНО: НЕ удалять Hermes-venv, не удалять skills, не трогать ~/.hermes/.env.
Hermes нужен как CLI — мы его будем вызывать из hermes-bridge.

КРИТЕРИЙ: systemctl is-active hermes → inactive. Telegram getUpdates свободен.
БЮДЖЕТ: 15 минут.

---

🎫 M-2: Создать компонент hermes-bridge (HTTP-обёртка над Hermes CLI)

ЗАДАЧА: Маленький HTTP-сервер (Flask/FastAPI/Node), который принимает POST /ask
и возвращает ответ от Hermes-CLI.

КОНТЕКСТ: Hermes-gateway остановлен. Hermes вызывается как CLI:
hermes chat -q "<запрос>" --cli -Q -s content-factory/<skill>

ЧТО СДЕЛАТЬ:
1. ~/factory/hermes-bridge/server.py (или .js):
   - POST /ask { skill: 'analyst'|'scriptwriter'|'json-builder'|'onboarding',
                 prompt: '...' }
   - Заголовок X-BRIDGE-TOKEN для авторизации.
   - Запускает subprocess:
     /home/ubuntu/hermes-agent/.venv/bin/hermes chat -q <prompt> --cli -Q -s content-factory/<skill>
     с env HERMES_HOME=/home/ubuntu/.hermes
   - Таймаут 300 сек.
   - Возвращает { answer: '...', stderr: '...', returncode: 0|1 }
   - GET /health → { ok: true }
2. Dockerfile ~/factory/hermes-bridge/Dockerfile:
   FROM python:3.11-slim (или node:22-slim)
   RUN pip install flask gunicorn
   COPY server.py /app/
   CMD gunicorn -w 2 -b 0.0.0.0:8642 server:app
3. Добавить сервис в ~/factory/docker-compose.yml:
   hermes-bridge:
     build: ./hermes-bridge
     ports: ["8642:8642"]  # только внутри compose-сети
     env_file: .env
     volumes:
       - /home/ubuntu/.hermes:/root/.hermes:ro  # доступ к skills
       - /home/ubuntu/hermes-agent:/hermes-agent:ro  # доступ к CLI
     restart: unless-stopped
4. Сгенерировать HERMES_BRIDGE_TOKEN в ~/factory/.env.
5. docker compose up -d hermes-bridge.
6. Тест:
   curl -X POST http://localhost:8642/ask \
     -H "X-BRIDGE-TOKEN: $(grep HERMES_BRIDGE_TOKEN ~/factory/.env | cut -d= -f2)" \
     -H "Content-Type: application/json" \
     -d '{"skill":"analyst","prompt":"тест"}'
   → должен вернуть { answer: "...", returncode: 0 }

КРИТЕРИЙ: bridge работает, отдаёт ответы Hermes. Docker ps показывает factory-hermes-bridge.
БЮДЖЕТ: 60 минут.

---

🎫 M-3: Миграция 002 — таблица sessions (state machine в БД)

ЗАДАЧА: Создать ~/factory/infra/db/002_sessions.sql с таблицей sessions.

КОНТЕКСТ: Спека 13 раздел 3.4. State machine теперь в БД, не в MEMORY.md.

СХЕМА:
CREATE TABLE sessions (
  tg_user_id   INTEGER PRIMARY KEY,
  state        TEXT NOT NULL DEFAULT 'IDLE',
  topic_id     INTEGER,
  script_id    INTEGER,
  generation_id INTEGER,
  selected_platforms TEXT,
  post_at      TEXT,
  updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
INSERT INTO sessions (tg_user_id, state) VALUES (941296693, 'IDLE');
UPDATE schema_version SET version=2;

ЧТО СДЕЛАТЬ:
1. Создать ~/factory/infra/db/002_sessions.sql (миграция).
2. Применить: FACTORY_DB_PATH=~/factory/data/factory.db MIGRATIONS_DIR=~/factory/infra/db ~/factory/infra/db/migrate.sh
3. Проверить: sqlite3 ~/factory/data/factory.db "SELECT * FROM sessions;"
4. (Опц.) Очистить ~/.hermes/memories/MEMORY.md от STATE-строки — больше не нужна.

КРИТЕРИЙ: таблица sessions создана, оператор 941296693 в состоянии IDLE.
БЮДЖЕТ: 15 минут.

---

🎫 M-4: Воркфлоу wf-tg-bot (главный приёмник TG-сообщений)

ЗАДАЧА: Создать воркфлоу wf-tg-bot в n8n, который принимает все TG-сообщения,
парсит команды, ведёт state machine.

ЛОГИКА ВОРОКФЛОУ:
Telegram Trigger (updates: messages, callback_query) →
  Code (whitelist: message.from.id == 941296693, иначе ignore) →
  Code (парсер команды: text.toLowerCase().trim() → command + args) →
  Switch по command:
    - menu/start/старт → Telegram Send (приветствие + меню)
    - help/помощь → Telegram Send (список команд из спеки 12)
    - status/статус → HTTP db-bridge SELECT → Telegram Send (шаблон)
    - cancel/стоп/отмена → HTTP db-bridge UPDATE sessions.state='IDLE' → Telegram Send
    - start_cycle → HTTP db-bridge UPDATE state='CYCLE_ANALYTICS_PENDING'
                   → HTTP wf-analytics webhook (mock) → HTTP hermes-bridge /ask (skill=analyst)
                   → HTTP db-bridge INSERT topic → Telegram Send (этап 1 с кнопками)
    - callback_query → Code (парсинг callback_data) → Switch (по action) → ...
    - default (unknown) → Telegram Send ("Не понял. /help")

ВАЖНО: список команд и шаблоны сообщений — из спеки 12-telegram-ux.md.
Inline-кнопки — через reply_markup в Telegram-ноде.

ЧТО СДЕЛАТЬ:
1. Импорт через CLI (см. DEPLOYMENT.md §5).
2. JSON с явным id (UUID).
3. В n8n UI → Publish.
4. Тест из Telegram: /start, status, cancel — должны работать.

КРИТЕРИЙ: 4 команды (start, help, status, cancel) работают в live TG без
служебного мусора Hermes.
БЮДЖЕТ: 120 минут (самый большой тикет).

---

🎫 M-5: Реализация callback'ов в wf-tg-bot (inline-кнопки)

ЗАДАЧА: Добавить обработку callback_query (нажатие inline-кнопок) в wf-tg-bot.

КОНТЕКСТ: Спека 12 раздел 4. callback_data кодирует действие и id:
  approve:topic:{id} / edit:topic:{id} / reject:topic:{id} / alt:topic:{id}
  approve:script:{id} / edit:script:{id} / reject:script:{id}
  publish:gen:{id} / regen:gen:{id} / reject:gen:{id}
  toggle:platform:{name}
  schedule:{now|2h|tomorrow_12}
  confirm:publish

ЧТО СДЕЛАТЬ:
1. В wf-tg-bot добавить ветку для callback_query (Telegram Trigger ловит их тоже).
2. Code-нода парсит callback_data → action + entity_type + entity_id.
3. Switch по action:
   - approve:topic → HTTP db-bridge UPDATE topics SET status='approved'
                  + UPDATE sessions SET state='CYCLE_SCRIPT_PENDING'
                  → HTTP hermes-bridge /ask (skill=scriptwriter, контекст: тема)
                  → HTTP db-bridge INSERT script
                  → Telegram Send (этап 2 с кнопками)
   - edit:topic → повторно hermes-bridge (analyst) → другая тема
   - approve:script → ... creatify-link + hermes-bridge (json-builder) + creatify-submit
   - publish:gen → ... wf-publish
   - toggle:platform → UPDATE sessions.selected_platforms
   - confirm:publish → финальная публикация
4. После каждого callback → answerCallbackQuery (Telegram-нода) для анимации.

КРИТЕРИЙ: нажатие кнопки ✅ Утвердить на этапе 1 → переход к этапу 2.
БЮДЖЕТ: 90 минут.

---

🎫 M-6: Воркфлоу wf-creatify-webhook — интеграция в новый UX

ЗАДАЧА: Адаптировать wf-creatify-webhook под новую архитектуру.
Сейчас он создаёт алерт через wf-tg-alerts, нужно — обновлять sessions.state
и слать этап 3 через wf-tg-bot (или новую ветку).

ЧТО СДЕЛАТЬ:
1. Открыть wf-creatify-webhook в n8n UI.
2. После UPDATE generations SET status='done' добавить:
   - HTTP db-bridge: UPDATE sessions SET state='CYCLE_VIDEO_PENDING', generation_id=...
   - HTTP POST на wf-tg-bot webhook /webhook/factory/internal/video-ready
     (или прямо в этом воркфлоу — Telegram Send этап 3 с кнопками).
3. Протестировать: вручную POST на webhook creatify → приходит сообщение этапа 3.

КРИТЕРИЙ: при готовом видео оператор видит в TG "Этап 3/4 — Видео готово" с кнопками.
БЮДЖЕТ: 45 минут.

---

🎫 M-7: Финальное тестирование + документация

ЗАДАЧА: Сквозной live-тест в TG + обновить DEPLOYMENT.md и README.md.

ЧТО СДЕЛАТЬ:
1. В TG прогнать: /start → /help → /status → /cancel → /start_cycle → approve
   на этапах 1-4 → публикация (mock).
2. Проверить: НИКАКИХ служебных сообщений от Hermes (Session ID, tokens,
   approvals) в чате быть не должно.
3. Обновить ~/factory/DEPLOYMENT.md:
   - Убрать упоминания Hermes-gateway как TG-бота.
   - Добавить раздел "Новая архитектура (спека 13)".
   - Описать компоненты: n8n (оркестратор), hermes-bridge (LLM-движок).
4. На Mac у пользователя (через scp или git pull): обновить README.md.

КРИТЕРИЙ: live TG-тест проходит чисто, без мусора. Документация актуальна.
БЮДЖЕТ: 60 минут.

== ПОРЯДОК ДЕЙСТВИЙ ==

1. Прочитай /autopilot.
2. Прочитай ~/factory/specs/13-n8n-orchestrator-architecture.md (главная).
3. Передавай карточки M-1..M-7 в /autopilot строго по порядку.
   - M-1, M-2, M-3 — независимы, можно параллельно.
   - M-4 зависит от M-1 (TG свободен), M-2 (bridge), M-3 (sessions).
   - M-5 зависит от M-4.
   - M-6 зависит от M-2, M-4.
   - M-7 — последним.
4. Финальный отчёт: M-1..M-7 done/BLOCKED + что работает в live TG.

== ОЖИДАНИЯ ==

- После M-1 Hermes-gateway остановлен.
- После M-7 оператор пишет /start в TG → видит чистое меню, без мусора.
- Bridge корректно вызывает Hermes CLI для LLM-сцен.
- Если что-то BLOCKED — явно с причиной.

Приступай по /autopilot. Лимитов итераций нет.

== СТАРТОВЫЕ КОМАНДЫ ==

chmod 400 /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem
ssh -i /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem ubuntu@83.166.233.95
export PATH="$HOME/.local/bin:$PATH"
source ~/hermes-agent/.venv/bin/activate

# Прочитай спеку 13
less ~/factory/specs/13-n8n-orchestrator-architecture.md

# Текущее состояние
docker ps
sudo systemctl is-active hermes
sqlite3 ~/factory/data/factory.db ".tables"

# Старт — M-1 (остановить Hermes)
