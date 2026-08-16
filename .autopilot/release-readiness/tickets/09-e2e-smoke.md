# 09 — Полный E2E smoke (0 кредитов)

**Требования:** R01 (довести до идеала), R06 (сначала проверка, потом реализация), G09 (полные сценарии)
**Blocked by:** 01, 02, 03, 04, 05, 06, 07, 08
**Зона:** все воркфлоу + hermes + infra
**Волна:** 3
**Status:** done (16.08, 0 кредитов; live-подтверждение — deploy-гейт; платная приёмка — за пользователем)

## Что должно заработать

Весь продукт пройден по цепочке с мок-данными без платных вызовов: TG-команда → профиль → аналитика → тема → сценарий → submit → (mock) creatify done → webhook → видео в чат → публикация (до точки отправки в postmypost).

## Из брифа / манифеста, дословно

> «полные сценарии от аналитики до автопостинга не работают»
> «0 кредитов»

## Разделы спецификации

История 2, 12.

## Критерии приёмки

- [x] Мок-прогон полного цикла от /start до publish без ошибок и разрывов.
      Статическая трассировка цепочки (см. ниже) + симуляции мок-ответов существующим
      харнессом: `.scratch/ticket09_sim_chain.py` — 30/30 зелёных (0 кредитов).
      Звенья: Parser (/start→start, tg_user_id) → GPF (профиль Robotec ac_id=1) →
      SC Build analytics body (client_id=1) → SC Check analytics (контракт candidates[],
      ошибка → понятный текст) → SC Build bridge prompt (skill=analyst, кандидаты в промпте)
      → SC Parse topic (JSON-ответ аналитика → title/target_length=30) → SC Build insert topic
      (INSERT topics, client_id=1) → AU Parse script (full_text без markdown, target_length=30)
      → wf-creatify-link Code assemble (link.id → link_id) → wf-creatify-submit Code validate
      (валидный payload) → wf-creatify-webhook Code done build / Build update done
      (UPDATE generations status='done' + webhook_received=1) / Build session update
      (state='VIDEO_AWAIT') / Build stage3 (chat_id=оператор, video, «Этап 3/4») →
      AU Build publish body (platforms+file_ids из video_output_url) → AU Check result
      (post_id → ok; error → понятный текст).
      Все webhook-пути цепочки зарегистрированы (см. пункт ниже); HTTP-ноды webhook/factory
      из wf-tg-bot имеют options.timeout (0 без таймаута); BFS от tg-trigger достигает все
      ноды (validate_workflow.py 0 issues, multi-trigger BFS 24/24 OK).
      Pytest: `python3 -m pytest tests/ -q` — 25/25. test-04-content-quality-prompts 6/6.
- [x] Все webhook-пути зарегистрированы и достижимы с туннеля; secret_token и FACTORY_WEBHOOK_SECRET защищены.
      23 webhook-пути зарегистрированы (все с webhookId в JSON, httpMethod=POST, active=True):
      factory/{analytics,audience,adclone,asset,avatar-upload,my-avatars,banner,inspiration,
      creatify-link,creatify-submit,creatify/6d8f2a41c9e7b3d5f0a1c4e8,product,script,shorts,
      creator-content,creator-profile,creators-search,onboard,publish,tg-alert,transcript,
      comments} + factory/_test (zz-test-sqlite). Все 17 путей, вызываемых из wf-tg-bot
      (localhost:5678/webhook/factory/*), зарегистрированы — 0 «вызывается, но не
      зарегистрирован». Достижимость с туннеля: cloudflared → n8n:5678 (docker-compose),
      WEBHOOK_URL параметризован ($env), 0 хардкодов trycloudflare во всех workflows.
      Секреты — только имена переменных, реальных значений в репо нет (0 sk-/xoxb-/eyJ-совпадений).
      FACTORY_WEBHOOK_SECRET: проверка в wf-creatify-webhook IF auth (x-factory-secret ===
      $env.FACTORY_WEBHOOK_SECRET), fail-open при пустом env — осознанный FIX-10 (creatify не
      шлёт кастомный заголовок; включение после согласования с отправителем колбэков),
      переменная есть в .env.example. secret_token tg-trigger: осознанно пуст (D2 Y5: пустой
      токен безопасен — n8n опускает secret_token из setWebhook; env-подстановка при пустой
      переменной = fail-closed, ломающий бот, запрещено FIX-10-философией; включение позже —
      одна строка additionalFields.secretToken + переактивация); защита оператора — Access
      check (роль admin/operator из users) внутри execution + db-bridge (X-BRIDGE-TOKEN,
      fail-closed при заданном токене) + hermes-bridge (X-BRIDGE-TOKEN, hmac.compare_digest).
- [ ] Все 24 воркфлоу активны после деплоя (кроме zz-test-sqlite).
      **deploy-gate** (live-подтверждение на сервере после деплоя; репо-доказательство
      локально — ниже). В репо 24 файла workflows/*.json: 23 рабочих + zz-test-sqlite, все
      JSON валидны (json.load 24/24), все `active: true`; validate_workflow.py 0 issues на
      21 воркфлоу, multi-trigger BFS 24/24 OK (ложные «НЕДОСТИЖИМЫЕ» валидатора на
      wf-creatify-avatar/banner и wf-transcripts-comments — известный питфолл
      одностратового BFS, опровергнут multi-trigger BFS). cron-воркфлоу (publish-status */2,
      sync-accounts hourly, creatify-poll */5, avatar cron hourly) в репо активны.
      После деплоя проверить: n8n UI → Workflows → все 23 active (кроме zz-test-sqlite).
- [ ] В executions после smoke-прогона — 0 новых ошибок.
      **deploy-gate** (live; прогон чек-листа после деплоя + n8n executions без новых
      error-записей по всем воркфлоу).
- [x] Чек-лист «проверено бесплатно / проверить платно» заполнен для передачи пользователю.
      Создан `.autopilot/release-readiness/smoke-checklist.md` — полный: пункт | статус |
      доказательство | команда пользователю (бесплатные проверки проставлены, платные —
      с точными шагами).
- [x] 0 списаний creatify/scrapecreators.
      Ни одного сетевого вызова в рамках этого тикета: только чтение файлов, статический
      анализ, симы (node-песочница без HTTP). Статически подтверждено: во всех платных
      воркфлоу mock-переключатели на `$env.* === 'PLACEHOLDER_UNTIL_TOMORROW'` (Switch mock
      wf-creatify-submit/link, Switch mock upload/publication wf-publish, Switch mock
      analytics/audience/creators-search/creator-*/transcripts-comments), mock-ветки не
      содержат платных POST (BFS от mock-веток: платный POST достижим только из real-ветки
      при не-PLACEHOLDER ключах); единственные платные GET — балансы (бесплатны).
      Симы 30/30 и pytest 25/25 не делают HTTP. Балансы для платной приёмки — за
      пользователем (спека «Открытые места»: слепок 500/непроверено).

## Трассировка цепочки (статическая, с доказательствами)

| Звено | Путь в воркфлоу | Доказательство |
|---|---|---|
| TG /start | Parser → Switch kind → Switch cmd out[0] → ST Build settings | sim: /start → command=start, tg_user_id проброшен; Switch cmd 45 правил+fallback, все ветви ведут в реальные Build-ноды |
| Профиль | start_cycle → GPF Build/HTTP/Check → Switch gpf ok → GPF Route out[0] → SC Build state | sim GPF: SQL по sessions/client_profile; GPF Check ac_id>0 (Robotec=1); тикет 07 (профили) done |
| Аналитика | SC Build state → SC HTTP wf-analytics (webhook factory/analytics) → SC Check analytics → Switch SC analytics → SC CTX → SC Build bridge prompt → SC HTTP bridge analyst → SC Parse topic → Switch SC parse → SC Build insert topic → SC HTTP insert topic | sim 10 проверок; webhook зарегистрирован; тикет 02 (контракт candidates[]) done; 05-test зелёный |
| Тема | SC HTTP set topic → AU2/CT (settings, approve topic) | тикеты 01/02; Switch AU topic ветви approve/SC Stage1 |
| Сценарий | AU Build prompt → AU HTTP bridge scriptwriter → AU Parse script → Switch AU parse → AU AA → AU Verify → SC Cont build → AU HTTP insert script | sim AU Parse script (full_text чистый, без markdown, 30 сек); тикет 04 (промпты) 6/6 |
| Submit | AU Build link body → Switch AU link → AU LB creatify/parse → AU Gate (cr≥10) → AU HTTP creatify-link (webhook factory/creatify-link) → AU Check link → AU Build prompt json → AU HTTP bridge json-builder → AU Parse payload → AU Build submit body → Switch AU purity → AU HTTP creatify-submit (webhook factory/creatify-submit) → AU Check submit → TG generating | sim: link Code assemble link.id→link_id; submit Code validate валидный; гейт 10 (бот) и 50 (submit, «IF low credits» строго до HTTP POST real); тикет 02 done |
| Webhook done | creatify → wf-creatify-webhook (path factory/creatify/6d8f2a41c9e7b3d5f0a1c4e8): IF auth → HTTP SELECT (script_id-цепочка, D2) → IF found → IF already done → IF status done → Code done build → Build update done → HTTP UPDATE done → Build session update → HTTP session update (VIDEO_AWAIT) → Build stage3 → IF video exists → IF auto approve → Telegram stage3 (sendVideo v1.2, file+caption) / stage3 auto / fallback sendMessage | sim 8 проверок (done build, UPDATE done, session VIDEO_AWAIT, stage3 chat_id/video/текст); тикет 01 (sendVideo схема, failed/unknown алерты) done |
| Публикация | publish:gen кнопка → Switch cb out[7] → PG answer → PG Build session/HTTP → PG Build stage4 read → AUP Build settings/HTTP → AUP Check → Switch AU pub → AU Build select → AU HTTP select → AU Check pub → AU Build publish body → AU HTTP wf-publish (webhook factory/publish) → AU Check result → Switch AU pub result → AU Build final → AU HTTP final → TG published | sim 3 проверки (publish body platforms+file_ids, result post_id→ok, error→текст); тикет 06 (wf-publish 26 нод, upload_needed, text-only, 7 платформ) done |

## Осталось на deploy-гейт / платный тест пользователя

1. **deploy-гейт (сервер, после деплоя волны 3)**: активация 23 воркфлоу (n8n UI),
   smoke-прогон чек-листа, 0 новых ошибок в executions.
2. **Платно (пользователь)**: полный список — в `smoke-checklist.md` (реальная генерация
   creatify URL→видео / shorts / start_cycle, публикация на 7 платформ с подключёнными
   аккаунтами postmypost, балансы creatify/SC до и после).
3. **Секреты**: FACTORY_WEBHOOK_SECRET задан в .env сервера (сейчас fail-open, FIX-10);
   secret_token tg-trigger — по желанию, одной строкой + переактивация webhook.
