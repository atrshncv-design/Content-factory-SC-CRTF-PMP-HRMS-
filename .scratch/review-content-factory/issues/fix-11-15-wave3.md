# FIX-11+12+13+14+15 — Волна 3: UX TG и publish

**Status:** ready-for-agent
**Blocked by:** Волна 2 (последовательное применение к разным файлам не конфликтует)

## Задача
5 фиксов UX/publish. Результат — файлы в `.scratch/review-content-factory/fixes/`.

## FIX-11 — wf-tg-bot: esc() в stage-Format-нодах (К/В10)
4 Code-ноды: `SC Stage1 Format`, `ET Stage1 Format`, `CT Stage2 Format`, `OB Format` — динамические поля LLM
(title/rationale/adaptation/hook/body/full_text/name/industry/topics) НЕ экранированы esc().
Правка: обернуть все динамические куски в `esc(...)` (паттерн из MO Format/UX-1):
`const esc = s => String(s ?? '').replace(/([_*[\]`])/g, '\\$1');` — добавить в начало jsCode и применить.
Также статичные тексты с `/start_cycle` в TG topic rejected / TG script rejected / TG gen rejected / TG regen
→ заменить на `start\\_cycle` (экранированная форма). В busy-ветке `SC Check → TG SC busy` — `esc(state)`.

## FIX-12 — wf-tg-bot: CP-ветка (В11)
- `CP Build publish body` → в wf-publish уходит `{platforms, captions:{}, post_at, generation_id}` БЕЗ текста.
  Правка: тянуть `full_text` из scripts и `video_output_url` из generations (db-bridge SELECT в CP-ветке)
  и передавать в payload `{platforms, content, file_ids?, captions:{...}, post_at, generation_id}`.
- `CP HTTP wf-publish`: timeout 60000 → 300000 (wf-publish с PM-3 делает до 4×300s bridge-вызовов).

## FIX-13 — wf-publish-status (В12)
- Мёртвые `IF any?`/`NoOp no rows` (не соединены) — удалить; `First row` + LIMIT 20 → одна строка за тик.
  Правка: Split In Batches loop-back (как wf-sync-accounts) или убрать LIMIT; минимум — удалить мёртвые ноды.
- `HTTP GET real` / `HTTP UPDATE published/error` / `HTTP tg *` — добавить neverError + retryOnFail,
  HTTP-ошибку обрабатывать как status='error' (строка не должна висеть в pending_publication вечно).

## FIX-14 — wf-onboard (В5)
- Нет error-ветки: throw в SSRF check или ошибка HTTP → execution error, webhook не отвечает.
  Правка: try/catch в Code SSRF check + onError-ветки HTTP → Respond `{ok:false, error:...}`.
- SSRF-диапазоны: добавить 100.64.0.0/10 (CGNAT), 0.0.0.0/8; IPv6 кроме ::1; в идеале — резолв DNS.
- HTTP Request: retryOnFail:true, maxTries:3.

## FIX-15 — wf-analytics (В4)
- Контракт входа: читать query из тела (`body.query_list[0]` / `body.niche`), fallback на дефолт 'industrial robot' + пометка в meta.
- Выход: добавить `competitors_found` (сбор топ-авторов из candidates).
- HTTP IG/YT: добавить retry/backoff (options retryOnFail:true maxTries:3), onError continueRegularOutput.

## Ограничения
- Исходники НЕ менять. Никаких сетевых вызовов/SSH. Секреты не выводить. JSON валидный + node --check jsCode.
- В отчёте: по каждому файлу таблица (нода | было | стало).
- Язык: русский.
