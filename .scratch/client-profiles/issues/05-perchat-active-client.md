# 05 — Активный профиль per-чат: резолв во всех чтениях + починка битого id

**What to build:** Активный профиль привязывается к чату (users.active_client_id), а не глобально. Все ~11 чтений `active_client_id` из settings переводятся на per-чат резолв с fallback на глобальный и валидацией существования клиента (чинит битый live id 999). Записи (переключение, онбординг) пишут и per-чат, и глобальный.

**Blocked by:** 04 (файловая серия)

**Status:** done (14.08, верифицировано оркестратором)

- [x] Паттерн чтения во всех Build-нодах с `active_client_id`: единый резолв-шаблон `SELECT COALESCE((SELECT c.id FROM clients c WHERE c.status='active' AND c.id = COALESCE((SELECT u.active_client_id FROM users u WHERE u.tg_user_id = ?), (SELECT CAST(value AS INTEGER) FROM settings WHERE key='active_client_id'))), (SELECT c2.id FROM clients c2 WHERE c2.status='active' ORDER BY c2.id LIMIT 1), 0)` с params [p.tg_user_id]
- [x] settings-мапа-цепи (ST/MU/IN/HL Build settings): UNION-мапа с активным client_id (CAST AS TEXT) и client_name (NULL при отсутствии профиля); потребители мапы не менялись
- [x] ST2 Build client / CM Build / DU Build settings — резолв-подзапрос; DU Build script/submit — `const row=(s.rows||[])[0]||{}; const clientId=Number(row.ac_id)||0`
- [x] Записи: CL Build update → UPDATE users (params [chk.id, p.tg_user_id]) + синхрон settings через новую пару (CL Build update global → CL HTTP update global, гвард !validId); OB Build set active → UPDATE users + пара (OB Build set active global → OB HTTP set active global)
- [x] Починка битого 999: валидация существования клиента + fallback первый active-клиент + 0 встроена в резолв
- [x] Валидации (ОРКЕСТРАТОР): validate 0 issues (559 нод), lint 0, node --check 10/10, sim DU Build script (ac_id=2→client_id=2; ac_id=0→0), старых plain-чтений active_client_id из settings не осталось

Артефакт: `.scratch/client-profiles/fixes/wf-tg-bot.json` (559 нод; снапшот `wf-tg-bot.05.json`)

Примечания: не ломать остальные ключи settings (mode/limits/credits остаются глобальными как есть). Паттерн согласован в ADR-0001. jsCode проверять node --check ДО записи в файл.
