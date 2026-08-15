# ADR-0001: Per-chat client profiles (профили клиентов)

- Status: accepted (14.08.2026, интервью autopilot «профиль клиента»)
- Applies to: wf-tg-bot, hermes-bridge, factory.db (live), промпты генерации

## Context

Бот управляет контентом клиентов (компаний-заказчиков). До сих пор «текущий клиент» был глобальным (`settings.active_client_id`) и **контекст клиента хардкодился в промптах генерации** («Клиент: Robotec (промышленная робототехника, интегратор KUKA…)» в SC/CT/ET/AU Build bridge prompt). При нескольких клиентах/операторах это смешивает контексты. Требуется: интервью-профиль (8 вопросов), приём ссылок/текста/документов, переключение профилей в том же чате, доступ назначенных операторов.

## Decisions

1. **Активный профиль — per-чат.** `users.active_client_id INTEGER NULL` — приоритетный источник; `settings.active_client_id` остаётся legacy-fallback (и обновляется для совместимости старых чтений). Резолв: `users.active_client_id ?? settings.active_client_id ?? отсутствует (гейт)`.
2. **Контекст профиля — колонки `clients`.** `description TEXT` (что делает компания), `context_links TEXT` (JSON-массив ссылок), `context_docs TEXT` (JSON-массив `{name, mime, text, chars}`), `context_refs TEXT` (JSON-массив референсов/конкурентов). ЦА — в существующую `audience_json` как `{"raw": "<свободный текст>"}`.
3. **Документы — через hermes-bridge `/doc-text`.** n8n отдаёт `file_id`/`file_name` из `message.document`; bridge скачивает файл из Telegram (getFile + file/bot<token>/<path>), извлекает текст (txt — raw; pdf — pypdf; docx — python-docx; установка пакетов в venv — с согласия пользователя на деплое), возвращает `{name, mime, text, chars}` (текст обрезан до 30k; при `digest=true` — LLM-дайджест ~800 символов маркерным контрактом `<TEXT>`, fallback — обрезка до 2000).
4. **Доступ — таблица `users`.** Роли `admin` (владелец) и `operator` (назначенный). Whitelist бота проверяет `users` по tg_user_id (вместо хардкода `TG = 941296693`); владелец назначает операторов командой «добавить оператора <tg_id>». Владелец сидируется в DDL.
5. **Интервью — state machine в `sessions`.** Новые состояния `PROFILE_AWAIT` (шаг в `sessions.profile_draft` JSON `{mode: new|edit, client_id?, step, answers{...}, links[], docs[]}`) и `PROFILE_DOCS_SUBMITTING` (асинхронная обработка документа). 8 фиксированных вопросов, каждый пропускаемый кнопкой «Пропустить»; шаги ссылок/документов — мультизначные с кнопкой «Готово». Черновик живёт в `sessions.profile_draft TEXT`.
6. **Гейт.** Все входы генерации (start_cycle, url2video, shorts, text_post, asset, product, banner) без активного профиля → сообщение «нет активного профиля» + кнопка «Профиль».
7. **Промпты генерации** строят блок контекста из строки активного клиента (name/niche/description/audience/tone/links ≤5/docs-дайджест ≤2000 симв.) — единый паттерн CTX Build/Format в каждой ветке (SC/CT/ET/AU).

## Consequences

- Механическая замена чтений `settings.active_client_id` (~11 Build-нод) на per-chat резолв — тикет «широкого» изменения.
- OB (onboarding по URL) остаётся быстрым путём создания клиента; пишет и per-chat active.
- Битый `settings.active_client_id` (live: 999 при отсутствующем клиенте) — резолв падает на fallback (первый active-клиент или гейт).
- Документы/ссылки не шифруются; размер текста ограничен (30k на документ).
