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
| wf-creatify-webhook | POST `/webhook/factory/creatify/6d8f2a41c9e7b3d5f0a1c4e8` | ✅ done→status=done, повтор→duplicate, failed→failed (идемпотентность) |
| wf-creatify-poll | Cron `*/5 * * * *` | ✅ исполняется, success |
| wf-publish | POST `/webhook/factory/publish` {generation_id, platforms, post_at, captions} | ✅ posts строка + postmypost_id=999 (mock) |
| wf-publish-status | Cron `*/2 * * * *` | ✅ pending_publication → published + tg-алерт (mock) |
| wf-sync-accounts | Cron `0 * * * *` | ✅ social_accounts наполнен; status=2 → tg-алерт |
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
