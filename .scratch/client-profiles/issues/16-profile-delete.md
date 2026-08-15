# 16 — Удаление профиля (мягкое, с подтверждением)

**What to build:** Кнопка «Удалить» в карточке профиля: подтверждение «Точно удалить?» → мягкое удаление (status='deleted', данные в БД остаются); если удаляемый профиль был активным — активный профиль снимается.

**Blocked by:** 15 (файловая серия)

**Status:** done (15.08, верифицировано оркестратором)

- [ ] Карточка профиля (PF Format/TG pf): добавить кнопку «🗑 Удалить» (pf_del) — литерал
- [ ] Switch cb: правило pf_del (перед fallback; снапшот connections)
- [ ] Ветка pf_del: 'PDL Check' (SELECT id, name FROM clients WHERE id=<entity_id> AND status='active'; нет → «Профиль не найден»; иначе) → 'PDL Format' («Точно удалить профиль <name>? Данные сохранятся в архиве» + кнопки: «✅ Да, удалить» pf_del_yes:{id}, «↩️ Нет» pf_del_no, Меню) → 'TG pdl'
- [ ] pf_del_yes:{id} ветка: 'PDL Build del' (UPDATE clients SET status='deleted', updated_at=datetime('now') WHERE id=?) → 'PDL HTTP del' → 'PDL Check active' (был ли удаляемый профиль активным в этом чате: SELECT active_client_id FROM users WHERE tg_user_id=? → равно id?) → 'PDL Build users' (если да: UPDATE users SET active_client_id=NULL WHERE tg_user_id=?) → 'PDL HTTP users' → 'PDL Build global' (UPDATE settings SET value=<первый active id или NULL> WHERE key='active_client_id') → 'PDL HTTP global' → 'PDL Format ok' (esc: «✅ Профиль удалён (в архиве)» + кнопки Профиль/Меню) → 'TG pdl ok'
- [ ] pf_del_no → ответ «Отменено» (answerCallbackQuery) + карточка профиля (PF Build-цепочка)
- [ ] Списки/резолв уже фильтруют status='active' — проверить и НЕ ломать
- [ ] Валидации: validate 0 issues, lint 0, node --check, sim (PDL Check, PDL Build users, PDL Format ok)

Примечания: answerCallbackQuery (operation answerQuery) для каждой callback-ветки; entity_id для pf_del_yes:{id} — parts.slice(2).join(':') в Parser (уже работает). Мягкое удаление — история (topics/scripts/generations/posts) сохраняется.
