# PROGRESS — контент-завод

## Фича: Профили клиентов (14.08.2026, autopilot) — В РАБОТЕ
Спека: `.scratch/client-profiles/spec.md` · Тикеты: `.scratch/client-profiles/issues/` (21: 01–12 волна 1, 13–21 волна 2) · ADR-0001. База: live-экспорт wf-tg-bot **533 нод** (`.scratch/client-profiles/base/`).
Что: кнопка «Профиль» на старте и в меню → карточка активного профиля; интервью 8 пропускаемых вопросов (название/ниша/описание/ЦА/ссылки/документы/тон/референсы); приём файлов PDF/DOCX/TXT через hermes-bridge `/doc-text`; per-чат активный профиль (users.active_client_id); ролевой доступ (Whitelist→users, «добавить оператора <tg_id>»); контекст активного профиля в промптах генерации вместо хардкода «Клиент: Robotec»; гейт генерации без профиля. **Волна 2 (15.08)**: удаление профилей (мягкое) и операторов, редактирование вопросов, фото→OCR, возобновление интервью, per-профильные платформы.

| # | Тикет | Статус |
|---|-------|--------|
| 01 | Схема БД (клиенты-контекст, users.active_client_id, sessions.profile_draft, сид) | ✅ done (миграция готова, идемпотентна; применение — в 12/21) |
| 02 | hermes-bridge /doc-text (файлы→текст+дайджест) | ✅ done (30 тестов OK; /ask не тронут) |
| 03 | Доступ по ролям (Whitelist→users, add_operator/operators) | ✅ done (549 нод, validate 0/lint 0, sim OK) |
| 04 | Parser: profile/profiles/profile_doc + Switch cmd | ✅ done (555 нод, validate 0/lint 0, sim 5/5) |
| 05 | Активный профиль per-чат (резолв ~11 чтений, починка битого 999) | ✅ done (559 нод, validate 0/lint 0, sim ac 2→2/0→0) |
| 06 | Раздел «Профиль»: карточка, список, выбор, выход | ✅ done (595 нод, validate 0/lint 0, sim 4 кейса OK) |
| 07 | Интервью «Создать профиль» (8 вопросов, ссылки, документы) | ✅ done (652 нод, validate 0/lint 0, sim 5/5) |
| 08 | Редактирование + точечные добавления ссылок/документов | ✅ done (700 нод, validate 0/lint 0, sim 4/4; 1 ретрай) |
| 09 | Контекст профиля в промптах генерации (SC/CT/ET/AU) | ✅ done (712 нод, validate 0/lint 0, sim 3/3, hardcode 0) |
| 10 | Гейт активного профиля на входах генерации | ✅ done (719 нод, validate 0/lint 0, sim 3/3; 7 входов через GPF) |
| 11 | tg-commands-35, документация, синк репо | ✅ done (35 команд, DEPLOYMENT §, help; синк репо — в 12/21) |
| 12 | Деплой волны 1 (гейт: согласие пользователя) | ⏳ ждёт (объединён в 21) |
| 13 | Миграция v2: publish_platforms + profile_questions | ✅ done (скрипт готов, идемпотентен, вопросы из PFN Qlist) |
| 14 | hermes-bridge /img-text (фото→OCR через зрение) | ✅ done (тесты rc=0; /ask,/doc-text не тронуты) |
| 15 | Фото в профиль (OCR) + отклонение видео | ✅ done (745 нод, validate 0/lint 0, sim 6/6) |
| 16 | Удаление профиля (мягкое, подтверждение) | ✅ done (767 нод, validate 0/lint 0, sim 3/3) |
| 17 | Удаление оператора (команда владельцу) | ✅ done (789 нод, validate 0/lint 0, sim 5/5) |
| 18 | Вопросы интервью: редактирование владельцем | ✅ done (809 нод, validate 0/lint 0, sim 8/8) |
| 19 | Возобновление прерванного интервью | ✅ done (815 нод, validate 0/lint 0, sim 6/6) |
| 20 | Per-профильные платформы публикации | ✅ done (837 нод, validate 0/lint 0, sim 6/6) |
| 21 | Деплой волн 1+2 (гейт: согласие пользователя) | ⏳ |

## Ревью 3: полный повтор (14.08.2026) — ВЕРДИКТ ❌ НЕ ГОТОВ → ✅ ФИКС-ВОЛНА ЗАДЕПЛОЕНА
Спека: `.scratch/review-full-14aug/spec.md` · Тикеты: `.scratch/review-full-14aug/issues/` · Метод: 0 кредитов SC/creatify. Вердикт по 4 критериям (функциональность, кредиты, текстовые посты, auto-режим).

### ДЕПЛОЙ ФИКС-ВОЛНЫ (14.08, ~17:30 MSK): ✅ ЗАВЕРШЁН
- 8 воркфлоу применены через apply_fix.sh: wf-tg-bot **510 нод**, wf-publish 26, wf-creatify-webhook 25, wf-creatify-asset 9, 4 SC-файла (29/24/22/45)
- ⚠️ Питфолл деплоя: субагент A1-fix2 создал TG-ноды с typeVersion 2.2 (нет в n8n 2.34.4) → активация падала «Cannot read properties of undefined (reading 'execute')» → исправлено на v1.2 (telegram) / v3.4 (switch), передеплой
- Проверено: **24/24 active**, webhook_entity 24, probe tg-trigger **403**, zz-test 200, creatify-webhook 200, cron исполняется (publish-status exec 3063), активация в логах чистая
- Платные live-тесты — отдельно, после согласования (гейт на траты)

### Фикс-волна (14.08, подготовка в `.scratch/review-full-14aug/fixes/`, деплой после согласования)
| Тикет | Что | Статус |
|-------|-----|--------|
| A1-fix1 | wf-publish: text-only маршрутизация (R3, п.3) | ✅ 0 issues, sim 3/3 |
| A1-fix2 | wf-tg-bot: команда text_post (п.3) | ✅ 430 нод, 0 issues, lint 0 |
| A2 | wf-tg-bot: auto-режим (п.4) | ✅ 486 нод, 0 issues, lint 0 (AU-ветка 48 нод) |
| B1 | wf-tg-bot: neverError+таймауты 5 вызывающих (R1) | ✅ 500 нод, 0 issues, sim 4/4 (CP 402→esc, AS low_credits) |
| B2 | wf-tg-bot: dur-валидация 15-300 (R2) | ✅ 500 нод, 0 issues, sim 4/4 (5/400→wrong, 30/60→ok) |
| B3 | wf-creatify-webhook esc (Y6) ✅ + `/instruction` (Y10, в wf-tg-bot) | B3-esc ✅ · слеш ⏳ в финальном |
| C1 | 4 SC-файла low_credits (Y1) ✅ + AS-гейт (Y2, в wf-tg-bot) | C1-SC ✅ · AS ⏳ в финальном |
| C2 | wf-creatify-asset credit-гейт (Y7) ✅ + DU Gate ceil (Y4) | C2-asset ✅ · DU ⏳ в финальном |
| C2+B3+AS | финальный тикет wf-tg-bot (ceil + слеш + AS-гейт) | ✅ 505 нод, 0 issues, lint 0, sim 3/3 |
| D1 | DEPLOYMENT-правда (Y14) + register-tg-commands-31.sh (Y15) | ✅ 5 правок, скрипт сверен |
| D2 | tg_user_id хардкод (Y3), secret_token (Y5), AU-гейт (Y2-остаток) | ✅ 510 нод (53 ноды → p.tg_user_id), 0 issues; webhook 25 нод script_id-цепочка |

### Фикс-волна 2 (решения пользователя 14.08: выбор длины кнопками в manual / полный автомат / sendVideo) — ✅ ЗАДЕПЛОЕНА
| Тикет | Что | Статус |
|-------|-----|--------|
| T1 | wf-tg-bot: выбор длительности в ручном цикле (кнопки 30/60/90+своя, CYCLE_DUR_AWAIT, сценарий под длину, video_length=выбор) | ✅ 533 нод, 0 issues, sim 36/36 |
| T2 | wf-tg-bot: auto — полный автомат, длина из settings.video_length (дефолт 30), AU-цепочка параметризована, форс в submit body | ✅ 0 issues |
| T3 | wf-creatify-webhook: sendVideo файлом (resource='message'+file+caption — схема v1.2, проверена по исходникам!) + fallback | ✅ 27 нод, 0 issues |
| + | **TG sh video (AI Shorts) был СЛОМАН** (resource:'video' не существует в v1.2) → исправлен: message+file+caption | ✅ 533 нод |

⚠️ **Урок волны 2**: telegram-нода v1.2 НЕ имеет resource 'video' — sendVideo = resource 'message' + параметр `file` + подпись `additionalFields.caption`. Эталон TG sh video был невалиден (проверено по исходникам n8n 2.34.4 в контейнере).



| # | Кластер | Что | Статус |
|---|---------|-----|--------|
| 01 | wf-tg-bot UX | меню, кнопки, esc, команды, тупики | ✅ done — ГОТОВ (0🔴, 2🟡: `/instruction` слеш, 12 boolean-свитчей) |
| 02 | wf-tg-bot платные цепочки | гейты 10/50, mock/real, балансы | ✅ done — НЕ ГОТОВ (2🔴 устар. репо, live-сверка: никогда, dur 15-300, гейты SC, 39×941296693) |
| 03 | creatify-кластер (11) | link/submit/webhook/shorts/text/product/poll/asset/adclone/banner/avatar | ✅ done — 🟡 (3 блокера устар. репо: live-сверка закрыла туннель/poll/adclone=90; остались neverError, esc stage3) |
| 04 | SC-аналитика (6) | analytics/search/profile/content/audience/transcripts | ✅ done — репо устарел (FIX-05/06 в live); live: гейты mock есть, low_credits ДО вызова нет (Y1), webhook публичные (Y12) |
| 05 | публикация (3) | publish/publish-status/sync-accounts | ✅ done — 🔴 R3: text-only сломан (Switch upload needed перевёрнут); FIX-13 батч подтверждён live |
| 06 | системное | onboard/tg-alerts/скрипты/инфра/спеки/секреты | ✅ done — SSRF/db-bridge подтверждены live; DEPLOYMENT-ложь (wf-credit-check, id), скрипт 28vs31, compose устарел |

**ИТОГ Ревью 3 (14.08): ВЕРДИКТ ❌ НЕ ГОТОВ** — п.3 текстовые посты ❌ (двойное подтверждение), п.4 auto-режим ❌, п.1 частично (R1-R3), п.2 ✅ (creatify 379, SC 66). Отчёт: `docs/CODE-REVIEW-2026-08-14.md`. Фиксы — отдельным циклом волнами после «ок». 0 кредитов потрачено.

### Оркестратор: live-сверка (14.08, 0 кредитов) — ПОДТВЕРЖДЕНО
- 24/24 воркфлоу active, все webhook-пути + tg-trigger зарегистрированы; executions 2710 ok / 66 err (все ошибки ≤13.08, после Рана 2 новых нет)
- Балансы: creatify **379**, SC **66** (блокер «SC −1» из 13.08 закрыт); туннель живой
- **БЛОКЕР п.3 подтверждён**: сценария текстовых постов в боте НЕТ (33 правила Switch cmd; publish_type = медиа; CP = full_text+video; wf-creatify-text не подключён — `factory/script` 0 вхождений; wf-publish умеет text-only, но из бота недостижим)
- **БЛОКЕР п.4 подтверждён**: `mode auto` пишет settings, но `settings.mode` читается ТОЛЬКО для отображения (ST/ST2/MU/IN/HL Format) — ветвления цикла по нему нет; БД: mode=manual
- Репо workflows/*.json УСТАРЕЛ относительно live (FIX-05/06/08/13-15 не синхронизированы): audience 6vs14, creators-search 17vs25, submit 9vs16 (live credit-check есть), link туннель→$env.WEBHOOK_URL, poll fallbackOutput+обработка, adclone порог=90
- Хвосты: tg-trigger secret_token НЕ задан; FACTORY_WEBHOOK_SECRET не задан (fail-open, FIX-10); wf-publish-status мёртвые IF any?/NoOp + (mock)-текст; хардкод 941296693; DEPLOYMENT:329 опечатка id (реально ...016); секретов в диффе/истории нет; wf-credit-check не существует (согласовано)
- wf-onboard live: SSRF-фильтр НА МЕСТЕ (IPv6-блок, ipToNum 10/8+172.16/12+192.168/16+127/8, regex-валидация URL, FIX-13: 10 нод + error-ветки + Switch valid fallback)

---

## Ран 2: UX-реворк TG-бота (меню, инструкция, быстрые сценарии) — 14.08.2026
Спека: `.scratch/bot-ux-menu/spec.md` · Тикеты: `.scratch/bot-ux-menu/issues/` · База: `.scratch/bot-ux-menu/base/` (FIX-11/12 версии)

| # | Тикет | Что | Статус |
|---|-------|-----|--------|
| 01 | Живые балансы creatify+SC | старт/статус/бюджет читают балансы живыми GET (бесплатно) | ✅ done (287 нод, валидация 0 issues) |
| 02 | Меню-система | главное меню + 4 раздела + инструкция + новый старт | ✅ done (314 нод, 0 issues, 31 правило) |
| 03 | Кнопка «Меню» везде | на всех экранах wf-tg-bot + stage3 wf-creatify-webhook; тупики/тексты | ✅ done (57 send-нод, 0 issues) |
| 04 | URL→видео | интерактив: ссылка → длительность 30/60/90 → link+submit → статус; гейты 10/50 | ✅ done (374 нод, 0 issues; regen через гейт — фикс оркестратора) |
| 05a | AI Shorts | интерактив: тема → генерация → доставка видео + кнопки; фикс URL-пути | ✅ done (404 нод, линт 0, sims 34/34) |
| 05b | wf-creatify-shorts | расширение темы→сценарий через hermes-bridge (бесплатно) | ✅ done (17 нод, BFS чисто, контракт video_output) |

Порядок: 01 → 02 → 03 → 04 → 05a (последовательно, один файл wf-tg-bot.json); 05b параллельно (другой файл).

---

## Ран 1: фиксы по CODE REVIEW (13.08.2026) — ВСЕ ВОЛНЫ ЗАВЕРШЕНЫ

## Сделано
- ✅ CODE REVIEW: docs/CODE-REVIEW-2026-08-13.md, вердикт НЕ ГОТОВ
- ✅ Утечка секретов вычищена (filter-repo, cc3b65d); ротация отложена (решение пользователя)
- ✅ Новый SC-ключ: баланс 100→~68 кред; .env + Credential ...001; 24/24 active

## Волна 1 — критичные блокеры ✅ ЗАДЕПЛОЕНА
| Тикет | Что | Статус |
|-------|-----|--------|
| FIX-01+02+03a | wf-tg-bot: 14 кнопок (=), example.com-гейт, туннель | ✅ |
| FIX-03b+07 | wf-creatify-link: туннель, link_id приоритет | ✅ |
| FIX-04 | wf-creatify-poll: fallbackOutput, keypair-auth, обработка | ✅ |

## Волна 2 — защита трат ✅ ЗАДЕПЛОЕНА (live-тесты зелёные)
| Тикет | Что | Статус |
|-------|-----|--------|
| FIX-05 | wf-audience: validate + mock + гейт 30 + универсальный парсер | ✅ LIVE: демография khaby.lame |
| FIX-06 | SC-кластер 4 файла: mock/validate/ошибки | ✅ LIVE: search/profile/content/transcript |
| FIX-08+10 | submit: validate+credit-check; webhook: подпись+done/failed/unknown | ✅ |
| FIX-09 | adclone: порог 90 + cost_warning | ✅ |

## Волна 3 — UX/publish ✅ ЗАДЕПЛОЕНА (live-тесты зелёные)
| Тикет | Что | Статус |
|-------|-----|--------|
| FIX-11+12 | wf-tg-bot: esc() 4 stage-ноды + CP caption+timeout | ✅ |
| FIX-13+14+15 | publish-status loop (24), onboard error+SSRF (10), analytics контракт (17) | ✅ LIVE: onboard robotec.ru + SSRF-блок, analytics кандидаты |

## Волна 4 — безопасность/репо ✅
| Тикет | Что | Статус |
|-------|-----|--------|
| FIX-16 | db-bridge fail-closed (server.js на сервере применён + перезапуск, health/query/401 проверены) | ✅ |
| FIX-17 | docker-compose.yml актуальный (fixes/, НЕ применять на сервере — витрина) | ✅ prepared |
| FIX-18 | caption-adapter.md + DEPLOYMENT правки (fixes/) | ✅ prepared |
| FIX-19 | webhook mock-пометки (ушли в FIX-10) | ✅ |

## Питфоллы, найденные в ходе фиксов
1. **neverError в n8n 2.34.4 — ТОЛЬКО вложенный** `options.response.response.neverError` (подтверждено исходниками ноды), top-level `options.neverError` не читается.
2. Switch mock: boolean-выражение `$env.X === 'PLACEHOLDER'` + string-оператор → «Wrong type: boolean»; правильно — сравнение строк.
3. HTTP-нода НЕ прокидывает входной item — кросс-нод-ссылки `$('Code validate').first().json`.
4. scripcreators balance: ответ может быть JSON-строкой в `$json.data` (не объектом) — универсальный парсер.

## Тесты SC (потрачено ~32 кред из 100): все ✅
## ИТОГ Рана 1: 15 воркфлоу/файлов исправлены, 24/24 активны, все live-тесты зелёные
| 21 | Деплой волн 1+2 (гейт: согласие пользователя) | ✅ done (15.08: миграции, bridge, 847 нод, команды 35, live-тесты 0 кред) |
| 22 | TG-credentials всем нодам + фиксы live-проверок (гейт/switch/hardcode) | ✅ done (158 рёбер index, 90 replyMarkup, 13 updated_at, 24 boolean-switch, client_id per-чат) |
| 23 | Live-чек-лист волн 1+2 | ✅ done (доступ/карточка/гейт/интервью/вопросы/профиль — 0 кредитов; кнопки подтверждены) |
| 24 | Аудит всех 24 воркфлоу | ✅ done (0 issues; валидатор: index/type, replyMarkup, BFS со всех триггеров) |
| 25 | Фиксы по аудиту | ✅ done (zz-test-sqlite деактивирован; исполнения чисты после 11:15) |
| 26 | Синк репо + коммит | ✅ done (f8b2e98, 254 файла) |
| 27 | Шортсы: чистый сценарий, 30 сек (90–110 слов), строгий JSON, 1 повтор, ошибка | ✅ done (15.08 вечер) |
| 28 | Авто-шортсы + url2video: чистый текст, 30 сек, строгий JSON, 1 повтор | ✅ done (15.08 вечер) |
| 29 | Верификация волны 4: валидаторы, симы, деплой, smoke | ✅ done (15.08 вечер) |
| 27 | Шортсы: чистый сценарий, 30 сек, строгий JSON, 1 повтор | ✅ done (верифицировано) |
| 28 | AU/DU: чистый текст, 30 сек, строгий JSON, 1 повтор | ✅ done (верифицировано) |
| 29 | Верификация волны 4: валидаторы, деплой, smoke | ✅ done (exec 4332) |
| 30 | Верификация сценария в цикле (SH + AU) | ✅ done (верифицировано) | |
| 31 | Верификация видео в чате | ✅ done (верифицировано) | |
| 32 | Авто-режим (команда «авто») | ✅ done (live: флаг 0->1->0) | |
| 33 | Верификация волны 5 + деплой + миграция v3 | ✅ done (деплой 3 воркфлоу, миграция v3, smoke) |
| 34 | Release-readiness волна 1: TG-кнопки/видео (01) | ✅ done (16.08: 35/35 команд, callback_data, sendVideo v1.2, unknown-статусы, валидатор 0 issues) |
| 35 | Release-readiness волна 1: промпты скиллов (04) | ✅ done (16.08: test-04 6/6, нет хардкода Robotec) |
| 36 | Release-readiness волна 1: SC-кластер (05) | ✅ done (16.08: аудит 0 issues по 6 воркфлоу, sim 38/38, гейты low_credits) |
| 37 | Release-readiness волна 1: профили/bridge (07) | ✅ done (16.08: pytest 15/15, миграции v1-v3 в репо) |
| 38 | Release-readiness волна 1: системное/инфра (08) | ✅ done (16.08: DEPLOYMENT сверен, register-диспетчер, .env.example полный, compose актуален) |
| 39 | Release-readiness волна 2: полный цикл аналитика→submit (02) | ✅ done (16.08: контракт тем, строгий JSON, гейты 10/50, link/submit sim зелёные) |
| 40 | Release-readiness волна 2: премиум-Creatify (03) | ✅ done (16.08: avatar/banner/product/asset впаяны до точки списания; adclone/inspiration/text — deferred с причинами) |
| 41 | Release-readiness волна 2: публикация 7 платформ (06) | ✅ done (16.08: Switch upload_needed исправлен, text-only маршрут, caption-адаптация, 30/30 sim) |
| 42 | Release-readiness волна 3: E2E smoke (09) | ✅ done (16.08: цепочка /start→publish прослежена, 23 webhook-пути, smoke-checklist.md) |
| 43 | Ревью-фиксы безопасности (10) | ✅ done (16.08: header-auth 21 webhook + 30 вызывающих, fail-closed колбэк creatify, хардкод=0, DEPLOYMENT обновлён) |
| 44 | Деплой волн 1-3 на сервер (16.08, гейт пользователя «ок») | ✅ done: бэкап, синк 24 воркфлоу, миграции v5 (no-op), импорт 24 + publish 23 (zz-test-sqlite off), credential Factory Webhook Auth (пустое значение), bridge перезапущен, 35 команд, getWebhookInfo ok, fail-closed 500/403 подтверждён. Ждёт: FACTORY_WEBHOOK_SECRET в .env + значение в credential + платные тесты |
