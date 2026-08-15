# 03 — Доступ по ролям: Whitelist → users + команды операторов

**What to build:** Бот перестаёт пускать только по хардкод-списку: доступ проверяется по таблице `users` (роли admin/operator). Владелец назначает операторов командой «добавить оператора <tg_id>», видит список операторов. Назначенные получают доступ ко всему контент-заводу в своих чатах.

**Blocked by:** None — can start immediately (users-таблица уже есть на live; сид владельца в тикете 01 не блокирует — строка владельца уже существует)

**Status:** done (14.08, верифицировано оркестратором)

- [x] Цепочка доступа: tg-trigger → Access build (from.id) → Access HTTP (db-bridge, стиль ST HTTP settings) → Access check (role admin/operator → исходный item из $('tg-trigger'); иначе []) → Parser; Whitelist с хардкодом TG=941296693 удалён
- [x] Parser: add_operator («добавить оператора», /add_operator) с args.id; operators («операторы», /operators)
- [x] Switch cmd: 35→37 правил; выходы 36→38, fallback Gate Build уехал на out[37] (снапшот connections сделан — остальные ветки не сломаны, BFS чистый)
- [x] Ветка add_operator: ролевой гейт (admin → INSERT OR IGNORE users role='operator', валидация id 5-12 цифр; не-admin → отказ через TG с esc())
- [x] Ветка operators: список users с esc(), подсказка «добавить оператора <id>»
- [x] Валидации (прогнаны ОРКЕСТРАТОРОМ реальными скриптами скилла): validate 0 issues (549 нод, 251 jsCode), lint 0 находок, node --check новых jsCode OK, sim Access check (operator → item; нет строки → [])
- [ ] Хвост: help-текст не перечисляет add_operator/operators (обновить в тикете 11)

Артефакт: `.scratch/client-profiles/fixes/wf-tg-bot.json` (549 нод; снапшот `wf-tg-bot.03.json`)
