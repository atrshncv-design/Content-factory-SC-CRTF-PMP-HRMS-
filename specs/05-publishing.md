# Спека 05 — Блок автопостинга (Postmypost)

**Фаза:** P1 (автопостинг) · частично P0 (ручной постинг 1 клик)
**Статус:** к реализации

> Первоисточник: https://help.postmypost.io/docs/api/
> Base URL: `https://api.postmypost.io/v4.1`
> Авторизация: `Authorization: Bearer <POSTMYPOST_TOKEN>`
> Вебхуков **нет** — статус публикации ловим поллингом.
> Жёсткие лимиты: создание постов и загрузки — **10/мин**, остальное — 30/мин.

## 1. Цель блока

Опубликовать (или запланировать) готовый контент в выбранные соцсети:
- Вертикальное видео → Instagram Reels / YouTube Shorts / TikTok / VK / Rutube.
- Текстовые посты → Threads / X (Twitter) / Telegram / VK.

## 2. Поддерживаемые платформы (из подтверждённых в API)

| Платформа | Видео (Reels/Shorts) | Текст-пост | 备注 |
|-----------|:---:|:---:|------|
| Instagram | ✅ (`publication_type: 4`) | ✅ (`1`) | `instagram_share_to_feed` для Reels в ленту |
| YouTube | ✅ (`4` = Shorts) | ✅ | `youtube_privacy_status` |
| TikTok | ✅ (`1` с видео) | ✅ | `tiktok_*` настройки |
| Threads | — | ✅ | только текст |
| X / Twitter | — | ✅ | `x_reply_settings` |
| VK | ✅ | ✅ | |
| Telegram | ✅ | ✅ | канал |
| Rutube | ✅ | — | |
| OK | ✅ | ✅ | |
| **Max** | ❌ | ❌ | **не поддерживается** — исключаем из MVP |

**MVP-набор:** Instagram (Reels), YouTube (Shorts), TikTok, Telegram, VK.
Текст-посты: Threads, X. Rutube/OK — если успеем.

## 3. Подключение аккаунтов (один раз, вручную)

Аккаунты подключаются **через веб-кабинет postmypost** (OAuth по официальным
API соцсетей), а не через наш API. Делается один раз администратором.

Контент-завод только читает:
```
GET /accounts?project_id=<id>
Authorization: Bearer <TOKEN>
→ массив: { id, name, platform, login, connection_status }
```

- `connection_status=1` — ok.
- `connection_status=2` — AUTH_REQUIRED: алерт в TG «перелогинься в кабинете».

n8n `wf-sync-accounts` раз в час обновляет таблицу `social_accounts`.

## 4. Пайплайн публикации (3 шага)

### Шаг 1. Загрузить медиа по URL
Файл уже лежит у нас на SSD (`/var/media/<id>.mp4`). Но postmypost требует
публичный URL → отдаём через наш reverse-proxy публичную ссылку на файл:

```
POST /upload/init
Body: { "project_id": <id>, "url": "https://<домен>/media/<id>.mp4" }
→ { id, url, size, status }
```
> Альтернатива: прямая загрузка файла (multipart в S3 через `/upload/init` +
> `/upload/complete`). В MVP используем **загрузку по URL** — проще, файл уже есть.

### Шаг 2. Дождаться обработки файла
```
GET /upload/status?id=<upload_id>
→ { id, file_id, status }   ← status: 1=ok | 2=error | 3=processing | 4=uploading | 5=waiting
```
Поллим до `status=1`, получаем `file_id`.

### Шаг 3. Создать публикацию
```
POST /publications
Body: {
  "project_id": <id>,
  "post_at": "2026-08-10T12:00:00+03:00",   ← время публикации (ISO 8601)
  "account_ids": [<id_instagram>, <id_youtube>, ...],
  "publication_status": 5,                    ← 5 = в очередь на post_at
  "details": [
    { "account_id": <id_instagram>,
      "publication_type": 4,                  ← Reels
      "content": "<caption>",
      "title": "<заголовок для видео-платформ>",
      "file_ids": [<file_id>],
      "instagram_share_to_feed": true,
      "nsfw": false },
    { "account_id": <id_youtube>,
      "publication_type": 4,                  ← Shorts
      "content": "<caption>",
      "title": "<title>",
      "file_ids": [<file_id>],
      "youtube_privacy_status": 1 },          ← public
    { "account_id": <id_threads>,
      "publication_type": 1,                  ← текст-пост
      "content": "<текст для Threads, длиннее>" },
    { "account_id": <id_x>,
      "publication_type": 1,
      "content": "<короткий текст для X>" }
  ]
}
```

> **Ключевое:** одна публикация → разные `details` под каждую платформу
> (Reels для IG/YT/TikTok, текст для Threads/X/TG). Caption адаптирует Сценарист/
> Оркестратор (или отдельный субагент «адаптер подписей» — на усмотрение, в MVP
> можно один общий caption + платформо-специфичные правки).

### Шаг 4. Отслеживать статус (поллинг)
```
GET /publications/{id}
→ { id, publication_status, ... }
```
Статусы: `1=PUBLISHED`, `2=PUBLISHING`, `3=ERROR`, `5=PENDING_PUBLICATION`.
Ловим переход `2→1` (успех) или `→3` (ошибка).

## 5. Лимиты и очередь

- **10 запросов/мин** на `/upload/*` и `POST /publications`.
- При `429` — уважать `Retry-After` и заголовки `X-Rate-Limit-*`.
- В n8n-воркфлоу — узкая горловина: не более 1 создания поста раз в 7 сек
  (с запасом), либо очередь с учётом окна.

## 6. n8n-воркфлоу

### 6.1 `wf-publish`
```
[Webhook from Hermes, body={generation_id, platforms, post_at, captions}]
   ├─ [HTTP: POST /upload/init {url: <media_url>}]   ← retry 3x
   ├─ [Loop: GET /upload/status до file_id]           ← задержка 5 сек
   ├─ [Code: собрать details[] под платформы]
   ├─ [HTTP: POST /publications]                       ← retry с Retry-After
   ├─ [SQLite: INSERT posts (postmypost_id, status=pending_publication)]
   └─ [HTTP → Hermes :8000/internal/publish-queued]
```

### 6.2 `wf-publish-status` (поллинг, каждые 2 мин)
```
[Cron: */2 * * * *]
   ├─ [SQLite: SELECT WHERE status IN (pending_publication, publishing)
   │            AND post_at <= now+1h]
   ├─ [HTTP: GET /publications/{id}]   ← батчем по статусам
   ├─ [IF publication_status==1]:
   │     └─ [SQLite: UPDATE status=published, published_at] + TG уведомление
   └─ [IF publication_status==3]:
         └─ [SQLite: UPDATE status=error, publish_result] + TG алерт
```

### 6.3 `wf-sync-accounts` (раз в час)
```
[Cron: 0 * * * *]
   └─ [HTTP: GET /accounts?project_id=...] → [SQLite: upsert social_accounts]
       └─ [IF connection_status==2]: TG алерт
```

## 7. Адаптация контента под платформы

Сценарист готовит базовый сценарий + caption. Для разных платформ нужны правки:

| Платформа | caption | доп. |
|-----------|---------|------|
| Instagram Reels | + хештеги, CTA | `share_to_feed=true` |
| YouTube Shorts | + заголовок (title) | `privacy=1` |
| TikTok | + хештеги, звук-тренд (опц.) | `comment/dх/duet/stitch` |
| Threads | длинный текст | только текст |
| X / Twitter | ≤280 символов | можно тред |
| Telegram | + кнопка-ссылка на сайт клиента | форматирование Markdown |
| VK | + хештеги | |

> В MVP — один базовый caption + короткая табличца правок от Оркестратора
> (не отдельный LLM-вызов, чтобы экономить токены). При желании — мини-субагент
> «адаптер» в P2.

## 8. Безопасность

- Bearer-токен в n8n Credentials (зашифрован), не светим.
- Публичная раздача файлов `/media/*` через reverse-proxy: **только чтение,
  только по непредсказуемому имени файла** (`<generations.id>.mp4` = UUID-like),
  запрет листинга. После публикации можно закрыть доступ (опц.).
- project_id хранится в `settings`.

## 9. Критерии готовности

1. `GET /accounts` отвечает, `social_accounts` заполнен, статусы ok.
2. `wf-publish` загружает MP4, создаёт публикацию со статусом 5, `posts` запись есть.
3. `wf-publish-status` ловит переход в `published` в течение ≤ 5 мин после `post_at`.
4. При `publication_status=3` — алерт в TG с `publish_result`.
5. Лимиты 10/мин не превышаются (нет 429 в нормальном режиме).
6. Один полный цикл: готовое видео → публикация в Instagram Reels + 1 текст-пост.
