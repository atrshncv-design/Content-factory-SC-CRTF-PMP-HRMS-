# ФИКСЫ по CODE REVIEW 13.08 — план «все сценарии до идеала»

> Источник: `docs/CODE-REVIEW-2026-08-13.md` (5×🔴, 14×🟠 + 🟡/🟢).
> Принцип: волнами, критичные блокеры сценариев сначала. Каждый фикс — правка JSON воркфлоу
> → применение на сервер (прямой UPDATE + restart) → бесплатный тест валидационных веток.
> Траты: SC — аккуратно (1 кред/вызов, новый ключ 100 кред); creatify — ТОЛЬКО «до точки списания».

## Волна 1 — критичные блокеры сценариев (К2–К5)

| Тикет | Что | Воркфлоу |
|-------|-----|----------|
| FIX-01 | К2: callback_data кнопок этапов 1–2: `'approve:topic:{{ $json.topic_id }}'` → `={{ 'approve:topic:' + $json.topic_id }}` (и approve/edit/reject:script) — 4 TG-ноды | wf-tg-bot |
| FIX-02 | К4: заглушка `example.com` → реальный URL из входа команды (или гейт) | wf-tg-bot (AS Build link body) |
| FIX-03 | К5: хардкод туннеля → `$env.WEBHOOK_URL` (2 места: wf-tg-bot AS Build bridge prompt, wf-creatify-link HTTP Request) | wf-tg-bot, wf-creatify-link |
| FIX-04 | К3: wf-creatify-poll — fallbackOutput extra + keypair-авторизация + обработка результата (UPDATE generations) | wf-creatify-poll |

## Волна 2 — защита трат и контракты (В1–В9)

| Тикет | Что | Воркфлоу |
|-------|-----|----------|
| FIX-05 | В1: wf-audience — low_credits-гейт (26 кред) + валидация handle + кэш по handle | wf-audience |
| FIX-06 | В2/В3: SC-кластер — валидация query/handle + mock/real-переключатели ($env === PLACEHOLDER) | creators-search, creator-profile, creator-content, transcripts-comments |
| FIX-07 | В6: wf-creatify-link — приоритет link_id `$json.id \|\| ($json.link && $json.link.id)` | wf-creatify-link |
| FIX-08 | В7: wf-creatify-submit — credit-check перед POST (floor 50) | wf-creatify-submit |
| FIX-09 | В9: wf-creatify-adclone — порог low_credits ≥90 (цена 84) + предупреждение | wf-creatify-adclone |
| FIX-10 | В8: wf-creatify-webhook — проверка секретного заголовка/подписи перед UPDATE | wf-creatify-webhook |

## Волна 3 — UX TG и publish (В10–В12)

| Тикет | Что | Воркфлоу |
|-------|-----|----------|
| FIX-11 | В10: esc() в 4 stage-Format-нодах + статичные `/start_cycle` | wf-tg-bot |
| FIX-12 | В11: CP-ветка — передача full_text/video в wf-publish + таймаут ≥300s | wf-tg-bot |
| FIX-13 | В12: wf-publish-status — Split In Batches loop, удаление мёртвых IF/NoOp, neverError | wf-publish-status |
| FIX-14 | В5: wf-onboard — error-ветка (try/catch → Respond) + SSRF-диапазоны 100.64/10, 0.0.0.0/8 | wf-onboard |
| FIX-15 | В4: wf-analytics — параметризация query из тела + competitors_found | wf-analytics |

## Волна 4 — безопасность и гигиена репо

| Тикет | Что |
|-------|-----|
| FIX-16 | db-bridge: fail-open → fail-closed при пустом токене (server.js) |
| FIX-17 | docker-compose.yml в репо → синхронизировать с live (db-bridge, cloudflared, extra_hosts) |
| FIX-18 | Репо: caption-adapter.md, строка wf-credit-check, id ...016, канонические экспорты |
| FIX-19 | wf-creatify-webhook: mock-пометки/хардкоды в real-ветке (local_path, mock:true) |

## Тесты (после каждой волны)

- Валидационные ветки (0 кред): невалидный вход → осмысленная ошибка, НЕ платный вызов.
- SC-сценарии (1 кред/вызов): creators-search, creator-profile, creator-content, audience (26 кред — 1 раз!), transcript/comments.
- TG-цикл в mock: /start_cycle → кнопки этапов 1–4 (эмуляция callback) — бесплатно.
- Creatify: только «до точки списания» (validate-ветки), реальные генерации — после явного «ок» пользователя.
