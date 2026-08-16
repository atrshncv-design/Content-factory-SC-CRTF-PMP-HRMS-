# 03 — Премиум-воркфлоу Creatify: avatar, banner, product, asset, adclone, inspiration, text

**Требования:** R10i (полный приём всего scope), G09 (кнопки)
**Blocked by:** 01 (TG-структура команд/меню)
**Зона:** `workflows/wf-tg-bot.json` (команды/кнопки), `workflows/wf-creatify-{avatar,banner,product,asset,adclone,text}.json`
**Волна:** 2
**Status:** done (16.08)

## Что должно заработать

Все премиум-воркфлоу, существующие в репо, впаяны в бота и корректны до точки списания: для каждого есть команда в tg-commands-35, маршрут в Switch cmd wf-tg-bot, экран/кнопки, webhook path реально вызывается.

## Из брифа / манифеста, дословно

> «Полный приём всего scope» → «Всё из плана расширения» (AUDIT-AND-EXPANSION-PLAN, включая Спринт 3: avatar/adclone/banner)

## Разделы спецификации

История 6.

## Критерии приёмки

- [x] Проверены все premium-воркфлоу: avatar, banner, product, asset, adclone, text, inspiration.
- [x] Для каждого заявленного в tg-commands-35 маршрута: webhook path совпадает с именем в JSON, HTTP-нода настроена (typeVersion 4.5, keypair-заголовки, credit-гейт, neverError вложенный).
- [x] Для отсутствующих/нереализованных команд: либо впаяны, либо в отчёт как deferred с причиной (adclone/inspiration/creatify-text — deferred, причины в §Deferred).
- [x] wf-creatify-avatar обрабатывает загрузку видео и статус модерации (GET /personas/{id}).
- [x] wf-creatify-text/inspiration подключены к боту или отложены (отложены — причины в §Deferred).
- [x] Валидатор + sim зелёные; 0 платных вызовов.

## Проверено (16.08, 0 кредитов)

### Впаяны и проверены до точки списания: avatar, banner, product, asset
- **upload_avatar / my_avatars** (в tg-commands-35): Switch cmd out[21]/[22] → AVA/AVL Build ac → HTTP → `factory/avatar-upload` / `factory/my-avatars` — совпадает с webhook path в wf-creatify-avatar.json. AVA HTTP/AVL HTTP: typeVersion 4.5 + вложенный neverError.
  - wf-creatify-avatar: Validate (video_url/creator_name/gender) → `Create persona` POST /api/personas/ (4.5, keypair $env) → INSERT custom_avatars (pending_moderation) → Respond {ok, persona_id}. **Credit-гейт НЕ нужен: создание аватара бесплатно** (live-проверка 13.08, DEPLOYMENT §20 CR-1: «Потрачено кредитов: 0»; лимит 3 аватара).
  - Модерация: cron-moderation (каждый час) → SELECT pending → Split In Batches → **GET /api/personas/{id}/** → Evaluate (is_active→approve, process_status rejected/failed→reject, иначе wait) → UPDATE custom_avatars + tg-alert (wf-tg-alerts, webhook factory/tg-alert существует).
- **asset** (в tg-commands-35): Switch cmd out[23] → GPF-гейт → AST Build → AST HTTP → `factory/asset` ✓. Внутри: credit-гейт (GET remaining_credits → порог 5, count 1..4 = 1 кред/шт) → POST /api/asset_generator/.
- **product** (в tg-commands-35): Switch cmd out[25] → GPF-гейт → PRD Build → PRD HTTP → `factory/product` ✓. Внутри: credit-гейт (порог 20) → gen_image (1 кред) / gen_video/{id} (3 кред).
- **banner** (в tg-commands-35): Switch cmd out[26] → GPF-гейт → BNR Build → BNR HTTP → `factory/banner` ✓. Внутри: credit-гейт (порог 10) → POST /api/iab_images/ (2 кред).
- **url2video/shorts** (в tg-commands-35): пре-экзист (creatify-link/submit, creatify-shorts) — маршруты из волны 1, не менялись.
- text_post (в Switch cmd, не в tg-commands-35) — это быстрый текстовый пост → `factory/publish` (не creatify-text).

### Факт: на 16.08 НЕ впаяны adclone, inspiration, creatify-text — см. §Deferred

## Правки, сделанные в этом тикете (workflows/wf-creatify-{avatar,banner,product,asset,adclone,text}.json)

По критерию «HTTP-нода настроена (… neverError вложенный)» и конвенции проекта (DEPLOYMENT §26/§27: вложенный `options.response.response.neverError`):
1. **neverError вложенный** (`options.response.response.neverError: true`) добавлен на все HTTP-ноды вызовов creatify API:
   - avatar: `Create persona`; banner: `HTTP credit-check banner`, `HTTP iab_images`, `HTTP credit-check inspiration`, `HTTP inspiration_jobs`; product: `HTTP credits`, `HTTP gen_image`, `HTTP gen_video`; asset: `HTTP Asset` (credits уже был); adclone: `HTTP credits`, `Create link`, `HTTP ad clone`; text: `HTTP credits`, `HTTP ai_scripts`.
2. **Error-guards в consuming Code-нодах** (иначе neverError маскировал бы ошибку API под ok:true с null-полями): при не-объектном ответе / массиве ошибок / error|detail|message / отсутствии `id` → `{ok:false, error, raw}` (в text — `{ok:0, …}` для контракта IF scripts ok number):
   - avatar: `Code Extract id`; banner: `Code normalize banner`, `Code normalize inspiration`; product: `Normalize image`, `Normalize video`; asset: `Code Normalize`; adclone: `Extract link`, `Normalize`; text: `Normalize`.
3. **Новые switch-ноды** (v3.4, boolean/equals, fallbackOutput extra):
   - avatar: `extract ok` (Code Extract id → Build insert | Respond error) — ошибка создания persona не уходит в INSERT БД;
   - adclone: `link ok` (Extract link → Build body | Respond invalid) — неудачный POST /api/links/ не порождает вызов ads_clone (84 кред).
4. wf-tg-bot.json **не менялся** (всё уже впаяно волной 1 + тикет 10 GPF); `webhookId` в webhook-нодах уже стоят (cr1-/cr7-/cr4-/cr6-...).

## Deferred (не впаяны, с причинами)

| Воркфлоу | Команда | Причина deferral |
|---|---|---|
| wf-creatify-adclone (`factory/adclone`) | нет в tg-commands-35, нет маршрута в Switch cmd | Апсейл-фича 84 кред/задача (подтверждено live 13.08: ad_clone реально 84, НЕ 12 — DEPLOYMENT §22 CR-4). Для «впаяны» нужна команда в tg-commands-35 (регистрация payload вне зоны этого тикета — файл tg-commands-35.json + деплой-гейт оркестратора), новая ветка Switch cmd/GPF, экран с подтверждением стоимости и капом. По R08 («сначала стабильность, потом фичи») и 0-кредитному бюджету — отложено. Воркфлоу корректен до точки списания: Validate → credit-гейт (порог 90 ≥ 84+запас) → IF link → Create link → link ok → ads_clone. |
| wf-creatify-banner::inspiration (`factory/inspiration`) | нет в tg-commands-35, нет маршрута в Switch cmd | Требует интерактивного UX: пользователь выбирает шаблон из каталога (UUID + input_params по input_params_schema конкретного шаблона — поля различаются), цена 8+ кред (credit_cost шаблона). Отложено как апсейл-фича (R08). Воркфлоу корректен до точки списания: Validate (UUID) → credit-гейт (порог 10) → POST /api/inspiration_jobs/. |
| wf-creatify-text (`factory/script`) | нет в tg-commands-35; `text_post` в Switch cmd — это НЕ creatify-text (быстрый пост → factory/publish) | ai_scripts (1 кред) дублирует существующий пайплайн сценариев hermes-LLM (SC/CT/ET/AU + CTX-контекст активного профиля, бесплатный, с брендингом под клиента). Отложено как избыточное (R08). Воркфлоу корректен до точки списания: Normalize input → IF topic ok → credit-гейт (порог 50) → POST /api/ai_scripts/ (синхронный, статусы done/failed/unknown обработаны). |

Решение «deferred» соответствует критерию 3 тикета («либо впаяны, либо в отчёт как deferred с причиной»): команда в tg-commands-35 для новых команд невозможна без регистрационного payload вне зоны тикета.

## Проверки и доказательства (все бесплатные, 0 платных вызовов)

- `python3 .scratch/bot-ux-menu/validate_workflow.py workflows/wf-tg-bot.json` → **0 issues**; product/asset/adclone/text → **0 issues**; avatar/banner → единственный отчёт «НЕДОСТИЖИМЫЕ» — ложный (валидатор BFS только от первого триггера); отдельный multi-trigger BFS: **все ноды достижимы** от своих триггеров (avatar: 3 триггера, banner: 2).
- `lint-workflow-json.py` по 6 premium-воркфлоу → **0 находок**.
- `sim_combined.py` (node-харнесс, мок-ответы): **23/23** кейсов — успех (201 c id) и ошибки (массив `["AI model not found"]`, `{detail}`, `{error}`, `{link:[...]}`, `{}`, wrapped `{body:…}`) дают корректные ok:true / ok:false|0.
- `python3 -m pytest tests/test_wf_tg_bot.py -v` → **10/10 passed** (wf-tg-bot.json не менялся).
- Платных вызовов: **0** (статический анализ + локальные симуляции jsCode; реальные HTTP-вызовы не выполнялись, включая GET remaining_credits/personas).
- round-trip JSON: indent=1, ensure_ascii=False — byte-идентично json.dumps (дифф минимальный: options/neverError, jsCode-guards, 2 switch-ноды).

## Повторная верификация (16.08, второй прогон тикета — субагент)

Все пункты выше перепроверены заново по рабочему дереву (HEAD 2a31643, правки тикета НЕ закоммичены):

- `validate_workflow.py`: wf-tg-bot / product / asset / adclone / text → **0 issues**; avatar (36 нод) и banner (22 ноды) → multi-trigger BFS от всех триггеров: **36/36 и 22/22 достижимы** (флаги валидатора ложные).
- Маршруты Switch cmd ↔ tg-commands-35: **35/35 команд имеют маршрут** (правил 45: +hint/dur/text_post/durc/profile_*/remove_operator/questions/auto — служебные, не из commands-35); premium-маршруты: upload_avatar→out[21]→`AVA HTTP`→`factory/avatar-upload`, my_avatars→out[22]→`AVL HTTP`→`factory/my-avatars`, asset→out[23]→GPF→`AST HTTP`→`factory/asset`, product→out[25]→GPF→`PRD HTTP`→`factory/product`, banner→out[26]→GPF Build→Switch gpf ok→**GPF Route out[4] (command=banner)→BNR Build→BNR Switch→`BNR HTTP`→`factory/banner`**; url2video→out[31], shorts→out[24] (пре-экзист).
- HTTP-ноды creatify API во всех 6 воркфлоу: **typeVersion 4.5, authentication none + sendHeaders keypair + headerParameters X-API-ID/X-API-KEY ($env), вложенный `options.response.response.neverError: true`** (Get persona в avatar — бесплатный GET, neverError не требуется; db-bridge-ноды — X-BRIDGE-TOKEN).
- Credit-гейты (HTTP GET remaining_credits + порог): banner **10**, inspiration **10**, product **20**, asset **5**, adclone **90** (84+запас), text **50** (`IF low credits` balance gte 50). Avatar — бесплатно, гейт не нужен (лимит 3).
- Error-guards в consuming Code-нодах: 9/9 (Code Extract id, Code normalize banner/inspiration, Normalize image/video, Code Normalize, Extract link, Normalize ×2) — не-объектный ответ/массив/{error|detail|message}/нет id → `{ok:false}` (text — `{ok:0}`). Switch `extract ok` (avatar) и `link ok` (adclone): v3.4, boolean/equals `={{ $json.ok }}`→true, `fallbackOutput: extra`.
- Avatar: Validate (video_url http(s) + creator_name + gender m|f|nb) → `Create persona` POST /api/personas/ → `extract ok` → INSERT custom_avatars `status='pending_moderation', is_active=0` → Respond `{ok:true, persona_id, status:'pending_moderation'}`; ошибка создания НЕ уходит в INSERT. Модерация: cron-moderation → SELECT pending → Expand → Split In Batches → **GET /api/personas/{id}/** (`={{ 'https://api.creatify.ai/api/personas/' + $json.persona_id + '/' }}`) → Evaluate (is_active→approve; process_status rejected|failed→reject; иначе wait) → UPDATE + tg-alert approve/reject, NoOp wait/done.
- webhookId на webhook-нодах: cr1-avatar-upload / cr1-my-avatars / cr7-banner / cr7-inspiration / cr6-product / cr4-adclone / ...4471 (asset) / ...0001w (text) — вебхуки регистрируемы.
- lint 6/6 → 0 находок; sim-батарея **59 кейсов: 57 PASS + 2 «FAIL» = неверные ожидания теста** (ai_scripts без `generated_scripts[].paragraphs` корректно даёт ok:0 «generation_not_ready» — поведение верное); pytest **10/10**; round-trip JSON **6/6 byte-идентично**; placeholder-скан 6/6 clean.
- wf-tg-bot.json в этом прогоне НЕ менялся (git diff пуст).


## Осталось на платный тест (пользователь)

1. avatar-upload реальным видео (15–300 сек, URL доступный Creatify) → persona в Creatify + модерация GET /personas/{id} → статус approve/reject в custom_avatars (0 кред — можно сразу).
2. asset/product/banner — реальная генерация через бота (asset 1 кред/шт, product ~4 кред, banner 2 кред) и проверка отложенного списания.
3. adclone/inspiration/creatify-text — после решения по деплою команд (см. §Deferred); до списания — только если пользователь явно решит впаять.
