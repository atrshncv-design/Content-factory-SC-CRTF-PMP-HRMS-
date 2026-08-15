# T2: Меню-система (главное меню + 4 раздела) + инструкция + переработанный старт

Status: done
Blocked by: T1 (в базе уже есть живые балансы из T1)
Файл: `.scratch/bot-ux-menu/fixes/wf-tg-bot.json` (рабочая копия = результат T1)
Спека: `.scratch/bot-ux-menu/spec.md` §4.2–4.7, §7

## Задача
Двухуровневое меню: главное меню (`menu`) + разделы (`menu_gen`, `menu_analytics`, `menu_publish`, `menu_system`) + инструкция (`instruction`, синоним help) + переработанное стартовое сообщение.

## Что сделать

1. **Parser (jsCode) — расширить parseCommand:**
   - C-маппинг добавить: `'menu': 'menu', 'меню': 'menu'`, `'инструкция': 'instruction'`, `'url2video': 'url2video', 'видео из ссылки': 'url2video'` (help остаётся 'help').
   - Новые cmd:*-кнопки разбираются ТЕМ ЖЕ parseCommand (data.slice(4) уже есть): `cmd:menu` → menu; `cmd:menu_gen`/`cmd:menu_analytics`/`cmd:menu_publish`/`cmd:menu_system`/`cmd:menu_help` → command=menu + args.section='gen'|'analytics'|'publish'|'system'|'help'; `cmd:gen_url2video` → url2video; `cmd:gen_shorts` → shorts; `cmd:dur_30`/`cmd:dur_60`/`cmd:dur_90` → command=dur, args.value='30'/'60'/'90'.
   - Важно: `cmd:gen_shorts` → parseCommand('gen_shorts') — НЕ должен дать command='shorts' с пустым args (это ок: shorts без аргумента = интерактивный ввод темы, реализация в T5a — ветка `shorts` уже есть, добавить в неё обработку пустого аргумента: «пришли тему» + state; НО в T2 только маршрутизация — ветку `shorts` НЕ переделывать, если она существует; пустую обработку сделает T5a).
   - `dur` — новый command, только из callback.
2. **Switch cmd — добавить правила В КОНЕЦ (индексы старых веток НЕ сдвигать):** `menu`, `instruction` (help остаётся отдельным правилом; instruction = отдельная ветка с тем же текстом, что help-инструкция), `url2video`, `dur`. Старые правила не трогать.
3. **Новые ветки (Build → Format → TG Send + кнопки):**
   - `menu`: Build (читать живые балансы из `$('ST LB parse')`? НЕТ — ветки изолированы: добавить в menu-ветку свои LB-ноды `MU LB creatify` + `MU LB sc` + `MU LB parse` (копия паттерна T1) + `MU Format` (текст §4.2: шапка + балансы) + `TG menu` с кнопками разделов (row1 [⚡ Генерация][📊 Аналитика], row2 [📤 Публикация][⚙️ Система], row3 [📖 Инструкция]). callback_data: `cmd:menu_gen` и т.д.
   - `menu_gen`, `menu_analytics`, `menu_publish`, `menu_system`: Format (тексты §4.3–4.6 ДОСЛОВНО) + TG Send с кнопками (см. §4.3–4.6; хинт-кнопки — тоже кнопки с callback `cmd:help_hint:<command>`? НЕТ — проще: хинт-кнопки = кнопки с `cmd:<command>_hint`? Упрощение: хинт-кнопки показывают пример команды. Реализация: кнопка `cmd:hint_creators` → ветка hint: Format «Напиши: авторы <ниша>» + [📋 Меню]. ПЕРЕЧЕНЬ хинт-кнопок: creators, creator, creator_content, audience, transcript, comments, upload_avatar, asset, product, banner, publish_type, mode, client. Реальные кнопки: topics, competitors, accounts, my_avatars, status, budget, clients, ping, cancel, start_cycle, url2video, shorts, instruction, menu-разделы.
   - `instruction` (+ `help` — перенаправить на ту же ветку или продублировать текст): текст §4.7 ДОСЛОВНО (подставить {daily} из settings) + [📋 Меню].
   - `ST Format`/`TG start`: переработать текст §4.1 (клиент, режим, today/daily, живые балансы из ST LB parse — T1 уже дал) + кнопки: row1 [🔗 URL→видео][🎬 AI Shorts], row2 [📋 Меню][📊 Статус].
4. **Экранирование**: все статичные тексты — без неэкранированных `_ * [ ] \``; если команда с подчёркиванием в тексте (например start_cycle) — `\_` (в JSON-выражении `\\_`). Динамику — через esc() (эталон MO Format, копировать дословно).
5. **TG help**: текст заменить на инструкцию §4.7 (help = синоним), кнопка [📋 Меню] внизу.

## Валидация перед сдачей
- node --check всех новых jsCode; BFS-достижимость от tg-trigger.
- Проверить, что ВСЕ новые кнопки имеют callback_data в форме `cmd:*` и что parseCommand даёт ожидаемый command для каждой.
- sim-code-node.py для новых Format-нод (входы: Parser + LB parse + settings).
- lint-workflow-json.py — 0 новых находок.
- Никаких платных вызовов.

## Вывод
Полный JSON → `.scratch/bot-ux-menu/fixes/wf-tg-bot.json`. Ответ: новые ноды, правила Switch, результаты валидаций, diff-сводка.
