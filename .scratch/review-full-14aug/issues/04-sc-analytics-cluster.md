# 04 — Ревью кластера аналитики/SC (6 воркфлоу)

**What to review:** построчное ревью 6 воркфлоу: `wf-analytics`, `wf-creators-search`, `wf-creator-profile`, `wf-creator-content`, `wf-audience`, `wf-transcripts-comments`.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

**Контекст субагенту:** файлы `workflows/wf-analytics.json`, `workflows/wf-creators-search.json`, `workflows/wf-creator-profile.json`, `workflows/wf-creator-content.json`, `workflows/wf-audience.json`, `workflows/wf-transcripts-comments.json` в корне репо (рабочая копия = live 14.08). Чек-лист `references/workflow-review-checklist.md`; контракты SC — `references/api-endpoints.md`, `references/sc1-creators-search.md`, `references/sc2-creator-profile.md`, `references/fix-06-sc-cluster.md`; цены — `references/api-pricing-budget.md` (audience = 26 кред/запрос, profile НЕ кэшируется, search/keyword кэшируются). Сети нет, только чтение файлов репо.

- [ ] Каждый воркфлоу: webhook-контракт, validate → Switch valid → mock/real, fallbackOutput, real-ветка out[1]
- [ ] Платные вызовы: правильные пути (`/v3/tiktok/profile/videos`, `/v1/tiktok/profile`, `/v2/instagram/post/comments`, audience `/v1/tiktok/user/audience` = 26 кред!), keypair-заголовки, никогда без гейта
- [ ] wf-audience: низкий_порог 30, validate до вызова (26 кред!), mock-ветка, универсальный парсер баланса
- [ ] Обработка ошибок API: success:false / account_deactivated / 402 low_credits → понятное сообщение, не тихий обрыв
- [ ] Нормализация ответов (структуры reels[]/videos[]/search_item_list[]), кандидаты в топ-N
- [ ] wf-analytics: контракт ответа (candidates, platforms_ok/failed), фильтр 12–72ч, дедуп, virality
- [ ] Отчёт: таблица находок по каждому воркфлоу (severity, нода, влияние, доказательство), раздел «проверено и работает», вердикт по кластеру
