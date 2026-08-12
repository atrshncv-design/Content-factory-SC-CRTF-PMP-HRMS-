# Спека 02 — Блок аналитики (ScrapeCreators)

**Фаза:** P0 · **Статус:** к реализации

> Первоисточник: https://docs.scrapecreators.com/
> Авторизация: заголовок `x-api-key: <SCRAPECREATORS_API_KEY>`
> Base URL: `https://api.scrapecreators.com`
> Модель оплаты: pay-as-you-go, **cache hit = 0 кредитов**, cache miss = 1 кредит.
> Вебхуков **нет** — только синхронные запросы (работаем по cron/по требованию).

## 1. Цель блока

Дать субагенту-Аналитику (см. спеку 03) свежие данные, чтобы на их основе
выбрать тему дня для генерации. Конкретно:
1. Найти **трендовый контент за последние 12–72 часа** в нише клиента
   (промышленная робототехника для текущего кейса).
2. При отсутствии списка конкурентов — **самостоятельно найти** их соцсети.
3. Отдать агрегированный список кандидатов с метриками и оценкой «можно ли
   сделать через creatify».

## 2. Стратегия: «12–72 часа по нише»

Прямого фильтра «72 часа» в API нет. Используем комбинированную стратегию по
трём платформам + постфильтрацию по timestamp на нашей стороне.

### 2.1 Эндпоинты для поиска трендов

| Платформа | Эндпоинт | Параметр времени | Покрытие |
|-----------|----------|------------------|----------|
| Instagram | `GET /v2/instagram/reels/search` | `date_posted=last-hour` \| `last-day` \| `last-week` | 1ч / 24ч / неделя |
| TikTok | `GET /v1/tiktok/search/keyword` | `date_posted=yesterday` \| `this-week` | 24ч / неделя |
| YouTube | `GET /v1/youtube/search` (`type=videos`) | `uploadDate=today` \| `this_week` | 24ч / неделя |

### 2.2 Запросы (параметры)

**Instagram Reels** (лучший часовой фильтр):
```
GET /v2/instagram/reels/search
  ?query=<ниша на англ.>
  &date_posted=last-day
  &page=1
Header: x-api-key: <KEY>
```

**TikTok keyword**:
```
GET /v1/tiktok/search/keyword
  ?query=<ниша>
  &sort_by=most-liked
  &date_posted=yesterday
  &region=RU
  &trim=true
Header: x-api-key: <KEY>
```

**YouTube**:
```
GET /v1/youtube/search
  ?query=<ниша>
  &sortBy=popular
  &uploadDate=today
  &type=videos
  &region=RU
Header: x-api-key: <KEY>
```

### 2.3 Запросы по нише (keyphrases для robotec)

Заранее заготовленный набор запросов (в `settings` или промпте Аналитика).
Для robotec — комбинации:
- `industrial robot`, `robotic arm`, `factory automation`, `welding robot`,
  `KUKA robot`, `palletizing robot`, `manufacturing automation`
- На русском (для TikTok/VK/YT-RU): `промышленный робот`, `роботизация производства`,
  `сварочный робот`, `автоматизация завода`

> Аналитик **сам расширяет** этот набор, исходя из найденного (например, увидел
> тренд на `cobots` — добавляет в запросы). Это его задача, не захардкожено.

### 2.4 Постфильтрация 12–72 часа (на стороне n8n/Hermes)

Из ответа берём поле timestamp:
- IG: `taken_at` (UNIX)
- TikTok: `create_time` (UNIX)
- YouTube: `publishDate` (ISO)

n8n-нода `Function`/`Code`: оставить только записи где `now - ts ∈ [12h, 72h]`.
Затем **дедупликация** по нормализованному URL/author+title.

### 2.5 Сортировка и отбор кандидатов

Из отфильтрованного пула берём **топ-20** по «индексу виральности»:
```
virality = play_count_norm * 0.4 + like_count_norm * 0.3 + share_count_norm * 0.3
```
(нормализация — min-max по пулу). Этот топ-20 уходит в Аналитика.

## 3. Поиск конкурентов (если нет seed-списка)

### 3.1 Эндпоинты

| Что | Эндпоинт |
|-----|----------|
| IG-профили по Google-bios | `GET /v1/instagram/search/profiles?query=<ниша>&cursor=1` |
| YouTube-каналы | `GET /v1/youtube/search?type=channels&query=<ниша>` |
| TikTok-аккаунты | `GET /v1/tiktok/search/users?query=<ниша>` |
| Хэштег-топ | `GET /v1/tiktok/search/hashtag?hashtag=industrialrobot` |

Возвращают профили с `follower_count`, `is_verified`, `category_name`, `bio`.

### 3.2 Логика отбора конкурентов (Аналитик)

1. Из результатов выбрать **5–10 профилей**, релевантных нише:
   - `follower_count` от 5k (не мусор, но и не обязательно миллионники),
   - в bio/category есть признаки ниши (робототехника/автоматизация/производство),
   - активны (есть посты за последний месяц — проверяется отдельным вызовом
     `GET /v1/.../profile/videos` или `channel-videos`).
2. Записать в таблицу `competitors` (`is_seed=0`).
3. Для топ-3 конкурентов — забрать их **последние 10 видео** (через
   `/instagram/user/reels`, `/tiktok/profile/videos`, `/youtube/channel/shorts`),
   это даёт дополнительный пул «что работает у конкурентов».

### 3.3 Seed-список (фолбэк, если автопоиск пуст)

Если автопоиск вернул < 3 релевантных профилей — подмешать из `competitors`
с `is_seed=1`. Для robotec предзаготовить (разработчик вносит руками в БД):
- KUKA, ABB Robotics, FANUC, Yaskawa, Universal Robots — корпоративные
  IG/YT/Rutube.
- Российские: «Аркодим», плагиат-кейсы со склада «Озон»/«ВБ» (логистические роботы).

## 4. Контроль стоимости (cache hit — наш друг)

- Повторный запрос за те же данные в коротком окне = **0 кредитов**.
- При ручном режиме (когда человек верифицирует аналитику) — **не дёргать API
  повторно**, отдавать закешированный результат.
- Аналитик может инициировать «обновить данные» → один полный проход.
- Включать `trim=true` где доступно (TikTok) — облегчённый ответ, дешевле обработка.
- Логировать `credits_charged` из ответа в `logs.payload`.

## 5. n8n-воркфлоу `wf-analytics`

```
[Execute Workflow Trigger]  ← вызывается Hermes-ом (или cron в авто-режиме)
   │
   ▼
[Set: query_list = <из settings/промпта>] ─► [Split In Batches] по платформам
   │
   ├─► [HTTP: IG reels/search]   ─► [Code: filter 12-72h, normalize]
   ├─► [HTTP: TikTok search]     ─► [Code: filter, normalize]
   └─► [HTTP: YT search]         ─► [Code: filter, normalize]
   │
   ▼ (merge)
[Code: dedup, compute virality, top-20]
   │
   ├─► [SQLite: upsert competitors] (если был поиск конкурентов)
   └─► [HTTP → Hermes :8000/internal/analytics-ready]  ← отдаёт топ-20 Аналитику
```

**Retry-политика:** на каждом HTTP — 3 попытки с backoff (1s/5s/15s). При
исчерпании — не валим весь воркфлоу, а отдаём то, что собрали (даже 1 платформа
из 3 — рабочий результат). Факт частичного сбоя → `logs.level=warn`.

## 6. Контракт вход/выход

**Вход** (Hermes → n8n при запуске `wf-analytics`):
```json
{ "client_niche": "промышленная робототехника",
  "query_list": ["industrial robot", "welding robot", ...],
  "find_competitors": true,
  "competitor_seed": ["KUKA", "ABB Robotics"] }
```

**Выход** (n8n → Hermes) — массив кандидатов (топ-20):
```json
{
  "candidates": [
    { "title": "Робот сваривает деталь за 8 секунд",
      "source_platform": "instagram",
      "source_url": "https://...",
      "author": "@factory_robotics",
      "metrics": { "views": 1200000, "likes": 95000, "shares": 12000, "comments": 340 },
      "age_hours": 28,
      "virality_index": 0.91,
      "transcript_excerpt": "..." ,
      "feasibility_hint": "high"
    }
  ],
  "competitors_found": [
    { "handle": "@factory_robotics", "platform": "instagram", "followers": 145000 }
  ],
  "meta": { "credits_spent": 7, "platforms_ok": 3, "platforms_failed": 0 }
}
```

> `feasibility_hint` — предварительная оценка (на базе duration/format), финальный
> вердикт о возможности сделать через creatify принимает Аналитик (см. спеку 03).

## 7. Транскрипты (опционально, для анализа содержания тренда)

Чтобы Аналитик понимал **о чём** трендовый ролик (а не только метрики), для
топ-10 кандидатов берём транскрипт:
- `GET /v1/tiktok/video/transcript?url=...`
- `GET /v1/instagram/post/transcript?url=...` (если есть)
- `GET /v1/youtube/video/transcript?url=...`

Это +1 кредит на ролик, но критично для качества решения Аналитика. Включать
только для финального топ-10 (после первичного отсева), чтобы экономить.

## 8. Критерии готовности

1. `wf-analytics` отдаёт непустой `candidates[]` для ниши robotec.
2. Постфильтрация 12–72ч корректно отсекает старые и слишком свежие (< 12ч).
3. При `find_competitors=true` — таблица `competitors` наполняется.
4. `credits_spent` логируется и не превышает ~20 за полный цикл аналитики.
5. При отказе 1 платформы — воркфлоу не падает, отдаёт частичный результат + warn.
