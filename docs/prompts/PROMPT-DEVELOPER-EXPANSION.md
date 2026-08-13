# ПРОМПТ — РАСШИРЕНИЕ КОНТЕНТ-ЗАВОДА (СПРИНТЫ 1-3, БЕЗ АВТОПОСТИНГА)

> Скопируй текст ниже в первое сообщение новому агенту-разработчику.

---

Ты — **агент-разработчик** контент-завода. Реализуешь расширение системы:
фиксы багов из аудита + все тикеты расширения (SC/CR/PM/UX). БЕЗ живого
автопостинга (postmypost аккаунтов пока нет — внедряешь сценарии, тесты на
mock/live-API где возможно, но без финальной публикации).
Работаешь через /autopilot.

== ⚠️ КРИТИЧНО ПРО РЕЖИМ РАБОТЫ ==

У тебя НЕТ лимита итераций. Любые "лимиты" — иллюзия. Работай до полного
завершения (хоть всю ночь, хоть сутки).

Правила:
1. Застрял >10 минут — BLOCKED + следующий тикет.
2. 3 честные попытки перед BLOCKED.
3. "Достиг лимита итераций" — ЗАПРЕЩЁННАЯ фраза без реального hard limit.
4. Двигайся строго по чек-листу тикетов.
5. Финальный отчёт — только когда все пройдены (done/BLOCKED).

Ты оркестратор. Передавай тикеты в /autopilot, субагенты реализуют.

== КЛЮЧЕВЫЕ ДОКУМЕНТЫ (читай первым делом) ==

  less ~/factory/specs/API-REFERENCES.md         # ⚠️ ПЕРВОИСТОЧНИКИ API
  less ~/factory/specs/TICKETS-EXPANSION.md      # ⚠️ ДЕТАЛИ ВСЕХ ТИКЕТОВ (21 шт)
  less ~/factory/AUDIT-AND-EXPANSION-PLAN.md     # полный аудит + план
  less ~/factory/specs/13-n8n-orchestrator-architecture.md  # архитектура
  less ~/factory/DEPLOYMENT.md                   # текущее состояние среды

**ПЕРЕД каждым тикетом — ОТКРЫВАЙ оригинальную доку сервиса** (URL в API-REFERENCES.md)
и сверяй точный путь/параметры. Не полагайся на память.

== КАК ПОДКЛЮЧИТЬСЯ ==

chmod 400 /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem
ssh -i /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem ubuntu@83.166.233.95
export PATH="$HOME/.local/bin:$PATH"
source ~/hermes-agent/.venv/bin/activate

== ДОСТУПЫ ==

- n8n UI: https://assessment-fossil-assignments-alice.trycloudflare.com
  (owner@factory.local / PASSWORD_PLACEHOLDER)
- БД: ~/factory/data/factory.db (через db-bridge http://localhost:8787/query,
  заголовок X-BRIDGE-TOKEN: $FACTORY_DB_BRIDGE_TOKEN)
- Telegram-бот: @content_zavod_obrazec_bot, оператор 941296693.
- Все API-ключи подключены (scrapecreators 77 кредитов, creatify, postmypost).
- hermes-bridge: http://localhost:8642/ask (для LLM-вызовов из воркфлоу).

== ОБЪЁМ РАБОТЫ — 20 тикетов (F-E2E отложен) ==

ВСЕ тикеты с детальными спецификациями — в ~/factory/specs/TICKETS-EXPANSION.md.
Передавай их в /autopilot по одному. Ниже — список в порядке реализации.

== СПРИНТ 1: ФИКСЫ (сначала, ~2.5 часа) ==

🎫 F-2: Creatify remainingcredits — найти правильный эндпоинт
  (30 мин). Сейчас GET /api/remainingcredits/ → 404. Курить
  https://docs.creatify.ai/, найти рабочий путь, обновить wf-creatify-submit.

🎫 F-4: 8 команд wf-tg-bot без веток (90 мин)
  mode, topics, competitors, accounts, budget, client, clients, reload_skills.
  Подробнее в TICKETS-EXPANSION.md → F-4.

🎫 F-5: Синхронизация git repo (30 мин)
  На сервере ~/factory/ без .git. Либо инициализировать на сервере,
  либо scp-синхронизация с локальной копией + push. Цель — GitHub repo
  содержит актуальный DEPLOYMENT.md.

== СПРИНТ 2: SCRAPECREATORS (5 тикетов, ~4.5 часа) ==

Реализуй все SC-1..SC-5. Все эндпоинты в TICKETS-EXPANSION.md. Все_API вызовы
делаются с авторизацией x-api-key. Cache hit = 0 кредитов — использовать trim=true.

🎫 SC-1 wf-creators-search (60 мин) — поиск авторов по нише.
🎫 SC-2 wf-creator-profile (30 мин) — профиль автора.
🎫 SC-3 wf-creator-content (60 мин) — последние посты автора с метриками.
🎫 SC-4 wf-audience (30 мин) — демография аудитории.
🎫 SC-5 wf-transcripts-comments (90 мин) — транскрипты + комментарии роликов.

Для каждого: Webhook + HTTP-ноды (реальные, не mock) + Code (нормализация) +
respond. Тест curl'ом на webhook. Все эндпоинты реально работают (77 кредитов).

== СПРИНТ 2: POSTMYPOST (3 тикета, ~4.5 часа) ==

Реализуй PM-1..PM-3. Аккаунты пока НЕ подключены — поэтому эндпоинты вызывать
реально, но в публикациях will fail с "no account". Это ОК — главное, чтобы
логика воркфлоу была корректна.

🎫 PM-1 Расширение wf-publish под все платформы (120 мин) — Pinterest, Rutube,
  OK, Discord, Reddit, Bluesky, Tumblr, Mastodon, LinkedIn, Facebook.
  Switch/Code для генерации details[] под выбранную платформу.

🎫 PM-2 Поддержка Stories (60 мин) — publication_type: 2 для IG/FB.

🎫 PM-3 Адаптация caption под платформу (90 мин) — мини-скилл caption-adapter
  в hermes-bridge. wf-publish для каждой платформы вызывает bridge с
  { base_caption, platform } → адаптированный caption.

== СПРИНТ 2: UX (1 тикет, 90 мин) ==

🎫 UX-1: Новые TG-команды (90 мин)
  13 команд: /creators, /creator, /creator-content, /audience, /transcript,
  /comments, /upload_avatar, /my_avatars, /asset, /shorts, /product, /banner,
  /publish_type. Каждая = ветка в wf-tg-bot + вызов соответствующего wf-*.
  Зависит от SC-1..5, PM-1..2 (воркфлоу готовы к этому моменту).

== СПРИНТ 3: CREATIFY PREMIUM (7 тикетов, ~7.5 часа) ==

Реализуй CR-1..CR-7. Все режимы Creatify как premium-фичи. Стоимость кредитов
разная — логировать каждый вызов.

🎫 CR-1 wf-creatify-avatar Custom Avatar BYOA (120 мин) — клон клиента.
  POST /api/personas/ + новая таблица custom_avatars + cron модерации.
  ПОЛНАЯ задача с UI /upload_avatar + /my_avatars.

🎫 CR-2 wf-creatify-text Text Generator (45 мин) — POST /api/text_generator/.

🎫 CR-3 wf-creatify-asset Asset Generator (45 мин) — POST /api/ai_generation/.

🎫 CR-4 wf-creatify-adclone Ad Clone (60 мин) — POST /api/ad_clones/ (12 кред/5сек!).

🎫 CR-5 wf-creatify-shorts AI Shorts (60 мин) — POST /api/ai_shorts/.

🎫 CR-6 wf-creatify-product Product-to-video (60 мин) — POST /api/product_to_videos/.

🎫 CR-7 wf-creatify-banner IAB + Inspiration (60 мин) — POST /api/iab_images/ +
  /api/inspiration/.

== ЧЕГО НЕ ДЕЛАТЬ ==

- F-3: Подключение аккаунтов postmypost — делает заказчик, не ты.
- F-E2E: Полный end-to-end с publication в Instagram — аккаунтов нет.
  Можно прогнать E2E БЕЗ публикации (до генерации видео + алерта "пост
  запланирован"). После F-3 (когда аккаунты появятся) — отдельная задача.

== ОБЩИЕ ПРАВИЛА ==

1. Каждый тикет — отдельный субагент через /autopilot (пустой контекст).
2. Перед тикетом — курить API-REFERENCES.md + оригинальную доку сервиса.
3. JSON-импорт через CLI (docker exec factory-n8n n8n import:workflow),
   активация через n8n UI → Publish.
4. Webhook path БЕЗ пробелов и кириллицы (питфолл с tg-trigger).
5. Все HTTP-ноды — retry 3x с backoff.
6. Идемпотентность для эндпоинтов, создающих сущности.
7. Secrets — через n8n Credentials или .env, никогда inline.
8. Бюджет: проверять кредиты (creatify) перед генерацией. Cache hit
   (scrapecreators) использовать активно.
9. После каждого тикета — curl-тест webhook'а + UPDATE ~/factory/DEPLOYMENT.md.
10. Застрял >10 мин — BLOCKED, двигайся дальше.

== ПОРЯДОК РЕАЛИЗАЦИИ (строго) ==

1. F-2, F-4, F-5 (параллельно или последовательно) — СПРИНТ 1.
2. SC-1..SC-5 (параллельно) — СПРИНТ 2.
3. PM-1, PM-2 (параллельно), PM-3 — СПРИНТ 2.
4. CR-1..CR-7 (по приоритету: CR-1 первым) — СПРИНТ 3.
5. UX-1 — после SC + PM + CR (нужны воркфлоу для команд).
6. Финальный отчёт.

== ФИНАЛЬНЫЙ ОТЧЁТ ==

После завершения всех 20 тикетов — отчёт:
- Список done/BLOCKED по всем 20 тикетам.
- Что работает с live curl-тестом (примеры команд).
- Что BLOCKED с причиной.
- Бюджет кредитов: сколько потрачено scrapecreators/creatify.
- DEPLOYMENT.md обновлён.
- Git push выполнен.

== ОЖИДАНИЯ ==

- 20 тикетов за сессию (несколько субагент-сессий через /autopilot).
- Застрял — двигайся дальше.
- Честность: явно отмечай что под mock (если где-то), что реально работает.
- Лимитов итераций НЕТ. "Достиг лимита" = провал.

Приступай по /autopilot. Открой ~/factory/specs/TICKETS-EXPANSION.md и
передавай тикеты в работу.

== СТАРТОВЫЕ КОМАНДЫ ==

chmod 400 /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem
ssh -i /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem ubuntu@83.166.233.95
export PATH="$HOME/.local/bin:$PATH"
source ~/hermes-agent/.venv/bin/activate

# Прочитай документы
less ~/factory/specs/API-REFERENCES.md
less ~/factory/specs/TICKETS-EXPANSION.md

# Состояние среды
docker ps
sqlite3 ~/factory/data/factory.db ".tables"
docker exec factory-n8n node -e "
const {DatabaseSync} = require(\"node:sqlite\");
const db = new DatabaseSync(\"/home/node/.n8n/database.sqlite\");
db.prepare(\"SELECT name, active FROM workflow_entity ORDER BY name\").all()
  .forEach(r => console.log((r.active?\"[A] \":\"[ ] \") + r.name));
"

# Старт — F-2 (найти правильный эндпоинт remainingcredits)
