# CODE REVIEW — контент-завод (14.08.2026)

**Репо:** `atrshncv-design/Content-factory-SC-CRTF-PMP-HRMS-` (рабочая копия = live 14.08, HEAD cc3b65d + незакоммиченный Ран 2)
**Метод:** полный повтор — все 24 воркфлоу построчно (6 субагентов, только файлы репо) + read-only SSH-сверка оркестратора (n8n БД readOnly, factory.db, systemctl, бесплатные GET балансов). **0 кредитов SC/creatify потрачено** (ни одного HTTP к платным API).
**Артефакты:** спека `.scratch/review-full-14aug/spec.md` · тикеты `issues/01-06` · отчёты `reports/01..06`
**Верификация:** все 🔴-находки субагентов перепроверены по live (см. §0 — часть относится к устаревшим репо-экспортам).

---

## 0. ВАЖНОЕ ОТКРЫТИЕ: репо-экспорты workflows/*.json УСТАРЕЛИ относительно live

Фикс-волны 13–14.08 (FIX-05/06/08/13-15/16) применены на сервер, но в репо НЕ синхронизированы:

| воркфлоу | репо | live | что не в репо |
|---|---|---|---|
| wf-audience | 6 нод | 14 | FIX-05: mock + гейт 30 + универсальный парсер |
| wf-creators-search | 17 | 25 | FIX-06: validate + mock + Switch valid |
| wf-creator-profile | 14 | 20 | FIX-06 |
| wf-creator-content | 12 | 18 | FIX-06 |
| wf-transcripts-comments | 27 | 37 | FIX-06 (доменный regex вместо url.includes) |
| wf-creatify-submit | 9 | 16 | FIX-08: credit-check + webhook_url из $env |
| wf-publish-status | 23 | 24 | FIX-13: Expand rows → Split In Batches (батч) |
| wf-onboard | 5 | 10 | FIX-13: SSRF IPv6-блок + error-ветки + Switch valid |
| db-bridge server.js | fail-open | fail-closed | FIX-16: 500 без токена, 401 timingSafeEqual |
| wf-creatify-link | туннель-хардкод | `$env.WEBHOOK_URL` | FIX-03b |
| wf-creatify-poll | мёртв | fallbackOutput+обработка | FIX-04 |
| wf-creatify-adclone | порог 20 | порог **90** | FIX-09 |

**Следствие:** 🔴-находки субагентов по этим файлам понижены/закрыты (см. §3). **Вердикт построен по LIVE-состоянию.** Процессный долг: синхронизация репо с сервером нарушена (rsync после деплоев не выполнен).

---

## 1. ВЕРДИКТ ГОТОВНОСТИ (критерии интервью 14.08)

# ❌ НЕ ГОТОВ

| Критерий | Статус | Доказательство |
|----------|--------|----------------|
| п.1: функциональность (все тикеты DONE + базовый контур без блокеров) | ⚠️ ЧАСТИЧНО | UX-слой и ядро Рана 2 работают (гейты 10/50, живые балансы, меню, 31 команда), НО: 5 вызывающих webhook без neverError (молчаливый error при 4xx/5xx), нет валидации длительности 15–300 (dur=5 → платный 400), нет low_credits-гейта ДО вызова у SC search/profile/content/transcripts, AS-цепочка start_cycle без гейта 10/50, wf-publish text-only сломан маршрутизацией |
| п.2: кредиты (нет BLOCKED из-за нулевых балансов) | ✅ | creatify **379**, SC **66** (бесплатные GET, 14.08) — блокер «SC −1» из 13.08 закрыт |
| п.3: сценарий текстовых постов существует в боте | ❌ | См. §4: команды в боте нет (33 правила Switch cmd); **wf-publish не может опубликовать text-only даже напрямую** (Switch upload needed перевёрнут → text-only уходит в upload/init → 422); wf-creatify-text не подключён (`factory/script` 0 вхождений) |
| п.4: auto-режим настроен | ❌ | См. §4: `mode auto` пишет settings, но `settings.mode` читается ТОЛЬКО для отображения (ST/ST2/MU/IN/HL Format) — ветвления цикла нет; БД mode=manual |

**Обоснование одной строкой:** оба блокера пользователя подтверждены на live (текстовые посты отсутствуют и технически невозможны; auto-режим не реализован), плюс открытые хвосты надёжности/защиты трат. До вердикта «ГОТОВ» токены SC/creatify НЕ тратим (гейт на платные тесты остаётся закрытым).

---

## 2. ПОДТВЕРЖДЕНО LIVE (0 кредитов)

- **24/24 воркфлоу active**, все 24 webhook-пути + tg-trigger зарегистрированы
- **Executions**: 2710 success / 66 error — все ошибки датированы ≤13.08; после деплоя Рана 2 (14.08) новых error-executions НЕТ
- **Балансы**: creatify `remaining_credits: 379.0`; SC `creditCount: 66`; туннель живой
- **factory.db**: generations 13 (4 done/2 failed/7 abandoned), scripts 4, topics 7, social_accounts 5, сессия IDLE, settings mode=manual
- **Секреты**: в незакоммиченном диффе (18k строк) и git-истории после filter-repo — 0 вхождений (подтверждено субагентом 06: rev-list --all + fsck dangling — 0/0/0)
- **SSRF wf-onboard**: IPv4-блок 10/8+172.16/12+192.168/16+127/8+169.254 + IPv6-блок (`hostname.indexOf(':')`) + followRedirects:false — в live НА МЕСТЕ (FIX-13)
- **db-bridge**: fail-closed (500 «bridge not configured» без токена, 401 timingSafeEqual, лимит 256KB) — FIX-16 подтверждён
- **wf-publish-status**: батч-обработка через Expand rows → Split In Batches loop-back (FIX-13) — подтверждён
- **Живые балансы в боте**: 14 бесплатных GET + 7 универсальных парсеров (body→raw→JSON.parse(data)) — эталон T1

---

## 3. НАХОДКИ (severity после live-сверки; только LIVE-актуальные)

### 🔴 Критичные (подтверждены live)

| # | Область | Факт | Влияние |
|---|---------|------|---------|
| R1 | wf-tg-bot: 5 HTTP-нод (SC wf-analytics, OB wf-onboard, CP wf-publish, AS creatify-link, AS creatify-submit) | **neverError отсутствует** (live-инвентарь: neverError=NO у этих 5; у CRS/CRP/CRC/AUD/TR/CMT/AVA/AVL/AST/SHT/PRD/BNR = YES) | 4xx/5xx от получателя (402 out of credits, 422 публикация) → execution error → юзер молчит, state-машина застревает |
| R2 | wf-tg-bot DU Parse state / DU Build link body / DU Build submit | **Нет валидации длительности 15–300с** ДО платного вызова: `dur = Number(p.args.value) || ... || 0` — любой ввод (5, 12, 400) принимается; гейт пропускает dur=5 (cost=1) | Платный submit с невалидной длительностью → creatify 400 «between 15 and 300 seconds»: потеря кредита + UX-ошибка; dur=400 отсекается гейтом только случайно (cost>50) |
| R3 | wf-publish (live, 26 нод) | **Текстовые посты невозможны**: `Switch upload needed` перевёрнут — out[0]=skip ТОЛЬКО при НЕПУСТЫХ file_ids; пустой file_ids (текст) → out[1] → `Switch mock upload` → real: POST `/v4.1/upload/init` с несуществующим URL `$env.WEBHOOK_URL + media/<gen_id>.mp4` → 422 → execution умирает ДО Respond | Text-only публикация падает всегда; блокер п.3 подтверждён на уровне маршрутизации, а не только UX |

### 🟡 Важные (подтверждены live)

| # | Область | Факт | Влияние |
|---|---------|------|---------|
| Y1 | SC search/profile/content/transcripts (live, FIX-06) | mock/real-гейты ЕСТЬ, но **low_credits-гейта ДО вызова нет** (только постфактум-обработка 402 в Normalize) | При балансе ≤0 — минус или 402; audience (26 кред) защищён гейтом 30 (FIX-05) — остальные нет |
| Y2 | wf-tg-bot AS-цепочка (approve:script → link → submit) | Callback-вход платной генерации (start_cycle) **БЕЗ кредитного гейта 10/50** — гейты только у UV/DU/SH (T4/T5a) | При балансе <10 генерация уйдёт в минус |
| Y3 | wf-tg-bot: 39 Code-нод | **Хардкод tg_user_id 941296693** вместо `$('Parser').first().json.tg_user_id` | 2+ оператора → сессии смешиваются; расширение whitelist сломает |
| Y4 | wf-tg-bot DU Gate | `Math.round(5*dur/30)` vs фактическое округление creatify **вверх** (SH Gate использует ceil — верно) | Заниженная оценка стоимости у пользователя |
| Y5 | tg-trigger | **secret_token не задан** (`additionalFields: {}`) — хвост 13.08 | Webhook без секрета; защита только Whitelist внутри execution |
| Y6 | wf-creatify-webhook Build stage3 | TG-текст **без esc()** (динамический script_excerpt) | `_`/`*` в сценарии → Telegram 400 Markdown (питфолл F-4) |
| Y7 | wf-creatify-asset (live) | **Нет credit-гейта** (1 кред/шт, count≤4) и нет neverError; дефолт model_name не сверен с каталогом schemas | Минус при нулевом балансе; 400 при недоступной модели |
| Y8 | wf-creatify-text (live) | **НЕ подключён к боту** (0 вызовов `factory/script` в wf-tg-bot); client_id=1 хардкод; INSERT topics без OR IGNORE; topic_id по MAX(id) — хрупко; 1 кред ai_scripts за вызов | Для текстовых постов MVP не используется; риск дублей тем и лишних кредитов; live-вызовы при плейсхолдер-ключах → 401 |
| Y9 | Таймауты (wf-tg-bot → воркфлоу) | SHT 300000 vs сумма 420000 (bridge 300000 + ai_shorts 120000); CP 300000 vs N×300000; AS 60000 vs 300000+ | Гарантированный таймаут вызывающего при медленном bridge |
| Y10 | Parser (wf-tg-bot) | Команда `instruction` без слеш-формы `/instruction` (30/31 со слешами) | setMyCommands предлагает `/instruction` → «Не понял» (повтор инцидента menu) |
| Y11 | wf-tg-bot: 12 Switch (SC allow, SC/OB/CT/ET/AS parse, CP allow, UV parse, DU gate/link/submit, SH gate) | boolean-левая часть + `string/equals` + rightValue `'true'` (strict) — паттерн FIX-06 «Wrong type: boolean» | ok=false-ветки рискуют exec error вместо сообщения (нужен live-тест ok=false) |
| Y12 | Публичные webhook без авторизации | SC-кластер (analytics/search/profile/content/audience/transcript/comments) + publish + tg-alert + zz-test — `options:{}` | Открытая трата кредитов любым, кто знает путь (audience 26 кред); tg-alert = спам-релей от имени бота; zz-test раскрывает settings |
| Y13 | FACTORY_WEBHOOK_SECRET | **не задан на сервере** — колбэк creatify fail-open (осознанный FIX-10: creatify не шлёт кастомный заголовок; включение — после согласования с отправителем) | Открытый колбэк: спуфинг done/failed возможен при знании статичного path-token |
| Y14 | DEPLOYMENT.md правдивость | :32 заявляет wf-credit-check с live-тестом — **воркфлоу не существует**; :329 vs :360 путает id wf-creator-profile (...015 vs реально ...016) | Документ вводит в заблуждение; оба пункта зафиксированы ревью 2 и не исправлены |
| Y15 | register-tg-commands.sh | Репо-скрипт регистрирует **28 команд** (tg-commands-25), а прод живёт на 31 (register-tg-commands-31.sh НЕ в репо, tg-commands-31.json untracked) | Повторный запуск репо-скрипта затрёт меню UX-2 (31→28); verify будет вечно фейлиться |

### 🟢 Мелочи / информационное
- answerQuery-тосты пустые (13 нод); alt:topic ≡ edit:topic (одна ET-цепочка); «🧹 Отмена» нет на TG gd wait/TG gg wait
- DU submit ok=true → пустой выход (QUICK_URL_GENERATING зависает при пропавшем callback без таймаута/фолбэка)
- adclone фолбэк brandUrl=robotec.ru при не-http brand_assets; banner/inspiration порог 10 при цене «8+» — тонкий
- wf-sync-accounts: mock-массив содержит TikTok connection_status=2 → в mock-режиме реальный tg-алерт каждый час (при откате в mock — спам)
- Caddyfile: catch-all публикует n8n UI/API на nip.io + /media/* без авторизации (смягчено firewall VK Cloud)
- Валидатор: «НЕДОСТИЖИМЫЕ» у multi-trigger воркфлоу (banner/avatar/transcripts-comments) — ложные срабатывания single-start BFS
- Экспорты репо: active=False у 8 воркфлоу — косметика (live 24/24 active), но усиливает рассинхрон

---

## 4. БЛОКЕРЫ ПОЛЬЗОВАТЕЛЯ — ПОДТВЕРЖДЕНЫ (п.3, п.4)

### п.3 — Текстовые посты в Threads и подобные соцсети: **ОТСУТСТВУЮТ (двойное подтверждение)**
1. **В боте нет сценария**: 33 правила Switch cmd (31 команда) — ни одной текстовой команды; `publish_type` = post/reels/story (тип медиа); CP-цепочка публикует только full_text+video видео-цикла; wf-creatify-text (генератор сценариев за 1 кред, webhook `factory/script`) **не вызывается ниоткуда** (grep по wf-tg-bot: 0 вхождений).
2. **wf-publish не умеет text-only в real**: Switch upload needed перевёрнут (R3) — пустые file_ids уходят в upload-ветку с несуществующим медиа-URL → 422 → execution умирает. В mock-режиме «работает», но фабрикует фейковый file_id 67890 (медиа-пост, не текст).
3. Текстовые посты в продукте идут бесплатным путём: wf-tg-bot → hermes-bridge scriptwriter → approve:script → INSERT scripts → publish:gen → wf-publish (content=full_text) — но этот путь НЕ публикует без видео из-за R3.

**Фикс-тикет в волну**: команда «текстовый пост» в боте + исправление Switch upload needed в wf-publish (пустые file_ids → текстовая ветка без upload) + подключение wf-creatify-text к сессии (или legacy-пометка).

### п.4 — Автоматический режим: **НЕ НАСТРОЕН**
1. Команда `mode manual|auto` работает: MO Build → UPDATE settings SET value='auto' WHERE key='mode' (валидация manual|auto, ответ «✅ Режим переключён»).
2. Но `settings.mode` читается **ТОЛЬКО для отображения**: ST Build settings / ST2 / MU / IN / HL Build → Format показывает «📅 Режим: manual» — ни одна ветка цикла (SC→CT→AS→PG→CP) не ветвится по нему. Пропуска подтверждений в auto нет.
3. БД: `mode|manual`.

**Фикс-тикет в волну**: реальное ветвление цикла по settings.mode (auto = автоподтверждение тем/сценариев/публикации + обработка ошибок без человека).

---

## 5. ПРОВЕРЕНО И РАБОТАЕТ (ядро Рана 2 — подтверждено)

- **Гейты 10/50 на ВСЕХ входах URL→видео и AI Shorts** (direct, callback, regen, shorts): BFS — все пути через LB creatify → parse → Gate → Switch gate; обходов НЕТ (фикс T4 подтверждён)
- **Живые балансы** (14 бесплатных GET + 7 универсальных парсеров): typeVersion 4.5, keypair через $env, вложенный neverError, timeout 15000
- **Меню 2 уровня + кнопка «📋 Меню» на 74/74 экранах; тупиков 0**
- **esc() покрытие 55/55 Format-нод** (эталон MO Format); статичные `_` — RAW + esc на рантайме (паттерн T2)
- **Кнопки**: 0 literal `{{ }}`; 13 правил Switch cb ↔ все callback_data 1:1; answerQuery перед каждой
- **QUICK_*-машина замкнута**: вход → ожидание ввода → гейт → генерация → доставка → отмена → IDLE
- **wf-creatify-webhook**: полная идемпотентность (SELECT→IF→UPDATE, done/failed/unknown, webhook_received=1)
- **wf-creatify-shorts**: двойная защита (SH Gate + Switch balance 30 + Exp bridge), контракт video_output
- **wf-creatify-product**: эталон кластера (валидация до списания, mode-роутинг, кредит-гейт 20, path-id gen_video)
- **wf-sync-accounts**: эталонный Split In Batches loop-back + UPSERT + алерт status=2
- **Заглушек Фазы 1 в платных ветках НЕТ** (example.com/picsum/samplelib = 0)
- Валидатор: wf-tg-bot 404/404 BFS, 177/177 jsCode — 0 issues; линтер 0 находок

---

## 6. РЕКОМЕНДАЦИИ К ФИКС-ВОЛНЕ (после «ок» пользователя, отдельный цикл)

1. **Волна A (блокеры пользователя)**: тикет «текстовые посты» (команда в боте + Switch upload needed fix + подключение wf-creatify-text/сессии); тикет «auto-режим» (ветвление цикла по settings.mode)
2. **Волна B (надёжность)**: никогда+таймауты на 5 вызывающих (SC/OB/CP/AS); валидация dur∈[15,300] в DU Parse state/DU Build; esc() в Build stage3; слеш `/instruction`
3. **Волна C (защита трат)**: low_credits-гейт ДО вызова на SC search/profile/content/transcripts; кредитный гейт на AS-цепочку; DU Gate round→ceil; гейт в wf-creatify-asset
4. **Волна D (долг/безопасность)**: замена 941296693 → `$('Parser').first().json.tg_user_id` (39 нод); secret_token tg-trigger; авторизация публичных webhook; правда в DEPLOYMENT (wf-credit-check, id); sync репо workflows/ + register-tg-commands-31.sh с сервера

## 7. OUT OF SCOPE / ОТКРЫТЫЕ ПУНКТЫ
- Фиксы — отдельный цикл волнами после «ок» (интервью п.4)
- Платные live-тесты — до вердикта «ГОТОВ» и отдельного согласования (гейт на траты закрыт)
- Ротация ключей/паролей на сервере — за пользователем (секреты вычищены из истории, но ключи действуют)
- Коммит рабочего состояния — после «ок» по отчёту (интервью п.6)
- Зависимости заказчика: postmypost-аккаунты (0 подключённых в проекте 355928) и модерация аватаров — вне критерия

---
*Отчёты кластеров: `.scratch/review-full-14aug/reports/01-wf-tg-bot-ux.md`, `02-wf-tg-bot-credits.md`, `03-creatify-cluster.md`, `04-sc-analytics-cluster.md`, `05-publish-cluster.md`, `06-system-cluster.md`*
