# 11 — Команды Telegram, документация, синк репозитория

**What to build:** Меню команд Telegram пополняется («профиль», «профили», «добавить оператора», «операторы»), документация (DEPLOYMENT, PROGRESS) отражает фичу, репозиторий синхронизирован с финальной версией воркфлоу.

**Blocked by:** 10 (финальная версия wf-tg-bot для синка)

**Status:** done (15.08, сделано оркестратором напрямую — механический тикет; субагент упёрся в лимит итераций)

- [x] tg-commands-35.json (35 команд: 31 + profile/profiles/add_operator/operators) — `.scratch/client-profiles/fixes/tg-commands-35.json`
- [x] register-tg-commands-35.sh (копия 31-го: payload 35, verify total=35, want-set +4 команды; TG_IP/логика не тронуты) — bash -n OK
- [x] wf-tg-bot: help-текст (IN Format + HL Format) — «Команды можно писать текстом: меню, статус, бюджет, инструкция, профиль, отмена»
- [x] DEPLOYMENT.md: раздел «§ Профили клиентов (15.08)» (фича, схема, команды, статус)
- [x] PROGRESS.md финализирован (01–11 done)
- [x] Секрет-скан новых файлов: clean (0 hits)
- [x] Валидации: json list/1 (719 нод), validate 0 issues, lint 0, tg-commands ровно 35
- [ ] Синк workflows/ (wf-tg-bot.json, hermes-bridge/server.py) — в тикете 12 ПОСЛЕ деплоя
- [ ] git commit волны — после «ок» пользователя (гейт деплоя)

Примечания: паттерн register-скрипта — register-tg-commands-31.sh (ждёт housekeeping 20с, verify дважды). Команды в меню — без слеша (автокомплит Telegram сам добавляет /).
