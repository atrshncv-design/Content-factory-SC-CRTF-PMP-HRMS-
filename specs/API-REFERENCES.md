# API-REFERENCES — первоисточники внешних сервисов

> Этот файл — **единственный источник правды** по API сервисов. Любая
> реализация воркфлоу и any-интеграция должна сверяться с официальной докой.
> При конфликте спек и доков — приоритет за доками.

## Реестр сервисов

| ID | Сервис | Базовый URL API | Документация | Авторизация |
|----|--------|-----------------|--------------|-------------|
| **API-1** | ScrapeCreators | `https://api.scrapecreators.com` | https://docs.scrapecreators.com/ | заголовок `x-api-key: <SCRAPECREATORS_API_KEY>` |
| **API-2** | Creatify | `https://api.creatify.ai/api/` | https://docs.creatify.ai/introduction | заголовки `X-API-ID: <CREATIFY_API_ID>` + `X-API-KEY: <CREATIFY_API_KEY>` |
| **API-3** | Postmypost | `https://api.postmypost.io/v4.1` | https://help.postmypost.io/docs/api/ | `Authorization: Bearer <POSTMYPOST_TOKEN>` |

## Доп. материалы (когда основной доки мало)

| Сервис | Полный текст для LLM | OpenAPI спецификация |
|--------|----------------------|----------------------|
| ScrapeCreators | https://docs.scrapecreators.com/llms-full.txt | https://docs.scrapecreators.com/openapi.json |
| Creatify | https://docs.creatify.ai/llms.txt | https://docs.creatify.ai/api-reference/openapi.json |
| Postmypost | — | из `postmypost/node-rest-sdk/src/api.ts` (GitHub) |

> **Агент-разработчик**: при работе с любым эндпоинтом ВСЕГДА открывай первоисточник.
> Не полагайся на память/спеки — они могут быть устаревшими. curl-проверка перед
> внедрением обязательна.

## Scope (что реально используем в контент-заводе)

### API-1 ScrapeCreators
**Используем:**
- 🔍 Тренды и поиск контента (TikTok, IG, YT, X): keyword search, hashtag search,
  trending feeds, popular creators.
- 👤 Авторы и аудитория углублённо: profiles, posts, reels, audience demographics
  (пол/возраст/гео), video transcripts, comments + replies.

**НЕ используем** (в текущем scope):
- Ad Libraries (TikTok/IG/FB/Google/LinkedIn).
- Все остальные 30+ платформ (Pinterest, LinkedIn, Reddit, Rumble, Twitch и пр.).
- Music APIs (Spotify, Apple Music, SoundCloud).

### API-2 Creatify
**Используем:**
- 🎬 URL-to-video (есть базово).
- 🧬 Custom Avatar (BYOA): загрузка видео клиента, клонирование лица/голоса
  (premium-фича для персонализации под бренд).
- 📝 Текстовый и визуальный стек: Text Generator, AI Scripts, Asset/Image
  Generator, Ad Clone, AI Shorts (длинное видео → короткие), AI Editing,
  Product-to-video, IAB баннеры, Inspiration templates.

**НЕ используем** (в текущем scope):
- Библиотечные AI-аватары (lipsync) — пользователь явно НЕ выбрал.
- Aurora (ультрареалистичный аватар) — НЕ выбран.

### API-3 Postmypost
**Используем:**
- 📹 Видео-платформы: Instagram Reels, YouTube Shorts, TikTok, VK, Rutube (база).
- ✍️ Текстовые: X (Twitter), Threads, Telegram, LinkedIn, Facebook.
- ⚡ Stories: Instagram, Facebook.
- 🎯 Нишевые/визуальные: Pinterest, OK, Discord, Reddit, Bluesky, Tumblr, Mastodon.

**Поддерживаемые типы публикаций:**
- `publication_type: 1` (POST) — текст + медиа.
- `publication_type: 2` (STORY) — Stories.
- `publication_type: 4` (REELS_SHORTS_CLIPS) — вертикальное видео.

## Принципы работы с API (для всех воркфлоу)

1. **Никогда не хардкодить ключи.** Только через n8n Credentials или `.env`.
2. **Всегда retry-логика**: 3 попытки с экспоненциальной задержкой (1с/5с/15с).
3. **Идемпотентность**: для эндпоинтов, создающих сущности (публикации,
   генерации), проверять существование перед созданием.
4. **Бюджет**: scrapecreators — `cache hit = 0 кредитов`, использовать `trim=true`.
   creatify — `GET /api/remainingcredits/` перед генерацией.
5. **Логи**: каждый вызов external API → INSERT в `factory.logs` через db-bridge.
6. **Версионирование**: при изменении схемы API — обновлять этот файл и
   соответствующий воркфлоу.

## Регламент обновления этого файла

- Любое изменение в списке эндпоинтов → коммит + push.
- При появлении новых фич в API (подписка, тариф) — добавлять сюда.
- Проверка актуальности — раз в месяц (читать Release Notes сервисов).
