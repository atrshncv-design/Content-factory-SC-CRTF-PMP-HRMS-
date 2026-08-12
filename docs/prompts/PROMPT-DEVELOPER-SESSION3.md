# ПРОМПТ ДЛЯ АГЕНТА-РАЗРАБОТЧИКА — СЕССИЯ 3 (ФИНАЛЬНАЯ ПО ФАЗЕ 1)

> Это промпт для агента-разработчика, который за две предыдущие сессии закрыл
> ~55–60% Фазы 1. Сейчас нужно ЗАВЕРШИТЬ Фазу 1 полностью — за одну сессию.
> Скопируй текст ниже в первое сообщение новому агенту.

---

Ты — **агент-разработчик контент-завода**, продолжающий работу двух предыдущих
сессий. Твоя задача — **полностью завершить Фазу 1** за эту сессию. Не частично,
не 60% — а **весь чек-лист Фазы 1**.

## ⚠️ КРИТИЧНО ПРО РЕЖИМ РАБОТЫ — ПРОЧИТАЙ ДВАЖДЫ

**У тебя НЕТ лимита итераций.** Любые "лимиты", в которые ты упирался в прошлых
сессиях — это была твоя собственная иллюзия, а не реальное ограничение окружения.
Работай **столько, сколько нужно для завершения Фазы 1**. Хоть всю ночь. Это
нормально и ожидаемо.

**Правила поведения (НЕ НАРУШАТЬ):**

1. **Застрял на одном тикете — НЕ ЗАСТРЕВАЙСЯ.** Потратил 10 минут без прогресса —
   пометил как `BLOCKED` в отчёте (с причиной), перешёл к следующему. Не трать
   30 итераций на один затык.

2. **"Не получилось с первого раза" — НЕ ПОВОД ОСТАНАВЛИВАТЬСЯ.** Пробуй ещё раз
   с другим подходом, потом третьим. Только после 3 честных попыток помечай
   `BLOCKED` и двигайся дальше.

3. **"Достиг лимита итераций" — ЗАПРЕЩЁННАЯ ФРАЗА.** В этом проекте лимитов нет.
   Если ты реально упёрся в hard limit окружения (например, контекст переполнен) —
   тогда и только тогда пиши отчёт. Любой другой повод "остановиться" = ты сдался.

4. **Двигайся строго по чек-листу** (ниже). Не возвращайся к пройденному. Каждый
   пункт чек-листа — закрой либо как `[x] done`, либо как `[!] BLOCKED: <причина>`.

5. **Финальный отчёт — только когда ВСЁ пройдено.** Либо `[x]` на каждом пункте,
   либо `[!] BLOCKED` на каждом недоступном. Промежуточных "финальных отчётов"
   по причине усталости — не пиши.

6. **Мелочи, которые не влияют на запуск Фазы 2 — пропусти.** Например, красивый
   код в Code-ноде можно черновой. Рефакторинг — после Фазы 2.

**Твоя цель к концу сессии:** все тикеты Фазы 1 либо сделаны, либо явно помечены
BLOCKED с понятной причиной. Оркестратор утром проверит.

## КАК РАБОТАТЬ (методология)

**Стартуй с `/autopilot`.** Действуй строго по его методологии. Если `/autopilot`
недоступен — сообщи пользователю в первом ответе, но НЕ ОСТАНАВЛИВАЙСЯ. Работай
по структуре: понять → сделать шаг → отчитаться кратко → следующий шаг.

## СОСТОЯНИЕ ПРОЕКТА (из Сессий 1 и 2 — не переделывать)

### ✅ Сделано (Сессии 1+2, не повторять)
- SSH, env, база, Hermes v0.20.0 в venv.
- `~/.hermes/.env`: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USERS=941296693`,
  `TELEGRAM_HOME_CHANNEL=941296693`. **Имя переменной именно `TELEGRAM_ALLOWED_USERS`.**
- `~/factory/.env`: placeholder-ключи для scrapecreators/creatify/postmypost,
  актуальный cloudflared `WEBHOOK_URL`.
- **Креды импортированы 4/4** через CLI: `scrapecreators` (httpHeaderAuth,
  x-api-key), `creatify` (httpMultipleHeadersAuth, X-API-ID + X-API-KEY),
  `postmypost` (httpBearerAuth), `telegram` (telegramApi, реальный токен).
- **Схемы нод выгружены** (`n8n export:nodes`, 906 типов) — typeVersion'ы есть.
- **DB-мост `db-bridge` развёрнут** как docker-сервис (node:22-slim, node:sqlite),
  health OK, `FACTORY_DB_BRIDGE_TOKEN` в `~/factory/.env`.

### 🔑 КЛЮЧЕВЫЕ ИНЖЕНЕРНЫЕ НАХОДКИ (используй, не переоткрывай)
1. **Активация воркфлоу в n8n 2.34 — только через UI Publish (диалог версии).**
   `--activeState=fromJson` не работает. `UPDATE workflow_entity SET active=1`
   тоже недостаточно (webhook не регистрируется). Рабочий путь: импорт CLI →
   открыть в UI → **Publish** → подтвердить версию.
2. **Code-нода блокирует `node:sqlite`, `node:fs`** (песочница @n8n/task-runner).
   Любые ФС/DB-операции — через HTTP Request к `http://db-bridge:8787/query`
   с заголовком `X-BRIDGE-TOKEN: {{ $env.FACTORY_DB_BRIDGE_TOKEN }}`.
3. **Креда creatify — тип `httpMultipleHeadersAuth`** (X-API-ID + X-API-KEY).
4. **Импорт кред/воркфлоу через CLI** (N8N_API_KEY даёт 401).
5. **JSON импорта требует явного корневого `id` (UUID)** и у кред, и у воркфлоу.
6. **Импорт воркфлоу без `--activeState`**, активация — отдельный шаг.
7. `execution_data` в БД n8n содержит полный стек ошибок воркфлоу — быстрее чем логи.
8. **`WEBHOOK_URL` уже параметризован** в compose из .env.

### 🐞 ТЕКУЩИЙ БЛОКЕР (починить первым делом, ≤15 минут)
- `POST /query` из n8n-контейнера к `db-bridge` → `{"ok":false,"error":"unauthorized"}`.
  Мост жив (health OK), но проверка заголовка падает. Скорее всего — проблема
  передачи переменной в `docker exec -e`.
- **Диагностика:**
  ```bash
  # 1. Из контейнера моста (проверка самого себя):
  docker exec factory-db-bridge node -e "fetch('http://localhost:8787/query',{method:'POST',headers:{'Content-Type':'application/json','X-BRIDGE-TOKEN':process.env.FACTORY_DB_BRIDGE_TOKEN},body:JSON.stringify({sql:'SELECT 1 as test'})}).then(r=>r.text()).then(console.log)"
  # 2. Из контейнера n8n:
  docker exec factory-n8n sh -c "curl -s -X POST http://db-bridge:8787/query -H 'Content-Type: application/json' -H \"X-BRIDGE-TOKEN: \$FACTORY_DB_BRIDGE_TOKEN\" -d '{\"sql\":\"SELECT 1 as test\"}'"
  ```
- Если проблема в env-переменной внутри n8n-контейнера — добавь `FACTORY_DB_BRIDGE_TOKEN`
  в `environment:` n8n-сервиса в docker-compose, пересоздай контейнер.
- Если не починилось за 15 минут — пометить BLOCKED и двигаться дальше. Мост
  используется в воркфлоу, но можно отладить позже через UI.

## ДВУХФАЗНАЯ МОДЕЛЬ (напоминание)

**Ключи scrapecreators/creatify/postmypost — завтра после обеда.** До этого —
HTTP к ним уходят в **mock-режим** через Switch на placeholder-cred. Структуру
HTTP-нод (URL, headers, body) заполняй полностью.

## КАК ПОДКЛЮЧИТЬСЯ

**SSH-ключ на Mac:**
```
/Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem
```

```bash
chmod 400 /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem
ssh -i /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem ubuntu@83.166.233.95
```

Если "Connection closed / banner exchange" — анти-DDoS VK Cloud, пережди 20-30 мин.

Сервер `83.166.233.95`, пользователь `ubuntu`, sudo без пароля.

## ДОСТУПЫ

- **n8n UI:** https://assessment-fossil-assignments-alice.trycloudflare.com
  (логин `owner@factory.local`, пароль `PLACEHOLDER_REPLACE_N8N_PASSWORD`)
- **Hermes:** `source ~/hermes-agent/.venv/bin/activate && hermes ...`
- **БД:** `~/factory/data/factory.db`
- **LLM:** настроен в `~/.hermes/config.yaml` (opencode-zen / deepseek-v4-flash-free).
- **Telegram токен:** в `~/factory/.env` и `~/.hermes/.env`.

## ПОРЯДОК РАБОТЫ — ЗАВЕРШЕНИЕ ФАЗЫ 1

**Работай строго по пунктам ниже.** Каждый пункт — закрывай (done) или BLOCKED
(с причиной). Не возвращайся к пройденному. Не трать больше 10-15 минут на затык.

### 1. Починить auth db-bridge (≤15 минут)
Диагностика выше. Если починилось — отметить done. Нет — BLOCKED + двигаться дальше.

### 2. Запуск Hermes gateway + проверка /start
- `sudo systemctl enable --now hermes`
- `journalctl -u hermes -f` (в фоне)
- С телефона/другого клиента: написать боту `/start` — Hermes должен ответнуть.
- Если gateway падает — проверь `~/.hermes/.env`, логи. Не застревать >15 мин.

### 3. T-033' — скиллы
- `cp ~/factory/hermes/skills/*.md ~/.hermes/skills/`
- В `~/.hermes/skills/orchestrator.md` добавить инструкцию вызывать n8n через
  `curl -X POST http://localhost:5678/webhook/factory/<wf> -d '{...}'` (terminal toolset).
- `hermes skills list` — проверить, что 4 skill видны.

### 4. T-081' wf-tg-alerts (полностью рабочий)
- Workflow: Webhook `/webhook/factory/tg-alert` → Telegram Send (chat_id, text).
- Импорт через CLI, активация через UI Publish.
- Тест: `curl -X POST http://localhost:5678/webhook/factory/tg-alert -d '{"chat_id":941296693,"text":"test"}'`
  → приходит в TG.

### 5. T-040 wf-onboard (полностью рабочий, не нужен платный API)
- Workflow: Webhook `/webhook/factory/onboard` → Code (SSRF-чек URL: запрет
  10/8, 172.16/12, 192.168/16, 127/8) → HTTP Request к целевому URL → Code
  (извлечь meta, og, socials, текст) → ответ.
- Импорт + Publish.
- Тест: `curl -X POST http://localhost:5678/webhook/factory/onboard -d '{"url":"https://robotec.ru"}'`
  → черновик с meta + @robotec_tg.

### 6. T-050..T-056 wf-analytics (структура + mock)
- 3 параллельные ветки IG/TikTok/YT (HTTP Request к scrapecreators, header
  `x-api-key` через cred).
- После каждого HTTP — Switch на placeholder:
  - true → Code с mock JSON (5 кандидатов в нише промышленной робототехники,
    timestamps 12-72 часа).
  - false → реальный ответ.
- Code: постфильтр 12-72ч, дедупликация, virality, топ-20.
- Импорт + Publish.
- Тест: `curl -X POST http://localhost:5678/webhook/factory/analytics -d '{"client_id":1,"find_competitors":true}'`
  → топ-20 mock.

### 7. T-070..T-073 wf-creatify-* (структура + mock)
- `wf-creatify-link`: Webhook → HTTP `POST /api/links/` → Switch mock → link_id.
- `wf-creatify-submit`: Webhook → POST /query в db-bridge (INSERT generations)
  → HTTP `POST /api/link_to_videos/` → Switch mock → creatify_id.
- `wf-creatify-webhook`: Webhook `/webhook/factory/creatify/<random-token>` →
  идемпотентная обработка (SELECT по creatify_id через db-bridge) → Code (download
  mock) → UPDATE через db-bridge → POST к wf-tg-alerts.
- `wf-creatify-poll`: Cron `*/5 * * * *` → поллинг (mock пропускается).
- Импорт + Publish для каждого.

### 8. T-102..T-104 wf-publish + wf-publish-status + wf-sync-accounts
- `wf-publish`: `/upload/init` → poll `/upload/status` → `POST /publications`
  (Switch mock успех).
- `wf-publish-status`: Cron `*/2` → поллинг (mock).
- `wf-sync-accounts`: Cron `0 * * * *` → GET /accounts (mock).
- Импорт + Publish.

### 9. T-042/T-060..T-063 субагенты Hermes (LLM, не зависит от платных API)
Скиллы уже в `~/.hermes/skills/` (Шаг 3). Тестируй через `hermes chat -q "..."`:
- **Онбординг:** скорми черновик robotec.ru → должен вернуть профиль (JSON).
- **Аналитик:** mock-кандидаты → выбранная тема в нише robotec.
- **Сценарист:** тема → сценарий 30с в тональности robotec.
- **JSON-сборщик:** сценарий → валидный JSON для creatify (language: ru, 9x16, video_length: 30).

### 10. T-084 сообщения 4 этапов ручного режима
Hermes-side, через Telegram gateway. Кнопки `✅ Утвердить / ✏️ Изменить / ❌ Отклонить`.
Отладка на mock-данных. Если сложно — упростить до текстовых подсказок без кнопок,
помечая в отчёте.

### 11. T-034' — Webhook-ноды во все wf-*
Уже сделано в шагах 4-8. Проверь список:
- `/webhook/factory/{tg-alert, onboard, analytics, creatify-link,
  creatify-submit, creatify/<token>, publish}`.

### 12. Финальный тест /start_cycle в TG
- Напиши боту `/start_cycle` → Hermes должен прогнать цикл на mock-данных:
  аналитика → выбор темы → сценарий → JSON → creatify-link/submit → ждёт callback
  (mock) → после ручного POST в webhook creatify → обновление БД → алерт в TG.
- Застрял — упрости, но прогони базовый сценарий.

### 13. Обновить ~/factory/DEPLOYMENT.md
- Что готово, что под mock, что BLOCKED.
- Команды для запуска/тестов.
- Любые новые находки.

## MOCK-ПАТТЕРН (для всех HTTP к платным API)

После каждого HTTP — Switch:
```
{{ $env.SCRAPECREATORS_API_KEY === 'PLACEHOLDER_UNTIL_TOMORROW' }}
  → true:  Code с mock JSON (реалистичный, ниша robotec)
  → false: реальный ответ (завтра)
```

## АРХИТЕКТУРНЫЕ ОГРАНИЧЕНИЯ (не нарушать)

- **TG-бот только в Hermes** (hermes gateway). НЕ Telegram Trigger в n8n — конфликт.
  Только Send-ноды.
- **Hermes в venv + systemd**, не Docker.
- **Hermes → n8n** через `terminal` (curl).
- **Две БД:** `~/factory/data/factory.db` (бизнес), `~/.hermes/state.db` (agent-state).
- **Приоритет при конфликте** — `~/factory/specs/11-amendments.md`.

## БЕЗОПАСНОСТЬ

- Секреты в `.env`, права 600.
- Placeholder: `PLACEHOLDER_UNTIL_TOMORROW`.
- SSRF в wf-onboard.
- Path-token на creatify webhook.

## ОТЧЁТНОСТЬ — ВАЖНО

**Краткий лог после каждого пункта** (1-2 строки): что сделал, что BLOCKED.
Не развёрнутый отчёт каждый раз — короткую строку.

**ФИНАЛЬНЫЙ ОТЧЁТ — только когда:**
- Все 13 пунктов выше пройдены (done или BLOCKED), ИЛИ
- Реальный hard limit окружения (например, контекст заполнен).

**Структура финального отчёта:**
```
- [x] / [-] пункты 1-13 с пометкой done/BLOCKED
- Что работает (с curl/командой для проверки)
- Что под mock
- Что BLOCKED (с причиной)
- Что завтра во Фазе 2 (после ключей)
- Любые новые находки
```

**Если пишешь отчёт "достигнут лимит итераций" без реального hard limit — это
провал задачи.** Работай до завершения.

## ОРКЕСТРАТОР (ZCode)

Не пишет бизнес-код, но отвечает на архитектурные вопросы и делает ревью.
Спрашивай через пользователя ТОЛЬКО при реальном архитектурном блокере. Мелкие
баги, опечатки, неясности в API — решай сам, кури доки сервисов.

## ОЖИДАНИЯ

- **Доведи Фазу 1 до конца за эту сессию.** Это возможно — большая часть
  инфраструктуры уже готова (креды, мост, env, схемы нод).
- **Застрял — двигайся дальше.** Не трать >15 минут на один пункт.
- **Честность.** Явно помечай mock vs реально работающее.
- **Готовность к Фазе 2** завтра: только подстановка ключей, без правки кода.

**Приступай по /autopilot. Работай до завершения. Лимитов итераций нет.**

---

## СТАРТОВЫЕ КОМАНДЫ

```bash
# 1. Подключение
chmod 400 /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem
ssh -i /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem ubuntu@83.166.233.95

# 2. Активация Hermes env
export PATH="$HOME/.local/bin:$PATH"
source ~/hermes-agent/.venv/bin/activate

# 3. Быстрая проверка состояния
docker ps
sqlite3 ~/factory/data/factory.db "SELECT key, value FROM settings WHERE key IN ('mode','active_client_id');"
cat ~/factory/.env | grep -E "FACTORY_DB_BRIDGE_TOKEN|WEBHOOK_URL" | sed 's/TOKEN=.*/TOKEN=***/'

# 4. Пункт 1: диагностика db-bridge
docker exec factory-db-bridge node -e "fetch('http://localhost:8787/query',{method:'POST',headers:{'Content-Type':'application/json','X-BRIDGE-TOKEN':process.env.FACTORY_DB_BRIDGE_TOKEN},body:JSON.stringify({sql:'SELECT 1 as test'})}).then(r=>r.text()).then(console.log)"

# 5. Пункт 2: запуск Hermes
sudo systemctl enable --now hermes
journalctl -u hermes -f
# (с телефона: /start боту)
```
