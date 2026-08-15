# T2 — Полный автомат: консистентность длительности в auto (решение пользователя 14.08)

**What to build:** auto-режим остаётся ПОЛНЫМ автоматом (без показа видео, без выбора длины) — но video_length в AU-цепи консистентен: длина из настроек (settings.video_length, дефолт 30), НЕ из LLM-догадки.

**Blocked by:** T1 (выбор длины в manual) — тот же файл, база = результат T1

**Status:** ready-for-agent

**Контекст:**
- Пользователь подтвердил: «Полный автомат» — в auto НЕ показывать видео перед публикацией и НЕ спрашивать длину (это осознанное решение)
- T1 добавляет выбор длины в manual (CYCLE_DUR_AWAIT, quick_payload.duration)
- `AU Build prompt` (scriptwriter) сейчас жёстко «30 сек, ~65 слов»; `AU Build prompt json` (json-builder) — `(script.target_length || 30)`
- В auto длина должна браться из settings.video_length (проверить, есть ли такой ключ в settings; если нет — дефолт 30)

**Что сделать:**
1. `AU Build prompt`: параметризовать длину из settings.video_length (дефолт 30) — та же формула слов «({dur} сек, ~{Math.round(dur*65/30)} слов)»
2. `AU Build prompt json`: video_length = settings.video_length (дефолт 30), НЕ script.target_length
3. Проверить, что в auto нет запроса выбора длины (T1 не задел AU-путь) — BFS
4. Валидация: validate 0 issues, lint 0, node --check, sim
5. Результат: write_file `fixes/wf-tg-bot.json` + отчёт `fixes/T2-auto-duration.md`
