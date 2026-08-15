# T4: Быстрый сценарий «URL → видео» (интерактивный, с гейтами)

Status: done
Blocked by: T3 (кнопки меню везде)
Файл: `.scratch/bot-ux-menu/fixes/wf-tg-bot.json` (рабочая копия = результат T3)
Спека: `.scratch/bot-ux-menu/spec.md` §4.8, §5.2, §6, §7

## Задача
Интерактивный сценарий «URL → видео»: кнопка/команда → запрос ссылки → выбор длительности (30/60/90 сек) → создание link + submit → статус-сообщение; callback creatify доставит stage3 (видео + кнопки) через wf-creatify-webhook.

## Что сделать

### 0. СВЕРЕННЫЕ КОНТРАКТЫ (fixes-версии 14.08 — доверять им, live-сверка при деплое)
- **wf-creatify-link** (webhook `POST localhost:5678/webhook/factory/creatify-link`): вход `{url, aspect_ratio:'9x16', video_length:<dur>, language:'ru'}` (jsonBody `={{ $json }}` от Build-ноды) → ответ `{link_id}` (из `$json.id || $json.link.id`; путь `($json.body && $json.body.link_id) || $json.link_id`).
- **wf-creatify-submit** (webhook `POST localhost:5678/webhook/factory/creatify-submit`, fixes-версия 16 нод): вход `{script_id: <number>, client_id: <number>, json_payload: <object>, link_id: <string>}` (валидация: isNum script_id/client_id, json_payload object, link_id строка). Ответ: `{creatify_id, generation_id}`.
- **json_payload** для link_to_videos (по образцу цикла, AS Build bridge prompt): `{name, link: <link_id>, visual_style, script_style, aspect_ratio:'9x16', video_length: <dur>, language:'ru', target_audience, target_platform, model_version:'aurora_v1_fast', override_script, webhook_url}`. Для quick-сценария: `name: 'Ролик из ссылки'`, `visual_style: 'default'`, `script_style: 'informative'`, `target_platform: 'Instagram'`, `override_script: ''` (видео из ссылки, сценарий не переопределяем), webhook_url подставит сам submit (он добавляет `webhook_url: $env.WEBHOOK_URL + 'webhook/factory/creatify/6d8f2a41c9e7b3d5f0a1c4e8'` — НЕ дублировать).
- **script_id для quick**: в цикле script создаётся заранее. Для quick-сценария создать минимальную строку scripts: `INSERT INTO scripts (client_id, topic_id, hook, body, cta, target_length, format_tag, full_text, status) VALUES (?, NULL, '', '', '', ?, 'user', ?, 'pending')` с client_id = активный клиент (settings.active_client_id), target_length = dur, full_text = 'Ролик из ссылки: ' + url → lastInsertRowid → script_id. Это нужно, чтобы stage3 (LEFT JOIN scripts) и submit-валидация работали.


1. **Состояния сессий**: `QUICK_URL_AWAIT_LINK`, `QUICK_URL_AWAIT_DUR`, `QUICK_URL_GENERATING`. Колонка `sessions.quick_payload` (TEXT, JSON {url, duration}) — DDL НЕ в тикете (делает оркестратор на сервере), но все UPDATE/INSERT/SELECT должны использовать её. Защитное чтение: `COALESCE(quick_payload, '{}')`.
2. **Parser**: command `url2video` (текст: url2video, видео из ссылки) и `dur` (из callback `cmd:dur_30/60/90`, args.value=30/60/90) — маршрутизация уже добавлена в T2; здесь реализуем ветки.
3. **Ветка `url2video`** (Switch cmd): 
   - `UV Build state` (Code: SELECT state, quick_payload FROM sessions WHERE tg_user_id=$('Parser').first().json.tg_user_id) → `UV Check busy` (Switch: state==IDLE → идём; иначе → `UV Format busy` «⏳ Сейчас выполняется другой шаг. Заверши его или отправь: отмена» + [🧹 Отмена](cmd:cancel) [📋 Меню](cmd:menu), state не менять) → `UV Ask link` (Format «🔗 Пришли ссылку на материал для ролика. Например: https://robotec.ru/news/123» + [🧹 Отмена] [📋 Меню]; db-bridge UPDATE sessions SET state='QUICK_URL_AWAIT_LINK', quick_payload=NULL) → `TG uv ask link`.
   - Если url2video пришёл С аргументом (args.url) — пропустить шаг «пришли ссылку»: сразу валидация.
4. **Gate свободного текста** (Switch gate / новый узел): если state=QUICK_URL_AWAIT_LINK и пришёл текст (не команда):
   - Валидация `/^https?:\/\//i`. Невалид → `UV Format bad url` «❌ Это не похоже на ссылку. Пришли URL вида https://…» + [🧹 Отмена] [📋 Меню] (state остаётся).
   - Валид → `UV Save url` (UPDATE sessions SET state='QUICK_URL_AWAIT_DUR', quick_payload=JSON(url)) → `UV Ask dur` (Format «⏱ Длительность ролика: 30 сек — 5 кред · 60 сек — 10 кред · 90 сек — 15 кред. Остаток creatify: {cr}» + [⏱ 30 сек](cmd:dur_30) [⏱ 60 сек](cmd:dur_60) [⏱ 90 сек](cmd:dur_90) [🧹 Отмена] [📋 Меню]) → `TG uv ask dur`.
5. **Ветка `dur`** (Switch cmd): 
   - `DU Check state` (SELECT state, quick_payload) → если state != QUICK_URL_AWAIT_DUR → Format «⏱ Сначала начни сценарий: кнопка «URL → видео»» + [📋 Меню].
   - `DU Gate` (Code: живой баланс creatify — свои LB-ноды `DU LB creatify`+`DU LB parse` (паттерн T1); est_cost = 5 * dur/30): balance < 10 → `DU Format low` «⛔ Недостаточно кредитов creatify: {cr}. Нужно минимум 10 для генерации.» + [💰 Бюджет](cmd:budget) [📋 Меню]; est_cost > 50 → «⛔ Стоимость генерации (~{cost} кред) превышает лимит 50.» + [📋 Меню] (страховка).
   - Гейт пройден → `DU Format gen` «⏳ Создаю ролик из ссылки на {dur} сек (~{cost} кред). Пришлю сюда, как будет готово.» + [🧹 Отмена] [📋 Меню] → UPDATE sessions SET state='QUICK_URL_GENERATING', quick_payload={url, duration} → `DU HTTP link` (POST localhost:5678/webhook/factory/creatify-link, jsonBody {url}, neverError, timeout 60000) → `DU parse link` (Code: link_id из ответа — паттерн `($json.body && $json.body.link_id) || $json.link_id`) → `DU HTTP submit` (POST localhost:5678/webhook/factory/creatify-submit; jsonBody — СВЕРЯТЬ с live INSERT-нодой wf-creatify-submit: `{script_id, client_id, json_payload: {link, name, visual_style, script_style, aspect_ratio: '9x16', video_length, language: 'ru', target_platform, model_version, override_script, webhook_url}}`; НЕ выдумывать поля — при отсутствии доступа к live, скопировать структуру из `workflows/wf-creatify-submit.json` INSERT-ноды и пометить «требует сверки с live»; timeout 300000) → `DU parse submit` (Code: creatify_id/generation_id; при ошибке → `DU Format fail` «😕 Не удалось запустить генерацию: {err}» + [📋 Меню] и UPDATE sessions state='IDLE').
   - Успех: TG-сообщение уже отправлено (`DU Format gen`), state=QUICK_URL_GENERATING. Callback creatify → wf-creatify-webhook → stage3 (T3 добавил меню). Проверить: done-ветка wf-creatify-webhook ставит sessions.state='CYCLE_VIDEO_PENDING' — для quick-сценария это нормально (stage4 публикация работает одинаково). Если wf-creatify-webhook требует script_id из LEFT JOIN scripts — для quick-URL это может быть NULL → в done-ветке использовать COALESCE/защитно (поправить в wf-creatify-webhook.json в ЭТОМ тикете, если нужно, с пометкой).
6. **Отмена**: существующая CN-ветка должна дополнительно чистить quick_payload (UPDATE ... SET state='IDLE', quick_payload=NULL) — поправить CN Build.
7. **cmd:gen_url2video** → та же ветка url2video (кнопка из старта/меню). Убедиться, что parseCommand('gen_url2video') даёт url2video (T2).
8. **Перегенерация (regen)**: ветка regen (regen_gen) для QUICK_URL_GENERATING: повторный POST submit с тем же quick_payload (url+duration) после повторного link (или переиспользовать сохранённый link_id в quick_payload — добавить поле link_id при первом сабмите). Реализовать: `RG Check state` → если quick_payload.url существует → повторный submit → Format «🔁 Перегенерирую...» + [📋 Меню]. Иначе (цикл) — существующее поведение.
9. **Кнопка «📋 Меню»/«Отмена»** — во всех новых сообщениях (§4.8).

## Валидация перед сдачей
- node --check; BFS; sim-code-node для новых Code (gate, parse, format).
- Parser-харнесс: cmd:dur_30 → command dur value 30; cmd:gen_url2video → url2video; «видео из ссылки https://x» → url2video с args.url.
- lint — 0 новых.
- Никаких платных вызовов (HTTP-ноды к creatify-link/submit — только конфиг, не вызов).

## Вывод
Полный JSON → `.scratch/bot-ux-menu/fixes/wf-tg-bot.json` (+ правки wf-creatify-webhook.json при необходимости, с пометкой). Ответ: список новых нод и соединений, результаты валидаций, пометки «требует сверки с live».
