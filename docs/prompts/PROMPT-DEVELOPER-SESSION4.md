# ПРОМПТ ДЛЯ ГЛАВНОГО АГЕНТА-ОРКЕСТРАТОРА (ФАЗА 1 — /autopilot)

> Этот промпт — для ГЛАВНОГО агента, который работает через /autopilot.
> Он НЕ пишет бизнес-код сам. Он создаёт субагентов под каждый тикет.
> Скопируй текст ниже в первое сообщение новому агенту.

---

Ты — **главный агент-оркестратор Фазы 1** контент-завода. Работаешь через
**/autopilot**: каждый тикет уходит в ОТДЕЛЬНЫЙ субагент с чистым контекстом.

## ⚠️ ТВОЯ РОЛЬ — ОРКЕСТРАТОР, НЕ ИСПОЛНИТЕЛЬ

**Ты НЕ пишешь код, не редактируешь воркфлоу, не запускаешь Hermes сам.** Ты:

1. Загружаешь /autopilot.
2. Читаешь DEPLOYMENT.md и краткое описание проекта (ниже) — один раз, в своём
   контексте, чтобы понимать картину.
3. **Последовательно передаёшь карточки тикетов** (раздел КАРТОЧКИ ниже) в
   /autopilot — по одной на субагента.
4. Каждый субагент получает ТОЛЬКО свою карточку + общий технический скелет
   (раздел СКЕЛЕТ) — минимальный контекст, необходимый для его задачи.
5. Собираешь результаты каждого субагента, обновляешь прогресс.
6. Когда все карточки пройдены (done или BLOCKED) — пишешь финальный отчёт.

**Если ты пытаешься сделать тикет сам, без субагента — ты делаешь это неправильно.**
Перечитай /autopilot и используй его паттерн делегирования.

**Если твой контекст переполняется — значит, ты тащишь чужой контекст в себя.
   Субагенты должны работать изолированно, ты только координируешь.**

## ПРОЕКТ — КРАТКО (для тебя, не для субагентов)

Контент-завод: витринный демо-продукт. Robotec (robotec.ru) — демо-клиент.
Стек: Hermes Agent v0.20.0 (мозг+TG-бот) + n8n 2.34 (руки) + SQLite (БД) +
opencode zen deepseek v4 (LLM) + scrapecreators/creatify/postmypost (API).

Две фазы: Фаза 1 (сегодня) — инфраструктура и логика с mock-данными (ключей от
платных API нет до завтра). Фаза 2 (завтра) — подстановка ключей + end-to-end.

**Подробности:** прочитай сам `~/factory/DEPLOYMENT.md` и `~/factory/specs/11-amendments.md`.
Субагентам это давать НЕ НАДО — у каждого своя карточка.

## ДОСТУПЫ (для тебя и субагентов)

- **SSH:** `ssh -i /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem ubuntu@83.166.233.95`
- **n8n UI:** https://assessment-fossil-assignments-alice.trycloudflare.com
  (owner@factory.local / PLACEHOLDER_REPLACE_N8N_PASSWORD)
- **Hermes:** `source ~/hermes-agent/.venv/bin/activate && hermes ...`
- **LLM настроен**, Telegram токен в ~/factory/.env.

## СКЕЛЕТ (общий технический контекст — прикладывай к каждой карточке субагента)

Это минимальный набор фактов, который нужен каждому субагенту. Передавай его
ВМЕСТЕ с карточкой тикета (в одном промпте субагенту):

```
=== ОБЩИЙ КОНТЕКСТ (прочитай один раз) ===

Сервер: 83.166.233.95, юзер ubuntu, sudo без пароля.
SSH: ssh -i /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem ubuntu@83.166.233.95

n8n 2.34: https://assessment-fossil-assignments-alice.trycloudflare.com
  логин owner@factory.local / пароль PLACEHOLDER_REPLACE_N8N_PASSWORD

Инженерные факты (используй как есть):
1. Импорт кред/воркфлоу через CLI внутри контейнера:
   docker exec factory-n8n n8n import:credentials --input=/tmp/file.json
   docker exec factory-n8n n8n import:workflow --input=/tmp/file.json
2. JSON импорта требует явного корневого id (UUID) и у кред, и у воркфлоу.
3. Импорт воркфлоу без --activeState=fromJson. Активация — открыть в UI →
   Publish → подтвердить версию диалога. UPDATE БД не работает (webhook не
   регистрируется).
4. Креды созданы: scrapecreators (httpHeaderAuth, x-api-key),
   creatify (httpMultipleHeadersAuth, X-API-ID + X-API-KEY),
   postmypost (httpBearerAuth), telegram (telegramApi).
5. Code-нода блокирует node:sqlite и node:fs (песочница). Все DB-операции —
   через HTTP Request к http://db-bridge:8787/query с заголовком
   X-BRIDGE-TOKEN: {{ $env.FACTORY_DB_BRIDGE_TOKEN }}. Body: {"sql":"...","params":[...]}.
6. Текущий баг: POST /query из n8n-контейнера даёт unauthorized (токен не виден
   в контейнере). Если твой тикет использует мост — проверь первым делом, что
   FACTORY_DB_BRIDGE_TOKEN добавлен в environment: n8n-сервиса в docker-compose
   и контейнер пересоздан.
7. Hermes: source ~/hermes-agent/.venv/bin/activate && hermes <command>
   LLM уже настроен (opencode-zen / deepseek-v4-flash-free).
8. Платные API scrapecreators/creatify/postmypost — ключи будут завтра. Сейчас
   в ~/.hermes/.env и ~/factory/.env стоят placeholder PLACEHOLDER_UNTIL_TOMORROW.
   Все HTTP к этим API — в mock-режиме через Switch на placeholder.
9. mock-паттерн: после каждого HTTP к платному API — Switch на
   {{ $env.<API_KEY_VAR> === 'PLACEHOLDER_UNTIL_TOMORROW' }} → true: Code с
   mock JSON, false: реальный ответ.
10. Чтение спек (если нужно): ~/factory/specs/{02-analytics, 04-generation,
    05-publishing, 11-amendments}.md. Спека 11-amendments приоритетнее 03/06/10.

Правила:
- Застрял >10 минут — пометил BLOCKED, двигайся дальше.
- Сдаваться без 3 честных попыток нельзя.
- Финальный отчёт только когда всё сделано или реальный hard limit окружения.
```

## КАРТОЧКИ ТИКЕТОВ

Передавай их в /autopilot **по одной** (или пачкой, если autopilot поддерживает
батч). Каждая карточка — самостоятельный промпт для субагента.

---

### 🎫 КАРТОЧКА T-A: Починить auth db-bridge

```
ЗАДАЧА: POST /query из n8n-контейнера к db-bridge возвращает unauthorized.

ДЕТАЛИ:
- db-bridge — docker-сервис (node:22-slim), health-check работает
  (curl http://db-bridge:8787/health из n8n-контейнера → {"ok":true,...}).
- Токен FACTORY_DB_BRIDGE_TOKEN задан в ~/factory/.env.
- Проверка заголовка X-BRIDGE-TOKEN в server.js через timingSafeEqual.

ЧТО СДЕЛАТЬ:
1. Проверить из контейнера моста:
   docker exec factory-db-bridge node -e "fetch('http://localhost:8787/query',{method:'POST',headers:{'Content-Type':'application/json','X-BRIDGE-TOKEN':process.env.FACTORY_DB_BRIDGE_TOKEN},body:JSON.stringify({sql:'SELECT 1 as test'})}).then(r=>r.text()).then(console.log)"
2. Проверить из контейнера n8n:
   docker exec factory-n8n sh -c 'curl -s -X POST http://db-bridge:8787/query -H "Content-Type: application/json" -H "X-BRIDGE-TOKEN: $FACTORY_DB_BRIDGE_TOKEN" -d "{\"sql\":\"SELECT 1 as test\"}"'
3. Если в n8n-контейнере $FACTORY_DB_BRIDGE_TOKEN пустой — добавить переменную
   в environment: сервиса n8n в ~/factory/docker-compose.yml, пересоздать:
   cd ~/factory && docker compose up -d n8n
4. Повторить тест №2 — должен вернуть {"ok":true,"rows":[{"1":1}]} или похожее.

КРИТЕРИЙ ГОТОВНОСТИ: curl из n8n-контейнера с токеном возвращает ответ от БД,
не unauthorized.

БЮДЖЕТ ВРЕМЕНИ: 15 минут. Если не починилось — BLOCKED + причина.
```

---

### 🎫 КАРТОЧКА T-B: Запуск Hermes gateway + проверка /start

```
ЗАДАЧА: Запустить Hermes как systemd-сервис, проверить что TG-бот отвечает /start.

КОНТЕКСТ:
- systemd-юнит /etc/systemd/system/hermes.service уже создан ( ExecStart:
  /home/ubuntu/hermes-agent/.venv/bin/hermes gateway run).
- ~/.hermes/.env содержит TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USERS=941296693,
  TELEGRAM_HOME_CHANNEL=941296693.
- Hermes v0.20.0 в venv. LLM настроен (opencode-zen).

ЧТО СДЕЛАТЬ:
1. sudo systemctl daemon-reload
2. sudo systemctl enable --now hermes
3. journalctl -u hermes -f (в фоне / в отдельном окне)
4. Подождать 30 сек, проверить статус: sudo systemctl status hermes — должен быть
   active (running).
5. Из логов journalctl убедиться, что gateway подключился к Telegram
   (long-polling запущен, ошибок нет).
6. С телефона (или через @userinfobot) отправить боту /start.
7. Проверить в journalctl что сообщение пришло, Hermes его обработал.
8. Дождаться ответа бота (Hermes должен ответить, т.к. LLM работает).

КРИТЕРИЙ ГОТОВНОСТИ: бот в TG отвечает на /start, в journalctl нет ошибок.

ЕСЛИ НЕ ЗАПУСКАЕТСЯ (3 попытки):
- проверь ~/.hermes/.env (правильные имена переменных, валидный токен)
- hermes gateway setup (интерактивный мастер) — проверить конфиг TG
- логи journalctl -u hermes -n 100
Если не починилось за 30 минут — BLOCKED + выписка из логов.
```

---

### 🎫 КАРТОЧКА T-C: Скиллы Hermes (T-033')

```
ЗАДАЧА: Перенести 4 промпта субагентов в ~/.hermes/skills/, доработать orchestrator.md.

ЧТО СДЕЛАТЬ:
1. mkdir -p ~/.hermes/skills
2. cp ~/factory/hermes/skills/*.md ~/.hermes/skills/
3. В ~/.hermes/skills/orchestrator.md добавить в раздел "Связь с n8n" инструкцию:
   "Для вызова n8n-воркфлоу используй toolset terminal и curl:
    curl -X POST http://localhost:5678/webhook/factory/<wf-name> -H 'Content-Type: application/json' -d '<json>'
   Где <wf-name>: analytics, onboard, creatify-link, creatify-submit, publish."
4. hermes skills list — проверить что 4 skill видны (orchestrator, analyst,
   scriptwriter, json-builder).
5. Простой тест: source ~/hermes-agent/.venv/bin/activate && \
   hermes chat -q "Прочитай skill orchestrator и скажи, какой первый шаг цикла" --cli -Q
   Должен ответить осмысленно со ссылкой на analytics.

КРИТЕРИЙ ГОТОВНОСТИ: 4 skill в hermes skills list, orchestrator.md содержит
инструкцию про curl к webhook'ам.

БЮДЖЕТ: 15 минут.
```

---

### 🎫 КАРТОЧКА T-D: wf-tg-alerts

```
ЗАДАЧА: Создать воркфлоу wf-tg-alerts в n8n через CLI-импорт.

ЛОГИКА ВОРКФЛОУ:
Webhook (POST /webhook/factory/tg-alert, no auth) →
  Telegram Send (chat_id из body.chat_id, text из body.text, cred: telegram)

ТРЕБОВАНИЯ:
- Webhook-нода: type "n8n-nodes-base.webhook", path "factory/tg-alert",
  httpMethod "POST", respondMode "onReceived".
- Telegram-нода: type "n8n-nodes-base.telegram", resource "message",
  operation "sendMessage", chatId "={{ $json.body.chat_id }}",
  text "={{ $json.body.text }}", credentials выбраны (telegram).

ЧТО СДЕЛАТЬ:
1. Написать JSON файла воркфлоу в /tmp/wf-tg-alerts.json со структурой:
   { "id": "<UUID>", "name": "wf-tg-alerts", "active": false,
     "nodes": [...], "connections": {...}, "settings": {}, "versionId": "<UUID>" }
   (точные typeVersion взять из выгруженных схем: ~/factory/schemas/ или через
   n8n export:nodes ранее).
2. docker exec factory-n8n n8n import:workflow --input=/tmp/wf-tg-alerts.json
   (путь в /tmp внутри контейнера — скопировать через docker cp).
3. В n8n UI: открыть wf-tg-alerts → справа вверху Publish → подтвердить версию.
4. Тестовый curl с хоста:
   curl -X POST "https://assessment-fossil-assignments-alice.trycloudflare.com/webhook/factory/tg-alert" \
     -H "Content-Type: application/json" \
     -d '{"chat_id": 941296693, "text": "test from wf-tg-alerts"}'
5. Должно прийти сообщение в TG от бота.

КРИТЕРИЙ ГОТОВНОСТИ: curl снаружи доставляет сообщение в TG за <3 сек.

БЮДЖЕТ: 30 минут. mock не нужен — это полностью рабочий тикет.
```

---

### 🎫 КАРТОЧКА T-E: wf-onboard

```
ЗАДАЧА: Создать воркфлоу wf-onboard (fetch сайта клиента с SSRF-защитой).

ЛОГИКА:
Webhook (POST /webhook/factory/onboard, body: {"url": "..."}) →
  Code (SSRF-чек URL: распарсить, если IP приватный 10/8, 172.16/12, 192.168/16,
        127/8, ::1, 169.254/16 — отказ) →
  HTTP Request (GET указанного URL, timeout 10s, limit 200KB) →
  Code (извлечь: title, meta description, og:title, og:image, h1, ссылки на
        соцсети — instagram.com/, t.me/, youtube.com/, vk.com/, tiktok.com/,
        x.com/, facebook.com/, rutube.ru/) →
  Respond to Webhook (JSON {url, title, meta, socials[], text_excerpt})

ТРЕБОВАНИЯ:
- SSRF-чек: использовать dns.lookup + проверку диапазонов. Запретить
  перенаправления на приватные IP (следить за redirects).
- Лимит размера ответа 200KB (обрезать body).
- text_excerpt: первые 8000 символов видимого текста (после удаления тегов).

ИМПОРТ: через CLI (см. СКЕЛЕТ п.1-3), активация через UI Publish.

ТЕСТ:
curl -X POST "https://assessment-fossil-assignments-alice.trycloudflare.com/webhook/factory/onboard" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://robotec.ru"}'
→ ответ должен содержать title="Robotec" (или похожее), и socials с
   https://t.me/robotec_tg.

ССЫЛКА НА СПЕКУ: ~/factory/specs/08-onboarding.md (раздел 2 — Ступень 1).

КРИТЕРИЙ ГОТОВНОСТИ: curl с robotec.ru возвращает JSON с найденной TG-ссылкой.
SSRF-защита работает (curl с http://127.0.0.1 → отказ).

БЮДЖЕТ: 45 минут.
```

---

### 🎫 КАРТОЧКА T-F: wf-analytics (mock)

```
ЗАДАЧА: Создать воркфлоу wf-analytics с 3 ветками и mock-режимом.

ЛОГИКА:
Webhook (POST /webhook/factory/analytics, body: {client_id, find_competitors}) →
  Split (3 параллельные ветки):
    Ветка IG:  HTTP Request (GET https://api.scrapecreators.com/v2/instagram/reels/search,
               query: {query: "industrial robot", date_posted: "last-day", page: 1},
               cred: scrapecreators) → Switch на placeholder:
                 true:  Code с mock (3 IG-reel'а в нише промышленных роботов,
                        timestamps 12-72 часа)
                 false: реальный ответ
    Ветка TikTok: аналогично, GET /v1/tiktok/search/keyword,
                  query: {query: "industrial robot", sort_by: "most-liked",
                          date_posted: "yesterday", region: "RU", trim: "true"}
    Ветка YT: аналогично, GET /v1/youtube/search,
              query: {query: "industrial robot", sortBy: "popular",
                      uploadDate: "today", type: "videos"}
  Merge (все 3 ветки) →
  Code (постфильтр 12-72ч по timestamp, дедупликация по URL,
        расчёт virality_index, топ-20) →
  Respond to Webhook ({candidates[], meta: {credits_spent, platforms_ok}})

ВАЖНО: mock JSON реалистичный — 5 кандидатов в нише промышленной робототехники
(роботы KUKA, сварочные манипуляторы, palletizing), метрики views/likes/shares,
timestamps в диапазоне 12-72 часа от now.

ИМПОРТ: через CLI, активация через UI Publish.

ССЫЛКА НА СПЕКУ: ~/factory/specs/02-analytics.md (разделы 2-5).

ТЕСТ:
curl -X POST ".../webhook/factory/analytics" \
  -H "Content-Type: application/json" \
  -d '{"client_id": 1, "find_competitors": false}'
→ топ-20 mock-кандидатов с virality_index.

КРИТЕРИЙ ГОТОВНОСТИ: 3 ветки исполняются, постфильтр 12-72ч отсекает лишнее
(проверить: mock должен содержать 1-2 записи с timestamp >72ч — они должны
быть отфильтрованы).

БЮДЖЕТ: 60 минут.
```

---

### 🎫 КАРТОЧКА T-G: wf-creatify-link (mock)

```
ЗАДАЧА: Создать воркфлоу wf-creatify-link.

ЛОГИКА:
Webhook (POST /webhook/factory/creatify-link, body: {url, overrides?}) →
  HTTP Request (POST https://api.creatify.ai/api/links/,
               body: {"url": "{{ $json.body.url }}"},
               cred: creatify) →
  Switch на placeholder:
    true:  Code с mock {id: "<UUID>", status: "ok"} (сгенерировать случайный UUID)
    false: реальный ответ
  Respond to Webhook ({link_id, raw})

ССЫЛКА: ~/factory/specs/04-generation.md (раздел 3, Шаг 1).

ТЕСТ: curl -X POST ".../webhook/factory/creatify-link" \
  -d '{"url":"https://example.com"}' → {link_id: "<UUID>"}.

КРИТЕРИЙ: mock возвращает валидный UUID, готовый для wf-creatify-submit.

БЮДЖЕТ: 30 минут.
```

---

### 🎫 КАРТОЧКА T-H: wf-creatify-submit (mock)

```
ЗАДАЧА: Воркфлоу wf-creatify-submit с записью в БД через db-bridge.

ЛОГИКА:
Webhook (POST /webhook/factory/creatify-submit, body: {json_payload, link_id,
         script_id, client_id}) →
  HTTP Request (POST http://db-bridge:8787/query,
               header X-BRIDGE-TOKEN: {{ $env.FACTORY_DB_BRIDGE_TOKEN }},
               body: {"sql": "INSERT INTO generations (script_id, client_id,
                 request_payload, status, created_at) VALUES (?, ?, ?, 'pending',
                 datetime('now'))", "params": ["{{script_id}}", "{{client_id}}",
                 "{{JSON.stringify(json_payload)}}"]}) →
  HTTP Request (POST https://api.creatify.ai/api/link_to_videos/,
               body: json_payload + webhook_url:
                 "https://assessment-fossil-assignments-alice.trycloudflare.com/webhook/factory/creatify/<TOKEN>",
               cred: creatify) →
  Switch на placeholder:
    true:  Code с mock {id: "<UUID>", status: "pending", progress: 0}
    false: реальный ответ
  HTTP Request (UPDATE generations SET creatify_id=?, link_id=? WHERE id=...) →
  Respond to Webhook ({creatify_id})

ВАЖНО: path-token на webhook creatify — генерировать случайный, хранить в
settings или env CREATIFY_WEBHOOK_TOKEN.

ССЫЛКА: ~/factory/specs/04-generation.md (раздел 3, Шаг 3) + 11-amendments.md.

ТЕСТ: curl POST creatify-submit с mock-payload → {creatify_id: "<UUID>"} +
проверка через db-bridge что строка в generations появилась.

КРИТЕРИЙ: задача создана, запись в БД есть.

БЮДЖЕТ: 45 минут. ЗАВИСИТ ОТ T-A (db-bridge auth).
```

---

### 🎫 КАРТОЧКА T-I: wf-creatify-webhook (callback)

```
ЗАДАЧА: Приём callback'а готовности видео от creatify.

ЛОГИКА:
Webhook (POST /webhook/factory/creatify/<TOKEN>, no auth — path-token в URL,
         body от creatify: {id, status, video_output, failed_reason}) →
  HTTP Request (POST db-bridge: SELECT * FROM generations WHERE creatify_id=?) →
  Switch по status:
    done:  HTTP Request (GET video_output → write в /var/media/<gen_id>.mp4
                              через db-bridge или SystemCommand) →
           HTTP Request (UPDATE generations SET status='done', local_path=?,
                         completed_at=datetime('now')) →
           HTTP Request (POST /webhook/factory/tg-alert с {"chat_id": 941296693,
                         "text": "Видео #N готово"})
    failed: HTTP Request (UPDATE status='failed', failed_reason=?) →
            POST в tg-alert

ИДЕМПОТЕНТНОСТЬ: проверка creatify_id в БД — если уже status='done', игнорировать.

ССЫЛКА: ~/factory/specs/04-generation.md (раздел 6.3).

ТЕСТ: вручную POST с mock-payload на webhook creatify → в БД статус done,
       файл создан (если реально качаем — иначе mock), алерт в TG.

КРИТЕРИЙ: повторный POST с тем же creatify_id не создаёт дубль.

БЮДЖЕТ: 45 минут. ЗАВИСИТ ОТ T-A, T-D.
```

---

### 🎫 КАРТОЧКА T-J: wf-creatify-poll

```
ЗАДАЧА: Cron-воркфлоу для компенсирующего поллинга.

ЛОГИКА:
Schedule Trigger (every 5 minutes) →
  HTTP Request (POST db-bridge: SELECT creatify_id FROM generations WHERE
               status IN ('pending','running') AND created_at < datetime('now',
               '-15 minutes') AND webhook_received=0) →
  Если есть результаты → HTTP Request (GET creatify /api/link_to_videos/?ids=csv,
                                     cred: creatify) →
  Switch на placeholder:
    true:  ничего не делаем (mock)
    false: Code (для каждого — если status терминальный, повторить логику
                  wf-creatify-webhook: скачать, UPDATE, алерт)

ССЫЛКА: ~/factory/specs/04-generation.md (раздел 6.4).

ТЕСТ: в mock-режиме — cron запускается каждые 5 мин, ничего не падает.

КРИТЕРИЙ: воркфлоу активно, в логах n8n видно запуски каждые 5 мин, ошибок нет.

БЮДЖЕТ: 20 минут. ЗАВИСИТ ОТ T-A.
```

---

### 🎫 КАРТОЧКА T-K: wf-publish (mock)

```
ЗАДАЧА: Воркфлоу публикации в postmypost (mock).

ЛОГИКА:
Webhook (POST /webhook/factory/publish, body: {generation_id, platforms[],
         post_at, captions}) →
  HTTP Request (POST https://api.postmypost.io/v4.1/upload/init,
               body: {"project_id": "{{ $env.POSTMYPOST_PROJECT_ID }}",
                      "url": "https://assessment-fossil-assignments-alice.trycloudflare.com/media/{{generation_id}}.mp4"},
               cred: postmypost, header Authorization: Bearer) →
  Switch на placeholder:
    true:  Code mock {id: 12345, status: "FILE_UPLOADED_SUCCESSFULLY", file_id: 67890}
    false: реальный ответ
  Loop: GET /upload/status?id=12345 — пока status != 1 (в mock сразу успех) →
  HTTP Request (POST /api/publications, body: собрать details[] под платформы
               из settings.platforms, publication_status: 5, post_at) →
  Switch на placeholder: mock успех {id: 999, status: "PENDING_PUBLICATION"}
  HTTP Request (INSERT в posts через db-bridge) →
  Respond to Webhook ({post_id})

ССЫЛКА: ~/factory/specs/05-publishing.md (раздел 4).

ТЕСТ: curl POST publish → post_id, в БД posts запись появилась.

КРИТЕРИЙ: mock публикации проходит end-to-end, в posts есть строка.

БЮДЖЕТ: 60 минут. ЗАВИСИТ ОТ T-A.
```

---

### 🎫 КАРТОЧКА T-L: wf-publish-status

```
ЗАДАЧА: Cron-поллинг статусов публикаций (mock).

ЛОГИКА:
Schedule Trigger (every 2 minutes) →
  HTTP Request (POST db-bridge: SELECT id, postmypost_id FROM posts WHERE
               status IN ('pending_publication','publishing') AND post_at <=
               datetime('now','+1 hour')) →
  For each: HTTP Request (GET postmypost /publications/{id}) →
            Switch placeholder: mock status='PUBLISHED' →
            HTTP Request (UPDATE posts SET status='published',
                          published_at=datetime('now')) →
            POST в wf-tg-alert "Опубликовано"

ССЫЛКА: ~/factory/specs/05-publishing.md (раздел 6.2).

ТЕСТ: в mock — cron крутится, ошибок нет. Реально публикаций ещё нет.

КРИТЕРИЙ: активный cron, нет ошибок в логах.

БЮДЖЕТ: 25 минут.
```

---

### 🎫 КАРТОЧКА T-M: wf-sync-accounts

```
ЗАДАЧА: Cron-синхронизация аккаунтов postmypost (mock).

ЛОГИКА:
Schedule Trigger (hourly) →
  HTTP Request (GET https://api.postmypost.io/v4.1/accounts?project_id=...,
               cred: postmypost) →
  Switch placeholder: mock массив аккаунтов →
  For each: HTTP Request (UPSERT в social_accounts через db-bridge) →
  Если connection_status=2 (AUTH_REQUIRED) → POST в wf-tg-alert "Перелогинься"

ССЫЛКА: ~/factory/specs/05-publishing.md (раздел 6.3).

ТЕСТ: cron запускается, в mock нет ошибок.

КРИТЕРИЙ: активный cron, social_accounts наполняется mock-данными.

БЮДЖЕТ: 25 минут.
```

---

### 🎫 КАРТОЧКА T-N: Субагент Онбординг (тест Hermes skill)

```
ЗАДАЧА: Проверить скилл onboard в Hermes на mock-черновике сайта.

КОНТЕКСТ: skill onboard.md уже в ~/.hermes/skills/ (сделано в T-C). Скилл
описывает: на вход черновик сайта (meta/socials/text), на выход JSON-профиль
клиента (name, domain, industry, niche, audience, tone, socials[], competitors[],
suggested_topics[], confidence).

ЧТО СДЕЛАТЬ:
1. source ~/hermes-agent/.venv/bin/activate
2. Сохранить mock-черновик robotec.ru в файл /tmp/robotec-draft.json:
   {
     "url": "https://robotec.ru",
     "title": "Robotec — интеграция промышленной робототехники",
     "meta_description": "Системный интегратор промышленных роботов KUKA...",
     "socials": [{"platform": "telegram", "url": "https://t.me/robotec_tg"}],
     "text_excerpt": "Системный интегратор промышленной робототехники..."
   }
3. hermes chat -q "Прочитай скилл onboard. Обработай черновик сайта клиента из
   файла /tmp/robotec-draft.json. Верни только JSON-профиль по схеме скилла." \
     --cli -Q -s onboard
4. Распарсить ответ, проверить что JSON валиден и содержит обязательные поля:
   name, industry, niche, audience, tone, socials[], competitors[],
   suggested_topics[] (минимум 3), confidence.

КРИТЕРИЙ: Hermes возвращает валидный JSON-профиль для robotec с
industry="промышленная робототехника" или похожим, минимум 3 темы.

БЮДЖЕТ: 20 минут.
```

---

### 🎫 КАРТОЧКА T-O: Субагент Аналитик (тест Hermes skill)

```
ЗАДАЧА: Проверить скилл analyst на mock-кандидатах.

КОНТЕКСТ: skill analyst.md в ~/.hermes/skills/. На вход список кандидатов
(top-20), на выход JSON {chosen:{title, source_url, rationale, feasibility,
adaptation_for_client, target_length_sec}, alternatives[]}.

ЧТО СДЕЛАТЬ:
1. source ~/hermes-agent/.venv/bin/activate
2. Создать /tmp/mock-candidates.json с 5 кандидатами в нише промышленных
   роботов: title, source_url, source_platform, metrics{views, likes, shares},
   age_hours (12-72), virality_index (0.5-0.95), transcript_excerpt.
3. hermes chat -q "Прочитай скилл analyst. Из кандидатов в /tmp/mock-candidates.json
   выбери ОДНУ тему для B2B-клиента Robotec (промышленная робототехника KUKA).
   Верни строго JSON по схеме скилла, без markdown." \
     --cli -Q -s analyst
4. Распарсить ответ, проверить что chosen.title осмысленный, rationale связан
   с metrics и niche.

КРИТЕРИЙ: Hermes выбирает 1 тему, rationale упоминает виральность/нишу.

БЮДЖЕТ: 20 минут.
```

---

### 🎫 КАРТОЧКА T-P: Субагент Сценарист (тест)

```
ЗАДАЧА: Проверить скилл scriptwriter.

ЧТО СДЕЛАТЬ:
1. source ~/hermes-agent/.venv/bin/activate
2. hermes chat -q "Прочитай скилл scriptwriter. Напиши сценарий для темы:
   'Как сварочный робот KUKA снижает брак на 40%'. Тон: экспертно-деловой,
   ROI, окупаемость. Целевая длина 30 сек (60-70 слов). Верни JSON по схеме
   скилла." --cli -Q -s scriptwriter
3. Проверить: hook (3 сек, цепляет), body (20 сек, цифры/кейс), cta (последние
   3-5 сек, призыв к действию), full_text (60-70 слов), format_tag.

КРИТЕРИЙ: валидный JSON с hook/body/cta, full_text 60-70 слов.

БЮДЖЕТ: 15 минут.
```

---

### 🎫 КАРТОЧКА T-Q: Субагент JSON-сборщик (тест)

```
ЗАДАЧА: Проверить скилл json-builder.

ЧТО СДЕЛАТЬ:
1. source ~/hermes-agent/.venv/bin/activate
2. hermes chat -q "Прочитай скилл json-builder. Собери JSON для POST
   /api/link_to_videos со следующими входами:
   - сценарий: 'Сварочный робот KUKA работает 24/7 с точностью 0.05 мм. На
     заводе Автокомпласт он заменил 3 ручных поста и окупился за 14 месяцев.
     Закажите бесплатный аудит производства.'
   - target_length_sec: 30
   - link UUID: 7a7b8c9d-1234-5678-9abc-def012345678
   - webhook_url: https://assessment-fossil-assignments-alice.trycloudflare.com/webhook/factory/creatify/abc123token
   - voice_id: ru-male-expert-001 (пример)
   - target_platform: Instagram
   Верни ТОЛЬКО валидный JSON, без markdown, без пояснений." \
     --cli -Q -s json-builder
3. Распарсить ответ JSON.parse. Проверить поля: language='ru', aspect_ratio='9x16',
   video_length=30, override_script содержит текст сценария, webhook_url не пустой.

КРИТЕРИЙ: ответ парсится JSON.parse без ошибки, обязательные поля валидны.

БЮДЖЕТ: 20 минут.
```

---

### 🎫 КАРТОЧКА T-R: Сообщения 4 этапов ручного режима

```
ЗАДАЧА: Реализовать UX 4 этапов ручного режима в Hermes через Telegram.

КОНТЕКСТ: Hermes gateway работает (T-B), оркестратор-skill загружен (T-C).
Hermes сам отправляет сообщения с inline-кнопками через hermes-telegram.

ЧТО СДЕЛАТЬ:
1. В ~/.hermes/skills/orchestrator.md добавить секцию "Ручной режим — 4 этапа"
   с шаблонами сообщений (см. ~/factory/specs/06-telegram-bot.md раздел 6).
2. Сообщения:
   - Этап 1 (аналитика): "📊 Тема: ... | Обоснование: ... | Кнопки:
     ✅ Утвердить / ✏️ Изменить / ❌ Отклонить / 🔄 Другая тема"
   - Этап 2 (сценарий): "✍️ Сценарий: ... | Кнопки: ✅ / ✏️ / ❌"
   - Этап 3 (видео): "🎬 Видео готово | MP4 | Кнопки: ✅ Опубликовать /
     ✏️ Перегенерировать / ❌ Отклонить"
   - Этап 4 (площадки): "📤 Куда публикуем? | Чекбоксы: Instagram/YouTube/...
     | Кнопка 📤 Запланировать + выбор времени"
3. Inline-кнопки: callback_data кодирует действие и id сущности
   (approve:topic:42, edit:script:17, publish:gen:9).
4. Тест: через hermes chat симулировать получение решения от Аналитика (mock),
   Hermes должен сформировать сообщение для TG и предложить кнопки.

УПРОЩЕНИЕ ЕСЛИ СЛОЖНО: вместо inline-кнопок — текстовые подсказки
"Отправь 'approve' для утверждения, 'edit' для правки, 'reject' для отказа".

ССЫЛКА: ~/factory/specs/06-telegram-bot.md.

КРИТЕРИЙ: в Hermes orchestrator-skill описаны 4 этапа, простой тест через
hermes chat показывает что агент понимает формат.

БЮДЖЕТ: 40 минут.
```

---

### 🎫 КАРТОЧКА T-S: Финальный тест /start_cycle

```
ЗАДАЧА: Прогнать цикл /start_cycle на mock-данных.

КОНТЕКСТ: все предыдущие тикеты закрыты. Hermes gateway работает (T-B),
оркестратор-skill активен (T-C, T-R), все n8n-воркфлоу на mock (T-D..T-M),
субагенты проверены (T-N..T-Q).

ЧТО СДЕЛАТЬ:
1. С телефона / из клиента: отправить боту /start_cycle.
2. Hermes должен:
   - вызвать wf-analytics через curl (mock) → получить топ-20 кандидатов
   - делегировать субагенту-Аналитику → получить выбранную тему
   - отправить в TG сообщение этапа 1 с кнопками (или текстовыми подсказками)
3. Ответить оператору (с телефона) "approve" или нажать ✅ Утвердить.
4. Hermes:
   - делегировать Сценаристу → получить сценарий
   - отправить в TG этап 2
5. approve → Hermes:
   - создать link (wf-creatify-link mock) → link_id
   - делегировать JSON-сборщику → payload
   - submit (wf-creatify-submit mock) → creatify_id
   - отправить в TG "Видео генерируется (mock)..."
6. Имитировать callback: вручную POST на webhook creatify с mock-payload
   {id: creatify_id, status: "done", video_output: "https://example.com/test.mp4"}
7. wf-creatify-webhook должен обновить БД и прислать алерт в TG "Видео готово".
8. approve → выбор платформ → publish (mock).

ЗАСТРЯЛ — УПРОЩАЙ: достаточно прогнать этапы 1-3 (до сценария), остальное
помечать как "частично".

КРИТЕРИЙ: как минимум этапы 1-3 проходят от TG-команды до TG-ответа на mock.

БЮДЖЕТ: 60 минут. Это интеграционный тест, может потребовать отката по тикетам.
```

---

### 🎫 КАРТОЧКА T-T: Обновление DEPLOYMENT.md

```
ЗАДАЧА: Обновить ~/factory/DEPLOYMENT.md с финальным статусом Фазы 1.

ЧТО ЗАПИСАТЬ:
1. Что готово (done): список тикетов с однострочным описанием.
2. Что под mock: какие HTTP уходят в mock, какой паттерн.
3. Что BLOCKED: с причиной.
4. Команды для запуска/тестов каждого воркфлоу.
5. Что завтра во Фазе 2: какие ключи подставить, какие Switch будут
   автоматически переключаться на реальный HTTP.
6. Любые новые находки, не описанные ранее.

КРИТЕРИЙ: DEPLOYMENT.md актуализирован, новый разработчик может по нему
понять состояние без чтения чата.

БЮДЖЕТ: 25 минут.
```

---

## ТВОЙ ПОРЯДОК ДЕЙСТВИЙ (главный агент)

1. **Прочитай /autopilot** — структурируй его методологию.
2. **Прочитай сам** (в своём контексте): `~/factory/DEPLOYMENT.md`,
   `~/factory/specs/11-amendments.md` — общая картина.
3. **Последовательно передавай карточки в /autopilot** в порядке T-A → T-B → T-C
   → T-D → T-E → T-F → T-G → T-H → T-I → T-J → T-K → T-L → T-M → T-N → T-O →
   T-P → T-Q → T-R → T-S → T-T.
4. **Параллелизация (опц.):** если autopilot поддерживает — некоторые карточки
   независимы и могут идти параллельно (T-N/O/P/Q — тесты скиллов; T-J/L/M —
   простые cron'ы). T-S (интеграционный) — последним, после всех.
5. **Собирай результаты** каждого субагента: done / BLOCKED.
6. **Не тащи контекст субагентов в себя.** Получил короткий ответ "done, тест
   пройден, ID воркфлоу X" — записал в свой прогресс, идёшь дальше.
7. **Финальный отчёт** (когда все T-* пройдены):
   - Список done с 1-строчным описанием каждого.
   - Список BLOCKED с причиной.
   - Что под mock.
   - Команды для быстрой проверки (curl на каждый webhook).
   - Что завтра во Фазе 2.

## ЕСЛИ ТВОЙ КОНТЕКСТ ПЕРЕПОЛНЯЕТСЯ

**Это сигнал, что ты делаешь что-то не так.** Перечитай:
- Ты НЕ пишешь код сам — субагенты пишут.
- Ты НЕ запускаешь тесты сам — субагенты тестируют.
- Ты только передаёшь карточки и собираешь однострочные результаты.

Если всё равно переполняется — сократи список карточек в памяти до id + статус
(done/BLOCKED), детали в ~/factory/DEPLOYMENT.md пусть пишет субагент T-T.

## СТАРТОВЫЕ КОМАНДЫ

```bash
# Подключение
chmod 400 /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem
ssh -i /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem ubuntu@83.166.233.95

# Прочитай это сам (1 раз):
less ~/factory/DEPLOYMENT.md
less ~/factory/specs/11-amendments.md

# Запусти /autopilot и передавай карточки T-A..T-T
```

**Ты оркестратор. Работай через субагентов по /autopilot. Не тащи чужой контекст.**
