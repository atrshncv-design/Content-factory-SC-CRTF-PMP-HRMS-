# D2 — Долг: замена хардкода tg_user_id 941296693 + secret_token tg-trigger + AU-гейт

**What to build:** (1) все SQL-ноды wf-tg-bot и wf-creatify-webhook используют `$('Parser').first().json.tg_user_id` вместо хардкода 941296693 (расширение whitelist не сломает сессии); (2) tg-trigger получает secret_token; (3) AU-цепочка (auto-режим) получает кредитный гейт как AS (остаток финального тикета).

**Blocked by:** финальный тикет серии (C2+B3+AS) — база = его результат (505 нод)

**Status:** ready-for-agent

**Контекст:** фикс-волна по `docs/CODE-REVIEW-2026-08-14.md` (Y3, Y5, Y11). Ревью: 39 Code-нод wf-tg-bot + 3 ноды wf-creatify-webhook хардкодят `941296693` в SQL-параметрах; tg-trigger `additionalFields: {}` — secret_token не задан.

**Рабочие файлы (после серии):** `.scratch/review-full-14aug/fixes/wf-tg-bot.json`, `.scratch/review-full-14aug/fixes/wf-creatify-webhook.json`

- [ ] wf-tg-bot: во всех Code-нодах с `params: [..., 941296693]` заменить на `$('Parser').first().json.tg_user_id` (аккуратно: некоторые ноды вызываются НЕ из Parser-контекста — проверить по connections, что Parser достижим; для нод вне Parser-цепочки — брать из $json или сохранить хардкод с комментарием)
- [ ] **AU-гейт (остаток Y2)**: AU-цепочка (auto-режим): `AU Build link body → AU HTTP creatify-link` — добавить кредитный гейт как у AS (AS LB creatify → парсер → IF balance < 10 → AU Format low (esc) → TG AU alert; иначе → creatify-link). Паттерн — ноды AS LB creatify / AS Check link из этого же файла
- [ ] wf-creatify-webhook: Build session update/reset/Build alert — аналогично (там Parser недостижим — это webhook-воркфлоу! проверить: callback приходит от creatify, tg_user_id надо брать из sessions по generation_id или хранить в сессии — решить и описать)
- [ ] tg-trigger: `additionalFields: {secretToken: '={{ $env.FACTORY_WEBHOOK_SECRET }}'}` — но учесть FIX-10: env может быть пуст; сверить с документацией n8n telegramTrigger (secret_token опционален; если env пуст — n8n может упасть; решить: статичный токен в переменной n8n или пропустить)
- [ ] Валидация: validate 0 issues, lint 0, node --check, sim
- [ ] Отчёт: `.scratch/review-full-14aug/fixes/D2-hardcoded-user.md`
