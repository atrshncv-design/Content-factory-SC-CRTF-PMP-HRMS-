# CONTEXT — Контент-завод (content factory)

Фабрика коротких вертикальных видео под ключ: аналитика трендов → тема → сценарий → генерация (creatify) → публикация (postmypost). Демо-клиент: Robotec (robotec.ru).

## Глоссарий

- **Клиент** — компания-заказчик контент-завода (не человек). Хранится в `clients` (id, name, domain, industry, niche, audience_json, tone, profile_json, confidence, status, created_at, onboarded_by).
- **Профиль клиента** — совокупность контекстных данных клиента: название, ниша, описание, ЦА, ссылки на ресурсы компании, документы (извлечённый текст), тон, референсы/конкуренты. Питает промпты генерации (analyst/scriptwriter/json-builder через hermes-bridge).
- **Активный профиль** — профиль, контекст которого используется для генерации. Резолвится per-чат: `users.active_client_id` (приоритет) → `settings.active_client_id` (legacy fallback) → отсутствует (гейт).
- **Оператор** — пользователь бота с доступом ко всему контент-заводу (роль `admin` = владелец, `operator` = назначенный). Таблица `users` (tg_user_id, username, role, created_at, active_client_id).
- **Сессия** — state machine по tg_user_id: `sessions` (tg_user_id, state, topic_id, script_id, generation_id, selected_platforms, post_at, updated_at, quick_payload, profile_draft). Состояния: IDLE, CYCLE_* (цикл), QUICK_* (быстрые сценарии), PROFILE_AWAIT / PROFILE_DOCS_SUBMITTING (интервью профиля), ONBOARDING_PENDING.
- **Цикл** — полный конвейер: аналитика (wf-analytics + analyst) → тема → сценарий (scriptwriter) → генерация (creatify) → публикация (postmypost). Режимы: `manual` (подтверждения), `auto` (полный автомат).
- **Быстрые сценарии** — URL→видео (url2video), AI Shorts (shorts), текст-пост (text_post). Состояния QUICK_*, payload в `sessions.quick_payload`.
- **Поколение** (generation) — задача генерации видео в creatify: `generations` (client_id, script_id, creatify_id, link_id, request_payload, status, video_output_url, …).
- **Hermes-bridge** — HTTP-обёртка над Hermes CLI на хосте (порт 8642, токен X-BRIDGE-TOKEN): `/ask` (скиллы analyst/scriptwriter/json-builder/onboarding/caption-adapter) и `/doc-text` (извлечение текста из документа по file_id Telegram).
- **db-bridge** — HTTP-мост к SQLite factory.db из n8n-контейнера (SELECT/INSERT/UPDATE/DELETE; DDL запрещён — таблицы/колонки создаются напрямую через sqlite3 на сервере).

## Ключевые инварианты

- TG-приёмник — n8n Telegram Trigger (wf-tg-bot, ~533 ноды), state machine в `sessions`, inline-кнопки.
- LLM-движок — Hermes через hermes-bridge; n8n не вызывает платные API без кредитных гейтов.
- Промпты генерации обязаны использовать контекст **активного профиля** (per-чат), не хардкод.
- Платные вызовы (creatify/scrapecreators) — только после явного согласования пользователя.
- Секреты — только имена переменных в коде; значения в `.env` на сервере.

## Связанные документы

- Спеки: `specs/00-architecture.md` … `specs/13-n8n-orchestrator-architecture.md` (13 суперседит 06/11 в части TG)
- `docs/adr/0001-per-chat-client-profiles.md` — решение по профилям (см. ADR)
- `DEPLOYMENT.md` — состояние деплоя; `PROGRESS.md` — волны фиксов и фич
