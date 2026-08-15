# C1 — Защита трат: low_credits-гейт ДО вызова на SC search/profile/content/transcripts + гейт на AS-цепочку (wf-tg-bot)

**What to build:** перед платным SC-вызовом (creators-search, creator-profile, creator-content, transcripts-comments) проверяется баланс SC (бесплатный GET /v1/account/credit-balance) — при балансе ниже порога → понятный отказ без списания; то же для AS-цепочки генерации (approve:script → creatify-link/submit) — гейт 10/50 как у DU/SH.

**Blocked by:** None — can start immediately (база = live-экспорт `.scratch/review-full-14aug/base/`)

**Status:** ready-for-agent

**Контекст:** фикс-волна по `docs/CODE-REVIEW-2026-08-14.md` (Y1, Y2). Ревью: у SC search/profile/content/transcripts (live: 25/20/18/37 нод) mock/real-гейты ЕСТЬ (FIX-06), но low_credits-гейта ДО вызова НЕТ (только постфактум-обработка 402 в Normalize). У wf-audience гейт 30 уже есть (FIX-05) — эталон. В wf-tg-bot AS-цепочка (start_cycle → approve:script → creatify-link/submit) идёт БЕЗ кредитного гейта (гейты только у UV/DU/SH).

**Рабочие файлы (только база):**
- `.scratch/review-full-14aug/base/wf-creators-search.json` (25 нод)
- `.scratch/review-full-14aug/base/wf-creator-profile.json` (20 нод)
- `.scratch/review-full-14aug/base/wf-creator-content.json` (18 нод)
- `.scratch/review-full-14aug/base/wf-transcripts-comments.json` (37 нод)
- `.scratch/review-full-14aug/base/wf-tg-bot.json` (404 нод) — AS-цепочка
- Эталон low_credits-гейта: wf-audience (14 нод, live) — GET credit-balance → IF balance<порог → {ok:false, low_credits} до платного вызова

- [ ] В 4 SC-воркфлоу: вставить GET `/v1/account/credit-balance` (бесплатно, keypair-заголовки, typeVersion 4.5, никогда вложенный, timeout 15000) + IF balance < порог (порог ≥ цены эндпоинта: search/profile/content ≈ 1-3, transcripts ≈ 1-5) → {ok:false, error:'low_credits', balance} БЕЗ платного вызова; real-ветка — только при достаточном балансе; в mock-режиме гейт не блокирует (PLACEHOLDER-ветка)
- [ ] В wf-tg-bot AS-цепочка: вставить гейт 10/50 как у DU (LB creatify уже есть в других цепочках — переиспользовать паттерн: при approve:script → проверка баланса creatify → <10 отказ, cost>50 предупреждение)
- [ ] Валидация: `validate-workflow-json.py` 0 issues по всем 5 файлам, `lint-workflow-json.py` 0 находок, node --check, sim
- [ ] Отчёт: write_file в `.scratch/review-full-14aug/fixes/C1-credit-gates.md`
