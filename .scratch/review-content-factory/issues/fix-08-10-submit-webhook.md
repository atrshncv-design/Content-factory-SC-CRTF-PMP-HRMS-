# FIX-08+10 — wf-creatify-submit (credit-check) + wf-creatify-webhook (подпись)

**Status:** ready-for-agent
**Blocked by:** —

## Задача
Исправить 2 воркфлоу контура генерации. Результат:
`.scratch/review-content-factory/fixes/wf-creatify-submit.json` и `.scratch/review-content-factory/fixes/wf-creatify-webhook.json`.

## A. wf-creatify-submit (сейчас 8 нод: Webhook → INSERT generation → Switch mock → Code mock / HTTP real → Code extract → UPDATE creatify_id → Respond)
Проблема: нет credit-check перед платным POST `/api/link_to_videos/` (5 кред/30с; спека F-2 требует floor 50).
Правки:
1. Валидация входа: `{script_id, client_id, json_payload, link_id}` — все обязательны (script_id/client_id числа), иначе Error Respond `{ok:false, error:'invalid_input'}` (сейчас NOT NULL constraint → exec error → пустой 200).
2. credit-check в real-ветке: перед HTTP POST добавить HTTP GET `/api/remaining_credits/` (keypair-заголовки `{{ $env.CREATIFY_API_ID/KEY }}`, authentication:"none", typeVersion 4.5) → Code balance → IF `balance < 50` → Respond `{ok:false, error:'low_credits', balance}` без POST. Эталон: wf-creatify-text (HTTP credits → Code balance → IF floor 50).
3. HTTP-ноды НЕ прокидывают item — payload через кросс-нод-ссылку `$('Code extract'/'Code validate').first().json` (как в CR-6).

## B. wf-creatify-webhook (сейчас 21 нода: Webhook → HTTP SELECT → IF found → IF already done → IF status done → done-ветка (UPDATE + sessions + TG stage3) / failed-ветка)
Проблема: публичный callback без подписи — любой может POST'ом пометить generation done/failed (спуфинг); else-ветка IF status трактует любой статус ≠ done как failed.
Правки:
1. Валидация path-token/секрета: в Code-ноде после Webhook проверить, что секретный заголовок (например `x-factory-secret`, значение из `$env.FACTORY_WEBHOOK_SECRET`) равен ожидаемому; не совпадает/отсутствует → Respond `{ok:false, error:'unauthorized'}` ДО SELECT. (Переменную FACTORY_WEBHOOK_SECRET добавим в .env отдельно — воркфлоу должен просто проверять.)
   Если воркфлоу уже имеет механизм проверки — усилить его.
2. IF status done: явные ветки — `status === 'done'` → done-обработка; `status === 'failed'` → failed-обработка; прочие статусы (processing/in_queue/unknown) → Respond `{ok:true, status:'unknown'}` БЕЗ UPDATE generations (сейчас else-ветка портит generation).
3. В done-ветке убрать хардкод mock: `local_path: '/var/media/<id>.mp4'` и `mock:true` — формировать из реального ответа creatify (video_output_url), mock-флаг только при mock-переключателе (если есть).

## Ограничения
- Исходники НЕ менять. Никаких сетевых вызовов/SSH. Секреты не выводить.
- В отчёте: по каждому файлу таблица (нода | было | стало) + JSON новых нод.
- Язык: русский.
