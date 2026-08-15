# T3: Кнопка «📋 Меню» на всех экранах + тупики + устаревшие тексты

Status: done
Blocked by: T2 (меню должно существовать, чтобы кнопка работала)
Файлы:
- `.scratch/bot-ux-menu/fixes/wf-tg-bot.json` (рабочая копия = результат T2)
- `.scratch/bot-ux-menu/fixes/wf-creatify-webhook.json` (база: `.scratch/bot-ux-menu/base/wf-creatify-webhook.json`)
Спека: `.scratch/bot-ux-menu/spec.md` §4.10, §4.11

## Задача
Кнопка «📋 Меню» (callback `cmd:menu`) на КАЖДОМ пользовательском сообщении бота + исправление тупиков и устаревших текстов.

## Что сделать

### wf-tg-bot.json
1. **«📋 Меню» на всех TG Send-узлах** (кроме answerCallbackQuery — они не Send): пройтись по ВСЕМ нодам типа `n8n-nodes-base.telegram`, у которых есть `inlineKeyboard`, и добавить в конец клавиатуры строку с кнопкой `{text: "📋 Меню", callback_data: "cmd:menu"}` (если такой кнопки ещё нет). Узлы БЕЗ клавиатуры (TG ping, TG cancel, TG unknown, TG topic rejected, TG script rejected, TG gen rejected, TG published, TG regen, TG ob fail, TG script fail, TG ET fail, TG AS fail, TG SC busy, TG no candidates, TG generating, TG reload и т.п.) — ДОБАВИТЬ клавиатуру с кнопкой «📋 Меню» (callback `cmd:menu`). Полный список telegram-нод проверяется по файлу; эталон формы — `TG start`. ⚠️ УЖЕ СДЕЛАНО В T2 (НЕ трогать): TG start, TG help, TG menu, TG menu gen/analytics/publish/system, TG instruction, TG hint — у них кнопки уже есть.
2. **Тексты тупиков (заменить ДОСЛОВНО по спеке §4.11):**
   - TG topic rejected → «❌ Тема отклонена. Можно запустить цикл заново.» + кнопки [🔄 Запустить цикл](cmd:start_cycle) [📋 Меню](cmd:menu)
   - TG script rejected → «❌ Сценарий отклонён. Можно запустить цикл заново.» + [🔄 Запустить цикл] [📋 Меню]
   - TG gen rejected → «❌ Видео отклонено. Можно сгенерировать новое.» + [⚡ URL→видео](cmd:gen_url2video) [🎬 AI Shorts](cmd:gen_shorts) [📋 Меню]
   - TG published → «✅ Опубликовано. Можно генерировать дальше.» + [⚡ URL→видео] [🎬 AI Shorts] [📋 Меню] (убрать «(mock)»)
   - TG cancel → «✅ Отменено. Текущий шаг прерван.» + [📋 Меню]
   - TG unknown → «Не понял. Нажми «📋 Меню» или напиши: меню» + [📋 Меню] (убрать «/help»)
   - TG ping → «✅ Бот работает (n8n wf-tg-bot active, webhook).» + [📋 Меню] (убрать «long polling»)
   - TG generating → «🎬 Видео генерируется... Как только creatify ответит — пришлю ролик.» + [🧹 Отмена](cmd:cancel) [📋 Меню] (убрать «(mock)»)
   - TG regen → текст заменить на «🔁 Перегенерирую...» (сама перегенерация — в T4/T5a; в T3 только текст и кнопка [📋 Меню]; если ветка regen не вызывает повторную генерацию — оставить сообщение «🔁 Перегенерация...» и [📋 Меню], реализацию повтора закроют T4/T5a)
   - TG SC busy / TG no candidates / TG ob fail / TG onboard profile / TG script fail / TG ET fail / TG AS fail / TG CP refuse / TG client denied / TG reload — добавить [📋 Меню], тексты сохранить.
   - ⚠️ TG help и старт — УЖЕ переделаны в T2, не трогать.
3. **Экранирование**: в новых статичных текстах — без `_ * [ ] \``; `cmd:cancel` — это callback, не текст. В текстах со «Стоп» — без кавычек-проблем; текст «отмена» без подчёркиваний.
4. **Проверить**: все существующие кнопки `cmd:start_cycle`, `cmd:status`, `cmd:help`, `cmd:budget`, `cmd:topics` уже маршрутизируются (Switch cmd). Кнопка `cmd:menu` маршрутизируется (T2). Не создавать дублей кнопок в одном узле.

### wf-creatify-webhook.json
5. **«Telegram stage3»** (этап 3, видео готово): к кнопкам publish/regen/reject ДОБАВИТЬ строку [📋 Меню](cmd:menu) (callback в форме `={{ 'cmd:menu' }}` — статичная, можно просто `cmd:menu`). Проверить, что остальные кнопки в форме `={{ 'publish:gen:' + $json.gen_id }}` (эталон уже есть в файле). esc() на динамике — уже покрыто (FIX-11), не ломать.
6. **Не менять**: контракты, done/failed-ветки, db-bridge SQL, подпись webhook (FIX-10).

## Валидация перед сдачей
- node --check затронутых jsCode (если менялись).
- Список ВСЕХ telegram-нод wf-tg-bot с маркером «кнопка меню добавлена/уже была» — приложить к ответу (не менее 50 нод; каждую проверить).
- lint-workflow-json.py — 0 новых находок.
- BFS-достижимость.
- Никаких платных вызовов.

## Вывод
Оба JSON-файла: `.scratch/bot-ux-menu/fixes/wf-tg-bot.json` и `.scratch/bot-ux-menu/fixes/wf-creatify-webhook.json`. Ответ: таблица «узел → кнопка меню?», список изменённых текстов, результаты валидаций.
