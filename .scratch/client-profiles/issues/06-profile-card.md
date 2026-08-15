# 06 — Раздел «Профиль»: карточка, список, выбор, выход

**What to build:** В боте появляется раздел «Профиль»: кнопка на старте и в меню, карточка активного профиля (название, ниша, описание, ЦА, тон, число ссылок и документов), выбор профиля из списка, выход из профиля. Легаси-команды client/clients ведут в те же ветки.

**Blocked by:** 05 (файловая серия)

**Status:** done (14.08, верифицировано оркестратором)

- [x] Ветка profile: PF Build (резолв-шаблон T5) → PF HTTP → PF Check (ok:true/false) → PF Format (карточка: название/ниша/описание ≤200/ЦА обе формы/тон/счётчики links+docs+refs; esc()) → TG pf (7 кнопок: pf_new/pf_list/pf_edit/pf_add_link/pf_add_doc/pf_exit/cmd:menu)
- [x] Ветка profiles: PS Build (LIMIT 11) → PS HTTP → PS Format (список; 0 строк; >10 подсказка client <id>) → TG ps (динамика pf_switch:{id}, Меню)
- [x] Switch cb: 15→22 правила (pf_switch/pf_exit/pf_new/pf_edit/pf_add_link/pf_add_doc/pf_list), выходы 16→23, fallback 15→22 (существующие 0–14 не тронуты, снапшот до мутаций); Parser: `action.startsWith('pf_')` → cb, entity_id=parts[1]
- [x] pf_switch:{id}: PSW Check (валидация id) → users UPDATE + settings синхрон → карточка выбранного профиля
- [x] pf_exit: PX — users.active_client_id=NULL + settings → первый active-клиент → «Профиль снят» + кнопка Профиль
- [x] pf_new/pf_edit/pf_add_link/pf_add_doc — временные заглушки (PFN/PFE/PFL/PFD chains), полные в 07/08
- [x] Кнопки «👤 Профиль» (cmd:profile): TG start (3-й ряд), TG menu system
- [x] Валидации (ОРКЕСТРАТОР): validate 0 issues (595 нод), lint 0, node --check 13/13, sim PF Check (client→ok:true / []→ok:false), PS Format (1 строка/0), PX Build users (UPDATE NULL), маппинг выходов Switch cb 15–22

Артефакт: `.scratch/client-profiles/fixes/wf-tg-bot.json` (595 нод; снапшот `wf-tg-bot.06.json`)

Примечания: callback_data строками в `additionalFields.callback_data` (литерал `pf_new` без `={{ }}`); статика в TG-текстах без `_` или с esc() на рантайме; esc-строку копировать из эталона (MO Format), не набирать вручную.
