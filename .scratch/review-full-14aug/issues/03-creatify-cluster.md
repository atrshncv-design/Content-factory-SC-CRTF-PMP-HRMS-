# 03 — Ревью кластера генерации creatify (11 воркфлоу)

**What to review:** построчное ревью 11 воркфлоу генерации: `wf-creatify-link`, `wf-creatify-submit`, `wf-creatify-webhook`, `wf-creatify-shorts`, `wf-creatify-text`, `wf-creatify-product`, `wf-creatify-poll`, `wf-creatify-asset`, `wf-creatify-adclone`, `wf-creatify-banner`, `wf-creatify-avatar`.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

**Контекст субагенту:** файлы `workflows/wf-creatify-*.json` в корне репо (рабочая копия = live 14.08). Чек-лист `references/workflow-review-checklist.md`; контракты и цены — `references/api-pricing-budget.md`, `references/expansion-13aug-api-contracts.md`, `references/cr3-asset-generator.md`, `references/cr5-ai-shorts.md`, `references/cr6-product-to-video.md`; прецедент находок — `docs/CODE-REVIEW-2026-08-13.md` (К3 wf-creatify-poll, К4 example.com). Сети нет, только чтение файлов репо.

- [ ] Каждый воркфлоу: webhook-контракт (путь, метод, вход), validate → Switch valid → mock/real (строковое сравнение `$env`), fallbackOutput, real-ветка на out[1]
- [ ] Платные вызовы: правильные пути эндпоинтов (сверка с api-endpoints.md), keypair-заголовки typeVersion 4.5, вложенный neverError, таймауты, списание отложенное — никогда не вызывать
- [ ] Валидация входов до списания (URL, длительности 15-300с, обязательные поля контракта), low_credits-гейты и пороги
- [ ] wf-creatify-webhook: идемпотентность по creatify_id, SELECT перед UPDATE, статусы done/failed/unknown, секрет колбэка (fail-open при незаданном env — ок?)
- [ ] wf-creatify-submit: контракт `{script_id, client_id, json_payload, link_id}` (сверка с INSERT-нодой), mock-UUID, UPDATE creatify_id
- [ ] Заглушки Фазы 1 (example.com, mock-тексты) в платных ветках — реальные списания при real-ключах
- [ ] wf-creatify-text: контракт, mock/real, подключение к боту/публикации (текстовые посты)
- [ ] Отчёт: таблица находок по каждому воркфлоу (severity, нода, влияние, доказательство), раздел «проверено и работает», вердикт по кластеру
