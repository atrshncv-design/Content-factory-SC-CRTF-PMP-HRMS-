# T1 — Выбор длительности ролика в ручном цикле (решение пользователя 14.08)

**What to build:** в ручном режиме (mode=manual) бот перед началом генерации спрашивает длительность ролика КНОПКАМИ (30/60/90 + своя), сценарий пишется под выбранную длину, video_length в payload = выбранная длина (не LLM-догадка).

**Blocked by:** None — база = `.scratch/review-full-14aug/fixes/wf-tg-bot.json` (510 нод, live 14.08)

**Status:** ready-for-agent

**Контекст (проверено оркестратором):**
- `CT Build bridge prompt` (scriptwriter): промпт ЖЁСТКО «(30 сек, ~65 слов, русский)» — нет параметризации
- `AS Build bridge prompt` (json-builder): `video_length` из LLM — `(script.target_length || 30)` — модель сама решает, не контролируется
- `AU Build prompt` (auto): тоже жёстко 30 сек
- URL→видео уже имеет выбор длительности: кнопки dur_30/60/90 + произвольный ввод → `dur` → `DU Parse state` (валидация 15-300) → `video_length: Number(st.dur)` — ЭТАЛОН паттерна выбора
- Состояния: sessions.state (CYCLE_*), quick_payload (JSON в sessions) — паттерн для хранения выбранной длины
- tg_user_id: используется `p.tg_user_id` (D2 заменил хардкоды)
- esc-эталон MO Format; сериализация indent=1/ensure_ascii=False/без trailing newline; BFS обязателен

**Что сделать:**
1. **start_cycle (manual)**: после команды start_cycle (или после аналитики/тем — реши, где меньше всего ломает; РЕКОМЕНДАЦИЯ: сразу после start_cycle, ДО аналитики — «перед началом») — бот шлёт «⏱ Выбери длительность ролика» + кнопки `dur:30` / `dur:60` / `dur:90` + «🔢 Своя (напиши число 15–300)» + «🧹 Отмена» + «📋 Меню» → новое состояние CYCLE_DUR_AWAIT (sessions.state + quick_payload)
2. **Обработка выбора**: callback `dur:N` (или текст-число в состоянии CYCLE_DUR_AWAIT) → валидация 15–300 (паттерн DU Parse state) → сохранить длину в sessions (quick_payload.duration или новая запись) → продолжить цикл (аналитика)
3. **Параметризация scriptwriter**: `CT Build bridge prompt` (и AU — для консистентности, см. T2) подставляет выбранную длину: «{dur} сек, ~{Math.round(dur*65/30)} слов»
4. **video_length в payload**: `AS Build bridge prompt` — использовать ВЫБРАННУЮ длину (из sessions), НЕ `target_length` из LLM-ответа (или жёстко валидировать target_length == выбранная, иначе правка)
5. **auto-режим**: НЕ ломать полный автомат — в auto длина из настроек (дефолт 30; если есть settings.video_length — использовать), выбор кнопками ТОЛЬКО в manual (T2)
6. Валидация: validate 0 issues (BFS), lint 0, node --check, sim (выбор 30/60/90, ввод числа 45, невалидное 5/400 → повторный запрос)
7. Результат: write_file в `.scratch/review-full-14aug/fixes/wf-tg-bot.json` + отчёт `fixes/T1-duration-select.md`
