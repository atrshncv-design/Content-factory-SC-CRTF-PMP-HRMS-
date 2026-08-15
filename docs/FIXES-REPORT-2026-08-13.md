# ОТЧЁТ ПО ФИКСАМ — контент-завод (13.08.2026)

**Источник:** docs/CODE-REVIEW-2026-08-13.md → 4 волны фиксов.
**Результат:** 15 файлов исправлены; 24/24 воркфлоу активны; все live-тесты зелёные; **0 кредитов creatify, ~32 кред SC** (по плану тестов).

---

## Волна 1 — критичные блокеры (К2–К5) ✅ задеплоено

| Фикс | Воркфлоу | Что исправлено | Проверка |
|------|----------|----------------|----------|
| К2 | wf-tg-bot | 14 кнопок этапов 1–2: `callback_data` literal `{{ $json.topic_id }}` → `={{ 'approve:topic:' + $json.topic_id }}` (и edit/reject/alt) | верифицировано: все 14 с `={{` |
| К4 | wf-tg-bot | example.com-заглушка → валидатор URL (невалидный → `{ok:false}`, не платный вызов) | верифицировано |
| К5 | wf-tg-bot + wf-creatify-link | хардкод туннеля → `$env.WEBHOOK_URL` (через плейсхолдер `__WEBHOOK_URL__` в Code-ноде + подстановка в HTTP) | 0 вхождений туннеля |
| К3 | wf-creatify-poll | fallbackOutput:"extra" + keypair-авторизация + обработка результата (7→9 нод, UPDATE generations) | exec success в real |

## Волна 2 — защита трат (В1–В9) ✅ задеплоено, live-тесты зелёные

| Фикс | Воркфлоу | Что исправлено | Live-тест |
|------|----------|----------------|-----------|
| В1 | wf-audience | validate handle/platform + mock/real + low_credits-гейт 30 + универсальный парсер balance (6→14 нод) | ✅ демография khaby.lame (26 кред) |
| В2/В3 | SC×4 | mock/real-переключатели, Code validate (query/handle/platform/url), ошибки API | ✅ search 10 авторов · profile · content · transcript |
| В6 | wf-creatify-link | приоритет link_id: `$json.id \|\| (link.id)` | ✅ |
| В7 | wf-creatify-submit | validate входа + credit-check floor 50 (9→16 нод) | ✅ invalid_input |
| В8/В10 | wf-creatify-webhook | подпись x-factory-secret (fail-open пока секрет не задан!) + ветки done/failed/unknown + убраны mock-хардкоды (21→25) | ✅ |
| В9 | wf-creatify-adclone | порог low_credits 20→90 + cost_warning | ✅ |

## Волна 3 — UX/publish (В10–В12, В5, В4) ✅ задеплоено, live-тесты зелёные

| Фикс | Воркфлоу | Что исправлено | Live-тест |
|------|----------|----------------|-----------|
| В10 | wf-tg-bot | esc() в 4 stage-Format-нодах + `start\_cycle` в статичных текстах + esc(state) в busy | ✅ |
| В11 | wf-tg-bot | CP-ветка: full_text/video в payload wf-publish, timeout 300000 | ✅ |
| В12 | wf-publish-status | мёртвые IF удалены, Split In Batches loop (23→24), neverError | ✅ |
| В5 | wf-onboard | try/catch SSRF + 100.64/10, 0.0.0.0/8, IPv6-блок + error-Respond (5→10) | ✅ robotec.ru + SSRF-блок |
| В4 | wf-analytics | query из тела (query_list/niche) + competitors_found + retry (16→17) | ✅ кандидаты по запросу |

## Волна 4 — безопасность/репо ✅

| Фикс | Что | Статус |
|------|-----|--------|
| FIX-16 | **db-bridge fail-closed** — server.js на сервере пропатчен, контейнер перезапущен: health ✅, query ✅, без токена 401 ✅ | ✅ ЗАДЕПЛОЕНО |
| FIX-17 | docker-compose.yml актуальный (n8n 2.34.4 + db-bridge + cloudflared, extra_hosts, блокировка 0.0.0.0) | ✅ prepared (fixes/) |
| FIX-18 | caption-adapter.md (17 платформ) + DEPLOYMENT.md правки (credit-check, id 016, filter-repo note) | ✅ prepared (fixes/) |
| FIX-19 | webhook mock-пометки — убраны в рамках FIX-10 | ✅ |

## Питфоллы (важно для будущих правок)

1. **neverError в n8n 2.34.4 — ТОЛЬКО `options.response.response.neverError`** (вложенный). Top-level `options.neverError` молча игнорируется. Подтверждено исходниками ноды в контейнере.
2. **Switch 3.4**: boolean-выражение (`$env.X === 'PLACEHOLDER'`) с string-оператором → `Wrong type: boolean`; правильно — сравнивать строки (`leftValue: $env.X`, `rightValue: PLACEHOLDER`).
3. **HTTP-нода не прокидывает входной item** — после неё параметры брать кросс-нод-ссылкой `$('Code validate').first().json.*`.
4. **scrapecreators balance** может прийти JSON-строкой в `$json.data` (а не объектом) — парсер должен обрабатывать оба варианта.

## Что НЕ сделано (осознанно)

- **Ротация ключей** (пароль n8n, OPENCODE_ZEN_API_KEY) — по решению пользователя отложена. ⚠️ Ключи после утечки в истории — сменить при первой возможности.
- **F-3** (аккаунты postmypost) — за заказчиком (вне критерия готовности).
- **F-E2E** (полный цикл с реальной публикацией) — требует подключённых аккаунтов postmypost.
- **FIX-17/18** (compose, caption-adapter, DEPLOYMENT) — подготовлены в `.scratch/review-content-factory/fixes/`, в репо не перенесены (по договорённости правки только в fixes/; перенос — после «ок»).
- **Live-тест кнопок TG** (реальный клик в Telegram) — за оператором (эмуляция в mock была).

## Артефакты

- `docs/CODE-REVIEW-2026-08-13.md` — исходный отчёт ревью
- `.scratch/review-content-factory/fixes/` — все исправленные JSON (15 файлов + артефакты)
- `.scratch/review-content-factory/issues/fix-*.md` — тикеты фиксов
- `PROGRESS.md` — сводка
