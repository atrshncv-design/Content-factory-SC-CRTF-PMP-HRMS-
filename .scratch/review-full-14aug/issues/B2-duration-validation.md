# B2 — Валидация длительности 15–300с в URL→видео (dur)

**Файл:** `.scratch/review-full-14aug/fixes/wf-tg-bot.json` (база = результат B1, ~486+ нод)
**Проблема (R2):** `DU Parse state`: `dur = Number(p.args.value) || Number(qp.duration) || 0` — любой ввод (5, 12, 400) принимается; гейт пропускает dur=5 (cost=1); creatify вернёт 400 «between 15 and 300 seconds» ПОСЛЕ списания 1 кред на link.
**Что сделать:**
1. В `DU Parse state` (и/или `DU Build link body`) добавить проверку: `dur >= 15 && dur <= 300`; невалидный → режим `dur_wrong` (существующая ветка DU Format wrong — «длительность 15–300 секунд» + повторный запрос), БЕЗ платного вызова
2. Проверить, что `DU Gate` считает cost по валидной длительности (после B2 — C2-часть поменяет round→ceil)
3. Валидация: validate 0 issues (BFS), lint 0, node --check, sim
4. Отчёт: `.scratch/review-full-14aug/fixes/B2-duration-validation.md`

**Контекст для субагента:** база = fixes/wf-tg-bot.json (результат предыдущего в серии); 0 кредитов; esc-эталон MO Format (байт-точно); сериализация indent=1/ensure_ascii=False/без trailing newline; tg_user_id 941296693 не трогать; BFS обязателен; минимальные правки.
