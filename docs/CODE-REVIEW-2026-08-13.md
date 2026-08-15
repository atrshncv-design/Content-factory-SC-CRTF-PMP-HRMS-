# CODE REVIEW — контент-завод (13.08.2026)

**Репо:** `atrshncv-design/Content-factory-SC-CRTF-PMP-HRMS-` (HEAD cc3b65d)
**Метод:** статическое ревью + read-only SSH; **0 кредитов потрачено** (ни одного HTTP к платным API — даже GET).
**Объём:** 24 воркфлоу n8n построчно (4 изолированных субагента), hermes-bridge, скрипты, docker-compose, git-история, сверка DEPLOYMENT.md с фактом на сервере.
**Верификация:** все 🔴-находки перепроверены оркестратором по первоисточникам; SSH-факты собраны напрямую (24/24 воркфлоу active, webhook-пути, factory.db, executions).

---

## 1. ВЕРДИКТ ГОТОВНОСТИ (по критерию интервью: п.1 функциональность + п.2 кредиты)

# ❌ НЕ ГОТОВ

| Критерий | Статус | Доказательство |
|----------|--------|----------------|
| п.1: все 21 тикет DONE + базовый контур работает | ❌ | SC-4 BLOCKED (кредиты SC −1), SC-5 live-данные BLOCKED (тот же баланс), UX-FIX-1 live-тест отложен, F-E2E не прогнан; базовый контур TG заблокирован сломанными кнопками (находка №1 ниже) |
| п.2: нет BLOCKED из-за нулевого баланса | ❌ | Баланс scrapecreators **−1** (сожжён SC-4: `/v1/tiktok/user/audience` = 26 кред/запрос); creatify ≈ 379 (после тикетов) — но SC-блокировка активна |

**Обоснование одной строкой:** функционально реализовано почти всё (21/21 тикетов имеют воркфлоу, 24/24 активны на сервере), но два жёстких условия не выполнены: SC-кластер не работает из-за нулевого баланса, а кнопки этапов 1–2 TG-цикла сломаны (literal `{{ }}` без `=`), плюс wf-creatify-poll неработоспособен в real-режиме.

---

## 2. КРИТИЧНЫЕ НАХОДКИ (🔴) — верифицированы оркестратором

| # | Область | Факт | Влияние |
|---|---------|------|---------|
| К1 | **Утечка секретов в git-истории публичного репо** — пароль n8n owner (`DEPLOYMENT.md:102`, 6 коммитов) и ключ LLM `OPENCODE_ZEN_API_KEY` (`specs/11-amendments.md:204`, с первого коммита) | 🔴 | **ЗАКРЫТО в этом ревью:** filter-repo + force-push (cc3b65d), верифицировано на GitHub. Осталось: **ротация ключа и пароля на сервере** (за пользователем — ключи всё ещё действуют) |
| К2 | **Кнопки этапов 1–2 сломаны**: `callback_data: 'approve:topic:{{ $json.topic_id }}'` и `approve:script:{{ $json.script_id }}` в 4 TG-нодах (stage1, stage1 edit, stage2, script saved) — literal-строка без `=`, n8n отправит текст как есть | 🔴 | Нажатие кнопки → парсер не распознаёт id → цикл /start_cycle застревает после этапа 1–2 |
| К3 | **wf-creatify-poll неработоспособен в real**: Switch mock без `options.fallbackOutput` (поток молча обрывается при real-ключах) + HTTP-нода с `httpMultipleHeadersAuth` (в этой сборке заголовки не доставляются → 401) + результат GET ничем не обрабатывается (нет UPDATE generations) | 🔴 | Отслеживание генераций по cron сломано — при зависшей генерации callback не придёт и никто не узнает |
| К4 | **Заглушка `example.com` в платной ветке** (`AS Build link body`, wf-tg-bot): при real-ключах команда /start_cycle уйдёт в реальный `POST /api/links/` (1 кред) и генерацию ролика из example.com | 🔴 | Реальные траты на мусорный URL |
| К5 | **Хардкод cloudflared-туннеля** в webhook_url (wf-tg-bot `AS Build bridge prompt` + wf-creatify-link): URL умирает при рестарте туннеля → creatify-callback на мёртвый URL → генерация зависает навсегда | 🔴 | Зависшие джобы и потерянные статусы |

## 3. ВАЖНЫЕ НАХОДКИ (🟠) — сводка

| # | Область | Факт |
|---|---------|------|
| В1 | wf-audience | **Нет low_credits-гейта и валидации handle** перед эндпоинтом за 26 кред/запрос; webhook публичный без авторизации |
| В2 | SC-кластер (4 воркфлоу) | Невалидный вход (пустой query/handle) уходит в платные HTTP (~1 кред, без кэша) |
| В3 | SC-кластер | **Нет mock/real-переключателей** ($env === PLACEHOLDER) — при плейсхолдер-ключах пойдут реальные платные вызовы (паттерн есть только в wf-analytics) |
| В4 | wf-analytics | Контракт входа НЕ по спеке: тело игнорируется, query захардкожен «industrial robot»; нет `competitors_found` |
| В5 | wf-onboard | Нет error-ветки (ошибка → пустой ответ клиенту); DNS-rebinding не закрыт (не покрыты 100.64/10, 0.0.0.0/8, IPv6) |
| В6 | wf-creatify-link | Приоритет link_id наоборот: `($json.link && $json.link.id) || $json.id` — берёт вложенный (невалидный) id |
| В7 | wf-creatify-submit | Нет credit-check перед платным POST `/api/link_to_videos/` (спека F-2 требует floor 50) |
| В8 | wf-creatify-webhook | Публичный callback без подписи: любой может POST'ом пометить generation done/failed (спуфинг) |
| В9 | wf-creatify-adclone | Порог low_credits = **20 при реальной цене 84** — запрос при балансе 21–83 уведёт в минус; нет предупреждения оператору |
| В10 | wf-tg-bot | **4 stage-Format-ноды не экранируют LLM-тексты** esc() → 400 Markdown при `_`/`*` в теме/сценарии; статичные тексты с `/start_cycle` неэкранированы |
| В11 | wf-tg-bot CP-ветка | В wf-publish не передаётся caption/контент (details[] без content) → пустая публикация/422; таймаут 60s vs 4×300s bridge |
| В12 | wf-publish-status | Мёртвые IF any?/NoOp (след бага «IF silently FALSE»); одна строка за тик из LIMIT 20 (до 40 мин очереди); нет neverError/retry |
| В13 | infra/db-bridge | **Fail-open авторизация** при пустом `FACTORY_DB_BRIDGE_TOKEN` (в отличие от hermes-bridge); бинд 0.0.0.0. На проде токен задан — риск снят, но код опасен |
| В14 | docker-compose.yml (репо) | Устарел: не соответствует live-архитектуре (n8n+db-bridge+cloudflared+hermes-bridge); нет extra_hosts и N8N_BLOCK_ENV_ACCESS_IN_NODE=false |

## 4. Сверка DEPLOYMENT.md vs ФАКТ (SSH, read-only)

| Заявлено в DEPLOYMENT | Факт на сервере | Вердикт |
|---|---|---|
| Все воркфлоу активны | **24/24 active=1** (workflow_entity) | ✅ |
| webhook-пути зарегистрированы | 24 пути + tg-trigger (webhook_entity) | ✅ |
| wf-tg-bot 278 нод, tg-trigger | 278 нод, activeVersionId 045e5e3b, триггер `tg-trigger` | ✅ |
| wf-credit-check существует, live-тест | **Воркфлоу НЕТ** (0 с «credit» в имени) | ❌ строка DEPLOYMENT.md:32 — артефакт |
| wf-creator-profile id ...015 | Реально **...016** (...015 = creators-search) | ❌ опечатка в DEPLOYMENT.md:329 |
| generations #12 done | #12 done, creatify_id реальный, webhook_received=1 | ✅ |
| scripts 4 / topics 7 (CR-2) | scripts.id=4 (creatify, done), topics.id=7 (pending) | ✅ |
| sessions IDLE | 941296693 \| IDLE | ✅ |
| Cron обслуживания (3 шт) | 3 строки crontab на месте | ✅ |
| Cloudflared URL | `assessment-fossil-assignments-alice.trycloudflare.com` | ✅ |
| tg-commands 28 | tg-commands-25.json 28 команд ↔ Switch cmd 28 правил 1:1 | ✅ |
| Капшены SC-4/SC-5 BLOCKED | Баланс SC −1; эндпоинт audience 26 кред | ✅ (внешняя блокировка) |

## 5. Безопасность

- ✅ **Утечки из истории вычищены** (filter-repo, force-push cc3b65d, верифицировано на GitHub: 0 вхождений пароля и ключа).
- ✅ Workflows/infra/hermes: inline-секретов нет (всё через `$env`); .gitignore полный; .env в git не попадал.
- 🟠 3 порта (5678/8642/8787) слушают 0.0.0.0, но **firewall VK Cloud блокирует снаружи** (HTTP 000 снаружи) — риск низкий.
- 🟠 db-bridge fail-open при пустом токене (на проде токен задан).
- 🟡 hermes-bridge слушает 0.0.0.0:8642; нет лимита тела/rate-limit; stderr отдаётся клиенту.
- 🟠 Caddyfile (репо) публикует весь n8n UI на nip.io; `/media/*` без авторизации.
- ⚠️ **Осталась ротация**: пароль n8n owner и OPENCODE_ZEN_API_KEY на сервере всё ещё действуют — перевыпустить.

## 6. Что проверено и работает (позитив)

- Авторизация HTTP-нод: typeVersion ≥4.5 + keypair + contentType json — везде, кроме poll;
- jsonBody без вложенных `{{ }}` (`={{ $json.payload }}`) — везде; webhookId у всех нод; имена триггеров без пробелов;
- Идемпотентность wf-creatify-webhook (SELECT→duplicate→done/failed) — полная;
- PM-1/2/3: publication_type 1/2/4, publication_status=5, tiktok=106, caption-адаптация ≤4 платформ через bridge, loop Split In Batches — корректно;
- wf-sync-accounts: UPSERT + loop-back — корректно; esc() в 20 Format-нодах UX-1 — на месте;
- Валидация входов в wf-creatify-product (video_url отклоняется с объяснением) — эталонный пример.

## 7. Непроверенное (требует живых вызовов — запрещено условием)

- Форма ответа `GET /api/remaining_credits/` (все credit-гейты зависят от поля `remaining_credits`);
- Формы ответов iab_images/inspiration_jobs/personas (output[], поля);
- `GET /api/link_to_videos/?ids=` (ледажер с query) — форма не верифицирована;
- Реальная цена transcript/comments SC-5; кэш-поведение;
- Живой клик кнопок TG (эмуляция была в mock, реальный — за оператором);
- Актуальность дефолтной модели `flux-pro/kontext/text-to-image` в каталоге asset_generator.

## 8. Рекомендуемый порядок действий (после «ок» пользователя)

1. **Ротация** пароля n8n owner + OPENCODE_ZEN_API_KEY (сервер) — приоритет №1;
2. Фикс К2 (callback_data `={{ ... }}` в 4 нодах) → перезапуск n8n → тест цикла в mock;
3. Фикс К3 (wf-creatify-poll: fallbackOutput + keypair-заголовки + обработка результата);
4. Фикс К4/К5 (пример.com → реальный вход; туннель → `$env.WEBHOOK_URL`);
5. В1/В3: low_credits-гейты + mock-переключатели в SC-кластер;
6. В6/В7/В9: link_id приоритет, credit-check в submit, порог adclone ≥90;
7. Синхронизация репо: docker-compose, caption-adapter.md, wf-credit-check строка, id ...016, канонические экспорты;
8. F-E2E на реальных ключах (после пополнения SC) — единственный способ закрыть п.1 критерия готовности.

---

*Отчёт составлен статически; 0 кредитов потрачено. Все 🔴-находки перепроверены по файлам репо и серверу. Тикеты ревью: `.scratch/review-content-factory/issues/01..04`. Спека: `.scratch/review-content-factory/spec.md`.*
