# 18 — Вопросы интервью: редактирование владельцем

**What to build:** Список вопросов интервью хранится в настройках и редактируется владельцем («вопросы» — показать, «вопрос N <текст>» — заменить, «вопросы сброс» — дефолт). Интервью читает вопросы из настроек.

**Blocked by:** 17 (файловая серия). Контракт: settings.profile_questions (JSON-массив) из тикета 13.

**Status:** done (15.08, верифицировано оркестратором)

- [ ] Parser: команды `questions` = «вопросы»/«вопросы сброс»/«вопрос N <текст>» (парсинг: startsWith('вопросы сброс') → action reset; startsWith('вопрос ') с числом N → action set + args.n + args.value = текст после числа; 'вопросы' → action list; + слеш-формы /вопросы) — вернуть command='questions' с args.action/n/value; Switch cmd правило questions (перед fallback; снапшот connections)
- [ ] Ветка questions (ролевой гейт: только admin): 'QS Build' (SELECT value FROM settings WHERE key='profile_questions') → 'QS HTTP' → 'QS Check role' (SELECT role FROM users — не admin → «Только владелец» + Меню) → разбор: list → 'QS Format list' (esc: «Вопросы интервью (8): N. текст…» + подсказка «вопрос N <текст>» / «вопросы сброс») → 'TG qs'; set → 'QS Build set' (UPDATE settings SET value=<JSON с заменой N-го> WHERE key='profile_questions'; N валидация 1..8; пустой текст → ошибка) → 'QS HTTP set' → 'QS Format ok' («✅ Вопрос N обновлён: <текст>» + Меню) → 'TG qs ok'; reset → 'QS Build reset' (UPDATE settings SET value=<дефолтный JSON из тикета 13> WHERE key='profile_questions') → 'QS HTTP reset' → «✅ Вопросы сброшены к дефолту» + Меню
- [ ] PFN Qlist: читать вопросы из settings.profile_questions (SQL-запрос в Build-ноде Qlist-цепочки — добавить ключ 'profile_questions' в SELECT settings; fallback: если ключа нет/битый JSON → дефолтный массив захардкожен в Qlist) — количество вопросов = длина массива (не хардкод 8 в тексте «Вопрос N/8» — использовать фактическую длину)
- [ ] PFN Parse answer: KEY-маппинг шагов остаётся 1..8 по умолчанию; при кастомном списке другой длины — шаги 1-4,7 (текст), 5/6 (мульти) соответствуют ПОЗИЦИЯМ (не названиям): позиции 1-4,7 — текст, 5 — ссылки, 6 — документы, 8 — референсы (проверить: если вопросов меньше 8 — пропускать отсутствующие шаги при сохранении; больше 8 — лишние шаги как текст в answers.extra?). РЕШЕНИЕ: поддерживать ровно 8 позиций (замена текста, не количества; N 1..8) — количество не меняется, только формулировки
- [ ] Валидации: validate 0 issues, lint 0, node --check, sim (PFN Qlist с кастомными вопросами из стаба; QS Build set с N=3; QS Check role)

Примечания: количество вопросов фиксировано 8 (меняются формулировки); дефолтный массив — как в волне 1 (тикет 13). Секретов нет.
