# 04 — Parser: команды профиля + документы

**What to build:** Parser распознаёт команды профиля («профиль», «профили») и приём документов (message.document → profile_doc с file_id/file_name/mime). Switch cmd получает новые выходы для веток профиля.

**Blocked by:** 03 (файловая серия: каждый тикет = трансформация полного файла от результата предыдущего)

**Status:** done (14.08, верифицировано оркестратором)

- [x] Parser: `profile` = «профиль»/`/profile`/`/профиль`; `profiles` = «профили»/`/profiles`/`/профили`; слеш-формы обязательны (автокомплит Telegram). Легаси `client`/`clients` НЕ тронуты (унификация — в тикете 06)
- [x] Документ: `if (m.document)` ДО parseCommand → command='profile_doc', args {file_id, file_name, mime}; caption не парсится как команда
- [x] Switch cmd: правила +3 (profile, profiles, profile_doc) = 40; выходы 38→41: out[37]=PF Format, out[38]=PS Format, out[39]=PD Format, out[40]=Gate Build (fallback сдвинут аккуратно, снапшот connections до мутаций)
- [x] Временные ветки-заглушки: profile/profiles → «Раздел Профиль в разработке» + Меню; profile_doc → «Документы — в разделе Профиль → Добавить документ» + Меню (esc(), кнопка cmd:menu)
- [x] Валидации (ОРКЕСТРАТОР, реальные скрипты скилла): validate 0 issues (555 нод, 254 jsCode), lint 0, node --check, sim Parser 5 кейсов (профиль→profile, /профили→profiles, document→profile_doc с file_id/name/mime, 'client 5'→client args.id=5, callback cmd:menu→menu query_id)

Примечания: эталон Parser — база 533 нод (правила C-маппинга с en+ru+слеш). Снапшот connections ДО мутаций Switch cmd (выходы сдвигаются). Легаси-команды client/clients должны продолжать работать (могут вести в те же ветки, что profile/profiles).
