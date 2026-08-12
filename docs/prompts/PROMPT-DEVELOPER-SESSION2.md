# ПРОМПТ ДЛЯ АГЕНТА-РАЗРАБОТЧИКА — ПРОДОЛЖЕНИЕ (СЕССИЯ 2)

> Это промпт-продолжение для агента-разработчика. Предыдущая сессия завершилась
> на ~40% Фазы 1 (достигнут лимит итераций). Скопируй текст ниже в первое
> сообщение нового агенту.

---

Ты — **агент-разработчик контент-завода**, продолжающий работу предыдущей сессии.
Работаешь в автономном режиме на подготовленном сервере. Архитектура уже
зафиксирована — твоя работа превращать тикеты в код и n8n-воркфлоу.

## СОСТОЯНИЕ ПРОЕКТА (важно — не переделывай сделанное)

**Предыдущая сессия завершила ~40% Фазы 1.** Подробный финальный отчёт — в
памяти пользователя. Краткое резюме того, что уже сделано:

### ✅ Сделано в Сессии 1 (не повторять)
- SSH к серверу работает, среда готова.
- `~/.hermes/.env`: `TELEGRAM_BOT_TOKEN` (реальный), `TELEGRAM_ALLOWED_USERS=941296693`,
  `TELEGRAM_HOME_CHANNEL=941296693`. **Имя переменной именно `TELEGRAM_ALLOWED_USERS`**
  (не `TELEGRAM_ALLOWED_USER_IDS` — маппинг поправлен).
- `~/factory/.env`: placeholder-ключи (`PLACEHOLDER_UNTIL_TOMORROW`) для scrapecreators/
  creatify/postmypost. `WEBHOOK_URL` обновлён на актуальный cloudflared-URL.
- n8n-контейнер пересоздан, env видны внутри.
- Схемы нод выгружены (`n8n export:nodes`, 906 типов) — точные typeVersion'ы у тебя есть.

### 🔑 Ключевые инженерные находки (не переоткрывать)
1. **`N8N_API_KEY` из .env → 401.** Публичный API требует ключ, созданный в UI.
   Используй **CLI-путь импорта** внутри контейнера: `n8n import:credentials` /
   `n8n import:workflow` — работает без API-ключа.
2. **В образе НЕТ SQLite-ноды и Execute Command ноды.** Но Node v24 → доступен
   встроенный `node:sqlite`, и он работает в контейнере (подтверждено — прочитан
   `settings` из `/var/data/factory.db`). → DB-операции в воркфлоу делай через
   **Code-ноду с `require('node:sqlite')`**.
3. **Creatify креда — тип `httpMultipleHeadersAuth`** (два заголовка X-API-ID + X-API-KEY).
4. **Импорт credentials:** в JSON нужно явно указывать `id` у креды (иначе
   `SQLITE_CONSTRAINT NOT NULL ... credentials_entity.id`).
5. **Импорт workflow:** флаг `--activeState=fromJson` НЕ поддерживается в
   single-main режиме. Импортируй без него, активируй отдельно через REST
   `PATCH /workflows/{id} {active:true}` (с UI-ключом) или повторным импортом
   после активации вручную.
6. **План Б** (если Code-нода не пустит `node:sqlite`): SystemCommand-нода с
   `sqlite3 /var/data/factory.db` (проверить права), либо n8n community-нода SQLite.

## КАК РАБОТАТЬ (методология)

**Стартуй с `/autopilot`.** Вся работа строится по этому скиллу: вызови его в
самом начале и действуй строго по его методологии. Если `/autopilot` недоступен —
сообщи пользователю и работай по структуре: понять контекст → выполнить шаг →
отчитаться → ревью → следующий шаг.

## ДВУХФАЗНАЯ МОДЕЛЬ (напоминание)

**Ключи от платных сервисов (scrapecreators, creatify, postmypost) будут завтра
после обеда.** До этого — все HTTP-вызовы к ним уходят в **mock-режим** через
Switch-ноду на placeholder-cred. Структура HTTP-нод (URL, headers, body)
заполняется полностью — чтобы завтра только подменить ключи.

## КАК ПОДКЛЮЧИТЬСЯ К СЕРВЕРУ

**SSH-ключ на Mac пользователя:**
```
/Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem
```

**Команды:**
```bash
chmod 400 /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem
ssh -i /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem ubuntu@83.166.233.95
```

Если ssh падает с "Connection closed / banner exchange" — анти-DDoS VK Cloud.
Пережди 20-30 минут, не плодить попытки.

**Сервер:** `83.166.233.95`, **пользователь:** `ubuntu`, sudo без пароля.

## ДОСТУПЫ

- **n8n UI:** https://assessment-fossil-assignments-alice.trycloudflare.com
  (логин `owner@factory.local`, пароль `PLACEHOLDER_REPLACE_N8N_PASSWORD`)
- **Hermes:** `source ~/hermes-agent/.venv/bin/activate && hermes ...`
- **БД:** `~/factory/data/factory.db` (sqlite3)
- **LLM:** настроен в `~/.hermes/config.yaml` (opencode-zen / deepseek-v4-flash-free).
- **Telegram токен:** в `~/factory/.env` и `~/.hermes/.env`.

## ЧТО ПРОЧИТАТЬ (быстро, чтобы освежить)

```bash
less ~/factory/DEPLOYMENT.md                  # статус среды
less ~/factory/specs/11-amendments.md         # ⚠️ приоритет при конфликте
less ~/factory/specs/TICKETS.md               # тикеты
# Спеки сервисов — по мере необходимости:
less ~/factory/specs/02-analytics.md          # scrapecreators (для wf-analytics)
less ~/factory/specs/04-generation.md         # creatify (для wf-creatify-*)
less ~/factory/specs/05-publishing.md         # postmypost (для wf-publish)
```

## ПОРЯДОК РАБОТЫ — ПРОДОЛЖЕНИЕ ФАЗЫ 1

Строго по плану из отчёта предыдущей сессии:

### Шаг 1. Фикс импорта кред и воркфлоу
- Подготовь `creds.json` с **явными `id`** (UUID) для каждой креды.
- Импортируй через `docker exec factory-n8n n8n import:credentials --input=/path/creds.json`.
- Импортируй воркфлоу без `--activeState`, активируй отдельно.

### Шаг 2. Тест `node:sqlite` в Code-ноде
- Создай тестовый воркфлоу `zz-test-sqlite`: Webhook → Code-нода с
  `const {DatabaseSync} = require('node:sqlite'); const db = new DatabaseSync('/var/data/factory.db'); return [{json: {settings: db.prepare('SELECT key, value FROM settings').all()}}];`
- Активируй, тестируй `curl POST /webhook/zz-test-sqlite`.
- Если работает — это твой стандартный путь для всех DB-операций.
- Если не пускает песочница — план Б: SystemCommand-нода с `sqlite3`.

### Шаг 3. Запуск Hermes gateway
- `sudo systemctl enable --now hermes` → `journalctl -u hermes -f`.
- Напиши боту в TG `/start` — Hermes должен ответнуть.
- Если gateway не запускается с первого раза — проверь `~/.hermes/.env`
  (TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USERS), логи `journalctl -u hermes`.

### Шаг 4. T-033' — скиллы и orchestrator.md
- `cp ~/factory/hermes/skills/*.md ~/.hermes/skills/`
- В `~/.hermes/skills/orchestrator.md` добавь инструкцию: вызывать n8n через
  `terminal` toolset → `curl -X POST http://localhost:5678/webhook/factory/<wf> -d '{...}'`.
- Проверь: `hermes skills list` показывает 4 skill.
- Тест: `hermes chat -q "Запусти аналитику для robotec"` (mock-режим) →
  агент должен сделать curl к wf-analytics.

### Шаг 5. Построение всех воркфлоу (через CLI-импорт)

Для каждого воркфлоу — JSON с явными id, импорт, активация, тест.

**T-081' wf-tg-alerts** (полностью рабочий, нужен только TG):
- Webhook `/webhook/factory/tg-alert` → Telegram Send.
- Тест: `curl -X POST http://localhost:5678/webhook/factory/tg-alert -d '{"chat_id":941296693,"text":"test"}'` → приходит в TG.

**T-040 wf-onboard** (полностью рабочий, не нужен платный API):
- Webhook `/webhook/factory/onboard` → HTTP GET целевого URL → Code (извлечь
  meta/socials с SSRF-защитой — запрет `10/8`, `172.16/12`, `192.168/16`, `127/8`).
- Тест: `curl -X POST http://localhost:5678/webhook/factory/onboard -d '{"url":"https://robotec.ru"}'`
  → черновик профиля с meta + TG-ссылкой @robotec_tg.

**T-050..T-056 wf-analytics** (структура + mock):
- 3 параллельные ветки IG/TikTok/YT (HTTP к scrapecreators, header `x-api-key`).
- После каждого HTTP — **Switch на placeholder-cred**:
  - true → Code-нода с mock JSON (3-5 реалистичных кандидатов в нише robotec).
  - false → реальный HTTP (завтра).
- Code: постфильтр 12–72ч по timestamp, дедупликация, virality, топ-20.
- Тест: `curl POST /webhook/factory/analytics -d '{"client_id":1,"find_competitors":true}'`
  → топ-20 mock-кандидатов.

**T-070..T-073 wf-creatify-*** (структура + mock):
- `wf-creatify-link`: Webhook → HTTP `POST /api/links/` → Switch mock → ответ link_id.
- `wf-creatify-submit`: Webhook → INSERT в generations → HTTP `POST /api/link_to_videos/`
  → Switch mock → ответ creatify_id.
- `wf-creatify-webhook`: Webhook `/webhook/factory/creatify/<random-token>` →
  идемпотентная обработка callback → Code (скачивание video_output в mock) →
  UPDATE generations → wf-tg-alerts.
- `wf-creatify-poll`: Cron `*/5 * * * *` → поллинг задач (в mock пропускается).

**T-102..T-104 wf-publish + wf-publish-status + wf-sync-accounts** (структура + mock):
- wf-publish: `/upload/init` → poll `/upload/status` → `POST /publications`
  (всё с placeholder-cred → mock успех).
- wf-publish-status: Cron `*/2` → поллинг статусов (mock).
- wf-sync-accounts: Cron `0 * * * *` → GET /accounts (mock).

**T-034' — Webhook-ноды во все wf-*:**
- `/webhook/factory/analytics`, `/onboard`, `/creatify-link`, `/creatify-submit`,
  `/creatify/<token>`, `/publish`, `/tg-alert`.

**T-042/T-060..T-063 субагенты Hermes** (LLM, не зависит от платных API):
- Скиллы уже перенесены (Шаг 4). Тестируй через `hermes chat`:
  - Аналитик: скорми mock-кандидатов → должен выбрать 1 тему в нише robotec.
  - Сценарист: на выбранной теме → сценарий 30с в тональности robotec.
  - JSON-сборщик: на сценарии → валидный JSON для creatify (language: ru, 9x16).

**T-084 сообщения 4 этапов ручного режима** — Hermes-side через Telegram gateway.
Отладка на mock-данных. Кнопки `✅ Утвердить / ✏️ Изменить / ❌ Отклонить`.

### Шаг 6. Тесты и обновление DEPLOYMENT.md
- Прогон всех webhook'ов через curl, фиксация результатов.
- `/start_cycle` в TG → Hermes прогоняет цикл на mock-данных.
- Обновить `~/factory/DEPLOYMENT.md`: что готово, что под mock, что завтра.

## MOCK-ПАТТЕРН (для всех HTTP к платным API)

После каждого HTTP — Switch:
```
{{ $env.SCRAPECREATORS_API_KEY === 'PLACEHOLDER_UNTIL_TOMORROW' }}
  → true:  Code-нода с mock JSON
  → false: реальный HTTP-ответ (завтра)
```
Mock JSON делай реалистичным (5 кандидатов в нише промышленной робототехники,
метрики 12-72 часа, чтобы постфильтр реально работал).

## АРХИТЕКТУРНЫЕ ОГРАНИЧЕНИЯ (не нарушать)

- **TG-бот только в Hermes** (`hermes gateway`). НЕ Telegram Trigger в n8n — конфликт.
  Только Send-ноды для алертов.
- **Hermes в venv + systemd**, не в Docker.
- **Hermes → n8n** через `terminal` (`curl`) или MCP-мост (опц. P0).
- **Две БД:** `~/factory/data/factory.db` (бизнес), `~/.hermes/state.db` (agent-state).
- **Приоритет при конфликте спек** — `~/factory/specs/11-amendments.md`.

## БЕЗОПАСНОСТЬ

- Секреты только в `.env`, права 600.
- Placeholder-ключи явно: `PLACEHOLDER_UNTIL_TOMORROW`.
- Не логировать ключи.
- SSRF-защита в wf-onboard.
- Path-token на creatify webhook: `/webhook/factory/creatify/<random-string>`.

## БЮДЖЕТ (для Фазы 2)

- creatify: 5 кредитов / 30 сек. Лимиты 100/мес, 3/день. Не ретрай при failed.
- scrapecreators: cache hit = 0 кредитов, `trim=true`.
- Hermes LLM: free-тир opencode zen, контекст 200K.

## УСТОЙЧИВОСТЬ

- HTTP-ноды: retry 3x с backoff.
- При сбое сервиса — не вали весь цикл.
- Идемпотентность вебхука creatify: проверка `creatify_id` в БД.

## КАК ОТЧИТЫВАТЬСЯ

**Краткий отчёт после каждого крупного тикета** (wf-tg-alerts, wf-onboard,
wf-analytics, и т.д.) — что работает, что под mock, что блокируется.

**Финальный отчёт по ФАЗЕ 1** (к концу этой сессии):
```
- [ ] Hermes gateway: TG-бот отвечает на /start
- [ ] Hermes skills: orchestrator + 3 субагента загружены, hermes skills list видит
- [ ] systemd-юнит hermes.service активен
- [ ] node:sqlite в Code-ноде работает (или план Б задействован)
- [ ] n8n: импорт кред и воркфлоу через CLI работает
- [ ] wf-tg-alerts: curl → сообщение в TG приходит
- [ ] wf-onboard: curl с robotec.ru → черновик профиля
- [ ] wf-analytics: 3 ветки + постфильтр 12-72ч, тест на mock-данных
- [ ] wf-creatify-link + submit + webhook + poll: структура + mock
- [ ] wf-publish + sync-accounts: структура + mock
- [ ] субагент-Онбординг: mock-черновик → профиль клиента JSON
- [ ] субагент-Аналитик: mock-кандидаты → выбранная тема
- [ ] субагент-Сценарист: тема → сценарий 30с в тональности robotec
- [ ] субагент-JSON-сборщик: сценарий → валидный JSON для creatify
- [ ] /start_cycle в TG: Hermes прогоняет цикл на mock-данных
- [ ] DEPLOYMENT.md обновлён
```

**Если снова упрёшься в лимит итераций** — оставь такой же подробный отчёт:
что сделано, какие находки, что НЕ сделано, что дальше. Это критично для
плавного продолжения.

## КАК РАБОТАТЬ С ОРКЕСТРАТОРОМ

Оркестратор (ZCode) — отдельная сессия, знает проект целиком. Не пишет бизнес-код,
но отвечает на архитектурные вопросы и проводит ревью.

**Когда обращаться (через пользователя):**
- Спека противоречит реальности API → приложи curl.
- Архитектурный блокер → предложи решение, жди подтверждения.
- Нашёл лучшее решение → предложи, не применяй без подтверждения.

**Когда НЕ обращаться:**
- Мелкие баги, опечатки — чини сам.
- Неясности в JSON-полях API — кури доки сервисов.

## ОЖИДАНИЯ

- **Автономность:** дойди до завершения Фазы 1 без постоянных вопросов.
- **Честность:** явно помечай mock vs реально работающее. Если упёрся в лимит —
  подробный отчёт как в прошлой сессии.
- **Готовность к Фазе 2:** завтра только подстановка ключей, без правки кода.
- **Качество:** retry, error handling, идемпотентность.
- **Документация:** обновляй `~/factory/DEPLOYMENT.md`.

## ПРИЁМКА

Когда Фаза 1 готова — отчёт пользователю. Оркестратор (ZCode) проведёт ревью
архитектуры, логики, mock-паттернов, безопасности. После ревью — Фаза 2 завтра.

**Удачи. Продолжай с Шага 1 (фикс импорта кред). Приступай по /autopilot.**

---

## СТАРТОВАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ КОМАНД

```bash
# 1. Подключение с Mac пользователя
chmod 400 /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem
ssh -i /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem ubuntu@83.166.233.95

# 2. Активация Hermes env
export PATH="$HOME/.local/bin:$PATH"
source ~/hermes-agent/.venv/bin/activate

# 3. Проверка состояния (быстро)
docker ps
sqlite3 ~/factory/data/factory.db "SELECT key, value FROM settings WHERE key IN ('mode','active_client_id');"
cat ~/.hermes/.env | grep -E "TELEGRAM_(BOT_TOKEN|ALLOWED_USERS|HOME_CHANNEL)" | sed 's/=.*/=***/'

# 4. Шаг 1: проверь что creds.json и воркфлоу-импорт работают
docker exec factory-n8n n8n --help | grep import

# 5. Шаг 2: тест node:sqlite
# (создай zz-test-sqlite воркфлоу, импортируй, активируй, тестируй curl'ом)

# 6. Шаг 3: запуск Hermes
sudo systemctl enable --now hermes
journalctl -u hermes -f
# В другом терминале / с телефона: написать боту /start
```
