# 06 — Публикация: wf-publish, publish-status, sync-accounts, 7 платформ

**Требования:** G07 (7 платформ), G09 (полный цикл до автопостинга)
**Blocked by:** —
**Зона:** `workflows/wf-publish.json`, `workflows/wf-publish-status.json`, `workflows/wf-sync-accounts.json`
**Волна:** 2
**Status:** done (16.08, 0 кредитов; платная приёмка — за пользователем)

## Что должно заработать

Публикация корректна для IG/TikTok/YouTube (видео) и TG/X/Threads/VK (текст). Text-only маршрут работает. Status-сron и sync-accounts cron живы.

## Из брифа / манифеста, дословно

> «+ текстовые: TG, X, Threads, VK»
> «аккаунты postmypost подключит пользователь перед платными тестами»

## Разделы спецификации

История 8.

## Критерии приёмки

- [x] **wf-publish Switch upload_needed корректен (не перевёрнут); text-only маршрут работает.**
  Переработан в 3 ветки (rules ×2 + extra): out0 — file_ids целочисленные (медиа готово) → skip; out1 — text-only (file_ids пуст И платформы без instagram/youtube/tiktok) → skip; out2 (extra) — upload нужен (видео без file_ids ИЛИ file_ids = URL-строка от бота). Text-only (TX/CP/AU шлют `file_ids: []`) больше НЕ уходит в upload/init: в real не будет 422 «Не удалось загрузить файл по ссылке» (url `media/null.mp4`), в mock не фабрикуется фейковый file_id. Доказательство: sim-прогон switch-условий по 5 сценариям (см. ниже) + Code build details text-only → details[] только content, type=1, без file_ids. Питфолл соблюдён: баговый switch из `.scratch/review-full-14aug/fixes/wf-publish.json` (пустые file_ids → skip, ломает видео) НЕ использован.
- [x] **Для 7 платформ заданы publication_type/platform_id и адаптация caption (X ≤280, Threads длинный, TG без markdown, VK-особенности задокументированы).**
  publication_type: видео (ig/yt/tiktok) → 4 (REELS_SHORTS_CLIPS) + file_ids из upload/init, youtube_privacy_status=1+title, instagram_share_to_feed при type 4, tiktok_comment/duet/stitch; текст (tg/x/threads/vk) → 1 (POST), только content. platform_id: account_ids[запроса] → social_accounts (БД, синк wf-sync-accounts) → legacy {ig:101, yt:102, tiktok:106, threads:104, x:105}; TG/VK legacy нет — до подключения аккаунтов detail без account_id (Code filter accounts отрежет, публикация остальных не ломается; sim: NO_ACCOUNT). Адаптация caption: контракт caption-adapter (hermes/skills) + гарантии на стороне публикации в Code build details и Code merge adapted — TG: markdown СТРИПИТСЯ (postmypost публикует TG plain-текстом, символы разметки иначе видны буквально; sim: `*мир*` → `мир`); X: жёсткий лимит 280 (обрезание+«…», sim: len=278); Threads: длинный (контракт, без ограничений); VK: без markdown, raw URL, приветствие по client_profile.name + ограничение postmypost (пост от подключённого сообщества/страницы; видео в VK вне scope) — задокументировано в DEPLOYMENT.md §21a и в комментарии-шапке Code build details.
- [x] **wf-publish-status cron `*/2` работает без мёртвых IF any?/NoOp + (mock)-текстовых пометок.**
  Cron `*/2 * * * *` на месте; мёртвые `IF any?`/`NoOp no rows` в репо-экспорте уже отсутствуют (live FIX-13, валидатор: 0 НЕДОСТИЖИМЫХ); (mock)-маркер убран из «Build body tg published» — сообщение «Опубликовано #<id>» чистое (sim подтверждён); neverError вложенный на HTTP GET real / UPDATE published/error / tg-нодах — на месте.
- [x] **wf-sync-accounts cron синкает аккаунты; в БД 5 соцаккаунтов (IG/YT/Threads/X/TikTok), отсутствие VK-аккаунта — задокументировано.**
  Cron `0 * * * *`; UPSERT `INSERT INTO social_accounts ... ON CONFLICT(id) DO UPDATE` через db-bridge (sim: sql+params); алерт при connection_status=2; mock-снимок = 5 аккаунтов (IG=101, YT=102, Threads=104, X=105, TikTok=106) — повторяет серверную БД (синк 13.08, спека Открытые места G01). Локальная `data/factory.db` — пустая дев-копия (эталон — серверная БД). Отсутствие VK задокументировано: DEPLOYMENT.md §21a + комментарий в jsCode Code mock accounts.
- [x] **Валидатор + sim зелёные; 0 платных postmypost-вызовов на списание.**
  `validate_workflow.py` по всем 3 воркфлоу: 0 issues (включая node --check всех jsCode). Sim: 30/30 зелёных — Switch upload needed ×5 сценариев (text-only→skip, video→upload, video+URL→upload, media ready→skip, twitter→text-only); Code build details ×5 (text-only details, TG strip, X≤280, media mock file_ids=[67890], media URL→file_ids из upload/init [777], media ready [12345], NO_ACCOUNT tg/vk); Code merge adapted ×4; алерт без (mock); sync-accounts mock/normalize/UPSERT; HTTP real upload jsonBody (URL приоритет + фолбэк + project_id число); достижимость всех нод; neverError на 3 real-нодах. Реальных HTTP-вызовов postmypost не было (0 кредитов).

## Что осталось на платный тест (действия пользователя)

1. **Подключить аккаунты postmypost** (IG/TikTok/YT/Threads/X + TG + VK) в кабинете проекта; после этого wf-sync-accounts (cron hourly) наполнит social_accounts, включая VK (сейчас отсутствует — G01).
2. Убедиться, что `POSTMYPOST_TOKEN`/`POSTMYPOST_PROJECT_ID` реальные (не PLACEHOLDER_UNTIL_TOMORROW) в .env сервера.
3. Живой E2E: text-only payload `{platforms:[threads,x,vk], content:'...'}` → ожидается publication без file_ids (не 422 upload/init); media payload `{platforms:[instagram], generation_id:<id>, file_ids:['<video_url>']}` → upload/init скачает URL → publication type=4; проверить caption TG без markdown-символов, X ≤280.
4. Проследить wf-publish-status: post → published/error + tg-алерт «Опубликовано #id» без (mock).
5. Проверить поведение 422 «аккаунт не подключён» при neverError: вебхук отвечает, пост уходит в status=error через поллинг.
