# wf-analytics — normalize-ноды под реальные ответы scrapecreators (12.08, исправлено)

## Проблема (было)
- Активная версия wf-analytics имела 13 нод: HTTP IG/TikTok/YouTube шли НАПРЯМУЮ в Merge → Postprocess.
- Postprocess фильтрует `typeof r.ts_unix === 'number'` — сырые ответы API не имели ts_unix → records=[], candidates=0, platforms_failed=3.

## Реальные структуры ответов (проверено curl 12.08, ключ из ~/factory/.env)
- **IG** `GET https://api.scrapecreators.com/v2/instagram/reels/search?query=...&date_posted=last-day&page=1`
  → `{success, credits_remaining, credits_charged, reels: [...], next_page}`
  - item: `caption`, `url` (=`https://www.instagram.com/reel/{shortcode}/`), `owner.username`, `video_view_count`, `video_play_count`, `like_count`, `comment_count`, `taken_at` — **ISO-строка** (`2026-08-12T04:28:56.000Z`), `shortcode`, `video_url`
- **YT** `GET https://api.scrapecreators.com/v1/youtube/search?query=...&region=RU&sortBy=popular&uploadDate=today&type=videos`
  → `{success, videos: [...], channels, playlists, shorts, shelves, lives, continuationToken}`
  - item: `title`, `url` (`https://www.youtube.com/watch?v=...`), **`viewCountInt`** (число; НЕ viewCount), **`publishedTime`** (ISO; НЕ publishedAt), `channel.title` (объект channel: `{id,title,handle,thumbnail}`), `lengthSeconds`, `badges`
- **TikTok** `GET https://api.scrapecreators.com/v1/tiktok/search/keyword?query=...&region=US&trim=true`
  → `{success, search_item_list: [...], cursor}`
  - item: `desc`, **`statistics`** (НЕ stats): `play_count, digg_count, share_count, comment_count`, `create_time` (уже unix int), `author.unique_id` / `author.nickname`, `url` (`https://www.tiktok.com/@user/video/{aweme_id}`), `aweme_id`, `video`
  - ⚠️ region=RU даёт ПУСТОЙ `search_item_list` — в HTTP-ноде стоит region=US (проверено: 30 items)
  - ⚠️ в HTTP-ноде TikTok НЕ слать `sort_by`/`date_posted` — их нет в реальном контракте

## Единый формат кандидата (на выходе normalize-нод, вход Postprocess)
`{title, source_platform, source_url, author, metrics: {views, likes, shares, comments}, ts_unix, transcript_excerpt, feasibility_hint}`
- ts_unix ОБЯЗАТЕЛЬНО число (unix sec): IG/YT — `Math.floor(Date.parse(iso)/1000)`, TikTok — `create_time` как есть
- пустой массив → вернуть `[]` (не падать)
- недостающее поле → 0 / ''

## Маппинги (3 ноды: Normalize IG / Normalize TikTok / Normalize YouTube, id ...00e/...00f/...010)
| платформа | title | source_url | author | views | likes | shares | comments | ts_unix |
|---|---|---|---|---|---|---|---|---|
| instagram | `caption` | `url` (fallback `https://www.instagram.com/reel/{shortcode}/`) | `owner.username` | `video_view_count||video_play_count` | `like_count` | 0 | `comment_count` | `Date.parse(taken_at)/1000` |
| youtube | `title` | `url` | `channel.title||channel.name||channelTitle` | `viewCountInt||viewCount||view_count` | `likeCount||like_count` | 0 | 0 | `Date.parse(publishedTime)/1000` (fallback publishedAt) |
| tiktok | `desc` | `url` (fallback `https://www.tiktok.com/video/{aweme_id}`) | `author.unique_id||author.nickname` | `statistics.play_count` | `statistics.digg_count` | `statistics.share_count` | `statistics.comment_count` | `create_time` (int) |

## Postprocess (не менялся)
- фильтр 12–72ч по ts_unix, дедуп по normUrl(source_url), virality min-max (views 0.4/likes 0.3/shares 0.3), топ-20
- `platforms_ok` = число уникальных source_platform среди records С ts_unix числом; `platforms_failed = 3 - platforms_ok`

## Что сделано
- 13 → 16 нод: вставлены Normalize IG / Normalize TikTok / Normalize YouTube (code v2, mode runOnceForAllItems) между HTTP-нодами и Merge; HTTP TikTok переведён на region=US + trim=true (убран sort_by/date_posted).
- Обновлены workflow_history (activeVersionId a3446e2f + draft 9d733a60) и workflow_entity через node:sqlite; `docker restart factory-n8n`.

## Тест (12.08, после фикса)
- `curl -X POST http://localhost:5678/webhook/factory/analytics -d '{"client_id":1,"find_competitors":false}'`
- exec id **990**, status success: **candidates=14, platforms_ok=3, platforms_failed=0** (tiktok 270976 views лидирует по virality)
