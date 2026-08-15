# A2 — Блокер п.4: автоматический режим (mode auto) реально работает

**What to build:** `mode auto` переключает цикл на автоматический: темы/сценарии/публикация проходят БЕЗ ручных подтверждений (с автоподтверждением и обработкой ошибок), ручной режим — как сейчас.

**Blocked by:** None — can start immediately (база = live-экспорт `.scratch/review-full-14aug/base/`)

**Status:** ready-for-agent

**Контекст:** фикс-волна по `docs/CODE-REVIEW-2026-08-14.md` (§4 п.4). Ревью подтвердило: команда `mode manual|auto` РАБОТАЕТ (MO Build → UPDATE settings SET value WHERE key='mode'), НО `settings.mode` читается ТОЛЬКО для отображения (ST/ST2/MU/IN/HL Format показывают «📅 Режим:») — ни одна ветка цикла по нему не ветвится. БД: `mode|manual`.

**Рабочий файл (только база, НЕ репо workflows/!):**
- `.scratch/review-full-14aug/base/wf-tg-bot.json` (404 нод, live 14.08)
- Справочники: `references/state-machine-test-u7.md` (state machine: IDLE → CYCLE_ANALYTICS_PENDING → CYCLE_SCRIPT_PENDING → CYCLE_GENERATION_PENDING → CYCLE_PUBLISH_PENDING → IDLE), `references/ux2-menu-quick-scenarios.md`, скрипты валидации в скилле.

- [ ] **Гейт по mode на входах цикла**: SC Build state (start_cycle) читает settings.mode; при `auto` — после аналитики НЕ ждать approve:topic, а автоподтверждать лучшую тему (INSERT topics + переход в script-этап); при `manual` — как сейчас (кнопки).
- [ ] **Автоподтверждение сценария**: при auto — approve:script автоматически после генерации сценария (CT/ET цепочки), переход к генерации.
- [ ] **Автопубликация**: при auto — подтверждение публикации (CP confirm) автоматически по выбранным платформам/времени, ИЛИ публикация в дефолтные платформы без stage4; ошибки генерации в auto — алерт оператору + возврат в IDLE (не зависание).
- [ ] **Переключение mid-run**: `/cancel` в auto работает; переключение manual↔auto в любой момент (MO Build уже есть); отображение актуального режима в статусе.
- [ ] **Безопасность трат**: в auto гейты 10/50 работают ТАК ЖЕ (при балансе <10 или cost>50 — стоп + сообщение, даже в auto).
- [ ] Валидация: `validate-workflow-json.py` 0 issues, BFS, `lint-workflow-json.py` 0 находок, node --check, sim-прогон.
- [ ] Отчёт: write_file в `.scratch/review-full-14aug/fixes/A2-auto-mode.md` — схема переходов в auto, изменённые ноды, остатки.
