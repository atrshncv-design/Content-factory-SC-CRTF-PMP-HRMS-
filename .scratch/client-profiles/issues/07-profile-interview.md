# 07 — Интервью «Создать профиль» (8 вопросов, ссылки, документы)

**What to build:** Пользователь создаёт профиль клиента через интервью из 8 фиксированных пропускаемых вопросов: название, ниша, что делает компания, ЦА, ссылки на ресурсы (по одной, кнопка «Готово»), документы (файлом или ссылкой), тон, конкуренты/референсы. В конце профиль сохраняется и становится активным в чате.

**Blocked by:** 06 (файловая серия). Контракт обработки документов — из тикета 02 (endpoint `/doc-text`), сам bridge может быть ещё не задеплоен (E2E-тест документов — в тикете 12).

**Status:** done (14.08, верифицировано оркестратором)

- [x] pf_new → полный цикл: PFN Build ensure (INSERT OR IGNORE sessions) → start (state=PROFILE_AWAIT, draft {mode:new,step:1..8}) → PFN Qlist (8 вопросов «Вопрос N/8», шаги 5/6 мульти «пришли по одной, потом Готово») → TG pfn (Пропустить/Отмена; на 5/6 +Готово); busy-ветка «Интервью уже идёт»
- [x] Ответы свободным текстом: Gate Check += PROFILE_AWAIT → mode profile_answer → PFN Parse answer (шаги 1-4/7 текст ≤2000; 5 URL→links; 6 только файл/ссылка; 8 многострочный refs; невалид → понятное сообщение) → save draft → Qlist
- [x] Сохранение: PFN Build save (INSERT clients: name/niche/description/audience_json {"raw"}/tone/context_links/context_docs/context_refs split('\n'), status active, onboarded_by) → per-чат users+settings → clear (IDLE, profile_draft=NULL) → «Профиль создан и активен»
- [x] Пропустить/Готово: pf_skip (step+1; с 8 → сохранение), pf_done (5→6, 6→7) — Switch cb += pf_skip/pf_done (24 правила, выходы 25, fallback сдвинут, снапшот до мутаций)
- [x] Документы: PD Check (PROFILE_AWAIT+step6→interview_doc; PROFILE_DOCS_SUBMITTING→processing «ещё обрабатывается»; иначе outside) → bridge /doc-text (digest=true, timeout 300000) → PD Parse (append draft.docs, PROFILE_AWAIT, «Добавлено: name (N симв.)»)
- [x] CN Build += profile_draft=NULL (отмена очищает черновик)
- [x] Валидации (ОРКЕСТРАТОР): validate 0 issues (652 нод), lint 0, node --check 32/32, sim 5/5 (шаг 1→name+step2; ссылка→links; не-URL→invalid; документ→docs+PROFILE_AWAIT; ошибка bridge→fail)

Артефакт: `.scratch/client-profiles/fixes/wf-tg-bot.json` (652 нод; снапшот `wf-tg-bot.07.json`)

Примечания: состояние одно (PROFILE_AWAIT) + шаг в draft (не плодить 8 состояний). Вопросы — статичным списком в Code-ноде (массив строк), текст вопросов в esc() для TG. Кнопки «Пропустить»/«Готово» — callback `pf_skip`/`pf_done` (литералы). Не создавать дублей: ветка должна переиспользовать PF Format из 06 для карточки.
