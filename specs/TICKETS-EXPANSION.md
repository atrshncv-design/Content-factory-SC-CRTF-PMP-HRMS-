# СПЕКИ + ТИКЕТЫ РАСШИРЕНИЯ (СПРИНТЫ 1-3)

> Этот файл — **детальные спецификации и гранулярные тикеты** для реализации
> расширения контент-завода. Каждый тикет = 1-3 часа работы, готов под
> автономного агента-разработчика через /autopilot.
>
> Порядок реализации: Спринт 1 (F) → Спринт 2 (SC+PM+UX) → Спринт 3 (CR).
>
> Первоисточники API: `specs/API-REFERENCES.md`. Перед реализацией каждого
> тикета — ОТКРЫТЬ соответствующую доку сервиса и сверить точный путь/параметры.

---

# 🚀 СПРИНТ 1 — ФИКСЫ ПЕРЕД ФАЗОЙ 2

## Спека F: обязательные фиксы

Подготовка системы к запуску Фазы 2 (end-to-end тест с реальной публикацией).
Без этих фиксов E2E не пройдёт.

---

### 🎫 F-2: Creatify remainingcredits — правильный эндпоинт

**Баг:** `GET /api/remainingcredits/` → HTTP 404 Not Found.

**Контекст:** Спека 04 Generation требует проверку остатка кредитов перед
запуском генерации (хард-лимит 100 видео/мес, credit_floor=50). Сейчас проверка
не работает.

**Задача:**
1. Открыть https://docs.creatify.ai/ → найти актуальный эндпоинт для баланса
   кредитов workspace.
2. Возможные варианты (проверить curl'ом):
   - `GET /api/remainingcredits` (без trailing slash)
   - `GET /api/credits/`
   - `GET /api/workspace/credits/`
   - `GET /api/workspaces/current/`
3. Найденный путь захардкодить в wf-creatify-submit (или вынести в отдельный
   `wf-credit-check`).
4. Тест: `curl -H "X-API-ID: $CID" -H "X-API-KEY: $CKEY" <URL>` → 200 с числом.

**Критерий:** GET возвращает 200 + число кредитов (либо объект с полем credits).
Воркфлоу проверяет остаток перед `POST /api/link_to_videos/` и при `<50` — алерт.

**Бюджет:** 30 минут.

---

### 🎫 F-3: (Заказчик) Подключить postmypost аккаунты

**Задача заказчика:** В кабинете https://postmypost.io подключить через OAuth:
- Instagram (бизнес-аккаунт, через Facebook)
- YouTube
- TikTok
- Threads
- X (Twitter)
- Telegram (канал)
- VK
- (опц.) LinkedIn, Facebook, Pinterest, Rutube

**Проверка:** `curl -H "Authorization: Bearer $TOKEN" "https://api.postmypost.io/v4.1/accounts?project_id=355928"`
должен вернуть массив с перечнем подключённых аккаунтов.

---

### 🎫 F-4: Реализация 8 команд wf-tg-bot

**Баг:** в wf-tg-bot нет веток для команд: `mode`, `topics`, `competitors`,
`accounts`, `budget`, `client`, `clients`, `reload_skills`. При вызове — default
"не понял".

**Задача:** Для каждой команды добавить ветку в wf-tg-bot с шаблоном ответа:

| Команда | Логика | Источник данных |
|---------|--------|-----------------|
| `mode manual\|auto` | UPDATE settings.mode → подтверждение | db-bridge |
| `topics` | Список тем за сегодня: id, status, title | `SELECT id, status, title FROM topics WHERE cycle_date=date('now')` |
| `competitors` | Список конкурентов активного клиента | `SELECT handle, platform FROM competitors WHERE client_id={active}` |
| `accounts` | Статус подключённых соцсетей | `SELECT name, platform, connection_status FROM social_accounts` |
| `budget` | Кредиты creatify + today/month videos + прогноз | settings + COUNT generations |
| `client <id>` | Сменить active_client_id (admin) | UPDATE settings |
| `clients` | Список клиентов | `SELECT id, name, status FROM clients` |
| `reload_skills` | (теперь NOOP, Hermes не используется как gateway) — удалить или сделать заглушкой | — |

**Критерий:** все 7 активных команд работают в live TG, `reload_skills` можно
удалить из menu (Hermes-gateway остановлен, скиллы не нужны оператору).

**Бюджет:** 90 минут.

---

### 🎫 F-5: Синхронизация git repo

**Задача:**
1. На сервере `~/factory/` нет `.git`. Создать git init на сервере ИЛИ
   синхронизировать через scp с локальной копией.
2. Файлы для синхронизации (то, что изменилось на сервере после последнего
   push): `DEPLOYMENT.md`, `specs/`, `infra/` (если есть новое), `workflows/`
   (JSON выгрузки новых воркфлоу).
3. Коммит с понятным сообщением, push в main.

**Критерий:** GitHub repo содержит актуальный `DEPLOYMENT.md` с разделом про
новую архитектуру (спека 13).

**Бюджет:** 30 минут.

---

### 🎫 F-E2E: End-to-end тест Фазы 2

**Задача:** после F-2..F-5 прогнать полный цикл на реальных ключах:
1. TG: `/onboard https://robotec.ru` → реальный профиль от scrapecreators.
2. TG: `/start_cycle` → реальная аналитика → выбор темы → сценарий → JSON →
   реальная генерация в creatify (5 кредитов) → callback готовности →
   скачивание MP4.
3. TG: выбор платформ → реальная публикация в Instagram Reels + Threads
   (или другие подключённые).
4. Проверить: metрики в postmypost появились, ролик виден в Instagram.

**Критерий:** 1 ролик реально опубликован в Instagram (или запланирован с
post_at в ближайший час). Все шаги прошли без ошибок в логах.

**Бюджет:** 60 минут (с отладкой).

---

# 📊 СПРИНТ 2 — РАСШИРЕНИЕ SCRAPECREATORS (SC)

## Спека SC: углублённая аналитика авторов и аудитории

ScrapeCreators — 36+ платформ. Мы используем только 4 (IG/TikTok/YT/X) для
трендов. Нужно добавить углублённый анализ **авторов** (профиль, контент,
аудитория, комментарии) — это даёт контент-заводу возможность:
- Находить конкурентов и микроинфлюенсеров по нише.
- Анализировать что у них заходит (топ-посты, метрики, комментарии).
- Понимать их аудиторию (пол/возраст/гео) для таргетинга.
- Извлекать идеи из комментариев («что обсуждают», «какие вопросы»).

**Все эндпоинты:** https://docs.scrapecreators.com/ (открыть перед реализацией).

**Авторизация:** `x-api-key: $SCRAPECREATORS_API_KEY` (header).

**Бюджет кредитов:** cache miss = 1 кредит, cache hit = 0. Включать `trim=true`
где доступно.

---

### 🎫 SC-1: wf-creators-search — поиск авторов по нише

**Эндпоинты:**
- `GET /v1/instagram/search/profiles?query=<ниша>&cursor=1`
- `GET /v1/youtube/search?type=channels&query=<ниша>`
- `GET /v1/tiktok/search/users?query=<ниша>`
- `GET /v1/twitter/search/profiles?query=<ниша>` (если есть)
- `GET /v1/tiktok/search/hashtag?hashtag=<tag>` (топ-авторы по хештегу)

**Логика воркфлоу:**
1. Webhook `/webhook/factory/creators-search` { query, platforms[] }.
2. Параллельные HTTP-вызовы к выбранным платформам.
3. Code: нормализация, дедупликация, топ-N (по follower_count).
4. Code: upsert в `competitors` (если нет — создать).
5. Respond: массив { handle, platform, followers, category, bio }.

**UI:** команда `/creators <niche>` → список топ-10 авторов в нише.

**Критерий:** `/creators промышленная робототехника` возвращает 5-10 реальных
авторов с метриками.

**Бюджет:** 60 минут.

---

### 🎫 SC-2: wf-creator-profile — профиль автора

**Эндпоинты:**
- `GET /v1/instagram/profile?username=<handle>` или `/basic-profile`
- `GET /v1/tiktok/profile?username=<handle>` (+ `/profile/region` если надо)
- `GET /v1/youtube/channel?id=<channelId>`
- `GET /v1/twitter/profile?username=<handle>`

**Логика:**
1. Webhook `/webhook/factory/creator-profile` { platform, handle }.
2. HTTP к нужному эндпоинту.
3. Code: нормализация ответа (follower_count, following_count, post_count,
   avg_engagement, bio, is_verified, category, profile_image_url).
4. Respond: JSON-профиль.

**UI:** команда `/creator <platform> <handle>` → карточка автора.

**Критерий:** `/creator tiktok @someuser` → полный профиль.

**Бюджет:** 30 минут.

---

### 🎫 SC-3: wf-creator-content — последние посты автора

**Эндпоинты:**
- `GET /v1/instagram/user/reels?username=<handle>&max_id=<pagination>`
- `GET /v1/tiktok/profile/videos?username=<handle>&max_cursor=<pagination>`
- `GET /v1/youtube/channel/videos?channel_id=<id>` (+ `/channel/shorts`)
- `GET /v1/twitter/user-tweets?username=<handle>`

**Логика:**
1. Webhook `/webhook/factory/creator-content` { platform, handle, limit=10 }.
2. HTTP к эндпоинту списка постов.
3. Code: нормализация, расчёт средней вовлечённости (ER = (likes+comments*3+shares*5)/views),
   топ-N по ER.
4. Respond: массив постов с метриками.

**UI:** команда `/creator-content <platform> <handle>` → список последних 10
роликов/постов с метриками.

**Критерий:** для топ-3 конкурентов клиента можно вытянуть их лучшие ролики и
проанализировать формат.

**Бюджет:** 60 минут.

---

### 🎫 SC-4: wf-audience — демография аудитории

**Эндпоинты:**
- `GET /v1/tiktok/user/audience?username=<handle>` (пол/возраст/гео)
- Для других платформ — см. доки (не все отдают аудиторию).

**Логика:**
1. Webhook `/webhook/factory/audience` { platform, handle }.
2. HTTP к эндпоинту.
3. Code: нормализация (gender%, age_ranges[], top_countries[]).
4. Respond: JSON с демографией.

**UI:** команда `/audience <platform> <handle>` → карточка демографии.

**Критерий:** для топ-3 конкурентов можно понять кто их аудитория.

**Бюджет:** 30 минут.

---

### 🎫 SC-5: wf-transcripts-comments — транскрипты и комментарии

**Эндпоинты:**
- `GET /v1/tiktok/video/transcript?url=<url>`
- `GET /v1/instagram/post/transcript?url=<url>` (если есть)
- `GET /v1/youtube/video/transcript?url=<url>`
- `GET /v1/tiktok/video/comments?url=<url>` (+ `/top`)
- `GET /v1/instagram/post/comments?url=<url>`
- `GET /v1/youtube/video/comments?url=<url>`

**Логика:**
1. Webhook `/webhook/factory/transcript` { url } → текст транскрипта.
2. Webhook `/webhook/factory/comments` { url, limit=50 } → массив комментариев
   с метриками (likes, replies), топ-N по вовлечённости.
3. Code: для топ-комментариев можно дополнительно дернуть ответы (replies).

**UI:**
- `/transcript <url>` → текст ролика.
- `/comments <url>` → топ-10 комментариев + общее настроение.

**Критерий:** для любого трендового ролика можно вытащить что в нём говорят и
что обсуждают в комментариях.

**Бюджет:** 90 минут.

---

# 🎬 СПРИНТ 3 — РАСШИРЕНИЕ CREATIFY (CR, PREMIUM)

## Спека CR: premium-режимы генерации Creatify

Сейчас используется только URL-to-video. Добавляем остальные режимы как
**premium-фичи** для апсейла клиентам. Все эндпоинты см. https://docs.creatify.ai/

**Авторизация:** `X-API-ID` + `X-API-KEY` (заголовки).
**Webhook:** все генеративные эндпоинты принимают `webhook_url` для callback.

---

### 🎫 CR-1: wf-creatify-avatar — Custom Avatar (BYOA, клон клиента)

**Эндпоинты:**
- `POST /api/personas/` (загрузка URL видео) — body: `{lipsync_input, creator_name, gender, video_scene}`.
- `POST /api/personas_v2/` (multipart upload файлов `video/mp4`).
- `GET /api/personas/{id}` (статус модерации: is_active=false→true, ~24ч).
- `GET /api/personas/?gender=&age_range=&suitable_industries=` (поиск библиотечных).

**Логика:**
1. Webhook `/webhook/factory/avatar-upload` { video_url, creator_name, gender }.
2. POST /api/personas/ → persona_id.
3. Запись в новую таблицу `custom_avatars` (id, client_id, persona_id, status, created_at).
4. Cron раз в час проверяет статус модерации → UPDATE status → алерт оператору
   «аватар одобрен».
5. При генерации URL-to-video (или другом режиме) можно указать
   `override_avatar = <persona_id>`.

**UI:**
- `/upload_avatar` → бот принимает видео-сообщение (или ссылку на MP4) →
  воркфлоу загружает → отслеживает модерацию → уведомление.
- `/my_avatars` → список аватаров клиента с их статусом.

**Критерий:** загрузка видео клиента → модерация → использование в ролике.

**Бюджет:** 120 минут.

---

### 🎫 CR-2: wf-creatify-text — Text Generator / AI Scripts

**Эндпоинты:**
- `POST /api/text_generator/` (async/streaming, модель Gemini).
- `POST /api/ai_scripts/` — body: `{title, description, language, target_audience, video_length}`.

**Логика:**
Альтернатива Hermes-LLM для текстовых задач внутри воркфлоу. Используется
когда нужен structured-ответ без вызова hermes-bridge.

**UI:** команда `/script <topic>` → AI Scripts генерит сценарий по теме.

**Критерий:** реальный сценарий от Creatify для заданной темы.

**Бюджет:** 45 минут.

---

### 🎫 CR-3: wf-creatify-asset — Asset/Image Generator

**Эндпоинт:** `POST /api/ai_generation/` (изображения товаров/визуал).

**Логика:**
1. Webhook `/webhook/factory/asset` { prompt, type, count }.
2. POST /api/ai_generation/.
3. Скачать результат в `/var/media/`.

**UI:** команда `/asset <описание>` → бот генерит картинку, присылает в TG.

**Критерий:** генерация изображения по описанию.

**Бюджет:** 45 минут.

---

### 🎫 CR-4: wf-creatify-adclone

**Эндпоинт:** `POST /api/ad_clones/` (12 кредитов / 5 сек!).

**Логика:** клонирование успешной чужой рекламы под клиента.
1. Webhook `/webhook/factory/adclone` { source_video_url, brand_assets }.
2. POST /api/ad_clones/.
3. Получить вариант под клиента.

**UI:** команда `/adclone <url>` → клон рекламы.

**Критерий:** реальный клон рекламы клиента.

**Бюджет:** 60 минут. ⚠️ Дорогой эндпоинт, использовать осторожно.

---

### 🎫 CR-5: wf-creatify-shorts

**Эндпоинты:** `POST /api/ai_shorts/`, `POST /api/ai_editing/`.

**Логика:** длинное видео → набор коротких Shorts/Reels.
1. Webhook `/webhook/factory/shorts` { source_video_url, max_count }.
2. POST /api/ai_shorts/.
3. Получить массив коротких роликов с таймстампами.

**UI:** команда `/shorts <url>` → нарезка Shorts.

**Критерий:** реальная нарезка.

**Бюджет:** 60 минут.

---

### 🎫 CR-6: wf-creatify-product

**Эндпоинт:** `POST /api/product_to_videos/` (2 кредита/изображение, 10/видео-30с).

**Логика:** изображение/видео товара → ролик (без URL).
1. Webhook `/webhook/factory/product` { image_url или video_url, target_audience }.
2. POST /api/product_to_videos/.

**UI:** команда `/product <image_url>` → ролик про товар.

**Критерий:** реальный ролик.

**Бюджет:** 60 минут.

---

### 🎫 CR-7: wf-creatify-banner

**Эндпоинты:** `POST /api/iab_images/` (стандартные IAB баннеры), `POST /api/inspiration/` (видео по шаблонам).

**Логика:** генерация рекламных баннеров для display-кампаний.

**UI:** команды `/banner <size> <prompt>` и `/inspiration <template_id>`.

**Критерий:** баннер IAB-размера.

**Бюджет:** 60 минут.

---

# 📤 СПРИНТ 2 — РАСШИРЕНИЕ POSTMYPOST (PM)

## Спека PM: все платформы и типы публикаций

Сейчас wf-publish работает с базовым набором (IG/YT/TikTok). Расширяем на все
20+ платформ Postmypost + Stories.

**Все эндпоинты:** https://help.postmypost.io/docs/api/

**Авторизация:** `Authorization: Bearer $POSTMYPOST_TOKEN`.

**Лимиты:** 10 запросов/мин на `/upload/*` и `POST /publications`.

---

### 🎫 PM-1: Расширение wf-publish под все платформы

**Эндпоинт:** `POST /v4.1/publications` с `details[]` под каждую платформу.

**Платформы для добавления:**
- Pinterest (пины)
- Rutube (видео)
- OK (посты)
- Discord (сообщения)
- Reddit (посты)
- Bluesky
- Tumblr
- Mastodon
- LinkedIn (профессиональные посты)
- Facebook (посты + Stories)

**Логика:**
1. Для каждой платформы определить её особенности (см. доку postmypost).
2. В wf-publish — Switch/Code для генерации details[] под выбранные платформы.
3. Проверка доступности платформы в `social_accounts` (GET /accounts).

**Критерий:** выбор 5+ разных платформ в `/publish` → все публикуются.

**Бюджет:** 120 минут.

---

### 🎫 PM-2: Поддержка Stories

**Эндпоинт:** тот же `POST /v4.1/publications` с `publication_type: 2` (STORY).

**Логика:**
1. В wf-publish добавить параметр `publish_type` (post/reels/story).
2. Для Story — короткий lived-контент, IG/FB.
3. UI: при `/publish` выбор типа.

**Критерий:** публикация в IG Story (через day-контент).

**Бюджет:** 60 минут.

---

### 🎫 PM-3: Адаптация caption под платформу

**Проблема:** один caption не подходит всем. X ≤280 символов, Threads длинный,
Telegram с кнопками, LinkedIn профессиональный тон.

**Решение 1 (быстро):** таблица шаблонов caption в БД (по платформе).
**Решение 2 (правильно):** мини-cубагент Hermes `caption-adapter` — принимает
базовый caption + платформу → отдаёт адаптированный.

**Логика:**
1. Новый скилл `caption-adapter` в hermes-bridge.
2. wf-publish для каждой платформы вызывает bridge с captions[i] = adapt(base, platform).
3. Получает адаптированный текст для details[i].content.

**Критерий:** для одной публикации в 4 разных соцсети — 4 разных caption.

**Бюджет:** 90 минут.

---

# 🎛 СПРИНТ 2 — РАСШИРЕНИЕ UX (UX)

## Спека UX: новые команды оператора

Добавить в wf-tg-bot команды для нового scope. Каждая команда = триггер + ветка
в Switch + вызов соответствующего воркфлоу.

---

### 🎫 UX-1: Новые TG-команды

**Команды для добавления в wf-tg-bot:**

| Команда | Что делает | Воркфлоу |
|---------|------------|----------|
| `/creators <niche>` | Поиск авторов в нише | SC-1 |
| `/creator <platform> <handle>` | Профиль автора | SC-2 |
| `/creator-content <platform> <handle>` | Посты автора | SC-3 |
| `/audience <platform> <handle>` | Демография аудитории | SC-4 |
| `/transcript <url>` | Транскрипт ролика | SC-5 |
| `/comments <url>` | Комментарии к ролику | SC-5 |
| `/upload_avatar` | Загрузка кастомного аватара | CR-1 |
| `/my_avatars` | Список аватаров клиента | CR-1 |
| `/asset <описание>` | Генерация изображения | CR-3 |
| `/shorts <url>` | Нарезка длинного в Shorts | CR-5 |
| `/product <image_url>` | Ролик про товар | CR-6 |
| `/banner <size> <prompt>` | IAB-баннер | CR-7 |
| `/publish_type post\|reels\|story` | Выбор типа публикации | PM-2 |

**Логика:**
1. В Code-ноде парсера команд добавить новые триггеры.
2. В Switch добавить ветки.
3. Для каждой — HTTP-запрос к соответствующему webhook'у `wf-*`.
4. Ответ от webhook → форматирование → Telegram Send.

**Также:** обновить setMyCommands через BotFather API с расширенным списком
(получится ~25 команд).

**Критерий:** все новые команды работают в live TG.

**Бюджет:** 90 минут (одна сессия).

---

# 📊 СВОДНАЯ ТАБЛИЦА ТИКЕТОВ

| ID | Спринт | Эпик | Бюджет | Зависимости |
|----|--------|------|--------|-------------|
| F-2 | 1 | Fixes | 30 мин | — |
| F-3 | 1 | (Заказчик) | — | — |
| F-4 | 1 | Fixes | 90 мин | — |
| F-5 | 1 | Fixes | 30 мин | — |
| F-E2E | 1 | Test | 60 мин | F-2, F-3, F-4 |
| SC-1 | 2 | ScrapeCreators | 60 мин | — |
| SC-2 | 2 | ScrapeCreators | 30 мин | — |
| SC-3 | 2 | ScrapeCreators | 60 мин | — |
| SC-4 | 2 | ScrapeCreators | 30 мин | — |
| SC-5 | 2 | ScrapeCreators | 90 мин | — |
| PM-1 | 2 | Postmypost | 120 мин | F-3 (аккаунты подключены) |
| PM-2 | 2 | Postmypost | 60 мин | PM-1 |
| PM-3 | 2 | Postmypost | 90 мин | — |
| UX-1 | 2 | UX | 90 мин | SC-1..5, PM-1..2 (воркфлоу готовы) |
| CR-1 | 3 | Creatify premium | 120 мин | — |
| CR-2 | 3 | Creatify premium | 45 мин | — |
| CR-3 | 3 | Creatify premium | 45 мин | — |
| CR-4 | 3 | Creatify premium | 60 мин | — |
| CR-5 | 3 | Creatify premium | 60 мин | — |
| CR-6 | 3 | Creatify premium | 60 мин | — |
| CR-7 | 3 | Creatify premium | 60 мин | — |

**Всего:** 21 тикет, ~22 часа работы.

---

# 🎯 ПОРЯДОК РЕАЛИЗАЦИИ

## Спринт 1 (сначала, ~4 часа)
F-2 → F-4 → F-5 (параллельно) → F-E2E (после F-3 от заказчика).

## Спринт 2 (~12 часов)
SC-1..SC-5 (параллельно) + PM-1..PM-3 (после F-3) + UX-1 (после SC+PM).

## Спринт 3 (~7.5 часов)
CR-1..CR-7 (по приоритету: CR-1 аватар первым как premium-фича, остальные по
запросу).

---

# 📐 ОБЩИЕ ПРАВИЛА ДЛЯ АГЕНТА-РАЗРАБОТЧИКА

1. **Перед каждым тикетом** открыть `specs/API-REFERENCES.md` и оригинальную
   документацию сервиса. Сверить точный эндпоинт, параметры, схему ответа.
2. **JSON-импорт через CLI** (`docker exec factory-n8n n8n import:workflow`),
   активация через n8n UI → Publish.
3. **Webhook path** без пробелов и кириллицы (питфолл с `tg-trigger`).
4. **Все HTTP-ноды** — retry 3x с backoff + логирование в factory.logs.
5. **Идемпотентность** для эндпоинтов, создающих сущности.
6. **Secrets** — через n8n Credentials или `.env`. Никогда inline.
7. **Бюджет** — проверять кредиты (creatify) и cache (scrapecreators).
8. **После каждого тикета** — live TG-тест или curl-тест webhook'а.
9. **Документация** — обновлять DEPLOYMENT.md после значимых изменений.
10. **Застрял >10 минут** — BLOCKED, переходи к следующему тикету.
