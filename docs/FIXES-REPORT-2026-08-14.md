# FIXES REPORT — контент-завод (14.08.2026)

**Волна 1:** фикс-волна по `docs/CODE-REVIEW-2026-08-14.md` (вердикт ❌ НЕ ГОТОВ → фиксы) — **ЗАДЕПЛОЕНА**
**Волна 2:** решения пользователя (выбор длины кнопками / полный автомат / sendVideo) — **ЗАДЕПЛОЕНА**
**Метод:** 0 кредитов SC/creatify (статика + sim + read-only SSH); подготовка субагентами на live-базе → показ → деплой после «ок» пользователя
**Базa:** live-экспорт 14.08 (`.scratch/review-full-14aug/base/` — репо-экспорты были устаревшими)

## Задеплоено на сервер (8 воркфлоу, apply_fix.sh)

| # | Воркфлоу | Нод до→после | Фиксы |
|---|---|---|---|
| 1 | wf-tg-bot | 404→**510** | text_post-команда (п.3), auto-режим AU-ветка (п.4), neverError+таймауты (R1), dur-валидация 15-300 (R2), DU Gate ceil (Y4), `/instruction` (Y10), AS-гейт (Y2), AU-гейт (Y2-ост.), хардкод 941296693→p.tg_user_id (Y3) |
| 2 | wf-publish | 26 | text-only маршрутизация (R3/п.3): пустые file_ids → текстовая публикация |
| 3 | wf-creatify-webhook | 25 | esc() в Build stage3 + Build update failed (Y6) |
| 4 | wf-creatify-asset | 7→9 | credit-гейт GET remaining_credits → порог 5 (Y7) |
| 5 | wf-creators-search | 25→29 | low_credits-гейт порог 5 (Y1) |
| 6 | wf-creator-profile | 20→24 | low_credits-гейт порог 5 (Y1) |
| 7 | wf-creator-content | 18→22 | low_credits-гейт порог 5 (Y1) |
| 8 | wf-transcripts-comments | 37→45 | 2 low_credits-гейта (transcript+comments) порог 5 (Y1) |

**Также:** DEPLOYMENT.md — 5 правок правдивости (wf-credit-check-фантом, id ...015/016, счётчики); `register-tg-commands-31.sh` скопирован с сервера в репо.

## Проверки после деплоя (0 кредитов)
- ✅ 24/24 воркфлоу active; webhook_entity 24
- ✅ probe tg-trigger → **403** (маршрут жив); zz-test → 200; creatify-webhook → 200
- ✅ Активация в логах чистая («Activated workflow wf-tg-bot»); cron исполняется (publish-status каждые 2 мин)
- ✅ Валидатор: все 8 файлов 0 issues; линтер 0 находок; sim-прогоны зелёные (dur 5/400→wrong, 30/60→ok; CP 402→esc-сообщение; AS low_credits→«Недостаточно кредитов»; text-only details без file_ids)

## Питфолл деплоя (важно для будущих волн)
**Субагенты создают ноды с несуществующими typeVersion**: A1-fix2 сделал telegram-ноды v2.2 и switch v2.2 — в n8n 2.34.4 есть только telegram v1.2 (89 нод) и switch v3.4 (33 ноды) → активация падала `Cannot read properties of undefined (reading 'execute')`, probe 500. Исправление: понизить typeVersion до эталона (telegram 1.2 / switch 3.4), передеплой. **Правило: перед деплоем проверять typeVersion новых нод против эталона базы** (валидатор этого не ловит).

## Остатки (не блокеры, задокументированы)
- tg-trigger secret_token — не задан (FIX-10: env может быть пуст; включение после согласования с отправителем колбэков)
- Мёртвая `const TG = 941296693` в Parser (безвредна)
- Y11: 12 boolean-свитчей со string-оператором — требует live-теста ok=false-веток
- DU quick url2video/легаси → fallback 941296693 в webhook (session-link не пишется) — отдельный тикет
- wf-credit-check не существует (удалён из архитектуры 13.08) — DEPLOYMENT приведён в соответствие
- Платные live-тесты (text_post, auto-цикл, кредитные гейты в real) — ПОСЛЕ согласования пользователя (гейт на траты)

## Артефакты
- Подготовка фиксов: `.scratch/review-full-14aug/fixes/` (8 JSON + 10 отчётов + трансформеры)
- Live-база: `.scratch/review-full-14aug/base/` (24 файла, экспорт 14.08)
- Отчёт ревью: `docs/CODE-REVIEW-2026-08-14.md`
- Репо синхронизирован с live (24 workflows/*.json, wf-tg-bot 510 нод) — не закоммичено
