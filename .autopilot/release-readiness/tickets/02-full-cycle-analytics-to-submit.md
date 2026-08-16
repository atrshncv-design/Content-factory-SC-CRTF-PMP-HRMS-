# 02 — Полный цикл: аналитика → тема → сценарий → JSON → submit

**Требования:** G03 (полный цикл не проверен), G09 (сценарии криво форматируются и уходят на генерацию), G04 (Robotec)
**Blocked by:** 04 (качество промптов)
**Зона:** `workflows/wf-analytics.json`, `workflows/wf-creatify-link.json`, `workflows/wf-creatify-submit.json`, `hermes/skills/{analyst,scriptwriter,json-builder}.md`, `hermes-bridge/server.py`
**Волна:** 2
**Status:** done

## Что должно заработать

Оператор может пройти цикл от аналитики трендов до отправки задачи в creatify: полученные темы превращаются в сценарий, сценарий — в строгий JSON-контракт для creatify submit, и submit вызывается без кривых payload.

## Из брифа / манифеста, дословно

> «полные сценарии от аналитики до автопостинга не работают»
> «сценарии неправильно форматируются и отправляются на генерацию кривыми»
> «Robotec остаётся»

## Разделы спецификации

История 2, 4; Решения (0 кредитов, источники правды, формат находки).

## Критерии приёмки

- [x] wf-analytics возвращает темы в контракте, который читает wf-tg-bot / hermes analyst.
      Проверено: Postprocess отдаёт `{candidates[], meta}`; bot «SC Check analytics» читает
      `r.candidates`, «SC Build bridge prompt» — title/source_platform/metrics/age_hours/
      virality_index/transcript_excerpt. Sim: 5 кандидатов из мок-записей, все поля контракта
      на месте, `meta.credits_spent=0` (`.scratch/ticket02_sim_chain.py`).
- [x] hermes analyst/scriptwriter используют контекст активного профиля (active_client_id=1, Robotec), без хардкода.
      Убран шаблонный плейсхолдер `{client_name}`/`{client_niche}` из analyst.md → явная ссылка
      на `client_profile` из `context`; scriptwriter/json-builder — «используй активный профиль,
      не хардкоди имя». test-04-content-quality-prompts 6/6.
- [x] Сценарий → json-builder → strict JSON без TG-разметки внутри JSON, без лишних обрамляющих markdown-блоков, без пропущенных полей.
      json-builder.md: требование «override_script без TG/markdown-разметки» + «все поля схемы
      обязаны присутствовать» + чек-лист самопроверки. server.py: `_normalize_json_answer` для
      skill=json-builder снимает markdown-обёртку (5/5 unit-кейсов). Submit-гейт: Code validate
      отклоняет payload с разметкой в override_script (sim подтверждает).
- [x] wf-creatify-submit принимает payload, валидирует обязательные поля, держит гейты 10/50 и credit-floor.
      Code validate усилен: `link` обязателен, `video_length ∈ {15,30,45,60}`, enums
      aspect_ratio/language/target_platform, override_script — строка без TG-разметки,
      webhook_url http(s); ошибки уходят в `Respond invalid input` (details).
      Гейт 10 — в боте (AS/AU/DU/SH Gate, `cr < 10` → low, до link); гейт 50 — в submit
      (`IF low credits: balance >= 50` → только тогда HTTP POST real; иначе `low_credits`),
      credit-floor строго ДО платного вызова (аудит соединений: Switch mock→HTTP credits→
      Code balance→IF low credits→HTTP POST real).
- [x] Link/submit цепочка: мок-ответы по всей цепи проходят без neverError/таймаутов.
      Мок-ветки всех трёх воркфлоу не содержат платных HTTP-вызовов (BFS-аудит:
      analytics 7 нод, link 4 ноды, submit 6 нод — 0 платных URL); в мок-ветке только
      Code/Merge/IF; никогдаError не используется для маскировки (вложен только
      `options.response.response.neverError`, проверено по всем нодам). Sim-цепочка:
      analytics Postprocess/Code balance → link Code mock/Code assemble (3 формы ответа
      creatify) → submit Code validate (6 сценариев)/Code mock/Code extract/Build update
      body/Code balance — 30/30 зелёных, 0 кредитов.
- [x] Валидатор + sim зелёные; 0 кредитных вызовов.
      `validate_workflow.py`: 0 issues на wf-analytics / wf-creatify-link / wf-creatify-submit;
      node --check всех jsCode OK; pytest tests/ 25/25 (test_hermes_bridge 11/11);
      test-04 6/6; 05-test (SC-кластер) зелёный. Ни одного HTTP-вызова creatify/scrapecreators
      не выполнялось — только статика, моки, симы.

## Дополнительно (исправления волны 2 в зоне)

- `wf-creatify-submit.json`:
  - Code validate — валидация контракта обязательных полей payload (см. выше), поле `errors`.
  - `Respond invalid input` — ответ с деталями ошибок вместо статичного `invalid_input`.
  - `HTTP POST real` — `webhook_url` собирается как в link-воркфлоу:
    `($env.WEBHOOK_URL || '').replace(/\/$/, '') + '/webhook/factory/creatify/6d8f2a41c9e7b3d5f0a1c4e8'`
    (раньше склейка без strip-слэша давала `https://доменwebhook/...` при WEBHOOK_URL без слэша).
- `wf-creatify-link.json`: Code assemble — fallback'и `data.id` / `link_id` (реальный ответ
  creatify может быть `{data:{id}}`), мок-путь не менялся.
- `wf-analytics.json`: правок не требовалось (доведён волной 1, тикет 05); контракт
  `candidates[]` подтверждён симами.

## Осталось на платный тест пользователя

1. `/start_cycle` при реальных ключах (SCRAPECREATORS_API_KEY != PLACEHOLDER): analytics
   реально тянет 3 платформы, гейт баланса SC (5) до списаний.
2. `AS/AU` цепочка с реальным CREATIFY_API_ID/KEY: link → json-builder → submit →
   `generations.creatify_id` заполняется, вебхук creatify приходит.
3. Баланс creatify < 50 — ответ `low_credits` (списаний нет).
