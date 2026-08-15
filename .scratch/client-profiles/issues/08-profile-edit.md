# 08 — Редактирование профиля и точечные добавления

**What to build:** Профиль можно изменить: пере-опрос с предзаполненными ответами («Пропустить» = оставить старое значение) и точечные добавления ссылки/документа в существующий профиль без пере-опроса. Приём документов вне интервью.

**Blocked by:** 07 (файловая серия; переиспользует механику profile_doc и draft)

**Status:** done (14.08, верифицировано оркестратором; ретрай после провала формата — исправлено)

- [x] Редактирование (pf_edit): PFE Build check (резолв T5) → PFE HTTP → PFE Check → Switch pfe (нет профиля → PFE Format none + TG pfe) → PFE Build ensure (INSERT OR IGNORE sessions) → PFE Build draft (mode edit, answers из clients, audience raw/type, links/docs parse try/catch, refs join) → PFN Qlist (edit: «Сейчас: …»)
- [x] PFN Parse answer: разрешён mode edit (mode !== 'new' && mode !== 'edit' → invalid); PFN Build save: edit → UPDATE clients (nv-NULL) + clear + «Профиль обновлён» (users/settings не трогает); new — как было
- [x] Добавить ссылку (pf_add_link): PFL Build check (резолв AS ac_id) → PFL Check (ac_id=0 → «Нет активного профиля» + Профиль) → PFL Build state (PROFILE_ADD_LINK) → PFL Format → TG pfl; ответ: Gate Check += PROFILE_ADD_LINK → profile_add_link → PAL Build read → PAL Parse (split('\n'), URL-фильтр, append к context_links, не-URL → ok:false «Только ссылки») → PAL Build write → PAL Format («Добавлено ссылок: N») → TG pal
- [x] Добавить документ (pf_add_doc): PFD Build check → PFD Check → PFD Build state (PROFILE_ADD_DOC) → PFD Format → TG pfd; файл: PD Check += PROFILE_ADD_DOC → add_doc → PD Read docs → bridge /doc-text → PD Parse (draft null → append к clients.context_docs + state PROFILE_ADD_DOC — 2 SQL через 2 item'а → PD HTTP save); ссылка: Gate Check += PROFILE_ADD_DOC → profile_add_doc → PAD Parse (URL → {name:url, mime:'link'}) → PAD Build write → PAD Format → TG pad
- [x] Валидации (ОРКЕСТРАТОР): формат list/len 1 ✓, validate 0 issues (700 нод), lint 0, node --check 57/57, sim 4/4 (edit-ответ перезаписывает name; PAL ссылки 2 шт + не-URL отказ; PD add_doc → UPDATE clients + PROFILE_ADD_DOC; PFE draft mode edit), Switch gate out[7..9] → PFN/PAL/PAD, Switch pd out[0..3] → draft/processing/docs/outside

Артефакт: `.scratch/client-profiles/fixes/wf-tg-bot.json` (700 нод; снапшот `wf-tg-bot.08.json`)

Примечания: append в JSON-массив — parse → push → stringify (try/catch на битом JSON — инициализировать []). НЕ удалять поля профиля при edit, если ответ «Пропустить». Все TG-тексты через esc().
