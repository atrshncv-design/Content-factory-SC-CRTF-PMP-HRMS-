# 01 — Ревью wf-tg-bot: UX-слой (меню, кнопки, esc, команды, тупики)

**What to review:** построчное ревью UX-слоя `workflows/wf-tg-bot.json` (404 ноды): Telegram-выходы, кнопки, меню, команды, тексты, состояния — на предмет сломанных интерактивов и несоответствия спеке 12 и UX-2.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

**Контекст субагенту:** файл `workflows/wf-tg-bot.json` в корне репо (рабочая копия = live 14.08, 404 ноды). Спеки: `specs/12-telegram-ux.md`, `specs/13-n8n-orchestrator-architecture.md`; чек-лист `references/workflow-review-checklist.md` (в скилле content-factory-development); прецедент находок — `docs/CODE-REVIEW-2026-08-13.md` и `references/tg-bot-ux-audit.md`. Инструменты: `scripts/extract-tg-ux-map.py`, `scripts/lint-workflow-json.py`. Сети нет, только чтение файлов репо.

- [ ] Инвентарь всех Telegram-нод (sendMessage/answerQuery) и их callback_data — найти literal `{{ }}` без `=` (сломанные кнопки), кнопки без веток ([NOROUTE]), callback_data не совпадающий с правилами Switch cb
- [ ] Все TG-тексты: esc()-покрытие (Markdown-экранирование `_*[]\``) в Format/Code-нодах, статичные тексты с `_` без esc, двойное экранирование
- [ ] Меню: 2 уровня (Генерация/Аналитика/Публикация/Система/Инструкция), кнопка «📋 Меню» на каждом экране, тупики (сообщение без кнопок и без выхода)
- [ ] Команды: 31 TG-команда (tg-commands-31.json) ↔ правила Switch cmd 1:1, слеш-формы в парсере, help-текст vs фактические команды
- [ ] Состояния QUICK_* (URL→видео, AI Shorts): переходы, ввод ожидающих ответов, отмена
- [ ] Отчёт: таблица находок (severity 🔴/🟡/🟢, файл+нода, влияние, доказательство), отдельный раздел «проверено и работает», вердикт по UX-слою
