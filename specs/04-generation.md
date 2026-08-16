# Спека 04 — Блок генерации (Creatify)

**Фаза:** P0 · **Статус:** к реализации

> Первоисточник: https://docs.creatify.ai/
> Base URL: `https://api.creatify.ai/api/`
> Авторизация: **два заголовка** на каждый запрос — `X-API-ID` + `X-API-KEY`.
> Режим: асинхронный (POST → pending → webhook/poll → done).
> **Вебхуки поддерживаются** (ключевое): per-request параметр `webhook_url`.

## 1. Цель блока

Принять сценарий + выбранный аватар/голос → сгенерировать вертикальное видео
(15–30 сек, ru) → получить готовый MP4 → скачать на свой SSD → передать в блок
публикации.

## 2. Стоимость и бюджет (критично)

| Параметр | Значение |
|----------|----------|
| URL-to-video (стандарт) | **5 кредитов / 30 сек** (биллинг порциями по 30 сек → 15 сек = те же 5) |
| Link scraping (`POST /api/links/`) | 1 кредит |
| AI Script (`POST /api/ai_scripts/`) | 1 кредит |
| Превью (`preview_list_async`) | 1 кредит / 30 сек |
| Aurora `aurora_v1_fast` | 0.5 кредитов/сек |

**Планы:** Starter $99 = 500 кредитов/мес · Pro $299 = 2000 кредитов/мес.

**Для нашего лимита «100 видео/мес»:**
- 100 × 5 кредитов = 500 кредитов → ровно API Starter, но без запаса.
- Рекомендация: **API Pro ($299)** — даёт ~400 видео, запас на превью и ретраи.
- Хард-лимиты в системе (см. спеку 00):
  - `daily_video_limit = 3` (в авто-режиме)
  - `monthly_video_limit = 100`
  - `credit_floor = 50` — стоп, если остаток ниже.

**Мониторинг остатка:** n8n-воркфлоу `wf-credit-check` раз в час →
`GET /api/remainingcredits/` → пишет в `settings.credits_remaining` + алерт в TG
при `< credit_floor`.

## 3. Пайплайн URL-to-video (последовательность вызовов)

### Шаг 1. Создать link
```
POST /api/links/
Headers: X-API-ID, X-API-KEY
Body: { "url": "<source_url темы>" }
```
Если источник — не товарная карточка (а, например, IG-reel или статья про
робототехнику), переопределить контент для лучшего результата:
```
POST /api/links/   { "url": "<source_url>" }
PUT  /api/links/{id}/  {
  "title": "...", "description": "...",
  "image_urls": ["..."], "video_urls": ["..."], "logo_url": "..."
}
```
Ответ содержит `id` (UUID link) — подставляем в Шаг 3.

### Шаг 2. (опционально) Сгенерировать AI-скрипт
Используем **только если** Сценарист Hermes не справился или как референс:
```
POST /api/ai_scripts/
Body: {
  "title": "...", "description": "...",
  "language": "ru", "target_audience": "...", "video_length": 30
}
```
В MVP — **не используем**, сценарий пишет Hermes (качественнее под нишу клиента).

### Шаг 3. Запустить генерацию (финальный JSON от Сборщика)
```
POST /api/link_to_videos/
Headers: X-API-ID, X-API-KEY
Body: <JSON из спеки 03, раздел 5>
```
Ответ (сразу):
```json
{ "id": "81123b51-...", "status": "pending", "progress": 0, "video_length": 30 }
```
`id` → пишем в `generations.creatify_id`.

### Шаг 4. Дождаться готовности

**Основной канал — вебхук.** При срабатывании:
```
POST https://<домен>/webhook/creatify
Body: { "id": "...", "status": "done",
        "video_output": "https://s3.../output.mp4", "video_thumbnail": "..." }
```
n8n-воркфлоу `wf-creatify-webhook` (см. раздел 5).

**Компенсирующий поллинг** (если callback не пришёл за 15 мин):
```
GET /api/link_to_videos/?ids=<uuid1>,<uuid2>&max=100
```
n8n-воркфлоу `wf-creatify-poll` каждые 5 мин по задачам со status=pending/running
и `created_at` старше 15 мин.

### Шаг 5. Скачать результат
После `status=done`:
- `video_output` URL → скачать в `/var/media/<generations.id>.mp4`.
- `video_thumbnail` → скачать рядом `.jpg`.
- Записать `local_path`, `credits_spent` (~5) в БД.
- Дублировать MP4 отправкой в TG-канал-архив (резерв).

> **Важно:** URL `video_output` может быть временным → скачивать **обязательно**,
> не полагаться на повторный fetch позже.

## 4. Полная схема полей `link_to_videos`

Из OpenAPI (для встраивания в промпт Сборщику — спека 03).

**Обязательное:** `link` (UUID).

**Опциональные (с enum'ами):**

| Поле | Тип | Значение для MVP |
|------|-----|------------------|
| `name` | string ≤255 | `robotec-<тема-slug>-<дата>` |
| `target_platform` | string | `Instagram` / `Tiktok` / `Youtube` |
| `target_audience` | string | из профиля клиента |
| `video_length` | enum | **`15` / `30`** (наш диапазон) |
| `aspect_ratio` | enum | **`9x16`** (вертикальный) |
| `language` | enum (~80) | **`ru`** |
| `model_version` | enum | `standard` (5 кред/30 сек) / `aurora_v1_fast` (0.5 кред/сек — дороже для >=10 сек) |
| `script_style` | enum 50+ | `ProblemSolutionV2`, `DontWorryWriter`, `*Hook`… |
| `visual_style` | enum 50+ | `DynamicProductTemplate`, `VlogTemplate`, `VanillaTemplate`… |
| `override_avatar` | UUID | из библиотеки (если фиксируем лицо) |
| `override_avatar_by_image` | URL | не используем в MVP |
| `override_voice` | UUID | из кеша `GET /api/voices/` (русский) |
| `override_script` | string | `full_text` сценария |
| `background_music_url` | URL | опц. |
| `background_music_volume` | 0.0–1.0 | `0.15` |
| `voiceover_volume` | 0.0–1.0 | `1.0` |
| `no_background_music` | bool | `false` |
| `no_caption` | bool | `false` (субтитры нужны для Reels) |
| `no_emotion` | bool | `false` |
| `no_cta` | bool | `false` |
| `no_stock_broll` | bool | `false` |
| `webhook_url` | uri ≤200 | `https://<домен>/webhook/creatify` |

## 5. Аватары и голоса (подготовка один раз)

### Аватары
```
GET /api/personas/?gender=m&age_range=adult&style=presenter
     &suitable_industries=...&keywords=engineer
```
Выбрать 2–3 «инженерных/экспертных» лица под тон robotec → записать их UUID в
`settings.preferred_avatars` (JSON-массив). Сборщик берёт оттуда.

### Голоса
```
GET /api/voices/   → отфильтровать по accent_name содержит "Russian"
```
Выбрать 1–2 (мужской экспертный, опц. женский) → UUID акцента в
`settings.preferred_voices`. Сборщик подставляет `override_voice`.

> Эти списки кешируются в БД, обновляются раз в месяц (или по кнопке в TG).

## 6. n8n-воркфлоу

### 6.1 `wf-creatify-link`
```
[Webhook from Hermes] → [HTTP: POST /api/links/] →
  (опц.) [HTTP: PUT /api/links/{id}/] → [return link_id]
```

### 6.2 `wf-creatify-submit`
```
[Webhook from Hermes, body=JSON от Сборщика]
   ├─ [SQLite: INSERT generations (creatify_id=null, status=pending, payload)]
   ├─ [HTTP: POST /api/link_to_videos/]   ← retry 3x
   ├─ [SQLite: UPDATE generations SET creatify_id=<resp.id>]
   └─ [return creatify_id]
```

### 6.3 `wf-creatify-webhook` (приём callback)
```
[Webhook: POST /webhook/creatify]   ← public, path-token protected
   ├─ [SQLite: SELECT WHERE creatify_id=<body.id>]   ← идемпотентность
   ├─ [IF status==done]:
   │     ├─ [HTTP: GET video_output → write file /var/media/<id>.mp4]
   │     ├─ [HTTP: GET thumbnail → /var/media/<id>.jpg]
   │     ├─ [SQLite: UPDATE generations SET status=done, local_path, webhook_received=1]
   │     ├─ [HTTP → Hermes :8000/internal/creatify-done]
   │     └─ [Telegram: send video to архив-канал + оператору]
   └─ [IF status==failed/rejected]:
         ├─ [SQLite: UPDATE generations SET status=failed, failed_reason]
         ├─ [HTTP → Hermes :8000/internal/creatify-failed]
         └─ [Telegram: alert оператору]
```

### 6.4 `wf-creatify-poll` (страховка, каждые 5 мин)
```
[Cron: */5 * * * *]
   ├─ [SQLite: SELECT creatify_id WHERE status IN (pending,running)
   │            AND created_at < now-15min AND webhook_received=0]
   ├─ [HTTP: GET /api/link_to_videos/?ids=<csv>]   ← батч до 100
   └─ [Code: для каждой — если status терминальный → повторить логику webhook]
```

## 7. Обработка сбоев

| Сбой | Действие |
|------|----------|
| `POST /api/links/` 4xx | алерт, ручной рестарт. Чаще всего — плохой URL. |
| `POST /api/link_to_videos/` 4xx (невалидный JSON) | алерт + кнопка «✏️ Исправить» в TG (отдаём Сборщику обратно) |
| `status=failed`/`rejected` | записать `failed_reason`, алерт, **без авто-ретрая** (стоит кредитов). Ручной рестарт кнопкой. |
| Webhook не пришёл | поллинг заберёт через 15 мин |
| URL `video_output` протух | не критично — мы скачали сразу; если не успели — `GET /api/link_to_videos/{id}/` вернёт актуальный |

## 8. Безопасность

- `X-API-ID` и `X-API-KEY` — в n8n Credentials (зашифрованы), не в нодах.
- Публичный webhook `/webhook/creatify` защищён **path-token**:
  реальный путь `/webhook/creatify/<случайный-токен>` (в `WEBHOOK_URL`).
- Идемпотентность: повторный callback с тем же `id` не создаёт дубль и не
  перезаписывает уже скачанный файл.
- Логи: ключи **не** пишутся (n8n маскирует в Credentials; payload логируем без них).

## 9. Критерии готовности

1. `wf-creatify-submit` создаёт задачу, `generations.creatify_id` заполняется.
2. Вебхук принимается, MP4 скачивается в `/var/media/`, БД обновляется.
3. При отсутствии вебхука — поллинг корректно завершает задачу за ≤20 мин.
4. При `failed` — алерт в TG с причиной, авто-ретрая нет.
5. Счётчик кредитов и дневной/месячный лимит проверяются до отправки задачи.
6. 1 полный цикл генерации для robotec (1 видео 30 сек, ru) проходит end-to-end.
