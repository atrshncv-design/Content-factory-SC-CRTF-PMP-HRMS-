# 10 — Гейт активного профиля на входах генерации

**What to build:** Все входы генерации (цикл, URL→видео, шортсы, текстовый пост, ассеты, продукт, баннер) блокируются без активного профиля: бот сообщает «Нет активного профиля — создай или выбери» с кнопкой «Профиль». С профилем — работают как раньше.

**Blocked by:** 06 (PF Check/карточка — переиспользуется)

**Status:** done (14.08, верифицировано оркестратором)

- [x] Общий гейт: GPF Build (резолв T5 AS ac_id) → GPF HTTP → GPF Check ({ok, ac_id, command}) → Switch gpf ok (ok=true → GPF Route; иначе GPF Format no «🚫 Нет активного профиля…» + TG gpf no с кнопками Профиль/Меню)
- [x] GPF Route (7 правил + fallback): start_cycle→SC Build state, asset→AST Build, shorts→SHT Build, product→PRD Build, banner→BNR Build, url2video→UV Build state, text_post→TX Build, fallback→Gate Build
- [x] Перемаршрутизация Switch cmd: out[5]/[23]/[24]/[25]/[26]/[31]/[33] → GPF Build (dur out[32] не тронут; остальные выходы не тронуты; снапшот connections до мутаций)
- [x] Порядок: единственный вход гейтируемых команд — GPF Build → GPF Check, далее роутер в исходные цепочки (до кредитных гейтов и платных вызовов по построению)
- [x] Валидации (ОРКЕСТРАТОР): validate 0 issues (719 нод), lint 0, node --check GPF 3/3, sim GPF Check (ac=3→ok:true; ac=0→ok:false), GPF Format no текст, GPF Route 7 правил+fallback

Артефакт: `.scratch/client-profiles/fixes/wf-tg-bot.json` (719 нод; снапшот `wf-tg-bot.10.json`)

Примечания: паттерн вставки — как кредитные гейты 10/50 (общий вход ВСЕХ путей к платной цепочке, включая regen-пути). Не ломать легаси-команды (client <id> без гейта — это не генерация).
