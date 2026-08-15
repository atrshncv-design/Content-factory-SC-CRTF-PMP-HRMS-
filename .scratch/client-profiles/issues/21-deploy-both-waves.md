# 21 — Деплой волн 1+2 (гейт пользователя)

**What to build:** Полный деплой на сервер 83.166.233.95 обеих волн: миграции v1+v2, установка pypdf/python-docx (согласие), hermes-bridge с /doc-text и /img-text, wf-tg-bot (719+ нод волны 2), 35 команд, live-тесты 0-кредитов (включая реальный документ и фото в TG по согласованию), синк репо + коммит. **Деплой — гейт: только после явного «ок» пользователя.**

**Blocked by:** 12 (волна 1), 20 (волна 2), 14 (bridge), 13 (миграция v2)

**Status:** ready-for-agent (фактический запуск — после согласия пользователя)

- [ ] Согласие пользователя: деплой волн 1+2; установка pypdf/python-docx в venv; живой тест документа и фото в TG
- [ ] Бэкап factory.db → миграция v1 (migrate-client-profiles.py) → миграция v2 (publish_platforms + profile_questions)
- [ ] hermes-bridge: server.py с /doc-text и /img-text → рестарт hermes-bridge → /health + smoke
- [ ] apply_fix волны: wf-tg-bot (финальная версия волны 2) + docker restart + активность + probe 403
- [ ] register-tg-commands-35.sh → getMyCommands=35
- [ ] Live-тесты 0-кредитов: доступ (owner/fake), карточка, интервью + возобновление, переключение, удаление профиля (мягкое), удаление оператора, гейт, вопросы (list/set/reset), платформы профиля, документ (реальный файл), фото (OCR — проверка, что Hermes-зрение реально возвращает текст), контекст в промптах (execution_data без платных вызовов)
- [ ] Синк репо: workflows/wf-tg-bot.json ← финальный fixes/, hermes-bridge/server.py, tg-commands-35.json, register-скрипт; секрет-скан; git commit волн (после «ок»)
- [ ] PROGRESS.md финал + отчёт

Примечания: 0 платных вызовов; OCR-результат проверять фактом (маркерный контракт), не выдумывать текст; pitfall-ы деплоя (typeVersion, probe 403/404/500, прямой UPDATE обеих таблиц + docker restart).
