# 05 — ScrapeCreators: аналитика, поиск авторов, профили, аудитория, контент, транскрипты

**Требования:** R10i (полный scope), G09 (полный цикл от аналитики)
**Blocked by:** —
**Зона:** `workflows/wf-analytics.json`, `workflows/wf-audience.json`, `workflows/wf-creators-search.json`, `workflows/wf-creator-profile.json`, `workflows/wf-creator-content.json`, `workflows/wf-transcripts-comments.json`
**Волна:** 1
**Status:** done

## Что должно заработать

Весь кластер SC-аналитики корректен до точки списания: моки, валидация, гейты low_credits, keypair-auth, обработка ошибок.

## Из брифа / манифеста, дословно

> «Полный приём всего scope» → «Всё из плана расширения»
> «0 кредитов»

## Разделы спецификации

История 2, 9.

## Критерии приёмки

- [x] В каждом SC-воркфлоу HTTP-нода typeVersion 4.5, keypair-заголовки (x-api-key из `$env.SCRAPECREATORS_API_KEY`, specifyHeaders:keypair), neverError вложенный (`options.response.response.neverError`). SC использует ОДИН заголовок `x-api-key` (см. specs/02-analytics.md, DEPLOYMENT.md); пара X-API-ID+X-API-KEY — это Creatify.
- [x] Гейт low_credits стоит ДО платного вызова; при low credits — ветка с понятным сообщением оператору (`{ok:false, error:'low_credits', balance:...}`).
- [x] Мок/реал переключается безопасно: Switch с string-оператором (leftValue `={{ $env.SCRAPECREATORS_API_KEY }}`, rightValue `PLACEHOLDER_UNTIL_TOMORROW`, operator string/equals).
- [x] Контракты ответов (reels/videos/tweets/comments/transcript) валидны; парсеры универсальны — обрабатывают и объект, и JSON-строку в `$json.data` / `$input..json.data` / `resp.data`.
- [x] Валидатор + sim зелёные; 0 платных SC-вызовов (только статический анализ и мок-симуляции).

## Проверки (0 платных вызовов)

1. **Аудит** — `python3 .autopilot/release-readiness/tickets/05-audit.py` → `TOTAL ISSUES: 0` по всем 6 воркфлоу (typeVersion 4.5, keypair, neverError, гейт до платного вызова на всех путях, string-оператор mock-switch, universal-парсеры, responseBody low_credits).
2. **Приёмочный тест** — `python3 .autopilot/release-readiness/tickets/05-test.py` → `🟢 All tests passed` (JSON loadable, audit 0 issues, node --check + reachability, mock/real switches string-based).
3. **Валидатор** — `python3 .scratch/bot-ux-menu/validate_workflow.py` → 5/6 «✅ ВАЛИДАЦИЯ ПРОЙДЕНА (0 issues)»; wf-transcripts-comments — единственная «недостижимость» — comments-цепочка, ложная тревога двухwebhook-воркфлоу (BFS валидатора стартует только от первого webhook). Проверено отдельным BFS: от `transcript-webhook` 22 ноды, от `comments-webhook` 23 ноды, покрытие 45/45, недостижимых из обоих webhook — 0.
4. **Sim** — все Code-ноды кластера прогонялись через sim-харнесс (stub `$`, `$json`, `$input`): валидаторы (ок/ошибки), парсеры баланса (объект/прямой/JSON-строка/недоступен), нормализаторы IG/TikTok/YT/TW (включая JSON-строку в data и 402→low_credits), моки, Detect transcript/comments, VTT-парсер транскрипта, Postprocess/Code Top-N/Code Final — ✅ все зелёные (38 проверок).

## Что доделано в этом прогоне (поверх предыдущего)

- `wf-transcripts-comments.json`: 5 HTTP-нод (TikTok/YouTube transcript, TikTok/YouTube/Instagram comments) переведены с `credentials.httpHeaderAuth` на keypair-заголовки (`authentication:none` + `sendHeaders:true` + `specifyHeaders:keypair` + `x-api-key` из `$env.SCRAPECREATORS_API_KEY`), удалена привязка credentials. URL остаётся динамическим через кросс-нод-ссылку `={{ $('Detect transcript').first().json.api_url }}` (HTTP-нода не прокидывает входной item).
- `wf-audience.json`: `Code balance` приведён к универсальному парсеру с `balance_unavailable` + pass-through параметров `Code validate`; `IF low credits` дополнен вторым условием (`balance_unavailable == false`) — гейт теперь ведёт себя как в остальных 5 воркфлоу (недоступный баланс НЕ блокирует цепочку, а low credits — блокирует с понятным сообщением).
- `05-audit.py`: `is_sc_http` теперь распознаёт и динамические URL (`Detect transcript`/`Detect comments`) — покрытие аудита расширено на все 5 переведённых нод.

## Осталось на платный тест пользователя

- С реальным ключом `SCRAPECREATORS_API_KEY` проверить каждый эндпоинт: analytics (reels/videos/search), audience, creators-search (с upsert в БД), creator-profile, creator-content, transcript (TT/YT), comments (TT/YT/IG).
- Проверить поведение гейта low_credits при балансе < порога (analytics 5, audience 30, остальные 5): ответ `{ok:false, error:'low_credits', balance:N}`.
- Проверить фактические имена полей ответов SC (reels/items, aweme_list/search_item_list, videos, tweets, comments, transcript VTT/segments) — парсеры универсальны и покрывают и объект, и JSON-строку, но точная структура живого ответа проверяется только платным вызовом.
