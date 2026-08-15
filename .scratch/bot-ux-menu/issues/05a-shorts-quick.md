# T5a: Быстрый сценарий «AI Shorts» (интерактивный, доставка видео, гейты)

Status: done
Blocked by: T4 (паттерны состояний/gейтов уже внедрены)
Файл: `.scratch/bot-ux-menu/fixes/wf-tg-bot.json` (рабочая копия = результат T4)
Спека: `.scratch/bot-ux-menu/spec.md` §4.9, §5.2, §6, §7

## Задача
Интерактивный сценарий «AI Shorts»: кнопка/команда без аргумента → запрос темы → (расширение темы→сценарий — T5b в wf-creatify-shorts) → генерация → ДОСТАВКА ВИДЕО в чат + кнопки «Опубликовать/Перегенерировать/Отклонить» + «Меню». Фикс сломанного URL-пути (D8).

## Что сделать

1. **Состояния**: `QUICK_SHORTS_AWAIT_TOPIC`, `QUICK_SHORTS_GENERATING`. quick_payload {topic, script}.
2. **Parser**: `shorts` уже есть. НОВОЕ правило в parseCommand: если `shorts` с аргументом, который похож на URL (`/^https?:\/\//i`) → command='shorts', args.url=<url> (обработать отдельно, см. п.6). `cmd:gen_shorts` → shorts без аргумента (T2).
3. **Ветка `shorts`** (расширить существующую SHT-цепочку: SHT Build → SHT Switch → SHT HTTP → SHT Format → TG shorts):
   - `SHT Build` переписать: 
     - если args.url похож на ссылку → {valid:false, redirect:true, text: «🔗 Для ссылок есть сценарий «URL → видео». Нажми кнопку или напиши: url2video» + [📋 Меню]} — НЕ слать source_video_url (D8).
     - если args.value (тема) есть → {valid:true, topic, direct:true}
     - если аргумента нет → {ask:true} → «🎬 Пришли тему для шортса (1–2 предложения). Я разверну её в сценарий и сгенерирую вертикальное видео (5 кред за 30 сек).» + [🧹 Отмена] [📋 Меню]; UPDATE sessions SET state='QUICK_SHORTS_AWAIT_TOPIC', quick_payload=NULL → TG send.
   - Gate свободного текста: state=QUICK_SHORTS_AWAIT_TOPIC и пришёл текст → тема (п.4). state=QUICK_SHORTS_GENERATING → «⏳ Генерируется, жди ответа» + [📋 Меню].
4. **Генерация** (общий путь для direct и из-под темы):
   - `SH Gate` (Code: живой баланс creatify — свои LB-ноды `SH LB creatify`+`SH LB parse`; est_cost = 5 * ceil(est_duration/30), est_duration = ceil(chars/200)): balance < 10 → «⛔ Недостаточно кредитов creatify: {cr}. Нужно минимум 10 для генерации.» + [💰 Бюджет] [📋 Меню]; est_cost > 50 → «⛔ Стоимость генерации (~{cost} кред) превышает лимит 50.» + [📋 Меню].
   - Пройден: UPDATE sessions SET state='QUICK_SHORTS_GENERATING', quick_payload={topic, script: null} → «⏳ Пишу сценарий и генерирую шортс...» + [🧹 Отмена] [📋 Меню] → `SH HTTP shorts` (POST localhost:5678/webhook/factory/shorts, jsonBody {topic, aspect_ratio:'9:16', style: 'auto'}, neverError, timeout 300000) — T5b расширит wf-creatify-shorts, чтобы он сам разворачивал тему через hermes-bridge. Если T5b ещё не готов — контракт {script} тоже принимается (topic передаётся как script fallback).
   - `SH parse` (Code: ответ wf-creatify-shorts — {ok, shorts_id, status, items:[{video_output,...}]}): 
     - ошибка/low_credits → «😕 Шортс не создан: {err}» + [📋 Меню]; UPDATE sessions SET state='IDLE'.
     - ok и video_output есть (status done) → ДОСТАВКА: `TG shorts video` (Telegram sendVideo, chat_id из Parser, video = video_output_url, caption «🎬 Шортс готов (id {shorts_id})» — esc(), caption без _ *) + `TG shorts buttons` (sendMessage с кнопками [📤 Опубликовать](publish:gen:{gen_id}? — см. ниже) [🔁 Перегенерировать](regen:gen:{shorts_id}) [❌ Отклонить](reject:gen:{shorts_id}) [📋 Меню]); UPDATE sessions SET state='CYCLE_VIDEO_PENDING', generation_id=<id> (если создали generation-строку — см. п.7) ЛИБО state='IDLE' если публикация не нужна.
     - ok, но status != done (асинхронный) → «⏳ Шортс генерируется (id {shorts_id}). Пришлю видео, как creatify ответит.» + [📋 Меню]; state=QUICK_SHORTS_GENERATING (webhook_url в payload wf-creatify-shorts — T5b; callback → wf-creatify-webhook — для shorts потребуется ветка, ПОМЕТИТЬ как «требует решения: доставка async-шортсов» — если T5b гарантирует sync video_output, эта ветка — страховка).
5. **Кнопки после доставки**: publish/regen/reject должны маршрутизироваться в Switch cb (существующие правила publish_gen/regen_gen/reject_gen — работают). Для shorts:
   - publish:gen → PG-ветка (stage4) — работает через sessions.generation_id; если generation-строка не создавалась — создать (п.7) чтобы stage4/publish имели generation_id.
   - regen:gen:{id} → RG-ветка: для QUICK_SHORTS — повтор генерации с тем же topic (новый вызов, новая оплата — нажатие = согласие).
   - reject:gen → «❌ Шортс отклонён.» + [📋 Меню] (или оставить существующее).
6. **URL-redirect**: «shorts https://...» → сообщение-редирект (п.3), state не менять.
7. **generation-строка для shorts** (чтобы stage4 работал): INSERT в generations {type/endpoint: 'ai_shorts', status: 'done', video_output_url, request_payload: {topic}} — СВЕРЯТЬ схему таблицы с live (SELECT * FROM generations LIMIT 1) и с wf-creatify-webhook SELECT; при невозможности — передавать в stage4 без generation_id (publish с content/file_ids — контракт FIX-12) и ПОМЕТИТЬ.
8. **Кнопки меню/отмены** — во всех новых сообщениях.

## Валидация перед сдачей
- node --check; BFS; sim-code-node для новых Code.
- Parser-харнесс: «shorts https://x» → redirect; «shorts тема» → topic; «шортсы» → ask.
- lint — 0 новых.
- Никаких платных вызовов.

## Вывод
Полный JSON → `.scratch/bot-ux-menu/fixes/wf-tg-bot.json`. Ответ: ноды, валидации, пометки «требует сверки с live» (схема generations, контракт wf-creatify-shorts).
