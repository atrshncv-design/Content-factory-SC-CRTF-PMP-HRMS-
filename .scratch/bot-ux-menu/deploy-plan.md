# План деплоя UX-реворка (Ран 2) — оркестратор, выполняется ТОЛЬКО с явного согласия пользователя

## Шаги (порядок)

1. **DDL** (на сервере, db-bridge DDL не выполняет — напрямую sqlite):
   ```bash
   ssh -i ~/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem ubuntu@83.166.233.95 \
     "sqlite3 ~/factory/data/factory.db 'ALTER TABLE sessions ADD COLUMN quick_payload TEXT;'"
   # проверить: sqlite3 ~/factory/data/factory.db '.schema sessions' | grep quick_payload
   ```
   ПЕРЕД DDL: сверить live-схему (`sqlite3 ~/factory/data/factory.db '.schema sessions'`) — колонок может быть больше/меньше, чем в наших предположениях.

2. **Применение воркфлоу** (паттерн apply_fix.sh, скрипт в скилле content-factory-development):
   - `scripts/apply_fix.sh wf-tg-bot .scratch/bot-ux-menu/fixes/wf-tg-bot.json` (scp сначала на сервер в ~/factory/fixes/)
   - `scripts/apply_fix.sh wf-creatify-webhook .scratch/bot-ux-menu/fixes/wf-creatify-webhook.json`
   - `scripts/apply_fix.sh wf-creatify-shorts .scratch/bot-ux-menu/fixes/wf-creatify-shorts.json`
   - Проверка после каждого: active=1, число нод (в ответе скрипта), webhook-маршрут жив (probe tg-trigger → 403).

3. **Регистрация команд**: tg-commands-31.json (31 команда) → заменить tg-commands-25.json на сервере, запустить register-tg-commands.sh (getMyCommands → 31, missing=[]).

4. **Live-тесты (0 кредитов)** — оператор в TG:
   - /start (новый текст + кнопки), меню, разделы, инструкция, статус (балансы живые), бюджет (оба баланса), темы, конкуренты, ping, отмена, unknown.
   - Валидация URL: в сценарии URL→видео вставить невалидную строку → сообщение-ошибка (бесплатно, до любых вызовов).

5. **Платные live-тесты — ТОЛЬКО с согласия пользователя** (зафиксировать остаток creatify до/после):
   - URL→видео 30 сек: 1 кред (link) + 5 кред (видео) = 6 кред
   - AI Shorts: bridge бесплатно + ~5 кред (ai_shorts 30 сек)

6. **Синхронизация репо**: скопировать финальные версии в `workflows/` (канонический экспорт REST-снимка), обновить DEPLOYMENT.md (раздел 27), tg-commands-31.json в репо, PROGRESS.md.

7. **Коммит волны** — по «ок» пользователя (рабочий репозиторий, ветка main).

## Риски
- apply_fix.sh требует python3 на сервере? Нет — всё в node внутри контейнера (node:sqlite). Скрипт сам.
- wf-tg-bot → 350+ нод: UPDATE больших JSON — ок (проверено на 278).
- Параллельные генерации: пользователь один, whitelist один.
- Анти-DDoS VK: при «Connection closed/banner exchange» — ждать 20–30 мин, НЕ плодить попытки.
