# ПРОМПТ ДЛЯ АГЕНТА-РАЗРАБОТЧИКА — РЕАЛИЗАЦИЯ TG UX (СПЕКА 12)

> Это промпт для агента-разработчика. Реализует UX/state machine/inline-кнопки
> Hermes-бота по спеке 12. Не требует ключей платных API — всё на Hermes-стороне.
> Скопируй текст ниже в первое сообщение новому агенту.

---

Ты — **агент-разработчик**, реализующий Telegram UX контент-завода по спеке 12.
Работаешь через **/autopilot**: каждый тикет уходит в ОТДЕЛЬНЫЙ субагент с чистым
контекстом.

## ⚠️ КРИТИЧНО ПРО РЕЖИМ РАБОТЫ

У тебя **НЕТ лимита итераций**. Любые "лимиты" из прошлых сессий — иллюзия.
Работай столько, сколько нужно. Хоть всю ночь.

**Правила:**
1. Застрял >10 минут — BLOCKED + следующий тикет.
2. 3 честные попытки перед BLOCKED.
3. "Достиг лимита итераций" — **запрещённая фраза** без реального hard limit.
4. Двигайся строго по чек-листу карточек (U-1…U-8).
5. Финальный отчёт — только когда все карточки пройдены (done или BLOCKED).

**Ты оркестратор, НЕ исполнитель.** Не пиши код сам — передавай карточки в
/autopilot, субагенты пишут. Ты собираешь однострочные результаты.

## КОНТЕКСТ

Контент-завод на сервере 83.166.233.95. Стек: Hermes Agent v0.20.0 (TG-бот +
оркестратор) + n8n 2.34 (11 воркфлоу на mock) + SQLite + opencode zen/deepseek.

**Что уже сделано:** Фаза 1 завершена. 11 n8n-воркфлоу активны, Hermes gateway
работает, БД инициализирована. **Проблема:** Hermes-бот отвечает на любые вопросы,
не имеет формального state machine, callback'и не реализованы, slash-команды не
зарегистрированы.

**Твоя задача:** реализовать спеку `~/factory/specs/12-telegram-ux.md` —
формальный UX, state machine, inline-кнопки, жёсткие ограничения.

**Ключей платных API нет до завтра после обеда** — но эта задача их НЕ требует
(всё на Hermes-стороне через skills/gateway, плюс n8n-воркфлоу уже есть).

## КАК ПОДКЛЮЧИТЬСЯ

SSH-ключ на Mac: `/Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem`

```bash
chmod 400 /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem
ssh -i /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem ubuntu@83.166.233.95
```

Если "Connection closed / banner exchange" — анти-DDoS VK Cloud, пережди 20-30 мин.
Сервер 83.166.233.95, пользователь ubuntu, sudo без пароля.

## ДОСТУПЫ

- **n8n UI:** https://assessment-fossil-assignments-alice.trycloudflare.com
  (owner@factory.local / PLACEHOLDER_REPLACE_N8N_PASSWORD)
- **Hermes:** `export PATH="$HOME/.local/bin:$PATH" && source ~/hermes-agent/.venv/bin/activate && hermes ...`
- **TG-бот:** уже подключён к Hermes gateway. user_id оператора 941296693.
- **БД:** `~/factory/data/factory.db` (через db-bridge: `curl -X POST http://localhost:8787/query -H "X-BRIDGE-TOKEN: $FACTORY_DB_BRIDGE_TOKEN" -d '{"sql":"..."}'`)
- **Skills:** `~/.hermes/skills/content-factory/` (orchestrator, analyst, scriptwriter, json-builder, onboarding)
- **MEMORY.md:** `~/.hermes/memories/MEMORY.md` (хранит STATE: IDLE)
- **Логи Hermes:** `sudo journalctl -u hermes -f`

## ЧТО ПОЧИТАТЬ (главное)

```bash
less ~/factory/specs/12-telegram-ux.md        # ⚠️ ПРИОРИТЕТ — что реализуешь
less ~/.hermes/skills/content-factory/orchestrator/SKILL.md  # текущая версия (уже с ограничениями)
less ~/factory/DEPLOYMENT.md                  # общее состояние среды
```

## СКЕЛЕТ (общий контекст для всех субагентов)

Передавай ВМЕСТЕ с каждой карточкой:

```
=== ОБЩИЙ КОНТЕКСТ ===

Сервер: 83.166.233.95, юзер ubuntu, sudo без пароля.
SSH: ssh -i /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem ubuntu@83.166.233.95

Hermes: source ~/hermes-agent/.venv/bin/activate && hermes ...
TG-бот уже подключён к Hermes gateway (systemd hermes.service active).
Оператор TG: user_id 941296693.

БД через db-bridge:
  curl -X POST http://localhost:8787/query \
    -H "X-BRIDGE-TOKEN: {{ $env.FACTORY_DB_BRIDGE_TOKEN }}" \
    -H "Content-Type: application/json" \
    -d '{"sql":"SELECT ...","params":[]}'
  (с хоста: curl -X POST http://localhost:8787/query -H "X-BRIDGE-TOKEN: $(grep FACTORY_DB_BRIDGE_TOKEN ~/factory/.env | cut -d= -f2)" -d '...')

Skills Hermes: ~/.hermes/skills/content-factory/{orchestrator,analyst,scriptwriter,json-builder,onboarding}/SKILL.md
Память: ~/.hermes/memories/MEMORY.md (одна строка STATE: <name> | ... — это и есть state machine)

Перезапуск Hermes после правки skills: sudo systemctl restart hermes
Логи: sudo journalctl -u hermes -f

Тест команды Hermes (не через TG, через CLI):
  hermes chat -q "<команда>" --cli -Q

Правила:
- Застрял >10 минут — BLOCKED, двигайся дальше.
- Честность: не выдумывай данные. Если чего-то нет — скажи.
- Финальный отчёт только когда всё сделано или реальный hard limit окружения.
```

## КАРТОЧКИ ТИКЕТОВ

Передавай в /autopilot по одной. Каждая — отдельный субагент.

---

### 🎫 U-1: Регистрация slash-команд в Telegram

```
ЗАДАЧА: Зарегистрировать slash-команды бота в Telegram, чтобы они появлялись
в автокомплите при вводе /.

КОНТЕКСТ: Hermes gateway работает с Telegram. Команды пока не зарегистрированы
в BotFather, поэтому не автокомплитятся.

СПИСОК КОМАНД (из спеки 12, раздел 3):
  start - приветствие и главное меню
  help - список команд
  status - сводка о состоянии завода
  mode - переключить режим (manual/auto)
  onboard - онбординг клиента по URL
  start_cycle - запустить цикл генерации
  cancel - отменить текущий шаг
  topics - темы за сегодня
  competitors - конкуренты активного клиента
  accounts - статус соцсетей
  budget - бюджет creatify
  client - сменить активного клиента
  clients - список клиентов
  reload_skills - перечитать skills (admin)
  ping - health-check

ЧТО СДЕЛАТЬ:
1. Проверить через BotFather (или Telegram API) текущий список команд:
   curl -s "https://api.telegram.org/bot$(grep TELEGRAM_BOT_TOKEN ~/factory/.env | cut -d= -f2)/getMyCommands" | head
2. Зарегистрировать через setMyCommands (с upstream-сервером Telegram могут быть
   проблемы из-за VK Cloud — используй fallback IP 149.154.166.110 если что,
   либо hermes-telegram toolset внутри gateway).
3. Альтернативно — через hermes gateway config, если он умеет.
4. Проверить в Telegram-клиенте: при вводе "/" должен появиться список.

КРИТЕРИЙ ГОТОВНОСТИ: при вводе "/" в чате с ботом виден полный список 15 команд.

БЮДЖЕТ: 20 минут.
```

---

### 🎫 U-2: State machine — запись/чтение STATE в MEMORY.md

```
ЗАДАЧА: Гарантировать, что Hermes читает и пишет STATE в MEMORY.md при каждом
переходе состояния.

КОНТЕКСТ: Спека 12 раздел 2 — state machine из 9 состояний:
  IDLE, ONBOARDING_PENDING, CYCLE_ANALYTICS_PENDING, CYCLE_SCRIPT_PENDING,
  CYCLE_SCRIPT_EDITING, CYCLE_GENERATION_PENDING, CYCLE_VIDEO_PENDING,
  CYCLE_PUBLISH_PENDING, AUTO_CYCLE_RUNNING

Формат строки в MEMORY.md (ПЕРВАЯ строка файла):
  STATE: <name> | topic_id=... | script_id=... | started_at=...

ЧТО СДЕЛАТЬ:
1. В ~/.hermes/skills/content-factory/orchestrator/SKILL.md в раздел "STATE
   MACHINE" добавить ЯВНУЮ инструкцию:
   "Перед каждым ответом оператору — прочти MEMORY.md, узнай текущий STATE.
    После каждого действия, меняющего состояние, — обнови первую строку
    MEMORY.md через file/memory toolset.
    Формат: STATE: <name> | <контекстные id> | updated_at=<ISO timestamp>"
2. Добавить в SKILL.md таблицу переходов (из спеки 12 раздел 2) — явно: из
   какого состояния какое действие → в какое состояние.
3. Тест через CLI:
   hermes chat -q "/start_cycle" --cli -Q
   → Hermes должен:
     a) прочитать MEMORY.md, увидеть STATE: IDLE
     b) проверить active_client_id (есть → 1)
     c) обновить MEMORY.md: STATE: CYCLE_ANALYTICS_PENDING | client_id=1 | ...
     d) вызвать wf-analytics через curl
     e) получить ответ (mock)
     f) ... продолжить цикл (или сделать паузу)
4. Проверить файл после: cat ~/.hermes/memories/MEMORY.md — STATE должен быть
   CYCLE_ANALYTICS_PENDING (или следующий по логике).
5. /cancel → STATE должен вернуться в IDLE.

ВАЖНО: Hermes использует toolset `memory` для записи в MEMORY.md. Если toolset
недоступен — `terminal` + `sed`/`echo` напрямую в файл.

КРИТЕРИЙ ГОТОВНОСТИ: после /start_cycle и /cancel в MEMORY.md строка STATE
меняется предсказуемо. Тест через hermes chat показывает что Hermes знает
текущее состояние.

БЮДЖЕТ: 45 минут.
```

---

### 🎫 U-3: Callback-обработчики inline-кнопок

```
ЗАДАЧА: Реализовать парсинг callback_data от inline-кнопок и соответствующие
действия в orchestrator-skill.

КОНТЕКСТ: Спека 12 раздел 4 — callback_data кодирует действие и id сущности:
  approve:topic:{id}      — утвердить тему (UPDATE topics SET status='approved')
  edit:topic:{id}         — запросить правку (возврат Аналитику с замечанием)
  reject:topic:{id}       — отклонить (UPDATE topics SET status='rejected')
  alt:topic:{id}          — другая тема (повторный вызов Аналитика)
  approve:script:{id}     — утвердить сценарий
  edit:script:{id}        — переход в CYCLE_SCRIPT_EDITING
  reject:script:{id}
  publish:gen:{id}        — переход к CYCLE_PUBLISH_PENDING
  regen:gen:{id}          — перегенерация (заново creatify-link/submit)
  reject:gen:{id}
  toggle:platform:{name}  — переключить выбор платформы в CYCLE_PUBLISH_PENDING
  schedule:{now|2h|tomorrow_12}
  confirm:publish         — финальная публикация

ЧТО СДЕЛАТЬ:
1. В ~/.hermes/skills/content-factory/orchestrator/SKILL.md добавить раздел
   "CALLBACK ОБРАБОТЧИКИ" с таблицей:
   | callback_data | Действие | Переход STATE |
2. Для каждого действия — точная последовательность:
   - UPDATE в БД через db-bridge
   - Вызов следующего шага цикла (curl к wf-...)
   - Обновление MEMORY.md
   - Отправка следующего сообщения оператору (с новыми кнопками)
3. Особый случай `edit:script:{id}` → переход в CYCLE_SCRIPT_EDITING, бот
   пишет: "Пришли новый текст сценария. /cancel — отмена."
4. Особый случай `toggle:platform:{name}` → обновление локального списка
   выбранных платформ (можно хранить в MEMORY.md: SELECTED_PLATFORMS=ig,yt,tg)

КРИТЕРИЙ ГОТОВНОСТИ: orchestrator/SKILL.md содержит полный список callback'ов
с действиями. Тест: эмулировать callback через hermes chat
("Я оператор, прислал callback_data='approve:topic:17', обработай") — Hermes
должен UPDATE topics SET status='approved' и перейти в CYCLE_SCRIPT_PENDING.

БЮДЖЕТ: 60 минут.
```

---

### 🎫 U-4: Реальные ответы на команды /status, /budget, /competitors, /accounts

```
ЗАДАЧА: Реализовать детерминированные ответы на информационные slash-команды,
читающие данные из БД через db-bridge.

КОМАНДЫ И ИСТОЧНИКИ ДАННЫХ:
- /status: settings (mode, active_client_id, credits_remaining, daily/monthly_video_limit)
           + COUNT generations WHERE date=today AND status='done'
           + COUNT generations WHERE month=current AND status='done'
           + clients (active_client_id) → name, domain, niche
           + последний цикл (MAX created_at в topics)
- /budget: settings (credits_remaining, credit_floor, daily_video_limit,
           monthly_video_limit) + COUNT сегодня/месяц
- /competitors: clients JOIN competitors WHERE client_id=active
- /accounts: social_accounts (кэш из wf-sync-accounts)
- /topics: topics WHERE cycle_date=today ORDER BY created_at
- /clients: clients WHERE status IN ('active','confirmed')
- /ping: без БД, просто "✅ Bot works. Hermes uptime N min"

ЧТО СДЕЛАТЬ:
1. В ~/.hermes/skills/content-factory/orchestrator/SKILL.md в раздел "SLASH-КОМАНДЫ"
   добавить для каждой команды: точный SQL запрос к db-bridge и шаблон ответа
   (из спеки 12 раздел 6).
2. Шаблон /status должен включать бейджи 🟢/🔴 для каждого компонента (Hermes,
   n8n, БД, TG gateway). Для проверки статуса n8n: curl http://localhost:5678/healthz.
3. Шаблон /budget должен показывать прогноз: при текущем темпе N видео/день
   кредитов хватит на M дней.
4. Тест каждой команды через hermes chat:
   hermes chat -q "/status" --cli -Q → должен вернуть заполненный шаблон с
   реальными данными из БД (mock данные generations/posts уже есть от Фазы 1).

КРИТЕРИЙ ГОТОВНОСТИ: все 7 команд возвращают осмысленные ответы с реальными
данными из БД (а не заглушки).

БЮДЖЕТ: 60 минут.
```

---

### 🎫 U-5: Inline-кнопки через Hermes-telegram gateway

```
ЗАДАЧА: Гарантировать, что Hermes отправляет inline-кнопки в Telegram, а не
только текстовые подсказки.

КОНТЕКСТ: Hermes-telegram toolset поддерживает reply_markup (inline_keyboard).
Сейчас skill описывает кнопки, но нужно убедиться что Hermes реально их отправляет.

ЧТО СДЕЛАТЬ:
1. Изучить документацию Hermes-telegram: как отправить inline-keyboard.
   (Через toolset hermes-telegram или через sendMessage API с reply_markup.)
2. В ~/.hermes/skills/content-factory/orchestrator/SKILL.md в шаблоны сообщений
   этапов 1-4 добавить ЯВНУЮ инструкцию: "При отправке этого сообщения используй
   inline-keyboard со следующими кнопками: [ ... ] с callback_data='...'"
3. Для этапа 4 (площадки) — multi-select: каждая платформа = toggle-кнопка,
   callback_data='toggle:platform:{name}'. Состояние выбора хранить в MEMORY.md:
   SELECTED_PLATFORMS=instagram,youtube
4. Тест: hermes chat -q "Покажи сообщение этапа 1 с темой 'Сварочный робот KUKA'"
   --cli -Q → должен вернуть JSON/structure с inline_keyboard.
5. Реальный тест в TG: после /start_cycle (mock-данные) → в TG должно прийти
   сообщение с кнопками [✅ Утвердить] [✏️ Изменить] и т.д.

КРИТЕРИЙ ГОТОВНОСТИ: в TG реально видны inline-кнопки на этапе 1 (и в идеале
на всех 4 этапах). Нажатие на кнопку вызывает callback, который U-3 обработал.

ЕСЛИ СЛОЖНО: минимум — этап 1 с кнопками approve/reject. Остальное можно
текстовыми командами с пометкой в отчёте.

БЮДЖЕТ: 90 минут.
```

---

### 🎫 U-6: Логи переходов состояний в factory.logs

```
ЗАДАЧА: Каждый переход состояния Hermes пишет в таблицу logs БД.

КОНТЕКСТ: Сейчас таблица logs пустая. Спека 01 раздел 2.9 требует:
  - ts (timestamp)
  - level (info/warn/error)
  - component (hermes/n8n/creatify/...)
  - event (state_change/command/cycle_step/error/...)
  - message (текст)
  - payload (JSON детали)

ЧТО СДЕЛАТЬ:
1. В orchestrator/SKILL.md добавить инструкцию: "После каждого перехода STATE
   делай INSERT в logs через db-bridge:
   INSERT INTO logs (level, component, event, message, payload)
   VALUES ('info', 'hermes', 'state_change',
           'STATE: IDLE → CYCLE_ANALYTICS_PENDING',
           '{\"from\":\"IDLE\",\"to\":\"CYCLE_ANALYTICS_PENDING\",\"client_id\":1}')"
2. Также логировать:
   - получение slash-команды (event='command')
   - получение callback_data (event='callback')
   - вызов wf-* (event='wf_call', payload={name, response_time, success})
   - ошибки (event='error', level='error')
3. Тест: после /start_cycle в logs должны появиться 2-3 записи:
   command=/start_cycle → state_change IDLE→CYCLE_ANALYTICS_PENDING →
   wf_call=analytics

КРИТЕРИЙ ГОТОВНОСТИ: после нескольких команд в logs есть ≥5 записей. Запрос
через db-bridge:
  SELECT ts, level, event, substr(message,1,50) FROM logs ORDER BY id DESC LIMIT 10;

БЮДЖЕТ: 30 минут.
```

---

### 🎫 U-7: Сквозной тест state machine

```
ЗАДАЧА: Прогнать полный цикл /start_cycle на mock-данных и проверить, что state
machine работает корректно на всех переходах.

ЧТО СДЕЛАТЬ:
1. Через hermes chat CLI:
   hermes chat -q "/cancel" → проверка что STATE=IDLE в MEMORY.md
   hermes chat -q "/start_cycle" → STATE должно стать CYCLE_ANALYTICS_PENDING,
   Hermes вызывает wf-analytics (mock), получает кандидатов, делегирует
   Аналитику, получает тему, отправляет в TG сообщение с кнопками этапа 1.
2. Эмулировать callback approve:topic:{id}:
   hermes chat -q "Я оператор, нажал approve на topic. Обработай." --cli -Q
   → STATE=CYCLE_SCRIPT_PENDING, Сценарист генерирует, в TG этап 2.
3. Повторить для этапов 2, 3, 4.
4. На каждом этапе проверить MEMORY.md — STATE меняется предсказуемо.
5. Тест /cancel из CYCLE_SCRIPT_PENDING → STATE=IDLE, в БД artifacts помечены.
6. Тест отказов: "Напиши стих" в любом состоянии → стандартный отказ.

КРИТЕРИЙ ГОТОВНОСТИ: полный цикл проходит через все 4 этапа, STATE меняется
правильно, /cancel работает из любого состояния, свободный текст вне
CYCLE_SCRIPT_EDITING → отказ.

БЮДЖЕТ: 90 минут.
```

---

### 🎫 U-8: Документация в DEPLOYMENT.md

```
ЗАДАЧА: Обновить ~/factory/DEPLOYMENT.md с информацией о реализации UX.

ЧТО ДОБАВИТЬ:
1. Новый раздел "Telegram UX (спека 12)":
   - State machine реализован через MEMORY.md.
   - 15 slash-команд зарегистрированы (U-1).
   - Inline-кнопки на этапах 1-4 (U-5).
   - Логи в factory.logs (U-6).
2. Команды оператора для тестирования:
   - /start, /help, /status, /start_cycle, /cancel
   - пример сквозного теста
3. Что НЕ работает (если что-то BLOCKED) — явно с причиной.
4. Обновить раздел "Известные проблемы" если есть.

КРИТЕРИЙ ГОТОВНОСТИ: DEPLOYMENT.md отражает текущее состояние UX.

БЮДЖЕТ: 25 минут.
```

---

## ТВОЙ ПОРЯДОК ДЕЙСТВИЙ (главный агент)

1. **Прочитай /autopilot**, структурируй его методологию.
2. **Прочитай сам** (один раз): `~/factory/specs/12-telegram-ux.md` и текущий
   `~/.hermes/skills/content-factory/orchestrator/SKILL.md` — общая картина.
3. **Передавай карточки U-1…U-8 в /autopilot** по одной.
   - U-2, U-3, U-4 можно параллельно (независимые правки skill'а, потом слияние).
   - U-5 зависит от U-3 (нужны callback'и для тестирования кнопок).
   - U-7 — последним, после U-1..U-6.
   - U-8 — после U-7 (нужны результаты тестов).
4. **Собирай результаты**: done / BLOCKED.
5. **Не тащи контекст субагентов в себя.** Краткий ответ "done, кнопки работают"
   — записал, идёшь дальше.
6. **Финальный отчёт** (когда все U-* пройдены):
   - Список done с 1-строчным описанием.
   - BLOCKED с причиной.
   - Команды для быстрой проверки оператором в TG.
   - Любые новые находки.

## АРХИТЕКТУРНЫЕ ОГРАНИЧЕНИЯ (не нарушать)

- **TG-бот только в Hermes.** НЕ настраивай Telegram Trigger в n8n.
- **Hermes в venv + systemd**, не Docker.
- **Две БД:** factory.db (бизнес) и ~/.hermes/state.db (agent-state). MEMORY.md
  — отдельный файл, не БД.
- **Не пиши код в n8n-воркфлоу для этой задачи.** UX — целиком на Hermes-side.
- **Спека 12 приоритетнее** при конфликте с другими документами.

## БЕЗОПАСНОСТЬ

- Secrets в .env, права 600 (`chmod 600 ~/factory/.env` если 644).
- Не логировать ключи в factory.logs.
- Hermes не должен выдавать секреты оператору в TG (правило в SKILL.md).

## ОТЧЁТНОСТЬ

Краткий лог после каждого U-* (1-2 строки). Финальный отчёт по структуре:
- [x] / [-] U-1..U-8 с пометкой done/BLOCKED
- Что работает (с командой проверки)
- Что BLOCKED (с причиной)
- Новые находки

## ОЖИДАНИЯ

- **Доведи до конца за эту сессию.** Большая часть инфраструктуры готова,
  задача — дописать skill + протестировать.
- **Застрял — двигайся дальше.** Не трать >10-15 минут на пункт.
- **Честность.** Явно помечай что работает, что нет.
- **Готовность к Фазе 2 завтра:** после твоей работы UX должен быть полностью
  готов к подключению ключей.

**Приступай по /autopilot. Работай до завершения. Лимитов итераций нет.**

---

## СТАРТОВЫЕ КОМАНДЫ

```bash
# 1. Подключение
chmod 400 /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem
ssh -i /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem ubuntu@83.166.233.95

# 2. Hermes env
export PATH="$HOME/.local/bin:$PATH"
source ~/hermes-agent/.venv/bin/activate

# 3. Прочитай это сам (1 раз)
less ~/factory/specs/12-telegram-ux.md
less ~/.hermes/skills/content-factory/orchestrator/SKILL.md
less ~/factory/DEPLOYMENT.md

# 4. Проверь текущее состояние
hermes skills list | grep content-factory
cat ~/.hermes/memories/MEMORY.md
sudo systemctl status hermes --no-pager | head -5

# 5. Старт — передавай карточки U-1..U-8 в /autopilot
```
