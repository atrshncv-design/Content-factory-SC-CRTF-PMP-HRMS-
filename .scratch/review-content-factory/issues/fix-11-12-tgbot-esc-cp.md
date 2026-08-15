# FIX-11+12 — wf-tg-bot: esc() + CP-ветка (Волна 3)

**Status:** ready-for-agent
**Blocked by:** —

## Задача
Исправить 2 бага UX в `workflows/wf-tg-bot.json` (исходник — файл репо, 278 нод).
Результат: `.scratch/review-content-factory/fixes/wf-tg-bot.json` (перезаписать файл Волны 1 — там уже есть фиксы кнопок/example.com/туннеля, НЕ потерять их!).

⚠️ ВАЖНО: в `.scratch/review-content-factory/fixes/wf-tg-bot.json` уже лежит исправленная версия (кнопки `={{ ... }}`, example.com-гейт, туннель-плейсхолдер). Работай ОТ НЕЁ, а не от исходника в workflows/ — иначе потеряешь фиксы Волны 1.

## Правки
1. **FIX-11 esc()** (4 Code-ноды Format): `SC Stage1 Format`, `ET Stage1 Format`, `CT Stage2 Format`, `OB Format` — динамические поля LLM (title/rationale/adaptation/hook/body/full_text/name/industry/topics) не обёрнуты esc(). Добавить в начало jsCode: `const esc = s => String(s ?? '').replace(/([_*[\]`])/g, '\\$1');` и обернуть все динамические куски. Эталон — нода `MO Format` (там esc уже есть). Также:
   - Статичные тексты с `/start_cycle` в `TG topic rejected` / `TG script rejected` / `TG gen rejected` / `TG regen` → `start\\_cycle` (экранированная форма, как в TG help).
   - В busy-ветке (`SC Check → TG SC busy`): `state` (вида CYCLE_ANALYTICS_PENDING) обернуть в `esc(state)`.
2. **FIX-12 CP-ветка**: `CP Build publish body` — в wf-publish уходит `{platforms, captions:{}, post_at, generation_id}` без текста. Нужно:
   - Перед ним добавить db-bridge SELECT (или расширить существующий): `SELECT full_text FROM scripts WHERE id = <script_id>` и `SELECT video_output_url FROM generations WHERE id = <generation_id>` — данные из состояния сессии (sessions.generation_id / scripts).
   - В payload wf-publish добавить `content: <full_text>` (или `captions` с текстом) и `file_ids`/video_url при наличии.
   - `CP HTTP wf-publish`: timeout 60000 → 300000.

## Ограничения
- Только чтение + запись результата в `.scratch/review-content-factory/fixes/wf-tg-bot.json`.
- Никаких сетевых вызовов/SSH. Секреты не выводить. JSON валидный + node --check jsCode.
- В отчёте: таблица (нода | было | стало).
- Язык: русский.
