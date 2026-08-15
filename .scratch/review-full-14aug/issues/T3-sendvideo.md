# T3 — Видео в TG файлом (sendVideo), не ссылкой (решение пользователя 14.08)

**What to build:** этап 3 основного цикла (после генерации) присылает РОЛИК ФАЙЛОМ в Telegram (sendVideo), а не текстовой ссылкой; кнопки ✅ Опубликовать / ✏️ Перегенерировать / ❌ Отклонить остаются.

**Blocked by:** None — база = `.scratch/review-full-14aug/fixes/wf-creatify-webhook.json` (25 нод, live 14.08)

**Status:** ready-for-agent

**Контекст (проверено оркестратором):**
- Сейчас: `Build stage3` (Code) собирает текст «🎬 Этап 3/4 — Видео готово\nСценарий: ...\nВидео: <URL>\nЧто делаем с видео?» → `Telegram stage3` (telegram v1.2, operation=**sendMessage**) с кнопками publish/regen/reject:gen:{id} — ролик НЕ встроен, только ссылка в тексте
- ЭТАЛОН sendVideo: в wf-tg-bot нода `TG sh video` (telegram v1.2, operation=sendVideo, video=`={{ $('SHT Format').first().json.video_output }}`) — смотри её параметры
- video_output_url приходит в `Code done build` (d.video_output_url) / webhook body (wb.video_output_url || wb.video_output)
- Кнопки: inlineKeyboard rows, callback_data `={{ 'publish:gen:' + $json.gen_id }}` и т.д. — сохранить как есть
- esc-эталон MO Format; tg_user_id: `uid` из `$('HTTP SELECT')` с fallback 941296693 (TODO D2 — не трогать fallback)

**Что сделать:**
1. `Telegram stage3`: sendMessage → **sendVideo** (telegram v1.2), `video` = `={{ $json.video }}` (или из Build stage3), текст — короткий («🎬 Этап 3/4 — Видео готово. Что делаем?»), кнопки те же
2. `Build stage3`: добавить `video` в возвращаемый json (d.video_output_url || wb.video_output_url || wb.video_output), текст — БЕЗ ссылки на видео (она теперь в attachment), но с esc(script_excerpt)
3. Защита: если video пуст (генерация без файла) — не падать: оставить sendMessage-fallback со ссылкой ИЛИ сообщение «видео недоступно» + кнопки (реши; НЕ терять кнопки)
4. Валидация: validate 0 issues, lint 0, node --check, sim (Build stage3 с video/без video)
5. Результат: write_file в `.scratch/review-full-14aug/fixes/wf-creatify-webhook.json` + отчёт `fixes/T3-sendvideo.md`
