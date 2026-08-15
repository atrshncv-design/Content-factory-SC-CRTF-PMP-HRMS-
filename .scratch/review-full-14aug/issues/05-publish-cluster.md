# 05 — Ревью кластера публикации (3 воркфлоу)

**What to review:** построчное ревью 3 воркфлоу: `wf-publish`, `wf-publish-status`, `wf-sync-accounts`.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

**Контекст субагенту:** файлы `workflows/wf-publish.json`, `workflows/wf-publish-status.json`, `workflows/wf-sync-accounts.json` в корне репо (рабочая копия = live 14.08). Чек-лист `references/workflow-review-checklist.md`; контракты — `references/wf-publish-all-platforms.md` (publication_status INTEGER enum: DRAFT=4/PENDING_PUBLICATION=5/TEMPLATE=10, tiktok=106, upload/init скачивает файл), `references/wf-publish-caption-adaptation-pm3.md` (caption-adapter через hermes-bridge, маркерный контракт `<CAPTION>`), `references/fix-13-15-ps-onboard-analytics.md` (Split In Batches loop-back, neverError вложенный). Сети нет, только чтение файлов репо.

- [ ] wf-publish: контракт webhook (content/file_ids ветвление, platforms, captions, post_at), маппинг details[] по 18 платформам, резолв account_ids (запрос → social_accounts → legacy), timeout вызывающего webhook ≥ суммы bridge-вызовов
- [ ] Текстовые посты: умеет ли wf-publish публиковать БЕЗ file_ids (текст-only для Threads/X/VK) — критично для блокера п.3
- [ ] wf-publish-status: Split In Batches loop-back (не First row — очередь >1 поста), статусы pending_publication/publishing/published/error, publication_status enum, tg-alert при ошибке
- [ ] wf-sync-accounts: cron, mock/real, Split In Batches loop-back, UPSERT через db-bridge, алерт при status=2
- [ ] postmypost: реальный ключ/проект (не PLACEHOLDER), mock-ветки без example.com, таймауты, никогда без гейта
- [ ] Отчёт: таблица находок по каждому воркфлоу (severity, нода, влияние, доказательство), раздел «проверено и работает», вердикт по кластеру
