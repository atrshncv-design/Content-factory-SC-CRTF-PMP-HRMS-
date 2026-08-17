# 05 — Бэкап, валидация и отчёт

Blocked by: 02-avv-expression-keyboard, 03-duration-buttons, 04-missing-menu-cancel
Status: done

## Что сделать

1. Перед любыми правками сделать бэкап директории `workflows/` в `backups/<timestamp>/`.
2. После правок запустить:
   - `python3 -m pytest tests/test_wf_tg_bot.py -v`
   - `git diff --stat`
3. Проверить, что `wf-tg-bot.json` валиден (загружается JSON, нет дублирующихся имён нод).
4. Сформировать финальный отчёт:
   - список изменённых нод
   - список найденных и исправленных проблем
   - команды для запуска тестов
   - путь к бэкапу

## Критерий приёмки

- Все тесты проходят.
- `git diff --stat` показывает только ожидаемые изменения в `workflows/wf-tg-bot.json` и `tests/test_wf_tg_bot.py`.
- Бэкап сохранён и его путь указан в отчёте.
