# АУДИТ + ПЛАН РАСШИРЕНИЯ (13.08.2026)

**Заказчик:** пользователь выполнил подключение ключей всех 3 сервисов.
**Scope (согласован):** см. `specs/API-REFERENCES.md`.
**Подход:** аудит → план → реализация.

---

## ЧАСТЬ 1. АУДИТ ТЕКУЩЕГО ПРОЕКТА

### 1.1. Что РАБОТАЕТ (подтверждено)

| Компонент | Статус | Доказательство |
|-----------|--------|----------------|
| Docker: n8n + db-bridge + cloudflared | ✅ Up | `docker ps` |
| Hermes (gateway остановлен, CLI работает через hermes-bridge) | ✅ | `systemctl inactive` — корректно после миграции на спеку 13 |
| Telegram webhook зарегистрирован | ✅ | getWebhookInfo: last_error: none, allowed: [message, callback_query] |
| 11 n8n-воркфлоу активны | ✅ | все `[ACTIVE]` в БД n8n |
| БД factory.db: 14 таблиц | ✅ | sessions в IDLE для 941296693 |
| Креды в n8n для 4 сервисов | ✅ | scrapecreators, creatify, postmypost, telegram |
| Ключи в `.env` реальные | ✅ | scrapecreators/creatify/postmypost подключены |
| `.env` права 600 | ✅ | `-rw-------` |
| `wf-onboard` (HTTP fetch robotec.ru) | ✅ | прошлый прогон был зелёным |
| `wf-tg-bot` webhook path `tg-trigger` | ✅ | после фикса аудитора (пробел в имени) |

### 1.2. НАХОДКИ — что плохо или отсутствует

| # | Находка | Severity | Статус |
|---|---------|----------|--------|
| **Б1** | **Утечка ключей**: реальные значения `SCRAPECREATORS_API_KEY` / `CREATIFY_*` / `POSTMYPOST_TOKEN` прошли через output SSH в лог оркестратора (ZCode). | 🔴 КРИТИЧНО | Требуется ротация после завершения работы. |
| **Б2** | **Creatify `/api/remainingcredits/` даёт 404**. Воркфлоу `wf-credit-check` (если есть) или встроенная проверка перед генерацией не работает. | 🟠 ВАЖНО | Сверить путь с https://docs.creatify.ai/, возможно `GET /api/credits/` или `/api/workspace/credits/`. |
| **Б3** | **Postmypost аккаунты НЕ подключены**. `GET /accounts` → `data: [], total: 0`. Без этого автопостинг невозможен. | 🟠 ВАЖНО | Пользователь обещал подключить сегодня. |
| **Б4** | **8 команд без реализации** в wf-tg-bot: `mode`, `topics`, `competitors`, `accounts`, `budget`, `client`, `clients`, `reload_skills`. Бот их зарегистрировал в BotFather, но веток нет → при вызове вернётся default "не понял". | 🟡 СРЕДНЕ | Добавить ветки или удалить из menu. |
| **Б5** | **Документация в git не синхронизирована** с сервером. На сервере DEPLOYMENT.md актуален (после миграции), в GitHub — устарел. | 🟡 СРЕДНЕ | Коммит + push. |
| **Б6** | **Нет cron для `wf-self-analytics`** (P2, по спеке 07). Метрики по своим постам не собираются. | 🟢 НИЗКО | P2, отложено. |
| **Б7** | **`N8N_API_KEY` в `.env` есть, но публичный API n8n требует ключ из UI** (401 на REST). Известная находка, не критична. | 🟢 НИЗКО | Внутренние операции делаем через CLI/SQL. |
| **Б8** | **Логи за последний час пусты** — Hermes-gateway остановлен, n8n не получает сообщений от оператора. Норма, но говорит о простое. | 🟢 НИЗКО | Ждём live-тест или подключение аккаунтов postmypost. |

### 1.3. ГЭПЫ ОТНОСИТЕЛЬНО ВЫБРАННОГО SCOPE

| Что нужно (scope) | Что есть сейчас | Гэп |
|--------------------|-----------------|-----|
| **ScrapeCreators: тренды + поиск** | wf-analytics (3 ветки: IG/TikTok/YT) | ✅ Закрыто |
| **ScrapeCreators: авторы углублённо** (профили, посты, аудитория, комментарии) | ❌ Нет | Новый воркфлоу `wf-creators-deep` |
| **Creatify: URL-to-video** | wf-creatify-link + wf-creatify-submit | ✅ Закрыто |
| **Creatify: Custom Avatar (BYOA)** | ❌ Нет | Новый воркфлоу `wf-creatify-avatar` (загрузка/обучение/использование) |
| **Creatify: Text Generator / AI Scripts** | ❌ Нет (делает Hermes-LLM) | Решение: оставить в Hermes ИЛИ добавить отдельный воркфлоу |
| **Creatify: Asset/Image Generator** | ❌ Нет | Новый воркфлоу `wf-creatify-asset` |
| **Creatify: Ad Clone** | ❌ Нет | Новый воркфлоу `wf-creatify-adclone` |
| **Creatify: AI Shorts / Editing** | ❌ Нет | Новый воркфлоу `wf-creatify-shorts` |
| **Creatify: Product-to-video** | ❌ Нет | Новый воркфлоу `wf-creatify-product` |
| **Creatify: IAB баннеры / Inspiration** | ❌ Нет | Новый воркфлоу `wf-creatify-banner` |
| **Postmypost: видео-платформы** | wf-publish (детализация по платформам в details) | ⚠️ Частично — проверить какие платформы реально прописаны |
| **Postmypost: Stories (IG/FB)** | ❌ Нет | Расширение `wf-publish` + UI для выбора типа |
| **Postmypost: текстовые платформы** (X/Threads/Telegram/LinkedIn/FB) | ⚠️ Частично | Проверить какие платформы есть |
| **Postmypost: нишевые** (Pinterest/Rutube/OK/Discord/Reddit/Bluesky/Tumblr/Mastodon) | ❌ Нет | Расширение `wf-publish` |

---

## ЧАСТЬ 2. ПЛАН РАСШИРЕНИЯ

### Принцип

Расширение делать **по приоритетам**, не всё сразу. Сначала фиксим баги, потом
расширяем scope. Каждый блок — отдельный epic с тикетами.

### Epic F (Fixes) — обязательные фиксы перед расширением

#### F-1: Ротация ключей (заказчик)
Заказчик ротирует все 4 ключа (scrapecreators, creatify API_ID+KEY, postmypost)
в кабинах сервисов, передаёт новые значения. Обновляем `~/factory/.env` и
Credentials в n8n UI.

#### F-2: Creatify remainingcredits — правильный эндпоинт
- Открыть https://docs.creatify.ai/, найти актуальный путь для остатка кредитов.
- Обновить `wf-credit-check` или логику в `wf-creatify-submit`.
- Тест: GET должен вернуть 200 с числом кредитов.

#### F-3: Postmypost аккаунты (заказчик)
Заказчик подключает Instagram/YouTube/TikTok/Threads/X/Telegram/VK в кабинете
postmypost. После — `GET /accounts` должен отдать массив.

#### F-4: 8 команд wf-tg-bot (реализация или удаление)
Реализовать ветки: `mode`, `topics`, `competitors`, `accounts`, `budget`,
`client`, `clients`, `reload_skills`. Для каждой — шаблон ответа (см. спеку 12).

#### F-5: Синхронизация git repo
Коммит DEPLOYMENT.md и других изменённых файлов с сервера → push в GitHub.

### Epic SC (ScrapeCreators расширение)

#### SC-1: Воркфлоу `wf-creators-search`
- Эндпоинты: `/v1/instagram/search/profiles`, `/v1/youtube/search?type=channels`,
  `/v1/tiktok/search/users`, `/v1/twitter/search/profiles`.
- Назначение: поиск авторов по нише/ключевику. Используется в онбординге клиента
  и в аналитике конкурентов.

#### SC-2: Воркфлоу `wf-creator-profile`
- Эндпоинты: `/v1/{platform}/profile` (по handle/id).
- Назначение: полные данные автора (followings, bio, средние метрики, и пр.).

#### SC-3: Воркфлоу `wf-creator-content`
- Эндпоинты: `/v1/instagram/user/reels`, `/v1/tiktok/profile/videos`,
  `/v1/youtube/channel/videos`, `/v1/twitter/user-tweets`.
- Назначение: последние N постов автора с метриками.

#### SC-4: Воркфлоу `wf-audience`
- Эндпоинты: `/v1/tiktok/user/audience`, и пр.
- Назначение: демография аудитории автора (пол/возраст/гео).

#### SC-5: Воркфлоу `wf-transcripts-comments`
- Эндпоинты: `/v1/{platform}/video/transcript`, `/v1/{platform}/video/comments`.
- Назначение: транскрипты + комментарии для анализа (что обсуждают, какие вопросы).

### Epic CR (Creatify расширение)

#### CR-1: Воркфлоу `wf-creatify-avatar` (Custom Avatar BYOA)
- Эндпоинты: `POST /api/personas/` (загрузка URL видео), `POST /api/personas_v2/`
  (multipart upload), `GET /api/personas/{id}` (статус модерации).
- Назначение: клонирование лица/голоса клиента. Premium-фича.
- UI в TG: команда `/upload_avatar` → бот принимает видео → воркфлоу загружает
  в Creatify → ждёт модерации → использует в будущих роликах.

#### CR-2: Воркфлоу `wf-creatify-text` (Text Generator + AI Scripts)
- Эндпоинты: `POST /api/text_generator/`, `POST /api/ai_scripts/`.
- Назначение: альтернатива Hermes-LLM для текста (если нужна интеграция в
  воркфлоу без вызова bridge).

#### CR-3: Воркфлоу `wf-creatify-asset` (Asset/Image Generator)
- Эндпоинты: `POST /api/ai_generation/`.
- Назначение: генерация изображений товара/визуала для постов.

#### CR-4: Воркфлоу `wf-creatify-adclone`
- Эндпоинты: `POST /api/ad_clones/`.
- Назначение: клонирование успешной чужой рекламы.

#### CR-5: Воркфлоу `wf-creatify-shorts` (AI Shorts/Editing)
- Эндпоинты: `POST /api/ai_shorts/`, `POST /api/ai_editing/`.
- Назначение: длинное видео клиента → набор коротких роликов.

#### CR-6: Воркфлоу `wf-creatify-product` (Product-to-video)
- Эндпоинты: `POST /api/product_to_videos/`.
- Назначение: изображение/видео товара → ролик (отличается от URL-to-video).

#### CR-7: Воркфлоу `wf-creatify-banner` (IAB баннеры + Inspiration)
- Эндпоинты: `POST /api/iab_images/`, `POST /api/inspiration/`.
- Назначение: рекламные баннеры для display-кампаний.

### Epic PM (Postmypost расширение)

#### PM-1: Расширение `wf-publish` под все платформы
- Текущая реализация: проверить какие платформы реально в details.
- Добавить недостающие: Pinterest, Rutube, OK, Discord, Reddit, Bluesky, Tumblr,
  Mastodon.
- Параметр `publication_type` переключатель (1/2/4).

#### PM-2: Поддержка Stories
- В wf-publish добавить ветку для `publication_type: 2`.
- UI: при `/publish` выбор «Пост / Reels / Story».

#### PM-3: Адаптация caption под платформу
- Для каждой платформы свой формат (X ≤280 символов, Threads длинный текст,
  Telegram с кнопками, LinkedIn профессиональный тон, и пр.).
- Реализовать либо через Hermes-LLM (отдельный субагент caption-adapter), либо
  через таблицу шаблонов в БД.

### Epic UX (расширение интерфейса оператора)

#### UX-1: Команды для нового scope
- `/creators <niche>` — поиск авторов (SC-1).
- `/creator <handle>` — профиль автора (SC-2/3/4).
- `/comments <url>` — комментарии к ролику (SC-5).
- `/avatar` — загрузка кастомного аватара (CR-1).
- `/asset <prompt>` — генерация изображения (CR-3).
- `/shorts <url>` — нарезка длинного в Shorts (CR-5).
- `/banner` — генерация баннера (CR-7).
- `/publish_type post|reels|story` — выбор типа публикации (PM-2).

#### UX-2: Inline-меню в Telegram
- Главное меню (после /start) расширить кнопками под новые команды.

---

## ЧАСТЬ 3. ПРИОРИТЕТЫ И ОЧЕРЕДЬ

**Принцип:** сначала фиксим баги (F-1..F-5), потом расширяем по убыванию
ценности для продаж.

### Спринт 1 (Фаза 2 = ближайшие дни)
1. **F-1** Ротация ключей (заказчик) — 5 мин.
2. **F-2** Creatify remainingcredits фикс — 30 мин.
3. **F-3** Подключение postmypost аккаунтов (заказчик) — 30 мин.
4. **F-4** 8 команд wf-tg-bot — 60 мин.
5. **F-5** git sync — 15 мин.
6. **E2E тест** на реальных ключах с publication в Instagram. Это и есть Фаза 2.

### Спринт 2 (расширение перед следующей сделкой)
1. **SC-1..SC-5** — углублённая аналитика авторов. Большая ценность для демо.
2. **PM-1** — расширение платформ постинга (Stories + нишевые).
3. **UX-1** — команды для новых сценариев.

### Спринт 3 (premium-фичи)
1. **CR-1** — Custom Avatar (клон клиента). Это то, что можно продавать как
   premium-фичу за доплату.
2. **CR-3/CR-5/CR-6** — Asset/Shorts/Product-to-video.
3. **CR-2/CR-4/CR-7** — Text/AdClone/Banner (по запросу).

---

## ЧАСТЬ 4. СЛЕДУЮЩИЕ ШАГИ

1. Заказчик:
   - Ротирует ключи (Б1).
   - Подключает аккаунты в postmypost (Б3).
2. Оркестратор (я):
   - Закоммичу API-REFERENCES.md и этот документ.
   - Подготовлю промпт разработчику на Спринт 1 (F-1..F-5 + E2E).
3. После Спринта 1 — приглашаем оператора на live E2E.
4. После E2E — запускаем Спринт 2 (расширение).

---

## Документы для чтения разработчиком

- `specs/API-REFERENCES.md` — первоисточники (закрепить).
- `specs/13-n8n-orchestrator-architecture.md` — текущая архитектура.
- `specs/12-telegram-ux.md` — UX для расширения командами (UX-1).
- Этот файл — `AUDIT-AND-EXPANSION-PLAN.md`.
