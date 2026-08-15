# T1 — Выбор длительности ролика в ручном цикле: РЕАЛИЗОВАНО (14.08.2026)

**Файл:** `.scratch/review-full-14aug/fixes/wf-tg-bot.json` — 510 → **533 ноды**, 0 issues, lint 0 (верифицировано оркестратором).
**Отчёт по данным субагента sa-0-72f3c10d** (файл отчёта не был дописан из-за лимита итераций; данные из финального ответа).

## Что сделано
- **Гейт после старта цикла** (между `SC HTTP setstate` и `SC Build analytics body`, сразу после start_cycle, ДО аналитики): `DR Build settings → DR HTTP settings → DR Check → Switch DR gate`. `mode=manual` → экран выбора; fallback (auto/прочее) → `SC Build analytics body` без изменений.
- **Экран выбора**: `DR Build ask state` (state=`CYCLE_DUR_AWAIT`, quick_payload=NULL) → `DR HTTP ask state` → `DR Format ask` («⏱ Выбери длительность ролика (15–300 сек)…») → `TG DR ask` (кнопки `cmd:durc_30/60/90`, «🔢 Своя (напиши число)», «🧹 Отмена», «📋 Меню»).
- **Обработка**: Parser: новый префикс `durc_` → `command='durc'`; новое правило `Switch cmd` (индекс 34, перед fallback). Текст-число в `CYCLE_DUR_AWAIT`: `Gate Check` + `cycle_dur` → новое правило `Switch gate` (индекс 6) → `DR Build state → DR HTTP state → DR Parse`. Валидация паттерном B2: `dur >= 15 && dur <= 300`; `dur_ok` → `DR Build save` (state=CYCLE_ANALYTICS_PENDING, quick_payload=`{"duration":N}`) → `DR HTTP save` → `DR Format ok` → `TG DR ok` → `SC Build analytics body` (цикл продолжается); `dur_wrong`/`ask_custom` → повторный запрос (`TG DR wrong`); вне состояния → `TG unknown`.
- Параметризация scriptwriter (CT Build bridge prompt) и json-builder (AS Build bridge prompt): используют выбранную длину из quick_payload.duration (дефолт 30) — «({dur} сек, ~{Math.round(dur*65/30)} слов)»; video_length в payload = выбранная.
- auto: НЕ ломает полный автомат — в auto выбор не показывается (гейт DR Check пропускает), длина дефолт 30 (T2 уточнит settings.video_length).

## Верификация
- validate 0 issues (533 нод, BFS 533/533, node --check 243 jsCode); lint 0; sim 36/36 (выбор 30/60/90 ok; ввод 45 ok; 5/400 → повторный запрос)
- DR-ноды 12 шт; `durc` в Parser; Switch cmd 35 правил; Switch gate 7 правил

## Остатки
- Отчёт субагента не дописан (лимит итераций) — восстановлен оркестратором
- T2 (auto: settings.video_length вместо дефолта 30) — следующий
