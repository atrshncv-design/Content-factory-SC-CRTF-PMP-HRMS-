# 12 — Деплой волны на сервер (гейт пользователя)

**What to build:** Полный деплой фичи на сервер 83.166.233.95: миграция БД, установка библиотек извлечения текста (с согласия пользователя), применение воркфлоу, регистрация команд, live-тесты 0-кредитов. **Деплой — гейт: запускается только после явного «ок» пользователя.**

**Blocked by:** 01, 02, 11 (все тикеты волны)

**Status:** ready-for-agent (фактический запуск — после согласия пользователя на деплой)

- [ ] Согласие пользователя на: (а) деплой волны, (б) установку pypdf/python-docx в ~/hermes-agent/.venv на сервере (правило autopilot: пакеты — только с разрешения)
- [ ] Применение миграции 01 (dry-run → apply; бэкап factory.db перед DDL)
- [ ] Деплой hermes-bridge server.py + рестарт hermes-bridge (systemd) + проверка /health и /doc-text (локальный smoke)
- [ ] apply_fix.sh для каждого изменённого воркфлоу (база — финальные fixes/ из тикетов 03–10) + docker restart + проверка active/числа нод
- [ ] register-tg-commands-35.sh → getMyCommands=35 (или сколько получилось)
- [ ] Live-тесты 0-кредитов: webhook-probe (fake from.id → тишина; owner → проходит; оператор → проходит после add_operator), sqlite-проверки (users.active_client_id, clients контекст, sessions.profile_draft), карточка профиля, интервью с пропусками, переключение, гейт без профиля, документ (реальный TG-файл — с согласия пользователя), контекст в промптах (проверка по execution_data, без платных вызовов)
- [ ] Отчёт о деплое + PROGRESS.md

Примечания: никаких платных вызовов (creatify/scrapecreators) в live-тестах. Питфоллы деплоя: typeVersion новых нод (telegram 1.2 / switch 3.4 — v2.2 не существует), probe 403=жив/404=нет/500=execution упал, прямой UPDATE обеих таблиц workflow (entity + history[activeVersionId]) + docker restart.
