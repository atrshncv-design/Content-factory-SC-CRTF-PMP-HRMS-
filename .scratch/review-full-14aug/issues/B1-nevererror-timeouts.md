# B1 — Надёжность: neverError + таймауты на 5 вызывающих webhook (wf-tg-bot)

**What to build:** 5 HTTP-нод wf-tg-bot (SC HTTP wf-analytics, OB HTTP wf-onboard, CP HTTP wf-publish, AS HTTP creatify-link, AS HTTP creatify-submit) получают вложенный neverError и адекватные таймауты, чтобы 4xx/5xx от получателей не роняли execution молча.

**Blocked by:** None — can start immediately (база = live-экспорт `.scratch/review-full-14aug/base/`)

**Status:** ready-for-agent

**Контекст:** фикс-волна по `docs/CODE-REVIEW-2026-08-14.md` (R1, Y9). Ревью: у этих 5 нод `neverError` отсутствует (live-инвентарь подтвердил neverError=NO), у соседних (CRS/CRP/CRC/AUD/TR/CMT/AVA/AVL/AST/SHT/PRD/BNR) = YES. Таймауты: SHT 300000 vs сумма 420000 (bridge 300000 + ai_shorts 120000); CP 300000 vs N×300000 (Split In Batches адаптации); AS 60000 vs 300000+.

**Рабочий файл:** `.scratch/review-full-14aug/base/wf-tg-bot.json` (404 нод, live 14.08). Эталон neverError — `CRS HTTP` (вложенный `options.response.response.neverError: true`); эталон обработки ошибок после neverError — CRS Format (try/catch + `body.ok !== true` → сообщение юзеру).

- [ ] Добавить `options.response.response.neverError: true` в 5 нод: SC HTTP wf-analytics, OB HTTP wf-onboard, CP HTTP wf-publish, AS HTTP creatify-link, AS HTTP creatify-submit
- [ ] Таймауты: AS creatify-link/submit — поднять до покрытия суммы (≥300000 или пересмотреть калибровку); CP HTTP wf-publish — документировать лимит или поднять; SHT — согласовать с целевым (wf-creatify-shorts: Exp bridge 300000 + ai_shorts 120000 = 420000 → вызывающий ≥420000)
- [ ] После neverError — ветка обработки ошибки (как CRS Format): `$json.error` / `$json.body.ok !== true` → человекочитаемое сообщение в TG, состояние сессии не зависает (IDLE или повтор)
- [ ] Валидация: `validate-workflow-json.py` 0 issues, BFS, `lint-workflow-json.py` 0 находок, node --check, sim
- [ ] Отчёт: write_file в `.scratch/review-full-14aug/fixes/B1-nevererror-timeouts.md`
