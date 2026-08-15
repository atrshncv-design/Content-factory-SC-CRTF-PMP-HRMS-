# C2 — Защита трат: DU Gate round→ceil + гейт в wf-creatify-asset

**What to build:** (1) формула стоимости URL→видео в wf-tg-bot DU Gate использует округление ВВЕРХ (как реально списывает creatify, и как уже делает SH Gate); (2) wf-creatify-asset получает кредитный гейт перед POST /api/asset_generator/.

**Blocked by:** None — can start immediately (база = live-экспорт `.scratch/review-full-14aug/base/`)

**Status:** ready-for-agent

**Контекст:** фикс-волна по `docs/CODE-REVIEW-2026-08-14.md` (Y4, Y7). Ревью:
1. DU Gate: `Math.round(5*dur/30)` vs фактическое списание creatify 5 кред/30с с округлением ВВЕРХ (SH Gate использует `5 * Math.ceil(dur/30)` — верно). dur=45: гейт «~8» (≤50 пропуск), creatify спишет 10.
2. wf-creatify-asset (7 нод, live): цепочка Webhook→validate→Switch→HTTP Asset БЕЗ credit-check (asset_generator = 1 кред/шт, count≤4); паттерн кластера (GET remaining_credits перед POST) нарушен; эталон — wf-creatify-product (credit-гейт 20).

**Рабочие файлы (только база):**
- `.scratch/review-full-14aug/base/wf-tg-bot.json` (404 нод) — DU Gate
- `.scratch/review-full-14aug/base/wf-creatify-asset.json` (7 нод)

- [ ] wf-tg-bot DU Gate: `Math.round` → `Math.ceil` (формула `5 * Math.ceil(dur/30)` как SH Gate)
- [ ] wf-creatify-asset: GET `/api/remaining_credits/` (бесплатно) перед HTTP Asset + IF balance < порог (порог ≥ 1×count; предложить ≥5) → {ok:false, low_credits, balance}; mock-режим не блокирует
- [ ] Валидация: `validate-workflow-json.py` 0 issues, `lint-workflow-json.py` 0 находок, node --check, sim
- [ ] Отчёт: write_file в `.scratch/review-full-14aug/fixes/C2-gate-fixes.md`
