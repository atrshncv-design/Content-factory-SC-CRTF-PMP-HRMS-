# ПРОМПТ — АУДИТ МИГРАЦИИ НА N8N-ОРКЕСТРАТОР

> Скопируй текст ниже в первое сообщение новому агенту-аудитору.

---

Ты — **агент-аудитор** контент-завода. Разработчик мигрировал на новую архитектуру
(n8n = оркестратор TG, Hermes = LLM-движок через bridge). Твоя задача —
**независимо проверить**, что миграция M-1..M-7 реально выполнена и работает.
Работаешь через /autopilot.

== ⚠️ КРИТИЧНО ПРО РЕЖИМ РАБОТЫ ==

У тебя НЕТ лимита итераций. Аудируй до полного заключения.
Застрял >10 минут — PARTIAL/BLOCKED + следующий пункт.
Ты оркестратор — передавай карточки A-1..A-7 в /autopilot.

**Главное правило аудита: не верь на слово разработчику.** Каждый пункт
проверяй руками — через SSH, curl, sqlite3, live TG-тест. Если разработчик
сказал "работает", а реально нет — отмечай FAIL с доказательством.

== ЧТО ПРОВЕРЯЕМ ==

Спека миграции: ~/factory/specs/13-n8n-orchestrator-architecture.md
Промпт миграции (что должен был сделать разработчик): ~/factory/docs/prompts/PROMPT-DEVELOPER-MIGRATION.md
Карточки M-1..M-7: остановка Hermes-gateway, hermes-bridge, таблица sessions,
wf-tg-bot, callback'и, wf-creatify-webhook, документация.

== КАК ПОДКЛЮЧИТЬСЯ ==

chmod 400 /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem
ssh -i /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem ubuntu@83.166.233.95
export PATH="$HOME/.local/bin:$PATH"
source ~/hermes-agent/.venv/bin/activate

TG-бот: @content_zavod_obrazec_bot, оператор user_id 941296693.
n8n UI: https://assessment-fossil-assignments-alice.trycloudflare.com
  (owner@factory.local / PASSWORD_PLACEHOLDER)

== КАРТОЧКИ АУДИТА (A-1..A-7) ==

🎫 A-1: Hermes-gateway остановлен (M-1)

ПРОВЕРЬ:
1. systemctl is-active hermes → должно быть inactive.
2. systemctl is-enabled hermes → должно быть disabled.
3. cat /etc/systemd/system/hermes.service | grep ExecStartPost → register-tg-commands.sh
   должен быть закомментирован или удалён.
4. ~/.hermes/config.yaml → telegram.enabled = false (или эквивалент).
5. curl к Telegram getUpdates — должен быть свободен (Hermes не поллит).
6. sudo journalctl -u hermes --since "1 hour ago" → не должно быть новых записей
   gateway-активности.

КРИТЕРИЙ ПРОХОДА: hermes inactive + disabled + Telegram свободен.
Если hermes active → FAIL. Если Telegram всё ещё занят Hermes → FAIL.

---

🎫 A-2: hermes-bridge работает (M-2)

ПРОВЕРЬ:
1. docker ps | grep hermes-bridge → сервис Up.
2. curl http://localhost:8642/health → {"ok": true} или эквивалент.
3. Тестовый запрос:
   curl -X POST http://localhost:8642/ask \
     -H "X-BRIDGE-TOKEN: $(grep HERMES_BRIDGE_TOKEN ~/factory/.env | cut -d= -f2)" \
     -H "Content-Type: application/json" \
     -d '{"skill":"analyst","prompt":"тест — ответь одним словом OK"}'
   → должен вернуть { answer: "OK..." или осмысленный ответ, returncode: 0 }.
4. ~/factory/hermes-bridge/ — есть server.py + Dockerfile.
5. docker-compose.yml содержит сервис hermes-bridge.
6. HERMES_BRIDGE_TOKEN в ~/factory/.env (значение не пустое).
7. Без токена (curl без X-BRIDGE-TOKEN) → 401 unauthorized.

КРИТЕРИЙ: bridge отвечает, авторизация работает, Hermes CLI под капотом отдаёт
осмысленный ответ. TIMEOUT: если bridge висит >60 сек на простой запрос — PARTIAL.

---

🎫 A-3: Таблица sessions в БД (M-3)

ПРОВЕРЬ:
1. sqlite3 ~/factory/data/factory.db ".schema sessions" → структура из спеки 13.
2. sqlite3 ~/factory/data/factory.db "SELECT * FROM sessions;" → есть запись для
   941296693, state='IDLE'.
3. schema_version: SELECT * FROM schema_version → должно быть 2.
4. Миграция 002_sessions.sql существует в ~/factory/infra/db/.
5. ~/.hermes/memories/MEMORY.md — если разработчик не очистил STATE-строку,
   это ОК (не критично), но отметить.

КРИТЕРИЙ: таблица sessions есть, оператор в IDLE, schema_version=2.

---

🎫 A-4: wf-tg-bot работает — детерминированные команды (M-4)

ПРОВЕРЬ:
1. В n8n: workflows list → есть wf-tg-bot, active=true.
2. Список команд: getMyCommands через Bot API — наш список 15 команд.
3. **Live тест в TG** (или через sendMessage API от имени оператора, если
   возможно):
   - /start или start → бот отвечает приветствием + меню (БЕЗ служебного мусора
     Hermes: никаких Session ID, tokens billed, "🔒 Always approve", "✨ Session
     reset").
   - status → сводка из БД (Robotec, кредиты 500, видео сегодня 1/3, и т.д.),
     НЕ Hermes /status.
   - cancel → "Состояние сброшено в IDLE" (НЕ LLM-импровизация).
   - help → список команд из спеки 12.
4. Если TG-тест недоступен автоматически — попросить пользователя прогнать
   тест руками. Или проверить через db-bridge logs: появились ли записи с
   component='n8n', event='command' после тестовых сообщений.
5. Проверить, что бот НЕ добавляет служебных сообщений (это и было причиной
   миграции). Если лезут — FAIL.

КРИТЕРИЙ: 4 команды работают детерминированно, БЕЗ служебного мусора. Это
главный пункт миграции — если мусор остался, миграция провалилась.

---

🎫 A-5: Callback'и inline-кнопок (M-5)

ПРОВЕРЬ:
1. wf-tg-bot содержит ветку обработки callback_query.
2. В TG (после /start_cycle, если работает) — приходят inline-кнопки на этапах.
3. Нажатие ✅ Утвердить → callback_data='approve:topic:{id}' доходит до n8n
   (видно в executions), бот переходит к этапу 2.
4. В БД: sessions.state меняется с CYCLE_ANALYTICS_PENDING на CYCLE_SCRIPT_PENDING.
5. Появляется новая запись в scripts.

КРИТЕРИЙ: хотя бы один callback (approve:topic) обрабатывается корректно —
обновляется БД, приходит следующее сообщение с кнопками.
Если live-тест кнопок требует живого оператора — отметить PARTIAL.

---

🎫 A-6: wf-creatify-webhook адаптирован (M-6)

ПРОВЕРЬ:
1. wf-creatify-webhook в n8n — активен.
2. После UPDATE generations SET status='done' — есть UPDATE sessions SET
   state='CYCLE_VIDEO_PENDING'.
3. Тест: вручную POST на webhook creatify с mock-payload → приходит сообщение
   "Этап 3/4 — Видео готово" с кнопками в TG.
   curl -X POST "https://assessment-fossil-assignments-alice.trycloudflare.com/webhook/factory/creatify/<token>" \
     -H "Content-Type: application/json" \
     -d '{"id":"test-audit-001","status":"done","video_output":"https://example.com/test.mp4"}'

КРИТЕРИЙ: webhook корректно обновляет sessions и шлёт этап 3.
Если не настроен token-путь — взять актуальный из wf-creatify-webhook ноды.

---

🎫 A-7: Документация актуальна (M-7)

ПРОВЕРЬ:
1. ~/factory/DEPLOYMENT.md содержит раздел про новую архитектуру (n8n-оркестратор).
2. ~/factory/DEPLOYMENT.md НЕ содержит упоминаний Hermes-gateway как активного
   TG-бота.
3. В DEPLOYMENT.md описан компонент hermes-bridge.
4. README.md в GitHub repo актуален — описание n8n-оркестратора.
5. ~/factory/specs/13-n8n-orchestrator-architecture.md читается как источник правды.

КРИТЕРИЙ: документация соответствует реальному состоянию.

== ПОРЯДОК ДЕЙСТВИЙ ==

1. Прочитай /autopilot.
2. Прочитай ~/factory/specs/13-n8n-orchestrator-architecture.md и
   ~/factory/docs/prompts/PROMPT-DEVELOPER-MIGRATION.md.
3. Передавай карточки A-1..A-7 в /autopilot (можно параллельно независимые).
4. Финальный отчёт:
   - Таблица: A-1..A-7 → PASS / PARTIAL / FAIL с доказательством.
   - Сводка: миграция успешна / частично / провалена.
   - Что нужно доработать (список).
   - Готовность к Фазе 2.

== ОЖИДАНИЯ ==

- Аудит честный, с доказательствами (curl output, journalctl, sqlite3 SELECT).
- Если разработчик что-то НЕ сделал — явно отметить FAIL.
- Если живой TG-тест требует оператора — попросить пользователя, не выдумывать.
- Никаких "верю на слово" — проверяй руки.

Приступай по /autopilot. Лимитов итераций нет.

== СТАРТОВЫЕ КОМАНДЫ ==

chmod 400 /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem
ssh -i /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem ubuntu@83.166.233.95
export PATH="$HOME/.local/bin:$PATH"
source ~/hermes-agent/.venv/bin/activate

# Прочитай спеки
less ~/factory/specs/13-n8n-orchestrator-architecture.md
less ~/factory/docs/prompts/PROMPT-DEVELOPER-MIGRATION.md

# Состояние
docker ps
sudo systemctl is-active hermes
sqlite3 ~/factory/data/factory.db ".tables"
sqlite3 ~/factory/data/factory.db "SELECT * FROM sessions;"

# Старт аудита — A-1
