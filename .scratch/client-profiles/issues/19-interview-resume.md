# 19 — Возобновление прерванного интервью

**What to build:** Если в сессии остался черновик интервью (PROFILE_AWAIT + profile_draft), кнопка «Создать профиль» и карточка «Профиль» предлагают продолжить с шага N, начать заново или отменить.

**Blocked by:** 18 (файловая серия)

**Status:** done (15.08, верифицировано оркестратором)

- [ ] pf_new (PFN-цепочка, сейчас 'PFN Build check'/'PFN Check'/'Switch pfn start'): дочерний режим — если state=PROFILE_AWAIT и draft есть → 'PFN Format resume' (esc: «Нашёл черновик интервью — продолжено с шага N/8» + кнопки: «▶️ Продолжить» pf_resume, «🔄 Начать заново» pf_restart, «Отмена» cmd:cancel) → 'TG pfn resume'; если state=PROFILE_AWAIT без draft (битый) или IDLE → как было (новое интервью)
- [ ] Switch cb: правила pf_resume, pf_restart (перед fallback; снапшот connections)
- [ ] pf_resume: answerCallbackQuery + 'PFN Read draft' (уже есть) → 'PFN Qlist' → 'TG pfn' (продолжение с draft.step); pf_restart: answerCallbackQuery + 'PFN Build start' (новый draft, step=1) → Qlist → TG pfn
- [ ] Карточка профиля (TG pf): при наличии draft (state=PROFILE_AWAIT) — кнопка «📝 Продолжить интервью» (pf_resume) — PF Build-цепочка: 'PF Build check' читает state (добавить SELECT state, profile_draft в PF Build SQL или отдельный 'PF Check draft' → Switch: draft есть → карточка + кнопка resume; иначе карточка как была)
- [ ] «Отмена» из resume-экрана — как было (CN Build чистит draft)
- [ ] Валидации: validate 0 issues, lint 0, node --check, sim (PFN Check с draft → resume-формат; pf_resume → Qlist с шага; pf_restart → новый draft)

Примечания: draft не удаляется при навигации (только Отмена/сохранение) — «прерванное» = ушёл из интервью без Отмены. Кнопки resume — на экране pf_new и в карточке (TG pf). answerCallbackQuery для pf_resume/pf_restart.
