# Тикеты для разработчика

> Спеки — в `specs/`. Этот файл — **гранулярные задачи**, сгруппированные по фазам
> и эпикам. Принцип: разработчик берёт тикеты **по порядку, в рамках эпика**.
> P0 обязателен к дедлайну.
>
> ⚠️ **Важно:** спеки 03/06/10 содержат неточности, выявленные spike'ом T-030.
> Перед стартом **обязательно** прочитать `specs/11-amendments.md` — она
> суперседит конфликтующие части. Тикеты T-030…T-035 ниже уже приведены в соответствие.
>
> Гранулярность: один тикет = **1–3 часа** работы (сделать + проверить).
> Эпики (E0…E12) группируют тикеты по теме; внутри эпика — сверху вниз.
>
> Обозначения: **[P0]** обязательно · **[P1]** автопилот · **[P2]** следующий шаг.
> Формат тикета: `ID | заголовок | спека | критерии готовности`.

---

# Фаза P0 — Рабочий вертикальный срез (дедлайн: завтра)

**Цель P0:** на переговорах дать команду `/onboard https://robotec.ru` → завод
сам выводит профиль → оператор запускает цикл → 1 видео (30с, ru) опубликовано
в Instagram Reels. Всё через TG-бот с верификацией на каждом шаге.

---

## Эпик E0 — Инфраструктура и развёртывание (спека 00)

### T-001 | Выбрать и подготовить VPS | 00
- [ ] 2 vCPU / 4 GB RAM / 40 GB SSD, Ubuntu 22.04+, SSH по ключу.
- [ ] Пользователь `factory` (не root), sudo-права.
- [ ] Домен с A-записью → IP сервера (для HTTPS-вебхуков).
- [ ] UFW: открыть только 80, 443, 22; остальное localhost.

**Готово:** `ssh factory@<host>` работает, домен резолвится.

### T-002 | Установить Docker + Docker Compose | 00
- [ ] Docker Engine + Compose v2.
- [ ] Добавить `factory` в группу `docker`.
- [ ] Каталог проекта `/opt/factory/` с правами.

**Готово:** `docker compose version` → v2.x.

### T-003 | Написать docker-compose.yml | 00
- [ ] Сервис `n8n` (n8nio/n8n:latest, порт 5678, volume `n8n-data`).
- [ ] Сервис `hermes` (build `./hermes`, порт 8000, volume `hermes-data`).
- [ ] Shared volume `data` (SQLite) и `media` (MP4) для обоих.
- [ ] `env_file: .env`, `restart: unless-stopped`, `depends_on`.
- [ ] Healthcheck на n8n (`/healthz`).

**Готово:** `docker compose up` поднимает оба сервиса без ошибок.

### T-004 | Настроить reverse-proxy (Caddy) с HTTPS | 00
- [ ] Caddy в том же compose, порт 80/443.
- [ ] Домен → `localhost:5678` (n8n UI).
- [ ] Публичный маршрут только `/webhook/*` и `/media/*`; остальное за basic-auth или VPN.
- [ ] Авто-сертификат Let's Encrypt.

**Готово:** `https://<домен>/` открывает n8n UI с валидным сертификатом.

### T-005 | Заполнить .env и проверить .gitignore | 00
- [ ] `.env` из шаблона `.env.example`, реальные значения.
- [ ] Права `.env` = 600, владелец `factory`.
- [ ] Проверить `git status` — `.env`, `*.db`, `media/` не отслеживаются.

**Готово:** секреты на месте, в git не попадают.

### T-006 | Cron: бэкап БД и чистка media | 00
- [ ] cron/systemd-timer: копия `factory.db` → `/var/backups/`, хранение 7 копий (04:00).
- [ ] cron: `find /var/media -mtime +7 -delete` (03:30).
- [ ] cron: еженедельный `VACUUM` SQLite (воскресенье 05:00).

**Готово:** по расписанию файлы чистятся, бэкапы плодятся.

---

## Эпик E1 — n8n: креды и подключение (спека 00)

### T-010 | Создать n8n Credentials для всех сервисов | 00
- [ ] `scrapecreators` (Header Auth: `x-api-key`).
- [ ] `creatify` (Header Auth: `X-API-ID` + `X-API-KEY`).
- [ ] `postmypost` (Bearer).
- [ ] `telegram` (Bot Token).
- [ ] `n8n-api` (API key для вызовов Hermes→n8n).

**Готово:** 5 кред в n8n UI, зашифрованы (`N8N_ENCRYPTION_KEY`).

### T-011 | Smoke-тест: проверить API через HTTP-ноды | 00
- [ ] `GET https://api.creatify.ai/api/remainingcredits/` → 200 с числом кредитов.
- [ ] `GET https://api.postmypost.io/v4.1/accounts?project_id=...` → 200 со списком.
- [ ] `GET https://api.scrapecreators.com/v1/account/credit-balance` → 200.
- [ ] Логи не содержат ключей (маскирование).

**Готово:** все 3 API отвечают 200 из n8n.

### T-012 | Активировать публичный webhook URL | 00
- [ ] `WEBHOOK_URL` в env, n8n видит публичный адрес.
- [ ] Тестовый webhook-воркфлоу принимает запрос извне.

**Готово:** внешний POST на `/webhook/test` доходит до n8n.

---

## Эпик E2 — БД и миграции (спека 01, 08)

### T-020 | Миграция 001: основная схема | 01
- [ ] Файл `db/migrations/001_init.sql` со всеми таблицами: settings, users,
      competitors, topics, scripts, generations, posts, social_accounts, logs,
      schema_version.
- [ ] Прагмы: WAL, foreign_keys, synchronous=NORMAL, busy_timeout=5000.
- [ ] Семена settings (mode=manual, лимиты, клиент Robotec).
- [ ] Семена users (tg_user_id=941296693).
- [ ] Скрипт `db/migrate.sh` (применяет неприменённые миграции по `schema_version`).

**Готово:** `./migrate.sh` создаёт БД, все таблицы и seed на месте.

### T-021 | Миграция 002: онбординг и client_id | 08
- [ ] Таблицы `clients`, `client_socials`.
- [ ] Колонка `client_id INTEGER NOT NULL DEFAULT 1 REFERENCES clients(id)` в
      topics, scripts, generations, posts, competitors.
- [ ] settings.active_client_id = 1.

**Готово:** миграция проходит, foreign keys консистентны.

### T-022 | Подключить n8n SQLite-ноду к БД | 01
- [ ] Установить/активировать SQLite-ноду (community или built-in).
- [ ] Подключение к `/var/data/factory.db` (общий volume).
- [ ] Тест: INSERT + SELECT через Execute Workflow.

**Готово:** n8n пишет и читает SQLite.

---

## Эпик E3 — Hermes runtime (спека 10)

> ⚠️ **T-030 (spike) — первый и обязательный.** Результат решает: идём native
> (правим 03/06 по спеке 10) или fallback (03/06 как есть). До spike — не писать
> код оркестратора.

### T-030 | SPIKE: валидация Hermes Agent | 10 ✅ ВЫПОЛНЕН
> Закрыт оркестратором 2026-08-11. Результат — `specs/10-validation-report.md` и `specs/11-amendments.md`.
> Архитектура NATIVE подтверждена: chat работает, delegate_task работает, gateway setup существует.

### T-031' | Hermes как systemd-сервис (НЕ Docker) | 11, 10
> Заменяет T-031. Спека 11 правка 4.
- [ ] Создать `/etc/systemd/system/hermes.service` (пример в спеке 11).
- [ ] ExecStart: `/home/ubuntu/hermes-agent/.venv/bin/hermes gateway run`.
- [ ] `sudo systemctl enable --now hermes`.
- [ ] Проверить: `systemctl status hermes` → active (running).
- [ ] Логи: `journalctl -u hermes -f`.

**Готово:** Hermes стартует как сервис, переживает ребут, шлёт логи в journald.

### T-032' | Hermes gateway setup: подключить Telegram | 11, 06
> Заменяет T-033. Спека 11 правка 3.
- [ ] `hermes gateway setup` → выбрать Telegram → ввести токен бота.
- [ ] Указать whitelist: 941296693.
- [ ] Перезапустить `hermes gateway`.
- [ ] Написать боту `/start` → Hermes отвечает.
- [ ] НЕ настраивать Telegram Trigger в n8n (конфликт).

**Готово:** бот в TG отвечает, команда `/start` обрабатывается Hermes-агентом.

### T-033' | Skills оркестратора и субагентов | 11, 03
> Обновляет T-032. Спека 11 правка 2.
- [ ] Скопировать `~/factory/hermes/skills/*.md` в `~/.hermes/skills/`.
- [ ] Доработать `orchestrator.md`: добавить инструкцию «вызови n8n через
      `curl http://n8n:5678/webhook/factory/<wf>`» (Вариант A).
- [ ] `hermes skills list` → наши 4 skill видны.
- [ ] `hermes chat -q "Запусти цикл аналитики для клиента 1"` → агент
      вызывает wf-analytics через terminal+curl.
- [ ] State цикла — в memory Hermes (не в factory.db).

**Готово:** один запуск Hermes прогоняет analytics → выбор темы (через delegate_task Аналитика).

### T-034' | n8n webhook-ноды для вызовов из Hermes | 11, 03
> Новый тикет. Заменяет вымышленные `/internal/*` эндпоинты.
- [ ] В каждом wf-* добавить Webhook-ноду с путём:
      `/webhook/factory/analytics`, `/webhook/factory/onboard`,
      `/webhook/factory/creatify-link`, `/webhook/factory/creatify-submit`,
      `/webhook/factory/publish`.
- [ ] Webhook-ноды принимают POST с JSON, передают в основной воркфлоу.
- [ ] Тест: `curl -X POST http://n8n:5678/webhook/factory/analytics -d '{...}'` отрабатывает.

**Готово:** Hermes может вызывать все воркфлоу через простые HTTP-webhook'и.

### T-035' | (Опц. P1) MCP-мост Hermes ↔ n8n | 11, 03
> Опционально для P0 (Вариант A с terminal+curl достаточно). Для P1 — MCP чище.
- [ ] Написать MCP-мост (Node/Python) с инструментами run_analytics, submit_creatify, publish_post.
- [ ] Зарегистрировать через `hermes mcp add factory_n8n --command node -- args/bridge.js`.
- [ ] Заменить в skills curl-вызовы на MCP-инструменты.

**Готово:** Hermes оркестратор вызывает n8n через типобезопасный MCP-контракт.

---

## Эпик E4 — Онбординг клиента (спека 08) — КЛЮЧЕВОЙ ДЕМО-МОМЕНТ

### T-040 | n8n: воркфлоу wf-onboard (fetch сайта) | 08
- [ ] Webhook-trigger `POST /onboard` (от Hermes или TG).
- [ ] HTTP GET целевого URL (/, /about, /sitemap.xml) с таймаутом 10с/страница.
- [ ] Code-нода: извлечь title/meta og/h1/socials-links/email/текст (≤8k символов).
- [ ] SSRF-защита в Code-ноде: запрет приватных IP (10/8, 172.16/12, 192.168/16, 127/8).
- [ ] Лимит размера ответа 200 КБ.

**Готово:** `wf-onboard` для robotec.ru возвращает черновик с meta + TG-ссылкой.

### T-041 | n8n: поиск соцсетей через scrapecreators | 08
- [ ] Если соцссылок в футере нет — поиск:
  `GET /v1/instagram/search/profiles`, `/v1/youtube/search?type=channels`,
  `/v1/tiktok/search/users` по имени компании.
- [ ] Дедупликация по имени/URL.

**Готово:** для robotec находит хотя бы TG @robotec_tg.

### T-042 | Hermes: субагент-Онбординг (анализ черновика) | 08, 03
- [ ] System prompt с инструкцией извлечь профиль (ниша/тон/аудитория/соцсети/конкуренты/темы).
- [ ] Вход: URL + черновик из T-040.
- [ ] Выход: JSON строго по схеме спеки 08 (с confidence и gaps).
- [ ] Валидация ответа Оркестратором (parse + обязательные поля).

**Готово:** для robotec → профиль с industry=«промышленная робототехника».

### T-043 | Запись профиля в БД | 08
- [ ] INSERT clients (status=draft) + client_socials + competitors seed.
- [ ] После «Принять» → UPDATE clients status=active, settings.active_client_id.

**Готово:** профиль в БД, активный клиент переключается.

### T-044 | TG: команда /onboard + карточка профиля | 06, 08
- [ ] Команда `/onboard <url>` → Hermes → wf-onboard → карточка в TG.
- [ ] Карточка с кнопками `[✅ Принять] [✏️ Дополнить] [❌ Заново]`.
- [ ] Показ confidence и gaps.

**Готово:** `/onboard https://robotec.ru` → карточка за ≤1 мин.

---

## Эпик E5 — Аналитика трендов (спека 02)

### T-050 | n8n: wf-analytics — ветка Instagram | 02
- [ ] HTTP `GET /v2/instagram/reels/search?query=...&date_posted=last-day&page=1`.
- [ ] Code: нормализация, извлечение метрик, timestamp.
- [ ] Retry 3x на HTTP.

**Готово:** ветка отдаёт массив reels с метриками.

### T-051 | n8n: wf-analytics — ветка TikTok | 02
- [ ] HTTP `GET /v1/tiktok/search/keyword?query=...&sort_by=most-liked&date_posted=yesterday&trim=true`.
- [ ] Code: нормализация.

**Готово:** ветка отдаёт массив видео с метриками.

### T-052 | n8n: wf-analytics — ветка YouTube | 02
- [ ] HTTP `GET /v1/youtube/search?query=...&sortBy=popular&uploadDate=today&type=videos`.
- [ ] Code: нормализация.

**Готово:** ветка отдаёт массив видео с метриками.

### T-053 | Code: постфильтр 12–72 часа + дедуп + virality | 02
- [ ] Объединить 3 ветки.
- [ ] Оставить только где `now - timestamp ∈ [12h, 72h]`.
- [ ] Дедупликация по нормализованному URL/author.
- [ ] Расчёт virality_index (нормализованный play/like/share).
- [ ] Сортировка, топ-20.

**Готово:** для robotec — ≥10 кандидатов в окне 12–72ч.

### T-054 | Транскрипты топ-10 | 02
- [ ] Для топ-10 кандидатов: `GET /v1/*/transcript?url=...`.
- [ ] Прикрепить `transcript_excerpt` к каждому.

**Готово:** кандидаты содержат выдержку из содержания.

### T-055 | Поиск конкурентов (если нет seed) | 02, 08
- [ ] Если `find_competitors=true`: `/instagram/search/profiles` + `/youtube/search` + `/tiktok/search/users`.
- [ ] Выбор 5–10 релевантных, upsert в `competitors`.

**Готово:** таблица competitors наполняется.

### T-056 | wf-analytics: финальная сборка и ответ Hermes | 02
- [ ] Execute Workflow Trigger (для вызова Hermes).
- [ ] Финальный JSON `{candidates[], competitors_found[], meta{credits_spent}}`.
- [ ] HTTP POST → Hermes `/internal/analytics-ready`.
- [ ] При частичном сбое 1 ветки — warn, не падать.

**Готово:** Hermes получает топ-20 кандидатов.

---

## Эпик E6 — Субагенты цикла (спека 03)

### T-060 | Hermes: субагент-Аналитик | 03
- [ ] System prompt + урезанная справка creatify (что реализуемо).
- [ ] Вход: candidates[] + профиль клиента (из active_client_id).
- [ ] Выход: JSON {chosen, alternatives} по схеме спеки 03.
- [ ] Запись в topics (status=pending, chosen=1, client_id).

**Готово:** выбирает 1 тему в нише robotec с осмысленным rationale.

### T-061 | Hermes: субагент-Сценарист | 03
- [ ] System prompt с шаблоном Hook/Body/CTA.
- [ ] Вход: выбранная тема.
- [ ] Выход: JSON {hook, body, cta, full_text, target_length_sec}.
- [ ] Контроль длины (~2 слова/сек → 30с ≈ 60-70 слов).
- [ ] Запись в scripts (status=pending, client_id).

**Готово:** читаемый сценарий 30с, тон robotec, CTA на аудит.

### T-062 | Кеш аватаров и голосов creatify | 04
- [ ] Разовый `GET /api/personas/?gender=m&age_range=adult&style=presenter&suitable_industries=...`.
- [ ] Разовый `GET /api/voices/` → отфильтровать Russian.
- [ ] Выбор 2-3 аватаров и 1-2 голосов → settings.preferred_avatars/voices (JSON).
- [ ] Команда TG `/refresh_avatars` для обновления.

**Готово:** settings.preferred_* заполнены UUID'ами.

### T-063 | Hermes: субагент-JSON-сборщик | 03, 04
- [ ] System prompt со ВСЕЙ схемой link_to_videos (из спеки 04, раздел 4).
- [ ] Вход: сценарий + link UUID + webhook_url + аватар/голос из кеша.
- [ ] Выход: строго валидный JSON, без markdown.
- [ ] Валидация Оркестратором (parse + чек-схема enum'ов), 1 ретрай.

**Готово:** JSON проходит `POST /api/link_to_videos/` без 4xx.

---

## Эпик E7 — Генерация видео (спека 04)

### T-070 | n8n: wf-creatify-link | 04
- [ ] Webhook от Hermes {url, overrides?}.
- [ ] HTTP `POST /api/links/` {url} → link_id.
- [ ] (опц.) `PUT /api/links/{id}/` с переопределениями title/description/images.
- [ ] Возврат link_id.

**Готово:** link создаётся, UUID возвращается.

### T-071 | n8n: wf-creatify-submit | 04
- [ ] Webhook от Hermes {json_payload, link_id}.
- [ ] INSERT generations (status=pending, payload, client_id).
- [ ] Проверка дневного/месячного лимита и credit_floor ПЕРЕД отправкой.
- [ ] HTTP `POST /api/link_to_videos/` (с webhook_url, language=ru, 9x16).
- [ ] UPDATE generations.creatify_id.
- [ ] Retry 3x, алерт при невалидном JSON.

**Готово:** задача создаётся, creatify_id в БД.

### T-072 | n8n: wf-creatify-webhook (приём callback) | 04
- [ ] Webhook-эндпоинт `/webhook/creatify/<path-token>` (публичный).
- [ ] Идемпотентность: SELECT WHERE creatify_id=… (повтор не создаёт дубль).
- [ ] При done: скачать video_output + thumbnail в /var/media/<gen_id>.mp4.
- [ ] UPDATE generations (status=done, local_path, credits_spent≈5).
- [ ] HTTP → Hermes /internal/creatify-done.
- [ ] TG: видео в архив-канал + оператору с кнопками.
- [ ] При failed/rejected: UPDATE + алерт.

**Готово:** готовое видео в /var/media + БД + TG за ≤20 мин.

### T-073 | n8n: wf-creatify-poll (страховка) | 04
- [ ] Cron `*/5 * * * *`.
- [ ] SELECT creatify_id WHERE status IN (pending,running) AND created_at < now-15min.
- [ ] HTTP `GET /api/link_to_videos/?ids=…` (батч ≤100).
- [ ] Для терминальных — повторить логику T-072.

**Готово:** потерянный callback компенсируется поллингом.

---

## Эпик E8 — TG-бот (спека 06)

### T-080 | ~~wf-tg-incoming~~ УДАЛЕНО | 11
> Спека 11 правка 3. Приём TG-сообщений — целиком в Hermes (`hermes gateway`).
> n8n НЕ настраивает Telegram Trigger (конфликт с Hermes gateway).
> Соответствующая функциональность — в T-032' (hermes gateway setup).

### T-081' | n8n: wf-tg-alerts (односторонние алерты) | 11, 06
> Переименовано из wf-tg-send. Спека 11 правка 3.
- [ ] n8n Workflow с Webhook-нодой `/webhook/factory/tg-alert`.
- [ ] Принимает POST {chat_id, text, level?}.
- [ ] Telegram-нода (Send message) с тем же токеном бота (что и Hermes).
- [ ] Вызывается из других воркфлоу при: creatify failed, postmypost error,
      credits < floor, account auth_required.
- [ ] НЕ настраивать приём (Trigger) — только отправка.

**Готово:** любой n8n-воркфлоу может послать алерт оператору через
`curl POST http://n8n:5678/webhook/factory/tg-alert -d '{...}'`.

### T-082 | Hermes: роутинг команд в /tg/handle | 06, 03
- [ ] /start, /help — приветствие + список команд.
- [ ] /mode manual|auto — переключение, запись в settings.
- [ ] /start_cycle — вызов /internal/start-cycle.
- [ ] /status — сводка (режим, кредиты, счётчики) из /internal/status.
- [ ] /budget — подробный бюджет.
- [ ] /topics, /competitors, /accounts — списки из БД.
- [ ] /settings (admin) — просмотр/правка.
- [ ] /cancel — отмена ждущего этапа.

**Готово:** все команды отвечают осмысленно.

### T-083 | Hermes: обработка inline-кнопок в /tg/handle | 06
- [ ] Парсинг callback_data: approve/edit/reject/publish/platform/schedule/retry.
- [ ] approve:* → UPDATE status + /internal/decision=approve.
- [ ] edit:* → запросить текст, ожидание, UPDATE.
- [ ] reject:* → UPDATE status=rejected.
- [ ] publish:* → переход к выбору платформ.
- [ ] answerCallbackQuery + editMessageReplyMarkup (убрать кнопки).

**Готово:** кнопки работают на всех 4 этапах ручного цикла.

### T-084 | Сообщения 4 этапов ручного режима | 06
- [ ] Этап 1 (аналитика): тема + обоснование + кнопки [✅ Утвердить][✏️ Изменить][❌ Отклонить][🔄 Другая тема].
- [ ] Этап 2 (сценарий): текст + [✅][✏️][❌].
- [ ] Этап 3 (видео): MP4 + [✅ Опубликовать][✏️ Перегенерировать][❌ Отклонить].
- [ ] Этап 4 (площадки): чекбоксы соцсетей + [📤 Запланировать] + время.

**Готово:** оператор проходит все 4 этапа кнопками.

### T-085 | Канал-архив для резервного копирования MP4 | 06
- [ ] Приватный TG-канал, бот админ.
- [ ] TELEGRAM_ARCHIVE_CHAT_ID в env.
- [ ] T-072 шлёт туда каждое готовое видео.

**Готово:** видео дублируются в канал-архив.

### T-086 | Алерты в TG | 06
- [ ] creatify failed, postmypost error, кредиты < floor, дневной лимит,
      аккаунт требует OAuth, scrapecreators частичный сбой, цикл завершён.
- [ ] Все через wf-tg-send.

**Готово:** все события раздела 7 спеки 06 приходят.

---

## Эпик E9 — Сквозная интеграция P0

### T-090 | Подключить соцсети в кабинете postmypost | 05
> Ручная задача для админа (не код). Минимум Instagram + Threads для демо.
- [ ] В кабинете postmypost подключить Instagram (OAuth).
- [ ] Подключить Threads.
- [ ] (опц.) YouTube, TikTok, VK, Telegram.

**Готово:** GET /accounts отдаёт подключённые.

### T-091 | Публикация в ручном режиме (1 клик) | 05, 06
> Минимальный путь постинга для P0 (автопостинг — уже P1, T-102).
- [ ] После «✅ Опубликовать» (этап 4) → wf-publish с 1 платформой.
- [ ] POST /upload/init (URL нашего MP4) → поллинг /upload/status → file_id.
- [ ] POST /publications (status=5, post_at, details[] для IG Reels).
- [ ] Соблюдение 10/мин (пауза 7с).
- [ ] Запись в posts, TG-уведомление «запланировано».

**Готово:** видео уходит в очередь postmypost на публикацию.

### T-092 | End-to-end тест: полный цикл robotec | 00
- [ ] /onboard https://robotec.ru → профиль принят.
- [ ] /start_cycle → аналитика → тема → сценарий → JSON → генерация → видео.
- [ ] Утверждение на каждом этапе через кнопки.
- [ ] Публикация в Instagram Reels.
- [ ] Проверка идемпотентности вебхука, алертов, статусов.

**Готово:** 1 видео robotec опубликовано без правки кода.

### T-093 | Документация по запуску (README проекта) | 00
- [ ] Инструкция: `docker compose up`, первичная настройка, команды TG.
- [ ]Troubleshooting (частые проблемы: webhook не доходит, БД locked, и т.д.).

**Готово:** новый разработчик поднимает завод по README.

---

# Фаза P1 — Автопилот (завтра, если P0 закрыт)

## Эпик E10 — Авто-режим и автопостинг (спеки 00, 05, 06)

### T-100 | Cron-триггер авто-цикла (09:00 MSK) | 00
- [ ] Cron-нода n8n → POST Hermes /internal/start-cycle.
- [ ] В auto-режиме: пауз нет, бот шлёт инфо без кнопок.

### T-101 | wf-publish: мультиплатформенная публикация | 05
- [ ] details[] под каждую платформу (Reels/Shorts/TikTok/Threads/X/TG).
- [ ] Адаптация caption (базовый + мини-правки).

### T-102 | wf-publish-status: поллинг статусов | 05
- [ ] Cron `*/2 * * * *`. GET /publications/{id}. Ловим 2→1 / →3.
- [ ] UPDATE posts, TG-уведомление.

### T-103 | wf-sync-accounts: раз в час | 05
- [ ] GET /accounts → upsert social_accounts. Алерт при connection_status=2.

### T-104 | wf-credit-check: мониторинг кредитов | 04
- [ ] Cron раз в час: GET /api/remainingcredits/.
- [ ] settings.credits_remaining. Алерт при < floor.

## Эпик E11 — Устойчивость и мониторинг

### T-110 | Ротация логов (03:00) | 01
- [ ] cron: DELETE FROM logs WHERE ts < datetime('now','-7 days').

### T-111 | Проверка всех retry-политик | 00
- [ ] scrapecreators 402/500/429 → 3 попытки + backoff.
- [ ] postmypost 429 → Retry-After.
- [ ] Hermes unavailable → retry + алерт.

### T-112 | Smoke-тест авто-режима 24ч | 00
- [ ] Завод работает сутки в auto без ручного вмешательства.

---

# Фаза P2 — После закрытия клиента

## Эпик E12 — Аналитика собственных роликов (спека 07)

### T-200 | Миграция 003: post_metrics + поля | 07
- [ ] Таблица post_metrics. posts.external_url, scripts.format_tag.

### T-201 | wf-self-analytics (cron 21:00) | 07
- [ ] Сбор метрик scrapecreators по своим постам за 14д.
- [ ] Расчёт ER, «выстрелившие» (>1.5×медианы).

### T-202 | Hermes: performance-digest в промпт Аналитика | 07
- [ ] /internal/performance-digest → подмешивание в промпт.

### T-203 | wf-weekly-digest (воскресенье 10:00) | 07
- [ ] Сводка в TG оператору.

## Эпик E13 — Веб-дашборд (спека 09)

### T-210 | Next.js: сервис + login | 09
- [ ] dashboard в docker-compose, порт 3000. Login по паролю, session-cookie.

### T-211 | Страницы P2.0: dashboard/videos/posts/new/onboard/settings/logs | 09
- [ ] Server Components → SQLite read-only. Server Actions для write.

### T-212 | Запуск цикла/онбординга из UI через Hermes | 09
- [ ] Те же эндпоинты /internal/*, что и TG.

### T-213 | Страница /analytics (P2.1) | 07, 09
- [ ] Графики по post_metrics (recharts).

### T-214 | Мульти-тенантность (P2.2) | 09
- [ ] dashboard_users, изоляция по client_id.

### T-215 | EN-язык (P2.2) | —
- [ ] language в промптах и creatify, i18n UI.

### T-216 | Расписание drag-and-drop + OAuth Google (P2.3) | 09

---

# Зависимости (граф по эпикам)

```
E0 (инфра) ──► E1 (n8n креды) ──► E2 (БД) ──► E3 (Hermes runtime) ──┐
                                                                      │
                E4 (онбординг) ◄──────────────────────────────────────┤
                                                                      │
                E5 (аналитика) ──► E6 (субагенты) ──► E7 (генерация) ──┤
                                                                      │
                E8 (TG-бот) ◄─────────────────────────────────────────┘
                                                                      │
                E9 (сквозная интеграция + публикация) ◄────────────────┘

P1: E10 (авто), E11 (устойчивость) — после E9.
P2: E12 (метрики), E13 (дашборд) — после закрытия клиента.
```

**Последовательность для P0:** E0 → E1 → E2 → (E3 параллельно с E4/E5/E8 заглушками)
→ E4 → E5 → E6 → E7 → E8 → E9.

---

# Чек-лист «можно показывать клиенту» (Definition of Done для P0)

- [ ] `/onboard https://robotec.ru` за ≤1 мин выводит профиль (ниша/тон/соцсети/конкуренты/темы).
- [ ] Бот отвечает `/start`, оператор (941296693) в whitelist.
- [ ] `/start_cycle` запускает ручной цикл, 4 этапа с кнопками.
- [ ] 1 видео robotec (30с, ru) сгенерировано через creatify.
- [ ] Видео опубликовано (или запланировано) в Instagram Reels.
- [ ] Алерты приходят при failed-сценариях.
- [ ] `/status` показывает остаток кредитов и счётчики.
- [ ] Бэкап БД и чистка media работают по расписанию.
- [ ] Новый клиент заводится одной командой `/onboard`.
- [ ] Компенсирующий поллинг creatify работает (если убрать webhook — видео всё равно приходит).

---

# Статистика

- **P0:** 9 эпиков (E0–E9), ~50 тикетов (T-001…T-093).
- **P1:** 2 эпика (E10–E11), 13 тикетов.
- **P2:** 2 эпика (E12–E13), 17 тикетов.
- **Всего:** 13 эпиков, ~80 тикетов.
