# 16 — Верификация + деплой (3 формата, строгие 30/60)

**Спека:** spec-3formats.md
**Blocked by:** 11, 12, 13, 14, 15
**Status:** ready-for-agent

## Что сделать

1. Локально: JSON всех воркфлоу валиден; validate_workflow.py 0 issues по wf-tg-bot, wf-creatify-shorts, wf-creatify-lipsync, wf-creatify-poll; pytest 25/25.
2. Бесплатные проверки (0 кредитов): script_only factory/shorts (30 и 60 сек → обрезка под cap), lipsync-воркфлоу mock/validate, команды asset/product/banner → «отключено».
3. Деплой (после «ок» пользователя): rsync воркфлоу → import + реактивация (урок: import деактивирует!), деактивация 5 премиум-воркфлоу, регистрация команд (без asset/product/banner), рестарт, smoke (webhook pending=0, активные воркфлоу).
4. PROGRESS.md + коммит.

## Критерии приёмки

- На сервере активны: wf-tg-bot, wf-creatify-shorts/link/submit/webhook/poll/lipsync (+ SC/аналитика/публикация); НЕ активны: asset/product/banner/adclone/text.
- Команды: без asset/product/banner.
- Меню: URL→видео, AI Shorts, Видео с аватаром, Запустить цикл.
- Платный smoke-прогон — за пользователем (3 формата по 5 кред/30с).
