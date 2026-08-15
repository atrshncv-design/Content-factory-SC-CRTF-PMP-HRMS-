# C2 — wf-creatify-asset: кредитный гейт перед POST /api/asset_generator/

**Статус:** DONE 14.08, 0 кредитов (только статические проверки + sim).
**Тикет:** `.scratch/review-full-14aug/issues/C2-gate-fixes.md` (Y7 из `docs/CODE-REVIEW-2026-08-14.md`).
**База:** `.scratch/review-full-14aug/base/wf-creatify-asset.json` (7 нод, live-экспорт).
**Результат:** `.scratch/review-full-14aug/fixes/wf-creatify-asset.json` (9 нод, 7 connections).

## Проблема (Y7)
Цепочка Webhook → Code validate → Switch → HTTP Asset (POST `/api/asset_generator/`,
1 кред/шт, count 1..4) шла **без проверки баланса** перед платным вызовом: при нулевом
балансе — уход в минус (списание отложенное: `credits_used=0` на POST, минус падает позже).

## Что сделано
Вставлены 2 ноды между `Code validate` и `Switch` (эталон — wf-creatify-product + T1-паттерн):

```
Webhook → Code validate → HTTP credits → Code credit check → Switch → HTTP Asset → Code Normalize → Respond ok
                                                            └─(fallback)─→ Respond error
```

1. **HTTP credits** (`n8n-nodes-base.httpRequest`, typeVersion 4.5) — бесплатный GET
   `https://api.creatify.ai/api/remaining_credits/` (путь с подчёркиванием), keypair-заголовки
   `X-API-ID`/`X-API-KEY` из `$env.CREATIFY_API_ID`/`$env.CREATIFY_API_KEY`,
   `options: {timeout: 15000, response: {response: {neverError: true}}}` — neverError ТОЛЬКО
   вложенный (n8n 2.34.4, top-level молча игнорируется). GET без sendBody. 0 кредитов.

2. **Code credit check** (`n8n-nodes-base.code`, tv 2, runOnceForAllItems):
   - универсальный парсер баланса `body(объект) → raw → JSON.parse(data)` (T1-эталон,
     протестирован: 6 вариантов входа), `remaining_credits` может быть float (`379.0` → `379`);
   - валидацию и payload берёт кросс-нод-ссылкой `$('Code validate').first().json` —
     **существующая валидация входа (prompt обязателен, count clamp 1..4) сохранена и не дублируется**:
     `v.ok === false` → проброс `{ok:false, error:'prompt обязателен'}`;
   - `balance` недоступен → `{ok:false, error:'balance_unavailable', raw}`;
   - **порог 5**: `balance < 5` → `{ok:false, error:'low_credits', balance}` (порог ≥ 1×max count=4,
     покрывает count 1..4 по 1 креду; ровно 5 проходит);
   - ok → `{...v, ok:true, balance}` — `payload` прокидывается дальше в HTTP Asset
     (`jsonBody = {{ $json.payload }}` — без изменений в HTTP Asset).

3. **Существующие ноды НЕ тронуты**: Webhook, Code validate, Switch, HTTP Asset,
   Code Normalize, Respond ok, Respond error — parameters идентичны базе (проверено diff-скриптом).
   Switch уже маршрутизирует `ok=false` в Respond error (fallback) — low_credits/ошибки
   валидации уходят в `Respond error` без доп. изменений.

4. Mock-режим: в этом воркфлоу mock-переключателя НЕТ, ключи реальные (`$env`) — гейт активен всегда.

## Валидации (все статические, 0 кредитов)
- `validate-workflow-json.py fixes/wf-creatify-asset.json` → **0 issues** (9 нод, 7 связей, BFS-достижимость, 3/3 jsCode)
- `lint-workflow-json.py fixes/wf-creatify-asset.json` → **0 находок**
- `node --check` → OK для Code validate / **Code credit check** / Code Normalize
- Sim `sim-code-node-both.py` (стабит и `$json`, и `$('Code validate')`), 6 сценариев — все зелёные:
  | # | Вход | Результат |
  |---|------|-----------|
  | T1 | balance `379.0` (float) | `{ok:true, payload, balance:379}` |
  | T2 | balance `4.0` (< 5) | `{ok:false, error:'low_credits', balance:4}` |
  | T3 | balance `5` (ровно порог) | `{ok:true, payload, balance:5}` |
  | T4 | `Code validate` → `{ok:false, error:'prompt обязателен'}` | проброс `{ok:false, error:'prompt обязателен'}` |
  | T5 | ответ без баланса (`HTTP 502`) | `{ok:false, error:'balance_unavailable', raw}` |
  | T6 | баланс в `data`-строке | `{ok:true, payload, balance:12.5}` (JSON.parse(data)) |
- Grep-ловушки: `={ ` (одна скобка) отсутствует; вложенный neverError на месте.

## Файлы
- **Фикс:** `.scratch/review-full-14aug/fixes/wf-creatify-asset.json`
- **Отчёт:** `.scratch/review-full-14aug/fixes/C2-asset-credit-gate.md`
- База не изменялась. На сервер НЕ применено (паттерн волн фиксов — применение после «ок»).

## Остаётся вне этого фикса (из Y7, отдельный тикет)
- `neverError` на самом платном POST (HTTP Asset): Y7 упоминал отсутствие neverError — гейт закрывает
  минус при нулевом балансе; обработка 4xx/5xx самого asset_generator — вне объёма C2-asset (см. B1).
- Дефолт `model_name` не сверен с каталогом schemas (отдельная проверка, в этом фиксе не трогалось).
