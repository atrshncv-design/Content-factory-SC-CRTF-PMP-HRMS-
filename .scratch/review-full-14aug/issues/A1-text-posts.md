# A1 — Блокер п.3: сценарий текстовых постов (Threads/X/VK и т.п.)

**What to build:** текстовые посты из бота: оператор вводит текст → выбирает платформы → публикация в Threads/X/VK/telegram и др. БЕЗ видео; плюс починка маршрутизации wf-publish (сейчас text-only невозможен).

**Blocked by:** None — can start immediately (база = live-экспорт `.scratch/review-full-14aug/base/`)

**Status:** ready-for-agent

**Контекст:** фикс-волна по `docs/CODE-REVIEW-2026-08-14.md` (§4 п.3, R3, Y8). Ревью подтвердило ДВОЙНОЙ блокер:
1. В wf-tg-bot (404 нод) нет ни одной текстовой команды (33 правила Switch cmd).
2. `wf-publish` (26 нод) физически не может опубликовать text-only: `Switch upload needed` перевёрнут — `out[0]=skip` ТОЛЬКО при НЕПУСТЫХ `file_ids`; пустой `file_ids` (текст) → out[1] → `HTTP real upload` POST `/v4.1/upload/init` с несуществующим URL `$env.WEBHOOK_URL + 'media/' + generation_id + '.mp4'` → 422 → execution умирает ДО `Code build details` → Respond не срабатывает.
3. `wf-creatify-text` (генератор сценариев за 1 кред, webhook `factory/script`) НЕ подключён к боту (0 вхождений).

**Рабочие файлы (только база, НЕ репо workflows/!):**
- `.scratch/review-full-14aug/base/wf-tg-bot.json` (404 нод, live 14.08)
- `.scratch/review-full-14aug/base/wf-publish.json` (26 нод, live 14.08)
- `.scratch/review-full-14aug/base/wf-creatify-text.json` (17 нод, live 14.08)
- Справочники: `references/wf-publish-all-platforms.md` (маппинг details[] по 18 платформам, threads/x/vk — только content), `references/ux2-menu-quick-scenarios.md` (паттерн веток QUICK_*), скрипты валидации в `/Users/aleksandrtrisenkov/.hermes/skills/software-development/content-factory-development/scripts/`.

- [ ] **Фикс 1 — wf-publish: маршрутизация text-only.** В `Switch upload needed`: пустые file_ids → ТЕКСТОВАЯ ветка (мимо upload/init, прямо в `Code build details` → `HTTP real publication`). Условие должно быть: `file_ids.length > 0` → upload-ветка, иначе → текстовая (без upload). Проверить, что details[] для threads/x/vk/telegram/discord/bluesky/mastodon собираются чисто текстовыми (content, publication_type=1, без file_ids) — это уже есть в `Code build details`.
- [ ] **Фикс 2 — wf-tg-bot: команда текстового поста.** Новая команда (например `text_post` / «текстовый пост» / «пост») в Parser + Switch cmd (правило + ветка) + интерактив по паттерну QUICK_*: запрос текста → `QUICK_TEXT_AWAIT` → ввод текста → выбор платформ (кнопки toggle как в stage4) → подтверждение → вызов wf-publish с `{platforms, content: <текст>, captions: {}, post_at, generation_id: null, file_ids: []}`. Состояния в sessions (quick_payload). esc()-экранирование ВСЕХ новых TG-текстов. Кнопка «📋 Меню» на всех новых экранах.
- [ ] **Фикс 3 (опционально, если влезает) — wf-creatify-text к боту** ИЛИ пометка legacy: решить судьбу генератора сценариев — либо подключить (команда «сценарий» → ai_scripts 1 кред → INSERT scripts с привязкой к сессии), либо не трогать (текстовые посты идут бесплатно через hermes-bridge scriptwriter). Если подключение требует >1 тикета — оставить на потом, зафиксировать решение.
- [ ] Валидация: `validate-workflow-json.py` 0 issues, BFS все ноды, `lint-workflow-json.py` 0 находок, node --check всех jsCode, sim-прогон новых Code-нод.
- [ ] Отчёт: write_file в `.scratch/review-full-14aug/fixes/A1-text-posts.md` — что изменено (ноды/ветки/контракты), как проверить, остатки.
