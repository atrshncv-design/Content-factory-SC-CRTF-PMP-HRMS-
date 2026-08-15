# FIX-13+14+15 — publish-status, onboard, analytics (Волна 3)

**Status:** ready-for-agent
**Blocked by:** —

## Задача
3 фикса. Результат — файлы в `.scratch/review-content-factory/fixes/`:
`wf-publish-status.json`, `wf-onboard.json`, `wf-analytics.json`.

## FIX-13 — wf-publish-status (23 ноды)
Проблемы: мёртвые `IF any?`/`NoOp no rows` (не соединены — след бага «IF silently FALSE»); `First row` берёт rows[0] из LIMIT 20 → 20 постов по одному за тик; нет neverError/retry → падение postmypost оставляет строку в pending_publication навсегда.
Правки:
1. Удалить мёртвые ноды `IF any?` и `NoOp no rows` (если они не соединены никуда).
2. Обработка строк: заменить `First row` + LIMIT 20 на Split In Batches loop-back (как в wf-sync-accounts: `Split In Batches` → Build body → HTTP → ... → замыкание `loop`→Split, `done`→NoOp done). ИЛИ (проще) убрать LIMIT → обрабатывать все строки через loop. Соблюсти паттерн loop-back из wf-sync-accounts (Split In Batches, done=0 → NoOp done, loop=1 → обработка).
3. На HTTP-ноды real (`HTTP GET real`, `HTTP UPDATE published`, `HTTP UPDATE error`, `HTTP tg *`): добавить `neverError: true` + `retryOnFail: true, maxTries: 3` (в options, если поддерживается — иначе только neverError) и ветку: HTTP-ошибка → UPDATE status='error' (строка не должна висеть вечно).

## FIX-14 — wf-onboard
Проблемы: нет error-ветки (throw в SSRF check или ошибка HTTP → exec error, webhook не отвечает); SSRF-диапазоны неполные (нет 100.64.0.0/10, 0.0.0.0/8, IPv6 кроме ::1); нет retry.
Правки:
1. Code SSRF check: обернуть логику в try/catch; в catch → `return [{json: {ok:false, error:'invalid url'}}]` (не throw). Добавить диапазоны 100.64.0.0/10 (CGNAT), 0.0.0.0/8 в блокируемые; для IPv6 — блокировать все кроме ::1 (или все, если проще).
2. HTTP Request (GET сайта): `retryOnFail: true, maxTries: 3`, `options.timeout` 15000; добавить `neverError: true` и после него Code-проверку `$json.ok === false` → Respond `{ok:false, error:...}` (клиент получает осмысленную ошибку, а не пустой ответ).
3. Убедиться, что ВСЕ ветки заканчиваются Respond (responseNode) — включая error-пути.

## FIX-15 — wf-analytics
Проблемы: тело входа игнорируется (query захардкожен 'industrial robot'); нет competitors_found; нет retry на HTTP.
Правки:
1. `Code` (или входной) — читать query из тела: `($json.body && $json.body.query_list && $json.body.query_list[0]) || ($json.body && $json.body.niche) || 'industrial robot'`; передавать в HTTP-ноды (кросс-нод-ссылка, HTTP не прокидывает item).
2. `Postprocess`: собрать `competitors_found` — топ-авторы из candidates (handle/platform) — добавить в выход.
3. HTTP IG/YT/TikTok: добавить `options: {retryOnFail: true, maxTries: 3, timeout: 45000}` (или в существующий options).

## Ограничения
- Исходники НЕ менять. Никаких сетевых вызовов/SSH. Секреты не выводить. JSON валидный + node --check jsCode.
- В отчёте: по каждому файлу таблица (нода | было | стало) + JSON новых нод.
- Язык: русский.
