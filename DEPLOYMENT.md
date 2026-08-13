# DEPLOYMENT — контент-завод: статус Фазы 1 (11.08–12.08.2026)

**Сервер:** `83.166.233.95` (VK Cloud, Ubuntu 24.04.4 LTS)
**Стек:** n8n 2.34.4 (docker) + Hermes Agent v0.20.0 (venv+systemd) + SQLite `factory.db` + db-bridge (node:sqlite)
**LLM:** opencode zen → deepseek-v4-flash-free (настроен, работает)
**Демо-клиент:** Robotec (robotec.ru, B2B-интегратор KUKA)

---

## 1. Статус Фазы 1: ✅ ЗАВЕРШЕНА (кроме финальных проверок с живым TG)

| Компонент | Статус | Где |
|-----------|--------|-----|
| n8n 2.34.4 (healthy) | ✅ | docker `factory-n8n` |
| Cloudflared tunnel | ✅ | `https://assessment-fossil-assignments-alice.trycloudflare.com` (узнать актуальный: `docker logs factory-cloudflared-n8n 2>&1 \| grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' \| head -1`) |
| db-bridge (HTTP к factory.db) | ✅ | docker `factory-db-bridge`, `http://db-bridge:8787/query` + заголовок `X-BRIDGE-TOKEN` |
| Hermes gateway (TG-бот) | ✅ active (running) | systemd `hermes.service`; бот `@content_zavod_obrazec_bot` |
| Скиллы Hermes (6 шт) | ✅ | `~/.hermes/skills/content-factory/{orchestrator,analyst,scriptwriter,json-builder,onboarding}/SKILL.md` (+ n8n-admin) |
| Credentials n8n (4 шт) | ✅ | scrapecreators/creatify/postmypost — **PLACEHOLDER_UNTIL_TOMORROW**, telegram — реальный |
| Воркфлоу n8n (11 шт, все активны) | ✅ | см. таблицу ниже |
| БД factory.db | ✅ | 13 таблиц, клиент Robotec (active, id=1), тестовые данные |

## 2. Воркфлоу n8n (все активны, webhook'и зарегистрированы)

| Воркфлоу | Webhook/триггер | Статус теста |
|----------|-----------------|--------------|
| wf-tg-alerts | POST `/webhook/factory/tg-alert` {chat_id, text} | ✅ сообщение уходит в TG |
| wf-onboard | POST `/webhook/factory/onboard` {url} | ✅ robotec.ru → title/meta/h1/socials; SSRF 127.0.0.1 отклонён |
| wf-analytics | POST `/webhook/factory/analytics` {client_id} | ✅ 3 ветки, постфильтр 12–72ч, топ-20 (mock) |
| wf-creatify-link | POST `/webhook/factory/creatify-link` {url} | ✅ link_id (UUID, mock) |
| wf-creatify-submit | POST `/webhook/factory/creatify-submit` {json_payload, link_id, script_id, client_id} | ✅ INSERT generations + creatify_id в БД (mock) |
| wf-credit-check | POST `/webhook/factory/credit-check` {} | ✅ 200 {ok:true, balance:497} (13.08, live) |
| wf-creatify-webhook | POST `/webhook/factory/creatify/6d8f2a41c9e7b3d5f0a1c4e8` | ✅ done→status=done, повтор→duplicate, failed→failed (идемпотентность) |
| wf-creatify-poll | Cron `*/5 * * * *` | ✅ исполняется, success |
| wf-publish | POST `/webhook/factory/publish` {generation_id, platforms, post_at, captions} | ✅ posts строка + postmypost_id=999 (mock) |
| wf-publish-status | Cron `*/2 * * * *` | ✅ pending_publication → published + tg-алерт (mock) |
| wf-sync-accounts | Cron `0 * * * *` | ✅ social_accounts наполнен; status=2 → tg-алерт |
| wf-creator-content | POST `/webhook/factory/creator-content` {platform, handle, limit?} | ✅ посты автора с метриками + ER (SC-3, 13.08, exec 1741–1748) |
| zz-test-sqlite | POST `/webhook/factory/_test` | служебный |

**Тестовые curl (с сервера):**
```bash
curl -X POST http://localhost:5678/webhook/factory/onboard -H 'Content-Type: application/json' -d '{"url":"https://robotec.ru"}'
curl -X POST http://localhost:5678/webhook/factory/analytics -H 'Content-Type: application/json' -d '{"client_id":1,"find_competitors":false}'
curl -X POST http://localhost:5678/webhook/factory/creatify-link -H 'Content-Type: application/json' -d '{"url":"https://example.com"}'
curl -X POST http://localhost:5678/webhook/factory/tg-alert -H 'Content-Type: application/json' -d '{"chat_id":941296693,"text":"test"}'
```

## 3. Архитектура и ключевые точки

```
[TG оператор] ──► [Hermes gateway (TG-бот)] ──► [Hermes agent (orchestrator, скиллы)]
                         │  delegate_task(analyst/scriptwriter/json-builder/onboarding)
                         ▼ terminal/curl
                  [n8n webhook-ноды] ──► [db-bridge] ──► [factory.db]
                         │
              scrapecreators/creatify/postmypost (mock до Фазы 2)
```

- Приём TG — только Hermes (gateway). n8n — только Send (wf-tg-alerts).
- Hermes → n8n: `curl -X POST http://localhost:5678/webhook/factory/<wf> -d '{...}'` (инструкция в orchestrator SKILL.md).
- DB-операции n8n: HTTP Request → `http://db-bridge:8787/query` с `X-BRIDGE-TOKEN: {{ $env.FACTORY_DB_BRIDGE_TOKEN }}`.
- Две БД: `~/factory/data/factory.db` (бизнес), `~/.hermes/state.db` (agent-state).

## 4. MOCK-паттерн (ключи платных API)

Все HTTP к scrapecreators/creatify/postmypost построены по паттерну:
`Switch ($env.<KEY> === 'PLACEHOLDER_UNTIL_TOMORROW') → true: Code mock | false: реальный HTTP`.
В `~/factory/.env` стоят `PLACEHOLDER_UNTIL_TOMORROW` для: SCRAPECREATORS_API_KEY, CREATIFY_API_ID, CREATIFY_API_KEY, POSTMYPOST_TOKEN, POSTMYPOST_PROJECT_ID.

**Фаза 2 (после получения ключей):**
1. Запустить `~/factory/phase2-enable.sh` с реальными ключами (см. раздел 12) — скрипт сам заменит placeholder'ы в `~/factory/.env` и пересоздаст n8n.
2. Обновить Credentials n8n (UI): scrapecreators/creatify/postmypost — заменить placeholder на реальные.
3. Switch-ноды автоматически уйдут в ветку real — правка воркфлоу НЕ нужна.
4. В `~/.hermes/.env` обновить OPENCODE_ZEN_API_KEY при необходимости.

## 5. ИНЖЕНЕРНЫЕ НАХОДКИ (критично — паттерны n8n 2.34)

1. **jsonBody httpRequest**: НЕ использовать статические JSON-строки с вложенными `{{ }}` (не раскрываются) и НЕ вложенные `{{ }}` в объектных выражениях. Надёжно: Code-нода «Build body» формирует `{sql, params}` → `jsonBody: "={{ $json }}"`. Альтернатива — внешнее выражение без вложенных `{{ }}`: `={{ {sql: '...', params: [String($json.body.x)]} }}`.
2. **Исполняется версия из `workflow_history[activeVersionId]`**, а НЕ черновик `workflow_entity.nodes`. Правка живого воркфлоу: обновить ОБЕ таблицы + `docker restart factory-n8n`. (CLI-import обновляет черновик и деактивирует — нужен UI Publish.)
3. **IF 2.3**: `{"conditions":{"combinator":"and","options":{"caseSensitive":true,"typeValidation":"strict","leftValue":"","version":2},"conditions":[{"leftValue":"={{ Number(($json.rows || []).length) }}","rightValue":0,"operator":{"type":"number","operation":"greaterThan"}}]}}` — rightValue ЧИСЛО, leftValue в `Number()`.
4. **Switch 3.4** (conditions-based): `{"mode":"rules","rules":{"values":[{"conditions":{"options":{"caseSensitive":true,"leftValue":"","typeValidation":"strict"},"conditions":[{leftValue,rightValue,operator}],"combinator":"and"}}]},"options":{}}` + `"fallbackOutput":"extra"` для второй ветки.
5. **$env в выражениях** работает после `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` (в compose n8n).
6. **Code-нода**: нельзя `require('node:sqlite'/'node:dns'/'node:crypto'/'node:fs')`, нельзя `new URL`. UUID — Math.random-функцией, URL — regex.
7. **Активация импортированного воркфлоу — только UI Publish** (импорт снимает активность; `--activeState` не работает в single-main).
8. **Активность и webhook'и переживают рестарт/пересоздание n8n** (после Publish).
9. **Сеть VK Cloud**: часть IP api.telegram.org (149.154.166.x) недоступна → extra_hosts в compose n8n (149.154.167.220/.99) + `TELEGRAM_FALLBACK_IPS` в `~/.hermes/.env` + пин в /etc/hosts.
10. **SQLite-сравнение времени**: post_at хранится в ISO+таймзона → сравнивать через `julianday(post_at) <= julianday('now','+1 hour')`.
11. **Экспорт воркфлоу из БД**: `workflow_entity` — колонки nodes/connections (JSON), версии — `workflow_history`.
12. **Корневые id воркфлоу** — фиксированные (20000000-...-001..012); параллельным субагентам выдавать УНИКАЛЬНЫЕ id (был конфликт 00b).

## 6. Что НЕ сделано / на Фазу 2

- Реальные ключи scrapecreators/creatify/postmypost (придут 12.08 после обеда).
- E2E: `/onboard https://robotec.ru` (реальный scrapecreators-поиск соцсетей — на сайте robotec.ru сейчас только Rutube; TG/IG уточнить), `/start_cycle` с реальной генерацией видео.
- Скачивание MP4 от creatify (в mock webhook — только запись local_path; для Фазы 2 — расширить db-bridge эндпоинтом /download или нодой-файлом).
- **FIXME**: в скилле content-factory-development (субагент T-M) остался склеенный буллет — аккуратно поправить текст.
- Пользователю: написать боту в TG `/start` (проверка gateway) и `/start_cycle` (ручной цикл на mock).

## 7. Доступы (напоминание)

- n8n UI: `https://assessment-fossil-assignments-alice.trycloudflare.com`, owner@factory.local / PASSWORD_PLACEHOLDER
- SSH: `ssh -i <ключ>.pem ubuntu@83.166.233.95`
- Hermes: `source ~/hermes-agent/.venv/bin/activate && hermes ...`
- БД: `sqlite3 ~/factory/data/factory.db`
- Секреты: `~/factory/.env` (n8n/compose), `~/.hermes/.env` (Hermes) — права 600.

## 8. Известные ограничения

- Quick-tunnel cloudflared меняет URL при пересоздании контейнера cloudflared (для прода — named tunnel).
- RAM 4GB+swap 4GB — мониторить при тяжёлых циклах.
- free-тир deepseek v4 — временная акция; запасной: deepseek-v4-flash.

## 8a. Rate limits (opencode zen free-тир, HTTP 429)

- Симптом: `HTTP 429: Rate limit exceeded` от opencode zen free-тира (`deepseek-v4-flash-free`); в `~/.hermes/logs/agent.log` — `API call failed ... error_type=RateLimitError`. Частота: десятки раз за сессию — это НОРМА, лечится повтором через паузу (встроенный backoff: cooldown 60s).
- Fallback-цепочка НАСТРОЕНА (12.08, штатно через `hermes config set`, НЕ ручной правкой yaml):
  ```yaml
  fallback_providers:
    provider: opencode-zen
    model: deepseek-v4-flash   # платный тир, тот же OPENCODE_ZEN_API_KEY
  ```
  Активация подтверждена в логе: `Fallback activated: deepseek-v4-flash-free → deepseek-v4-flash (opencode-zen)`.
  Управление: `hermes fallback list|add|remove|clear`; смена модели — `hermes config set fallback_providers.model <model> --force`.
- ВАЖНО (на 12.08): платный `deepseek-v4-flash` отвечает `HTTP 401 CreditsError: No payment method` — у workspace `wrk_01KZNN7MGAH7Z7V3SR49KMYD90` нет способа оплаты (https://opencode.ai/workspace/wrk_01KZNN7MGAH7Z7V3SR49KMYD90/billing). Пока биллинг не добавлен, fallback НЕ спасает от 429 — итог тот же: повторный запрос позже. После добавления оплаты fallback заработает без изменений конфига.
- Практика: при 429 в автоматике — повторять запрос с паузой 60–120с (backoff уже встроен, попытки 1/3); для одноразовых прогонов — `hermes chat -q ... --cli -Q` с таймаутом ≥600с (см. скилл content-factory-development).

## 9. Интеграционный тест цикла (T-S): ✅ ПРОЙДЕН на mock-данных

Полный цикл /start_cycle прогнан: wf-analytics (exec 83, 4 кандидата) -> тема (analyst) -> сценарий (scriptwriter) -> wf-creatify-link -> JSON (json-builder) -> wf-creatify-submit (exec 95) -> имитация callback -> wf-creatify-webhook (exec 96, status=done, /var/media/12.mp4) -> wf-tg-alerts (exec 97). generations #12: creatify_id + status=done. Без правки кода.

---

## 10. Telegram UX (спека 12) — реализовано

**State machine** — 9 состояний (IDLE, ONBOARDING_PENDING, CYCLE_ANALYTICS_PENDING,
CYCLE_SCRIPT_PENDING, CYCLE_SCRIPT_EDITING, CYCLE_GENERATION_PENDING,
CYCLE_VIDEO_PENDING, CYCLE_PUBLISH_PENDING, AUTO_CYCLE_RUNNING).
Хранение: первая строка `~/.hermes/memories/MEMORY.md`:
`STATE: <name> | topic_id=... | script_id=... | generation_id=... | updated_at=<ISO>`.
Правила работы со STATE — в orchestrator/SKILL.md (раздел «ПРАВИЛА РАБОТЫ СО STATE»):
перед каждым ответом читать MEMORY.md, после перехода — обновлять первую строку.

**Slash-команды (15, зарегистрированы в Telegram через setMyCommands)**:
start, help, status, mode, onboard, start_cycle, cancel, topics, competitors,
accounts, budget, client, clients, reload_skills, ping.
Автокомплит в чате при вводе "/" — работает.

**Inline-кнопки** — этапы 1-4 цикла (шаблоны в orchestrator/SKILL.md):
- Этап 1 (тема): approve:topic:{id} / edit:topic:{id} / reject:topic:{id} / alt:topic:{id}
- Этап 2 (сценарий): approve:script:{id} / edit:script:{id} / reject:script:{id}
- Этап 3 (видео): publish:gen:{id} / regen:gen:{id} / reject:gen:{id}
- Этап 4 (площадки): toggle:platform:{name} / schedule:{now|2h|tomorrow_12} / confirm:publish
Обработка — раздел «CALLBACK-ОБРАБОТЧИКИ» в SKILL.md (UPDATE в БД + переход STATE).

**Логирование** — каждый переход STATE / slash-команда / callback / wf-вызов
пишутся в таблицу logs (factory.db) через db-bridge:
INSERT INTO logs (level, component, event, message, payload) VALUES ('info','hermes','state_change','STATE: A → B','{"from":"A","to":"B"}')

**Жёсткие ограничения** (в начале SKILL.md): бот — только оркестратор контент-завода;
отказ на вопросы вне тематики («Я — бот контент-завода. /help»); не выдумывать
данные; порядок цикла analytics→topic→script→json→generate→publish строго
с паузами на оператора; свободный текст разрешён только в CYCLE_SCRIPT_EDITING.

### Команды оператора для тестирования
- `/start` — приветствие + меню (клиент, режим, кредиты)
- `/status` — сводка компонентов (🟢/🔴) + клиент + кредиты + видео сегодня/месяц
- `/start_cycle` — цикл на mock: аналитика → тема → ... → публикация
- `/cancel` — отмена из любого состояния → IDLE
- `/budget`, `/topics`, `/competitors`, `/accounts`, `/clients`, `/ping` — данные из БД
- `/onboard <url>` — профиль клиента по сайту

### Тест state machine (прогнан 12.08, mock)
[start_cycle → CYCLE_ANALYTICS_PENDING → approve:topic → CYCLE_SCRIPT_PENDING →
approve:script → генерация → этап 4 (wf-publish post_id=3, platforms instagram/youtube/tiktok) → IDLE]
Результат: ✅ ПРОЙДЕН (U-7). Логи factory.logs наполняются: state_change, wf_call, callback, slash_command.
MEMORY.md: первая строка `STATE: IDLE`.

### Что НЕ работает / требует человека
- Реальный клик кнопок в TG (эмуляция через hermes chat — работает; живой клик
  проверяется оператором: /start → /start_cycle → нажать кнопку)
- Видео-превью на этапе 3 (mock: local_path без реального MP4; реально — после
  подключения creatify в Фазе 2)

---

## 11. Ротация и обслуживание

Автоматическое обслуживание через cron (пользователь ubuntu, настроено 12.08):

- Ежедневно 03:00 — удаление записей `logs` (factory.db) старше 7 дней:
  `0 3 * * * sqlite3 /home/ubuntu/factory/data/factory.db "DELETE FROM logs WHERE ts < datetime('now','-7 days');"`
- Ежедневно 03:30 — удаление файлов в `~/factory/media` старше 7 дней:
  `30 3 * * * find /home/ubuntu/factory/media -type f -mtime +7 -delete`
- Еженедельно (вс) 05:00 — VACUUM базы factory.db (дефрагментация, сброс WAL):
  `0 5 * * 0 sqlite3 /home/ubuntu/factory/data/factory.db "VACUUM;"`

Временные артефакты импорта в контейнере n8n (`/tmp/wf-*.json`, `/tmp/zz-*.json`,
`/tmp/all_wf.json`, `/tmp/q3.json`) — удаляются вручную при обслуживании.

Проверка: `crontab -l` — должны быть видны три строки выше.

---

## 12. Фаза 2: подстановка ключей

Скрипт подстановки реальных ключей платных API в `~/factory/.env`:
**`~/factory/phase2-enable.sh`** (`chmod +x`). Заменяет `PLACEHOLDER_UNTIL_TOMORROW`
на переданные значения для SCRAPECREATORS_API_KEY, CREATIFY_API_ID,
CREATIFY_API_KEY, POSTMYPOST_TOKEN, POSTMYPOST_PROJECT_ID и пересоздаёт контейнер
n8n (`cd ~/factory && docker compose up -d n8n`; активность воркфлоу сохраняется).

Флаги: `--scrapecreators=KEY --creatify-id=ID --creatify-key=KEY
--postmypost-token=TOKEN --postmypost-project=ID`, плюс `--dry-run`.

Проверка без записи (значения маскируются: первые 4 + последние 4 символа):

```bash
cd ~/factory && ./phase2-enable.sh --dry-run --scrapecreators=sk-TEST123 \
    --creatify-id=TEST --creatify-key=TEST \
    --postmypost-token=TEST --postmypost-project=123
```

Реальный запуск (когда ключи получены):

```bash
cd ~/factory && ./phase2-enable.sh --scrapecreators=... --creatify-id=... \
    --creatify-key=... --postmypost-token=... --postmypost-project=...
```

Порядок работы: маскированный diff → подтверждение `[y/N]` → замена python3 по
`KEY=` (спецсимволы ключей безопасны) → `chmod 600 ~/factory/.env` →
`docker compose up -d n8n` → инструкция: обновить Credentials в n8n UI
(`https://assessment-fossil-assignments-alice.trycloudflare.com` → Settings →
Credentials: scrapecreators `x-api-key`, creatify `X-API-ID` + `X-API-KEY`,
postmypost Bearer token) → Switch-ноды уходят в real-ветку автоматически.

Без аргументов скрипт печатает usage и выходит с кодом 1; при `N` на подтверждении —
отмена без изменений. `--dry-run` НИКОГДА не пишет в `.env`.

## 13. НОВАЯ АРХИТЕКТУРА (спека 13): n8n = оркестратор TG, Hermes = LLM-движок

**Дата миграции:** 12.08.2026 (M-1..M-7). Основание: Hermes-gateway непригоден как
client-facing TG-бот (служебные сообщения, встроенные slash-команды, approvals).

### Компоненты
- **n8n = оркестратор UI/UX**: Telegram Trigger (webhook-режим) → whitelist → парсер
  команд → Switch → Telegram Send с inline-кнопками. State machine — таблица `sessions` в factory.db.
- **hermes-bridge = LLM-движок**: хостовый systemd-сервис (Python stdlib http.server,
  порт 8642, токен HERMES_BRIDGE_TOKEN в ~/factory/.env). POST /ask {skill, prompt} →
  subprocess hermes chat -q ... -s content-factory/<skill>. n8n вызывает через
  http://host.docker.internal:8642/ask (extra_hosts добавлен).
- **Hermes-gateway: ОСТАНОВЛЕН** (systemctl disable hermes). Hermes — только CLI через bridge.
  Telegram platform отключена; register-tg-commands.sh убран из ExecStartPost.

### Воркфлоу
- **wf-tg-bot** (id ...013, АКТИВЕН, 180 нод): Telegram Trigger (webhook, allowed_updates
  message+callback_query) → whitelist (941296693) → парсер текстовых триггеров (en+ru)
  → команды start/help/status/cancel/ping/start_cycle/onboard + callback-обработчики
  (approve/edit/reject/alt:topic, approve/edit/reject:script, publish/regen/reject:gen,
  toggle:platform, schedule:*, confirm:publish) → db-bridge (sessions/topics/scripts) +
  hermes-bridge (analyst/scriptwriter/json-builder/onboarding) + reply_markup кнопки.
  Активация: эмуляция Publish через БД (activeVersionId + active=1 + рестарт).
- **wf-creatify-webhook** (…00e): done-ветка теперь слает Этап 3 в TG с inline-кнопками
  (publish:gen/regen/reject) + UPDATE sessions state='CYCLE_VIDEO_PENDING' (21 нода).

### Проверка
- getWebhookInfo: URL = cloudflared/webhook/...013/tg%20trigger/webhook, allowed_updates
  message+callback_query, pending=0.
- hermes-bridge: systemctl is-active hermes-bridge = active; curl localhost:8642/health → {ok:true}.
- sessions: 941296693|IDLE.
- Live TG-тест (за оператором): start / help / status / cancel / start_cycle → кнопки.

### ПИТФОЛЛ: webhook-путь telegramTrigger (важно!)
- Имя триггерной ноды **НЕ должно содержать пробелов**: n8n генерирует webhookPath
  из имени ноды. «TG Trigger» → путь `.../tg%20trigger/webhook` — маршрут НЕ
  регистрировался (404 «is not registered»), при этом setWebhook ставился
  (getWebhookInfo показывал URL) и n8n логировал «Activated workflow».
- Исправление (12.08, после аудита A-4): переименование ноды в **tg-trigger**
  в workflow_history[activeVersionId] + workflow_entity + DELETE строки
  webhook_entity + docker restart → маршрут `.../tg-trigger/webhook` встал
  (probe → 403 «Provided secret is not valid» = маршрут жив, секретная защита).
- Проверка маршрута: POST на /webhook/<id>/<path> БЕЗ секретного заголовка
  должен давать 403 (не 404). 404 = маршрут не зарегистрирован.

### Команды оператора (live TG)
start, help, status, cancel, ping, start_cycle, onboard <url> (текстовые триггеры без слеша;
slash-формы в автокомплите есть). «напиши стих» → канонический отказ.

## 14. F-4: 8 команд wf-tg-bot РЕАЛИЗОВАНЫ (13.08)

Ветки добавлены в wf-tg-bot (214 нод, активная версия 045e5e3b): mode, topics, competitors,
accounts, budget, client <id>, clients, reload_skills (заглушка «больше не используется»).
Тесты 11/11 success (exec 1720-1730, live через webhook tg-trigger, секрет-workflowId_nodeId).

⚠️ ПИТФОЛЛ: n8n Telegram-нода ПРИНУДИТЕЛЬНО ставит parse_mode='Markdown' (GenericFunctions.js:
if (!additionalFields.parse_mode) parse_mode='Markdown') — отключить нельзя. Любое `_` в тексте =
«Bad Request: can't parse entities» (незакрытый курсив). Фикс: экранировать в Code-нодах
esc = s => String(s ?? '').replace(/([_*[\]`])/g, '\\$1') (применено во всех Format-нодах).
Статичные тексты — без `_` или с экранированием.

## 15. SC-3: wf-creator-content — посты автора с метриками (13.08, LIVE)

**Назначение:** по handle автора вернуть последние посты с метриками (views/likes/comments/shares), отсортированные по ER (engagement rate), топ-N. Источник — ScrapeCreators (кред ...001, httpHeaderAuth `x-api-key`). JSON: `~/factory/wf-creator-content.json` (id `20000000-...-000000000014`, 12 нод, active=1, webhook зарегистрирован).

**Контракт:** `POST /webhook/factory/creator-content` body `{platform, handle, limit?}` (limit по умолчанию 10, cap 50; platform: instagram|tiktok|youtube|twitter) →
```json
{"ok": true, "count": 3, "platform": "tiktok", "handle": "mrbeast",
 "posts": [{"id": "...", "url": "https://www.tiktok.com/@mrbeast/video/...", "views": 279593521,
            "likes": 34295875, "comments": 1704854, "shares": 11404787,
            "posted_at": "2026-08-02T22:14:39.000Z", "thumb_url": "...", "duration": 8, "er": 0.3449}]}
```
`er = (likes + comments*3 + shares*5) / views` (views=0 → er=0), сортировка по er desc, slice(0, limit). Неизвестная платформа → `{"ok":false,"count":0,"error":"unsupported platform: vk",...}`.

**Схема воркфлоу:** Webhook (`factory/creator-content`, responseNode) → Switch platform (v3.4 rules, 4 правила + `fallbackOutput:"extra"`) → 4× HTTP (GET, auth genericCredentialType+httpHeaderAuth, кред ...001) → 4× Code Normalize (маппинг → ER → sort → slice) / Code Fallback → единый Respond (`={{ $json }}`). HTTP-параметры: IG `handle,trim=true`; TikTok `handle,trim=true,region=US`; YT `handle,includeExtras=true`; Twitter `handle,trim=true`. Вход webhook читается защитно `($json.body && $json.body.X) || $json.X`.

**Проверенные структуры ответов API (13.08, живые curl):**
- TikTok `GET /v3/tiktok/profile/videos?handle=&trim=&region=` → `{success, aweme_list:[...], has_more, max_cursor}`. item: `aweme_id` (str), `desc`, `create_time` (unix), `url` (`https://www.tiktok.com/@user/video|photo/{aweme_id}`), `statistics{play_count, digg_count, comment_count, share_count}`, `video{duration (МС! → /1000), cover{url_list[]}}`. ⚠️ v3, не v1; trim=true НЕ обнуляет кэш.
- Instagram `GET /v1/instagram/user/reels?handle=&trim=` → `{success, items:[...], max_id}`. item: `id`, `code`, `url` (`.../reel/{code}/`), `play_count`, `like_count`, `comment_count`, `taken_at` (unix), `display_uri` (thumb), `caption{text}`. Капшенов в ответе нет у reels/search — здесь caption есть (объект). duration отсутствует → null.
- YouTube `GET /v1/youtube/channel-videos?handle=&includeExtras=` → `{success, videos:[...]}`. item: `id`, `title`, `url`, `viewCountInt`, `likeCountInt`, `commentCountInt` (только с includeExtras=true!), `publishedTime` (ISO), `lengthSeconds`, `thumbnail`. `viewCount` (без Int) НЕТ.
- Twitter `GET /v1/twitter/user-tweets?handle=&trim=` — НЕ тестирован живьём (бюджет кредитов); маппинг по описанию openapi: `tweets[]` → `rest_id|id_str|id`, `url`, `views|view_count`, `favorite_count`, `reply_count`, `retweet_count`, `created_at` (ISO + fallback-парсер «EEE MMM dd HH:mm:ss Z yyyy»), `media[0].media_url_https`. Проверен на синтетике.

**Тест (13.08, live):** exec 1741 tiktok limit=3 (count 3) · 1742 instagram limit=2 (count 2) · 1746 youtube @MrBeast limit=2 (count 2) · 1747 vk → `{ok:false, unsupported platform}` · 1748 tiktok без limit → count 10. Все success. Методика: нормализация сначала провалидирована локально в Node против реальных ответов API (харнесс `new Function('$input','$',jsCode)`).

⚠️ **Факт про кэш кредитов:** на `profile/videos` повторный ИДЕНТИЧНЫЙ запрос тем же handle через ~2 мин дал `credits_charged:1` (кэш НЕ сработал, в отличие от `tiktok/search/keyword`). Считай каждый вызов воркфлоу ≈ 1 кредит. Баланс после всех тестов SC-3: 55 кредитов.

## 16. SC-2: wf-creator-profile — профиль автора (13.08, LIVE)

**Назначение:** по `platform + handle` вернуть нормализованный профиль автора (подписчики, подписки, посты, bio, верификация, категория, аватар). Источник — ScrapeCreators (кред `...001`, httpHeaderAuth `x-api-key`). JSON: `~/factory/wf-creator-profile.json` (id `20000000-0000-4000-8000-000000000015`, 14 нод, active=1, webhook зарегистрирован). Ветка twitter/yt — дефенсивная, живьём НЕ тестирована (бюджет кредитов).

**Контракт:** `POST /webhook/factory/creator-profile` body `{platform, handle}` (platform: `instagram|tiktok|youtube|twitter`) →
```json
{"ok": true, "profile": {"platform": "tiktok", "handle": "khaby.lame", "nickname": "Khabane lame",
  "follower_count": 162634566, "following_count": 81, "post_count": 1348,
  "avg_engagement": 1971251, "bio": "Se vuoi ridere sei nel posto giusto...",
  "is_verified": true, "category": null, "profile_image_url": "https://..."},
 "meta": {"platform": "tiktok", "credits_charged": 1, "credits_remaining": 60}}
```
`avg_engagement`: TikTok = `statsV2.heart / videoCount` (средн. сердец на пост); IG = среднее лайков последних reels из `edge_felix_video_timeline.edges[]` (нет edges → null); YT/Twitter = null (профиль-ответ не содержит постов). Несуществующий аккаунт → `{"ok":false,"error":"account_deactivated","message":"Account doesn't exist",...}`; `success:false` → `{"ok":false,"error":"api_error"}`; неизвестная платформа → `{"ok":false,"error":"unsupported platform: vk"}`.

**Схема воркфлоу:** Webhook (`factory/creator-profile`, responseNode) → Switch platform (v3.4 rules, 4 правила + `options.fallbackOutput:"extra"`, out[0..3] → 4 ветки, out[4] → Error Respond) → 4× HTTP (GET, auth `genericCredentialType`+`httpHeaderAuth`, кред ...001) → 4× Code Tag (добавляет `{platform, handle}` к ответу — httpRequest НЕ прокидывает входной item) → Merge (append, 4 входа) → Code Normalize (единый JSON профиля + meta credits) → Respond (`={{ $json }}`). HTTP-параметры: IG `handle, trim=true`; TikTok `handle, trim=true`; YT `handle`; Twitter `handle`. Вход webhook читается защитно `($json.body && $json.body.X) || $json.X`.

**Проверенные структуры ответов API (13.08, живые curl с сервера):**
- TikTok `GET /v1/tiktok/profile?handle=&trim=` → `{success, credits_remaining, credits_charged, user{uniqueId, nickname, avatarLarger, avatarMedium, signature (bio), verified, privateAccount, ...}, stats{followerCount, followingCount, videoCount, heart...}, statsV2{... строки}, itemList[]}`. ⚠️ `stats.heart` переполняет int32 (отрицательное) — точные значения брать из `statsV2` (строки). Несуществующий аккаунт: `{success:true, account_deactivated:true, message:"Account doesn't exist"}` (успешный HTTP, флаг в теле).
- Instagram `GET /v1/instagram/profile?handle=&trim=` → `{success, credits_*, data{user{username, full_name, biography, edge_followed_by{count}, edge_follow{count}, edge_owner_to_timeline_media{count}|edge_felix_video_timeline{count, edges[{node{edge_media_preview_like|edge_liked_by{count}}}]}, is_verified, category_name (часто null), profile_pic_url_hd|profile_pic_url}}}`. post_count предпочитает `edge_owner_to_timeline_media` (все посты), fallback на `edge_felix_video_timeline` (видео).
- YouTube `GET /v1/youtube/channel?handle=` / Twitter `GET /v1/twitter/profile?handle=` — не тестированы живьём; маппинг дефенсивный по openapi: channel `{title, subscriberCount, videoCount, description, isVerified, thumbnails[0].url}` / profile `{name, followers_count, friends_count, statuses_count, verified, profile_image_url_https}`. Проверены на синтетике локальным Node-харнессом.

**Тест (13.08, live):** exec 1740 tiktok `khaby.lame` → ok:true (профиль) · 1743 instagram `nasa` → ok:true (104M подписчиков, post_count 4878, avg_engagement 323212) · 1744 tiktok повтор (тот же handle) → ok:true · 1745 vk → `{"ok":false,"error":"unsupported platform: vk"}`. Все success, HTTP 200. Ветвление подтверждено `dump-execution.js` (exec 1740): Switch → out[1] (tiktok) → HTTP TikTok → Tag TikTok → Merge → Normalize → Respond, lastNodeExecuted=Respond, error none.

⚠️ **Факт про кэш кредитов (подтверждён и для profile):** два ИДЕНТИЧНЫХ curl-запроса подряд (1 сек) на `/v1/tiktok/profile?handle=khaby.lame&trim=true` дали `credits_charged:1` ОБА — кэш SC на profile-эндпоинтах НЕ применяется (то же для `profile/videos` по SC-3; кэшируется только `search/keyword`). Считай каждый вызов воркфлоу ≈ 1 кредит, повторы бесплатными НЕ будут. Расход SC-2: 3 уникальных curl (cnc.rocks → account_deactivated, nasa, khaby.lame) + 6 повторов = 9 кредитов. Баланс после тестов SC-2/SC-3: **53 кредита** (`GET /v1/account/credit-balance`, бесплатный).

## 15. SC-1: wf-creators-search (13.08) — DONE
- webhook POST `/webhook/factory/creators-search` {query, platforms[]}
- 17 нод: Webhook → 3× Switch (instagram/youtube/tiktok) → 3× HTTP scrapecreators (кред ...001, retry 3x) → Normalize → Merge → Top-N (10) → db-bridge upsert competitors (INSERT OR IGNORE, client_id=активный клиент) → Respond
- Эндпоинты: /v1/instagram/search/profiles?query=&cursor=; /v1/youtube/search?query=&type=channels; /v1/tiktok/search/users?query=&trim=true
- Live-тест: `{"ok":true,"count":10,"inserted":10}` (query=robotics, tiktok; 10 авторов в competitors, client_id=1)
- ПИТФОЛЛ: Python f-string + `{{ }}` несовместимы (скобка теряется → Switch в fallback); правки активного воркфлоу — прямым UPDATE БД, формат `={{ }}`

## 16. SC-2: wf-creator-profile (13.08) — DONE
- webhook POST `/webhook/factory/creator-profile` {platform, handle}; id `...016`
- 14 нод: Webhook → Switch platform (4 правила + fallback→Error Respond) → 4× HTTP (IG/TikTok/YT/Twitter) → Tag → Merge → Normalize → Respond
- Эндпоинты: /v1/instagram/profile?handle=&trim=; /v1/tiktok/profile?handle=; /v1/youtube/channel?handle=; /v1/twitter/profile?handle=
- Live-тест: tiktok khaby.lame → {ok:true, profile{follower_count:162633484, avg_engagement:1971025, is_verified:true}}; vk → {ok:false, error:"unsupported platform: vk"}
- ⚠️ stats.heart TikTok переполняет int32 — точные значения из statsV2; account_deactivated = HTTP 200 + флаг в теле


## 17. SC-4: wf-audience — демография аудитории автора (13.08, LIVE; финальный демо-тест BLOCKED на кредитах)

**Назначение:** по `platform + handle` вернуть нормализованную демографию аудитории автора. Источник — ScrapeCreators (кред `...001`, httpHeaderAuth `x-api-key`). JSON: `~/factory/workflows/wf-audience.json` (id `20000000-0000-4000-8000-000000000017`, 6 нод, active=1, webhook зарегистрирован). Аудитория в SC есть ТОЛЬКО у TikTok — остальные платформы отвечают ошибкой.

**Контракт:** `POST /webhook/factory/audience` body `{platform, handle}` (поддерживается только `platform=tiktok`) →
```json
{"ok": true, "audience": {"platform": "tiktok", "handle": "khaby.lame",
  "gender": [], "age_ranges": [],
  "top_countries": [{"country": "Pakistan", "percent": 18.13}, ...]}}
```
- Неподдерживаемая/отсутствующая платформа → `{"ok":false,"error":"unsupported platform: audience data available only for tiktok"}` (Switch fallback, API не дёргается, кредиты не тратятся).
- `success:false` в ответе API → `{"ok":false,"error":"api_error","message":...}`.

**Реальная структура ответа API (13.08, живые curl):** `GET /v1/tiktok/user/audience?handle=` → `{success, credits_remaining, credits_charged, audienceLocations:[{country, countryCode, count, percentage:"18.13%"}]}` (108 стран, отсортированы по count DESC). ⚠️ **ПОЛ И ВОЗРАСТ В ОТВЕТЕ ОТСУТСТВУЮТ** — эндпоинт отдаёт только гео (`audienceLocations`); поэтому `gender: []` и `age_ranges: []` всегда пустые (нормализатор по контракту возвращает их пустыми массивами, а не опускает).

**Схема воркфлоу (6 нод):** Webhook (`factory/audience`, responseNode) → Switch platform (v3.4 rules, 1 правило `tiktok` + `options.fallbackOutput:"extra"`: out[0] → tiktok-ветка, out[1] → Error Respond) → HTTP TikTok Audience (GET `/v1/tiktok/user/audience`, query `handle` через защитный паттерн `($json.body && $json.body.handle) || $json.handle`, auth `genericCredentialType`+`httpHeaderAuth` кред ...001, retry 3x: `options{retryOnFail:true, maxTries:3, timeout:30000}`) → Code Normalize (единый JSON: `{ok, audience{platform, handle, gender[], age_ranges[], top_countries[{country, percent}]}}`; `percent` = `parseFloat(percentage.replace('%',''))`; отсутствие `audienceLocations` → пустой массив; `success:false` → api_error) → Respond (`={{ $json }}`). Ошибка платформы → второй Respond с фиксированным JSON (без выражения). jsCode нормализатора провалидирован локально в Node-харнессе против реального ответа API ДО импорта (108 стран, percent-число, пустые массивы, api_error).

**⚠️ ЦЕНА ЭНДПОИНТА: 26 КРЕДИТОВ ЗА ЗАПРОС (НЕ 1!)** — проверил по балансу: два curl подряд `khaby.lame` → `credits_remaining` 51→25→-1 при `credits_charged:26` каждый. Это самый дорогой эндпоинт SC из всех использованных (profile/videos/search = 1). Кэша нет (как и на других profile-эндпоинтах). **На момент тикета баланс SC = -1** (`GET /v1/account/credit-balance` → `{"creditCount":-1, "message":"You have -1 credits remaining."}`) — API отдаёт `HTTP 402 {"success":false,"message":"Looks like you're out of credits..."}` при запросе с балансом ≤ 0 (долг не разрешён, в отличие от положительного баланса, который уходит в минус после списания).

**Тест (13.08, live):**
- exec 1782/1783 — `{"platform":"tiktok","handle":"khaby.lame"}`: Webhook → Switch out[0] (tiktok) → HTTP TikTok Audience с верными URL/qs/creds (подтверждено error-контекстом: `uri=https://api.scrapecreators.com/v1/tiktok/user/audience`, `qs.handle=khaby.lame`, кред ...001 приложен) → **HTTP 402 out of credits** (баланс -1). Ошибка НЕ в воркфлоу: запрос ушёл правильно, API отказал из-за нулевого баланса; кредиты не списаны (осталось -1).
- exec 1786 (`platform=vk`) / 1787 (без `platform`) — success: `{"ok":false,"error":"unsupported platform: audience data available only for tiktok"}` — fallback-ветка работает.
- **Статус: BLOCKED только на финальном демо-тесте демографии** — нужен положительный баланс (≥1 кредит; один запрос стоит 26). После топ-апа: `curl -X POST http://localhost:5678/webhook/factory/audience -H 'Content-Type: application/json' -d '{"platform":"tiktok","handle":"khaby.lame"}'` → `{ok:true, audience{top_countries[...]}}` (108 стран), повтор тем же handle → ещё -26.

## 17. SC-4: wf-audience (13.08) — BLOCKED (кредиты SC = -1)
- webhook POST `/webhook/factory/audience` {platform, handle}; id `...017`, 6 нод, active=1
- Эндпоинт: /v1/tiktok/user/audience?handle= (ТОЛЬКО tiktok; пол/возраст в ответе ОТСУТСТВУЮТ — только audienceLocations)
- ⚠️ Стоит 26 кредитов/запрос (не 1!) — самый дорогой эндпоинт SC
- Live-тест tiktok: exec 1782/1783 → HTTP 402 out of credits (запрос ушёл верно); fallback: exec 1786/1787 success → {ok:false, unsupported platform...}
- Демо-тест демографии возможен после пополнения баланса

## 18. PM-1: wf-publish расширен под все платформы (13.08) — DONE
- wf-publish (id ...010) переработан: 17 нод, вход {platforms[], content, title?, link?, file_ids?, publication_type?} → генерация details[] под все платформы
- publication_type enum (из SDK): POST=1, STORY=2, REELS_SHORTS_CLIPS=4; publication_status=5 (PENDING_PUBLICATION) — подтверждён живым API
- Платформы: instagram/youtube/tiktok/threads/x/telegram (были) + pinterest/rutube/ok/discord/reddit/bluesky/tumblr/mastodon/linkedin/facebook (добавлены)
- ⚠️ НАЙДЕН БАГ старого кода: accountMap {instagram:101, youtube:102, tiktok:103, ...} — tiktok реально 106 (103 неверный); account_ids теперь из актуального маппинга
- Live-тест: тело публикации формируется корректно (dump exec 1795: project_id 355928, account_ids [101,102,106], publication_status 5, details[] с publication_type 4 и платформенными полями); POST → 422 «аккаунт не подключён к проекту» — ожидаемо (F-3 за заказчиком, аккаунтов postmypost нет)

## 18a. PM-2: Stories в wf-publish (13.08) — DONE
- Вход воркфлоу расширен параметром publish_type (post|reels|story) — маппинг platform+publish_type → publication_type в Code-ноде «Code build details» (мини-правка, PM-1 логика по умолчанию не тронута)
- Маппинг: publish_type='story' → publication_type=2 (STORY) для instagram и facebook; 'reels' → 4 (REELS_SHORTS_CLIPS); 'post' → 1 (POST); приоритет publish_type над publication_type из запроса; для остальных платформ story → прежний дефолт (1 или 4 по file_ids)
- Правка применена прямым UPDATE БД (обе строки workflow_history: активная baa89f73 + черновик 4b4276ca, и workflow_entity) + docker restart factory-n8n — воркфлоу остался активным, webhook factory/publish жив (без UI Publish)
- Тесты (ожидаемая ошибка «аккаунт не подключён» — ОК, F-3 за заказчиком):
  - exec 1817 {platforms:[instagram,facebook], content:'story test', publish_type:'story', file_ids:[1]} → details[]: publication_type=2 для instagram И facebook, content+file_ids на месте
  - exec 1820 {platforms:[instagram], publish_type:'reels', file_ids:[1]} → details[]: publication_type=4 + instagram_share_to_feed=true
  - ⚠️ publish_type='reels' БЕЗ file_ids уходит в upload-ветку (PM-1 поведение: upload/init реально скачивает файл по generation_id) — для проверки details[] слать file_ids
- Экспорт: ~/factory/workflows/wf-publish.json обновлён (17 нод, pubTypeReq в jsCode)

## 19. SC-5: wf-transcripts-comments (13.08) — workflow DONE, live-данные BLOCKED (SC баланс -1)
- id ...018, 27 нод, ДВА webhook: POST /webhook/factory/transcript {url} и POST /webhook/factory/comments {url, limit}
- Определение платформы из url (tiktok/youtube/instagram) через Switch; IG-транскрипт → {ok:false, error:'instagram transcript not supported'}
- Эндпоинты: /v1/tiktok/video/transcript?url=&language=; /v1/youtube/video/transcript?url=; /v1/tiktok/video/comments?url=&trim=; /v2/instagram/post/comments?url=&include_replies=; /v1/youtube/video/comments?url=
- Тесты: exec 1808-1810 success — логика и ветвление работают; API вернул 402 «out of credits» (баланс scrapecreators -1, сожжён SC-4: /v1/tiktok/user/audience = 26 кредитов/запрос!)
- ⚠️ БЮДЖЕТ: scrapecreators на нуле — нужен топ-ап; audience — самый дорогой эндпоинт (26 кред), транскрипты/комментарии — дешевле

## 20. CR-2: wf-creatify-text — AI Scripts (Creatify) как альтернатива Hermes-LLM для текстов (13.08) — DONE
- webhook POST `/webhook/factory/script` {topic, description?, language?='ru', target_audience?, video_length?=30}; id `...020`, 17 нод, active=1
- JSON: `~/factory/workflows/wf-creatify-text.json`. Эндпоинт: `POST /api/ai_scripts/` (1 кредит, СИНХРОННЫЙ — status=done + generated_scripts[] приходят сразу; webhook_url в схеме НЕТ — не шлём)
- Схема: Webhook → Normalize input (дефолты: language=ru, video_length=30; пустой topic → {ok:false,error:'topic_required'}) → IF topic ok → HTTP credits (GET /api/remaining_credits/, заголовки keypair $env, retry 3x) → Code balance → IF low credits (balance<50 → {ok:false,error:'low_credits',balance}) → HTTP ai_scripts (POST, body {title,description,language,target_audience,video_length}, заголовки X-API-ID/X-API-KEY из $env keypair, retry 3x, timeout 120s) → Normalize (извлекает script_id/status/text=generated_scripts[0].paragraphs; status≠done → {ok:false,error:'generation_not_ready'}) → IF scripts ok → db-bridge: INSERT topics (cycle_date=date('now')) → INSERT scripts (topic_id=MAX(id) по title, full_text, target_length, format_tag='creatify', status) → Finalize → Respond {ok:true, script_id (creatify uuid), db_script_id, text, status, credits_used, scripts_count}
- **Реальное тело запроса** (проверено curl + воркфлоу): `{"title":"промышленная робототехника","description":"промышленная робототехника","language":"ru","target_audience":"","video_length":30}` — обязательны title+description ИЛИ url (из openapi: title/description/url writeOnly, language enum, video_length enum 15|30|45|60, script_styles max 5 опц.)
- **Реальный ответ 201**: `{id:<uuid>, status:"done", generated_scripts:[{paragraphs:"<полный текст>", script_name:"V2Writer", script_style:"...", title:"..."} x5], credits_used:1, failed_reason:null, product{...}, ...}`
- **Live-тест (13.08)**: exec 1832 success → `{"ok":true,"script_id":"c49d6903-1640-4d9e-a8e7-1b6774fac06c","db_script_id":4,"text":"Вы когда-нибудь задумывались, что происходит за закрытыми дверями современных заводов?...","status":"done","credits_used":1,"scripts_count":5}`; scripts.id=4 (format_tag='creatify', status='done'), topics.id=7 ('промышленная робототехника', pending) в factory.db. Потрачено: **2 кредита** (1 валидационный curl + 1 live-тест), баланс 497→495.
- ПИТФОЛЛ: IF 2.3 с `typeValidation:"strict"` + number-оператор требует rightValue ЧИСЛОМ, не строкой (`"1"` → `Wrong type: '1' is a string but was expecting a number`, exec error, webhook ACK 200 пустым телом). Фикс: rightValue → число (1/50) прямым UPDATE БД + restart; эталон wf-creatify-submit (gte "50") работает, потому что там нет equals — для equals строка НЕ конвертируется.
- text_generator (SSE-streaming) не использован — ai_scripts синхронный и покрывает задачу (1 кредит); при необходимости SSE — отдельный тикет.

## 20. CR-1: wf-creatify-avatar — Custom Avatar BYOA (13.08) — DONE
- Таблица custom_avatars СОЗДАНА (factory.db): id, client_id, persona_id UNIQUE, creator_name, gender, status, is_active, created_at, updated_at
- Воркфлоу ...019, 35 нод, активен: (a) POST /webhook/factory/avatar-upload {video_url, creator_name, gender, client_id} → Validate → POST /api/personas/ → INSERT custom_avatars status=pending_moderation → {ok:true, persona_id, status}; (b) POST /webhook/factory/my-avatars {client_id} → список; (c) cron 0 * * * * модерация: GET /api/personas/{id} → approve/reject + tg-alert
- Тело PersonaCreate (сверено с докой): {lipsync_input: url mp4, creator_name (обяз), gender m|f|nb, video_scene?, keywords?, webhook_url?} → 201 {id, process_status, is_active}
- Live-тест: avatar-upload → persona ad747d62 реально создан в Creatify, строка в custom_avatars (id 1, pending_moderation), my-avatars отдаёт список. Потрачено кредитов: 0 (создание аватара бесплатно; лимит 3 аватара, GET /api/personas_v2/count/)
- ⚠️ ПИТФОЛЛ: httpRequest typeVersion 2 НЕ доставляет заголовки keypair (401 «Authentication credentials were not provided») — ноды ДОЛЖНЫ быть typeVersion 4.5 (фикс: 9 нод подняты); contentType:"json" обязателен для POST
- ⚠️ Видео для BYOA: 15-300 сек, URL должен быть доступен серверам Creatify (test-videos.co.uk/googleapis НЕ качаются; download.samplelib.com/mp4/sample-30s.mp4 — работает)


## 21. CR-3: wf-creatify-asset — Asset/Image Generator (Creatify) (13.08) — DONE
- webhook POST `/webhook/factory/asset` {prompt, type?, count?=1}; id `20000000-0000-4000-8000-000000000021`, 7 нод, active=1
- JSON: `~/factory/workflows/wf-creatify-asset.json`. Эндпоинт: `POST /api/asset_generator/` (НЕ /api/ai_generation/ — проверено по докам + живому API)
- **Реальное тело запроса** (сверено с https://docs.creatify.ai/api-reference/ai-generation/post-ai-generation.md + живьём): `{"model_name":"<модель>","input_params":{<параметры модели>},"webhook_url"?:...}` — обязательны model_name + input_params (prompt внутри input_params, НЕ на верхнем уровне). Каталог моделей: `GET /api/asset_generator/schemas/` (87 моделей; text_to_image: flux-2-pro/flux-pro/kontext/text-to-image/nano-banana-2-lite/wan2.7-image = 1 кредит, gpt-image-1.5 = 3 кред/шт; ⚠️ `bytedance/seedream/v4/text-to-image` из доки в живом каталоге ОТСУТСТВУЕТ — POST даёт 400 `["AI model not found"]`)
- **Реальный ответ 201**: `{id:<uuid>, model_name, gen_type:"image", status:"initializing", failed_reason:"", assets:[], output_nums, input_params{...}, credits_used:0, created_at, updated_at}` — генерация АСИНХРОННАЯ; статус дёргать `GET /api/asset_generator/{id}/` → status enum initializing|generating|done|failed; при done: `assets:[{id, type:"image", url:"https://cdn.creatify.ai/ai_tools_flow/c2pa/...jpg", thumbnail_url, name}]` (⚠️ assets — МАССИВ объектов, не строка как в доке), `credits_used:1`
- Схема: Webhook → Code validate (prompt обязателен → иначе {ok:false,error:'prompt обязателен'}; type→model_name дефолт `flux-pro/kontext/text-to-image`; count→num_images дефолт 1, clamp 1..4; payload собирается целиком в Code) → Switch (ok===true, fallbackOutput extra: out[0]→HTTP, out[1]→Respond error) → HTTP Asset (POST, `authentication:"none"` + sendHeaders keypair `{{ $env.CREATIFY_API_ID/KEY }}`, contentType json, `jsonBody: "={{ $json.payload }}"`, options{timeout:120000, retryOnFail:true, maxTries:3}) → Code Normalize ({ok, asset_id, url: assets[0].url, status, credits_used, gen_type, failed_reason, raw}) → Respond ok {ok:true, asset_id, url, status, ...}
- **Стоимость: 1 кредит за 1 изображение** (flux-pro/kontext/text-to-image; × num_images при count>1). Баланс creatify 495→490 за тикет (5 кред: 1 прямой flux-тест + 1 live-тест через воркфлоу + 3 неизвестных списания — вероятно отложенные за предыдущие генерации; seedream-проверка 400 бесплатна)
- **Live-тест (13.08)**: exec 1875 success → `{"ok":true,"asset_id":"14164c15-a73a-4a89-a737-c22daeb8fe11","url":null,"status":"initializing",...}` (url пуст т.к. генерация асинхронная) → через ~6с GET: status done, url=`https://cdn.creatify.ai/ai_tools_flow/c2pa/20260813/72ffda9769024b3281b0e8ed6836ed29.jpg` (HTTP 200, image/jpeg, 63KB). Валидационная ветка: пустой prompt → {ok:false, error:'prompt обязателен'} без списания.
- ⚠️ ПИТФОЛЛ: jsonBody-выражение с ВЛОЖЕННЫМИ фигурными скобками (`={{ {model_name:..., input_params: {prompt:...}} }}`) → `Error: invalid syntax` (n8n expression parser обрывается на внутренних `}}`, exec error, webhook ACK 200 пустым телом). Фикс: собирать payload в Code-ноде, jsonBody = `={{ $json.payload }}`.
- Доки: llms.txt индекс постраничный; полные OpenAPI-блоки — в .md-страницах api-reference/ai-generation/*; openapi.json → 404.

## 22. CR-4: wf-creatify-adclone — Ad Clone (Creatify) (13.08) — DONE (live-тест: задача принята, 201)
- webhook POST `/webhook/factory/adclone` {source_video_url, link?, brand_assets?, aspect_ratio?=9x16, language?, webhook_url?}; id `20000000-0000-4000-8000-000000000022`, 15 нод, active=1
- JSON: `~/factory/workflows/wf-creatify-adclone.json`. Эндпоинт: `POST /api/ads_clone/` (НЕ `/api/ad_clones/` — сверено с https://docs.creatify.ai/api-reference/ad-clone/post-ad-clone.md, схема `APIAdsCloneFlow`)
- **Реальное тело запроса** (схема APIAdsCloneFlow): `{link: <uuid Link>, video_url: <url reference-видео>, aspect_ratio: 9x16|16x9|1x1 (default 9x16), language?: <код языка, null = оригинал>, webhook_url?: <uri, maxLength 200>}` — **обязательны link + video_url**. Полей `source_video_url`/`brand_assets` в схеме НЕТ: воркфлоу маппит source_video_url→video_url, а brand_assets (строка-URL или {url}) → url для автосоздаваемого Link
- **Реальный ответ 201**: `{id:<uuid>, created_at, updated_at, link, video_url, aspect_ratio, language, webhook_url, video_output:null, credits_used:0, media_job:<uuid>, status:"running"}` — генерация АСИНХРОННАЯ; статус: `GET /api/ads_clone/{id}/` → status enum pending|in_queue|running|failed|done|rejected; при done: `video_output` (URL готового видео)
- **Схема воркфлоу**: Webhook → Code Validate (source_video_url обязателен http(s); link — UUID; aspect_ratio enum; brand_assets→brandUrl default https://robotec.ru) → IF valid → HTTP credits (GET /api/remaining_credits/) → Code balance → IF low credits (balance<20 → {ok:false,error:'low_credits',balance}) → IF link (есть → Build body; нет → HTTP POST /api/links/ {url: brandUrl, aspect_ratio, video_length:30, language} → Code Extract link) → Code Build body → HTTP POST /api/ads_clone/ (`authentication:"none"` + sendHeaders keypair `{{ $env.CREATIFY_API_ID/KEY }}`, contentType json, `jsonBody: "={{ $json.body }}"`, options{timeout:120000, retryOnFail:true, maxTries:3}) → Code Normalize → Respond {ok:true, ad_clone_id, status, credits_used, video_output, media_job, link}
- ⚠️ **ПИТФОЛЛ (критичный): сущность Link у Creatify = ВЕРХНИЙ id ответа POST /api/links/** (`{id: <link-uuid>, link: {id: <inner-uuid>, ...}}`) — вложенный `link.id` НЕВАЛИДЕН: `GET /api/links/<inner>/` → 404 "No Link matches the given query", `POST /api/ads_clone/` с ним → 400 `{"link":["Invalid link ID"]}` (фикс: Extract link берёт `d.id || (d.link && d.link.id)`). ⚠️ Ставит под вопрос `link.id` в wf-creatify-submit (link_to_videos) — там link_id для генерации стоит перепроверить на верхний id
- **Live-тест (13.08)**: exec 1876 success → `{"ok":true,"ad_clone_id":"1098a3b5-f8a4-4292-961e-402ae5b90891","status":"running","credits_used":0,"media_job":"11036cd8-0566-4810-9f15-a10106deb4f3","link":"91e44635-f95c-4f32-97d6-85c2eb15858d"}`; GET задачи: status=running (на момент отчёта), credits_used=84, video_url = reference на cdn.creatify.ai. Валидационная ветка (0 кредитов): пустой source_video_url → `{ok:false,error:'source_video_url обязателен и должен быть http(s) URL'}`
- ⚠️ **СТОИМОСТЬ: 84 кредита за генерацию** (НЕ 12, как оценивалось по скиллу ранее; сверено: credits_used задачи = 84, баланс 490→406). Списание поэтапное (~1 при старте + остаток при обработке). Потрачено за тикет: **86 кредитов** (link#1=1 + старт live-теста=1 + генерация=84), баланс creatify 492→406. Первый POST (exec 1873) упал 400 «Invalid link ID» — списал только 1 кред за link. Правило «≤15 кред → 1 реальный POST» нарушено фактически (запущен по устаревшей оценке 12) — для прод-использования закладывать **84 кред/задача**
- ⚠️ ПИТФОЛЛ: webhook-нода БЕЗ поля `webhookId` при импорте → webhookPath = `{workflowId}/webhook/{path}` (короткий путь 404); фикс: `"webhookId": "cr4-adclone"` в ноде → путь `factory/adclone`
- Тестовое видео: `https://samplelib.com/mp4/sample-30s.mp4` (прямой 200, video/mp4 21.6MB; download.samplelib.com отдаёт 301 — Creatify скачал по прямому URL)

## 21. PM-3: caption-adapter + адаптация caption в wf-publish (13.08) — DONE
- Скилл caption-adapter СОЗДАН: ~/.hermes/skills/content-factory/caption-adapter/SKILL.md (правила для 17 платформ; вывод строго <CAPTION>...</CAPTION>)
- hermes-bridge (server.py) расширен: ALLOWED_SKILLS += caption-adapter, для него --reasoning none (чистый текст); systemd hermes-bridge.service
- wf-publish: 26 нод. Цепочка: Code build details → Switch adapt captions (≤4 платформ) → zip captions → Split In Batches (loop) → Build prompt → HTTP bridge adapt (host.docker.internal:8642/ask, X-BRIDGE-TOKEN: $env.HERMES_BRIDGE_TOKEN, timeout 300s) → extract adapted (<CAPTION> regex, fallback = исходный) → merge adapted → Merge → Switch mock publication. >4 платформ — без адаптации (NoOp skip captions)
- E2E-тест (exec 1895): platforms [x, linkedin, telegram] → 3 РАЗНЫХ caption (x: лаконичный ≤280; linkedin: деловой + #ПромышленныеРоботы #KUKA #Автоматизация; telegram: с эмодзи 🤖🔔); публикация → «аккаунт не подключён» (ожидаемо, F-3)
- ПИТФОЛЛ: Code-ноды НЕ умеют HTTP (запрещено исходником) — bridge вызывается HTTP-нодой в цикле Split In Batches
## 22. CR-5: wf-creatify-shorts — AI Shorts (Creatify: текст → короткие ролики) (13.08) — DONE
- **Воркфлоу**: id `20000000-0000-4000-8000-000000000023`, 12 нод, webhook `POST /webhook/factory/shorts` (webhookId `cr5-shorts`), active=1. JSON: `~/factory/workflows/wf-creatify-shorts.json`.
- **Контракт POST /api/ai_shorts/** (сверен с https://docs.creatify.ai/api-reference/ai-shorts/post-ai-shorts.md, схема `ArtsyVideoFlowCreate`): ОБЯЗАТЕЛЬНЫЕ поля — `script` (string, текст→видео), `aspect_ratio` (enum: 9x16|16x9|1x1), `style` (enum: "4K realistic"|"3D"|"Cinematic"|"Cartoonish"|"Line art"|"Pixel art"|"Mysterious"|"Steam punk"|"Collage"|"Kawaii"). Опционально: `accent` (uuid), `caption_setting` (объект), `background_music_url`, `background_music_volume`, `voiceover_volume`, `webhook_url`. Поля `source_video_url`/`language`/`count` в схеме ОТСУТСТВУЮТ (длинное видео → короткие = это `/api/ai_editing/`, не ai_shorts). Auth: X-API-ID + X-API-KEY. Стоимость: 5 кред/30с, списание ОТЛОЖЕННОЕ (при POST credits_used=0, фактически при генерации).
- **Ответ 201** (`ArtsyVideoFlow`): `{id, status (pending|in_queue|running|failed|done|rejected), failed_reason, video_output (URL готового видео), preview, editor_url, progress, credits_used, duration, created_at, updated_at, name, script, aspect_ratio, style, media_job, permission_type, user, workspace}`.
- **Схема воркфлоу**: Webhook (`factory/shorts`) → Code validate (принимает `{source_video_url?, topic?, max_count?=5, language?='ru', script?, aspect_ratio?='9x16', style?='Cinematic', webhook_url?}`; script = body.script || body.topic — обязателен; source_video_url/ max_count/language принимаются, но в payload НЕ передаются — нет в схеме; max_count clamp 1..10) → Switch valid (boolean equals true + fallbackOutput extra; out[0]→HTTP credits, out[1]→Respond error `{ok:false,error}`) → HTTP credits (GET /api/remaining_credits/, keypair $env, timeout 15s) → Code balance → Switch balance (out[0]→Build payload, out[1]→Respond `{ok:false,error:'low_credits',balance}` при balance<30) → Code Build payload (payload `{script, aspect_ratio, style[, webhook_url]}` целиком в Code!) → HTTP ai_shorts (POST, `authentication:"none"` + sendHeaders keypair `{{ $env.CREATIFY_API_ID/KEY }}`, contentType json, `jsonBody: "={{ $json.payload }}"`, options `{timeout:120000, retryOnFail:true, maxTries:3, waitBetweenTries:5000}`) → Code Normalize (`{ok:true, shorts_id, status, items:[{id,status,video_output,preview,editor_url,progress,credits_used,duration,failed_reason,created_at,updated_at}], raw}`) → Respond ok `={{ $('Code Normalize').first().json }}`
- **Live-тест (13.08)**: exec 1904 success → `{"ok":true,"shorts_id":"80872351-35a5-4d6d-986c-58403d708873","status":"pending","items":[...]}` (script «Промышленные роботы: 5 фактов, которые изменят заводы», aspect_ratio 9x16, style Cinematic; created_from_api:true; media_job 66ddc99b...). Валидационная ветка (0 кредитов): `{}` → `{"ok":false,"error":"script или topic обязателен"}` (exec 1903). Баланс creatify 406→406 на момент POST (отложенное списание ~5 кред при генерации; допрашивать `GET /api/ai_shorts/{id}/`). Потрачено за тикет: 0 кред при POST.
- **Питфоллы применённые**: webhookId в ноде обязателен (`cr5-shorts`); httpRequest typeVersion 4.5; jsonBody = `{{ $json.payload }}` (payload в Code-ноде — вложенные `{}` в выражении = invalid syntax); Switch v3.4 с fallbackOutput extra; защитный паттерн `($json.body && $json.body) || $json`.

## 23. CR-6: wf-creatify-product — Product-to-video (Creatify: изображение товара → ролик) (13.08) — DONE
- **Воркфлоу**: id `20000000-0000-4000-8000-000000000024`, 14 нод, webhook `POST /webhook/factory/product` (webhookId `cr6-product`), active=1. JSON: `~/factory/workflows/wf-creatify-product.json`.
- **Контракт** (сверен с докой https://docs.creatify.ai/api-reference/product_to_video/post-apiproduct_to_videos-gen_image.md и ...-gen_video.md): ⚠️ РЕАЛЬНЫЙ контракт ОТЛИЧАЕТСЯ от тикета:
  - `POST /api/product_to_videos/gen_image/` (1 кредит): тело `{product_url (обязателен, прямой URL изображения PNG/JPG/WEBP), type?=product_anyshot, aspect_ratio?=16x9 (9x16|16x9|1x1), image_prompt?, override_avatar?, product_showcase_url?, webhook_url?}`. Поля `image_url`/`target_audience`/`language` в схеме ОТСУТСТВУЮТ. Ответ: `{id, status (initializing|image_generating|image_generated|...), generated_photo_url, ...}` — АСИНХРОННЫЙ.
  - `POST /api/product_to_videos/{id}/gen_video/` (3 кредита): **path-параметр id задачи** (НЕ приём URL видео!), тело `{motion_style? (talking|display), video_prompt?, webhook_url?}`. Ответ: `{id, status, generated_video_url, ...}`.
  - Полный цикл «изображение → ролик» = 2 вызова: gen_image → получить id → gen_video/{id}. Цена суммарно ~4 кредита.
- **Схема воркфлоу**: Webhook (`factory/product`) → Code validate (принимает `{image_url?, product_video_id?, video_url?, target_audience?, language?='ru', aspect_ratio?='16x9', image_prompt?, video_prompt?, motion_style?, webhook_url?}`; **обязателен image_url ИЛИ product_video_id**; video_url как вход НЕ поддерживается реальным контрактом → `{ok:false,error:'video_url не поддерживается...: gen_video принимает id задачи (product_video_id)'}`; image_url должен быть http(s); mode = gen_image | gen_video) → HTTP credits (GET /api/remaining_credits/, keypair `{{ $env.CREATIFY_API_ID/KEY }}`) → Code credit check (⚠️ HTTP Request НЕ прокидывает входной item — валидацию читает кросс-нод-ссылкой `$('Code validate').first().json`; balance<20 → `{ok:false,error:'low_credits',balance}`) → Switch mode (v3.4, 2 правила + fallbackOutput extra: out[0]→gen_image, out[1]→gen_video, out[2]→Respond error) → [gen_image: Code Build payload (`{product_url, aspect_ratio[, image_prompt, webhook_url]}`) → HTTP gen_image (POST, keypair $env, contentType json, `jsonBody: "={{ $json.payload }}"`, options `{timeout:120000, retryOnFail:true, maxTries:3, waitBetweenTries:5000}`) → Normalize image (`{ok:true, product_video_id, status, generated_photo_url, failed_reason, credits_used, raw}`) → Respond ok image] | [gen_video: Code Build payload (url `.../{id}/gen_video/`, `{motion_style?, video_prompt?, webhook_url?}`) → HTTP gen_video → Normalize video (`{ok:true, product_video_id, status, generated_photo_url, generated_video_url, ...}`) → Respond ok video]
- **Live-тест (13.08)**: exec 1913 (gen_image) success → `{"ok":true,"product_video_id":"15c67c47-96cd-49ae-b6d2-f60a6c981e3a","status":"initializing",...}` (image_url = https://picsum.photos/800/1200, Creatify сам скачал: product_url → cdn.creatify.ai/images/...jpg) → через ~30с GET задачи: `image_generated`, generated_photo_url=`https://cdn.creatify.ai/user/3554582/2026-08-13/f0d12e38.jpg`. Затем exec (gen_video по product_video_id) success → `{"ok":true,"product_video_id":"15c67c47-...","status":"video_generating",...}` → через ~2 мин: **`video_generated`, generated_video_url=`https://cdn.creatify.ai/product_to_videos/3554582/15c67c47-96cd-49ae-b6d2-f60a6c981e3a/20260813/9097d932.mp4`**. Полный цикл image→photo→video ЗЕЛЁНЫЙ.
- Валидационные ветки (0 кредитов): `{}` → `{ok:false,error:'image_url или product_video_id обязателен'}`; `{video_url:...}` → контракт-ошибка; `{image_url:'ftp://bad'}` → http(s)-ошибка. Баланс creatify за тикет: 406→406 на момент валидаций; при POST gen_image баланс 406→399 (−7: 1 кред gen_image + отложенные списания других задач/параллельных тикетов), после gen_video → 387→379 (отложенное списание gen_video + параллельные агенты); по прайсу доки: gen_image=1, gen_video=3.
- **Питфоллы применённые**: webhookId в ноде обязателен (`cr6-product`); httpRequest typeVersion 4.5; jsonBody = `{{ $json.payload }}` (payload в Code-ноде); Switch v3.4 с fallbackOutput extra; защитный паттерн `($json.body && $json.body) || $json`; **HTTP Request НЕ прокидывает входной item — кросс-нод-ссылка `$('Code validate').first().json` в Code credit check** (без неё ошибки валидации терялись и пользователь получал проходной баланс вместо `{ok:false,...}`); node:sqlite: параметры SQL — в `.get()/.all()`, НЕ в `prepare()`.

## 23. CR-7: wf-creatify-banner — IAB-баннеры + Inspiration (Creatify) (13.08) — DONE

- **Воркфлоу**: id `20000000-0000-4000-8000-000000000025`, 22 ноды, ДВА webhook-триггера, active=1 (publish:workflow CLI + docker restart), webhook_entity зарегистрирован. JSON: `~/factory/workflows/wf-creatify-banner.json`.

### Контракт POST /api/iab_images/ (сверен с https://docs.creatify.ai/api-reference/iab-images/post-iab-images.md + живьём)
- Тело: `{"image": "<url png|jpg|jpeg|webp>", "webhook_url"?: "<uri>"}` — поле называется **`image`** (НЕ image_url); параметра размеров/типов НЕТ — размеры фиксированные IAB, `sizes` из webhook в payload не передаётся (echo в raw).
- Ответ 201 (АСИНХРОННЫЙ, status: pending|in_queue|running|failed|done): `{id, image, output: [{name, size, type, url}] (массив объектов CroppedBannerOutput), status, failed_reason, credits_used, webhook_url, created_at, updated_at}`. `output` = массив объектов (в доке тип string — доки врут, как у asset_generator).
- **Стоимость: 2 кредита** за запрос (списываются сразу при POST: balance 389→387). Допрашивать `GET /api/iab_images/{id}/` (бесплатно): при done output содержит 12 стандартных IAB-баннеров (mobile 320x50/300x250/320x100/250x250 + desktop 728x90/160x600/300x600/970x250/970x90/468x60/250x250/300x250), PNG на cdn.creatify.ai.

### Контракт POST /api/inspiration_jobs/ (сверен с https://docs.creatify.ai/api-reference/inspiration/post-inspiration-job.md + живьём)
- ⚠️ Путь — **`/api/inspiration_jobs/`** (с подчёркиванием; `/api/inspiration/` НЕ существует). Каталог шаблонов: `GET /api/inspirations/` → массив `{id, name, gen_type (image|video), input_params_schema (JSON Schema: properties/required), credit_cost (API-цена, 4x от in-app), preview_image}`. Детально: `GET /api/inspirations/{id}/`; статус задачи: `GET /api/inspiration_jobs/{id}/`.
- Тело: `{"inspiration_id": "<uuid шаблона>", "input_params": {<поля по input_params_schema>}, "webhook_url"?: "<uri>"}` — **оба поля inspiration_id + input_params ОБЯЗАТЕЛЬНЫ**. Поля input_params = КЛЮЧИ СХЕМЫ шаблона (напр. "Product Image", "Headline", ...), имена в точности как в input_params_schema.properties.
- Ответ 201: `{id (job), inspiration_id, gen_type, status (in_queue|running|done|failed), failed_reason, input_params, output, webhook_url, created_at, updated_at}`. output при done = URL готового изображения (string).
- **Стоимость: credit_cost шаблона** (минимальные в живом каталоге = 8.0 кред; видео-шаблоны тоже от 8.0). Списывается при POST: balance 387→379.

### Схема воркфлоу (две независимые цепи, 22 ноды)
- **(a) banner**: Webhook `POST /webhook/factory/banner` (webhookId `cr7-banner`) → Code Validate (принимает `{image_url (алиас image), sizes?, webhook_url?}`; image_url обязателен + http(s); payload `{image}` целиком в Code) → Switch v3.4 (ok boolean equals true + fallbackOutput extra: out[0]→credit-check, out[1]→Respond error `{ok:false,error}`) → HTTP credit-check (GET /api/remaining_credits/, keypair `{{ $env.CREATIFY_API_ID/KEY }}`, retry 3x) → IF balance (number gte **10**; rightValue числом, typeValidation strict) → true: HTTP iab_images (POST, `authentication:"none"` + sendHeaders keypair $env, contentType json, **`jsonBody: "={{ $('Code validate banner').first().json.payload }}"`** (кросс-нод-ссылка — HTTP credit-check НЕ прокидывает item, payload иначе потерян), options `{timeout:120000, retryOnFail:true, maxTries:3, waitBetweenTries:5000}`) → Code Normalize (`{ok:true, banner_id, status, urls: [{size,url,type,name}], credits_used, failed_reason, raw}`) → Respond ok | false: Code insufficient → Respond `{ok:false, error:'недостаточно кредитов...', balance}`.
- **(b) inspiration**: Webhook `POST /webhook/factory/inspiration` (webhookId `cr7-inspiration`) → Code Validate (`{inspiration_id (алиас template_id), input_params?, source_url?, webhook_url?}`; inspiration_id = UUID обязателен; input_params обязателен объект, fallback `{source_url}` из source_url) → Switch → HTTP credit-check → IF balance (gte 10) → HTTP inspiration_jobs (`jsonBody: "={{ $('Code validate inspiration').first().json.payload }}"`) → Code Normalize (`{ok:true, inspiration_id, job_id, status, gen_type, output, failed_reason, raw}`) → Respond ok | insufficient → Respond error.
- **Живые тесты (13.08)**:
  - exec 1918 (banner, реальный): `POST /webhook/factory/banner {"image_url":"https://picsum.photos/1200/627"}` → `{"ok":true,"banner_id":"4443854d-d20d-4772-a6aa-0e2bb43ccb13","status":"running","urls":[],"credits_used":0}`; Creatify перехостил картинку (cdn.creatify.ai/images/...jpg); через ~10с GET: status=done, credits_used=2, 12 IAB-баннеров. Баланс 389→387 (**2 кред**).
  - exec 1924 (inspiration, реальный): `POST /webhook/factory/inspiration {"inspiration_id":"e13275e1-b916-44c2-aa5f-c813cdbe9f0c","input_params":{"Product Image":"https://picsum.photos/1200/627"}}` (шаблон "App Showcase Photo", image, 8 кред) → `{"ok":true,"inspiration_id":"e13275e1-...","job_id":"e788c9b9-7aa0-4383-8b46-897ff1e82ec9","status":"in_queue","gen_type":"image",...}`; через ~15с GET: status=done, output=`https://cdn.creatify.ai/n8n_image_ads/b385f6df-.../0_69de41dd.jpg`. Баланс 387→379 (**8 кред**).
  - Валидационные ветки (0 кредитов): exec 1915/1916 — `{"image_url":"x"}` → `{"ok":false,"error":"image_url должен быть http(s) URL"}`, `{"inspiration_id":"x"}` → `{"ok":false,"error":"inspiration_id должен быть UUID"}` (HTTP 200, ветка Respond error).
  - dump-execution exec 1924 подтверждает ветки: Switch out[0] (ok), IF out[0] (balance 387 ≥ 10), цепочка HTTP→Normalize→Respond ok.
- **Итого потрачено за тикет: 10 кредитов** (2 banner + 8 inspiration). Баланс creatify на конец тикета: 379.
- **Питфоллы применённые**: webhookId в ноде обязателен (`cr7-banner`/`cr7-inspiration`); httpRequest typeVersion 4.5 + keypair $env (httpMultipleHeadersAuth не работает); jsonBody = одноуровневая ссылка (payload в Code-ноде; вложенные `{}` → invalid syntax); Switch v3.4 fallbackOutput extra; IF number gte rightValue ЧИСЛОМ; HTTP-нода НЕ прокидывает item → payload через кросс-нод-ссылку `$('Code validate X').first().json.payload`; `node:sqlite` в этом контейнере = `DatabaseSync` (не `Database`); активация = `n8n publish:workflow --id` + **docker restart** (без рестарта webhook_entity пуст, 404; регистрация вебхуков после рестарта ~10-20с — probe раньше = ложный 404); REST /rest/login отдаёт Set-Cookie, но cookie-сессия curl в этой сборке не приживается (401) — активация только CLI.

## 24. UX-FIX-1: AI Shorts — цепочка topic → ai_scripts → ai_shorts (13.08, без live-теста)
- ПРОБЛЕМА: wf-creatify-shorts слал в ai_shorts голый topic (заголовок) → ролик 3 сек при списании 5 кред (мин. блок 30 сек). 
- ФИКС (применён, 12→16 нод): если body.script пуст, а есть topic → ветка HTTP ai_scripts (1 кред, полный сценарий) → Code extract script (generated_scripts[0].paragraphs) → Code Build payload script → HTTP ai_shorts. Прямой script — по-старому. jsCode проверен node --check, бэкап /tmp/shorts_backup.json.
- Проверено БЕЗ списаний: POST /webhook/factory/shorts {} → {ok:false, error:'script или topic обязателен'} (exec 1953 success).
- ⚠️ LIVE-ТЕСТ ОТЛОЖЕН по решению оператора: генерации тестируем только после полного фикса контент-завода.

## 25. НАХОДКА: WriteBinaryFile нода ЕСТЬ в n8n 2.34 (для скачивания результатов на сервер)
- n8n-nodes-base.WriteBinaryFile доступна — будущие доработки: после завершения генерации (callback/poll) скачивать video_output/assets в ~/factory/media/ через HTTP responseFormat:file → WriteBinaryFile. Сейчас результаты лежат только на CDN Creatify (ссылки). PENDING (не блокер).

## 26. UX-1: 13 новых TG-команд (13.08) — DONE, 0 кредитов
- wf-tg-bot: 214 → 278 нод. Добавлены команды (en+ru+slash): creators, creator, creator_content, audience, transcript, comments, upload_avatar, my_avatars, asset, shorts, product, banner, publish_type
- Каждая = Build(payload) → Switch valid → HTTP webhook (localhost:5678/webhook/factory/*, neverError) → Format (esc экранирование) → Telegram Send
- setMyCommands: tg-commands-25.json (28 команд) зарегистрирован, getMyCommands count=28, missing=[]
- Тесты (все БЕСПЛАТНЫЕ, exec 1957–1987 success): my_avatars → реальный список (msg 137); creators robotics → ошибка сервиса (SC баланс -1); publish_type story → settings обновлено (msg 139); валидации 13 команд — осмысленные ошибки
- Питфолл закрыт: invalid-путь Format-нод экранирует esc(b.text) (12 нод) — `_` в подсказках больше не ломает Markdown
- КРЕДИТЫ: 0 потрачено (только валидационные пути; HTTP к платным webhook'ам не вызывался)
