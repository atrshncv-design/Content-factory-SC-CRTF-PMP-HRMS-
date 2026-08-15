# 17 — Удаление оператора (команда владельцу)

**What to build:** Владелец удаляет оператора командой «удалить оператора <id>» с подтверждением; себя удалить нельзя; список операторов показывает роли.

**Blocked by:** 16 (файловая серия)

**Status:** done (15.08, верифицировано оркестратором)

- [ ] Parser: команда `remove_operator` = «удалить оператора <id>» (и слеш-формы /remove_operator, /удалить оператора — слеш-форма обязательна) с args.id; Switch cmd правило remove_operator (перед fallback; снапшот connections)
- [ ] Ветка: 'RO Check role' (SELECT role FROM users WHERE tg_user_id=? для отправителя; не admin → отказ «Только владелец») → 'RO Check target' (SELECT role FROM users WHERE tg_user_id=? для цели; цели нет → «Оператор не найден»; цель admin → «Владельца удалить нельзя»; цель operator → подтверждение) → 'RO Format confirm' («Удалить оператора <id>? Он потеряет доступ к боту» + кнопки: «✅ Да, удалить» ro_yes:{id}, «↩️ Нет» ro_no, Меню) → 'TG ro'
- [ ] ro_yes:{id} ветка (Switch cb правило ro_yes): 'RO Build del' (DELETE FROM users WHERE tg_user_id=? AND role='operator') → 'RO HTTP del' → 'RO Format ok' («✅ Оператор <id> удалён» + Меню) → 'TG ro ok'; ro_no → «Отменено» + Меню
- [ ] Список операторов (OP ветка) — уже показывает роли (проверить; если username пустой — показать '—')
- [ ] Валидации: validate 0 issues, lint 0, node --check, sim (RO Check role/target; RO Build del)

Примечания: валидация id (только цифры, 5-12); answerCallbackQuery для ro_yes/ro_no; entity_id из pf-паттерна работает для ro_yes:{id}. DELETE users — только role='operator' (страховка от удаления владельца даже при обходе гейта).
