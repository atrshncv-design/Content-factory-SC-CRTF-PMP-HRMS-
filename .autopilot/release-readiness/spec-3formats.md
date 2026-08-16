# Спека фичи: «3 формата генерации (5 кред/30с) + строгие 30/60»

Решение пользователя (16.08, /autopilot, гриллинг):
- В боте остаются ТОЛЬКО 3 формата генерации видео, все по тарифу **5 кред/30 сек**:
  1. **URL to Video** (существующий DU-поток, `link_to_videos`)
  2. **AI Avatar** (НОВЫЙ: `lipsyncs` — аватар озвучивает сценарий; выбран пользователем в гриллинге)
  3. **AI Shorts** (существующий поток, `ai_shorts`)
- Дорогие механики УБРАТЬ из бота: asset (Asset Generator), product (Product Video 10 кред/30с), banner, adclone (12 кред/5с), text (token-based), любые aurora-механики.
- Длительность — **строгий выбор {30, 60} сек** (кнопки, без произвольного ввода; 90 убрать — не проходит валидацию creatify).

## Требования (hard)

1. **Меню бота**: кнопки 🖼️ Ассет, 📦 Product, 🪧 Баннеры, 👥 Мои аватары — УБРАТЬ (аватар-персоны остаются как источник для AI Avatar, но в меню — только «🎭 Видео с аватаром»). Остаются: 🔗 URL→видео, 🎬 AI Shorts, 🎭 Видео с аватаром, 🔄 Запустить цикл, 🧹 Отмена, 📋 Меню.
2. **Команды** (tg-commands-35): убрать `asset`, `product`, `banner`. Оставить `upload_avatar`, `my_avatars` (нужны для AI Avatar).
3. **Switch cmd / обработчики**: ветки hint_asset / hint_product / hint_banner — удалить или «отключено»; недоступные команды — «⚠️ Формат отключён».
4. **Воркфлоу на сервере**: деактивировать wf-creatify-asset, wf-creatify-product, wf-creatify-banner, wf-creatify-adclone, wf-creatify-text (файлы в репо остаются; активны только shorts/link/submit/webhook/poll + новый lipsync).
5. **Строгие секунды {30, 60}**:
   - URL→видео (DU): кнопки «30 сек — 5 кред · 60 сек — 10 кред»; произвольный ввод отклонять.
   - Цикл (AU/CYCLE_DUR_AWAIT): кнопки 30/60.
   - Shorts: добавить выбор 30/60 перед сценарием; слова = dur × 2 (60/120); `Code Build payload` cap = dur × 2; `video_length` ∈ {30, 60}.
   - Lipsync: слова = dur × 2 (длительность = длине текста).
6. **AI Avatar (lipsync)** — новый воркфлоу `wf-creatify-lipsync.json`:
   - POST `/api/lipsyncs/` body: `{name, text, creator (id персоны), aspect_ratio: '9x16', model_version: 'standard'}` (standard = 5 кред/30с; aurora НЕ использовать).
   - `video_length`/`webhook_url` в контракте ОТСУТСТВУЮТ → длительность = длине текста; доставка через поллинг (расширить wf-creatify-poll: GET `/api/lipsyncs/?ids=...` для поколений с type=lipsync).
   - Гейт кредитов (как в shorts: HTTP credits + Code balance, порог ≥ 10).
   - INSERT generations (request_payload.type='lipsync', creatify_id=id) + привязка сессии (generation_id) — по образцу DU gen link.
   - Доставка: поллер при done → video_output_url → существующий механизм (download + Telegram sendVideo + кнопки).
7. **Сценарий для lipsync**: тема → scriptwriter (слова под длительность: 60 слов/30с, 120 слов/60с); строгий JSON `{hook, body, cta, full_text}` → `text = full_text` (вычистка меток как в shorts).

## Вне скоупа (не трогаем)

- Аналитика, публикация (postmypost), SC-кластер, профили, bridge — без изменений.
- `override_avatar` в URL→видео — не добавляем (аватар используется только в lipsync).
- Удаление файлов воркфлоу из репо — НЕ делаем (только деактивация на сервере).
