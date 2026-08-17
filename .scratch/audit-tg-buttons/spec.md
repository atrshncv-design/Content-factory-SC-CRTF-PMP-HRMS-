# Спека: аудит и починка Telegram-кнопок в wf-tg-bot.json

## Цель

Во всех пользовательских сценариях `wf-tg-bot.json` каждое исходящее сообщение бота (sendMessage / sendPhoto / sendVideo / sendDocument, но не `answerCallbackQuery`) должно содержать inline-клавиатуру с кнопками навигации **📋 Меню** (`cmd:menu`) и **🧹 Отмена** (`cmd:cancel`), за исключением явно перечисленных служебных сообщений.

## scope

- `workflows/wf-tg-bot.json` — единственный файл, который редактируется в рамках этого спринта.
- `wf-creatify-webhook.json` и `wf-tg-alerts.json` не затрагиваются (кроме пункта наблюдения в финальном отчёте).

## Найденные дефекты

### D1 — «Видео с аватаром»: кнопки не отображаются

Ноды:
- `TG avv ask avatar`
- `TG avv preview photo`
- `TG avv preview text`

Используют `inlineKeyboard = ={{ {rows: $json.rows} }}`. Генерирующие Code-ноды (`AVV Build preview`, `AVV Preview sel`) формируют `callback_data` как строки вида `={{ 'avv_sel:' + id }}`. В expression-клавиатуре вложенные `={{ }}` внутри строк ломают рендеринг: Telegram получает пустую или невалидную клавиатуру, поэтому кнопок нет.

Ожидаемое поведение:
- `TG avv ask avatar` показывает кнопки всех своих аватаров + стоковых creatify, плюс **Отмена** и **Меню**.
- `TG avv preview photo/text` показывают кнопки **✅ Этот**, **🔁 Другой**, **🧹 Отмена**, **📋 Меню**.

### D2 — Кнопки выбора длительности не работают

Ноды:
- `TG uv ask dur`
- `TG sh ask dur`
- `TG avv ask dur`
- `TG DR ask`
- `TG DR wrong`

Callback_data кнопок: `cmd:dur_30`, `cmd:dur_60`, `cmd:durc_30`, `cmd:durc_60`.

Parser не знает эти команды, поэтому нажатие падает в `command: 'unknown'` и уходит на fallback выход `Switch cmd` (output 0 = `start`).

Решение: заменить callback на `dur_30` / `dur_60` / `durc_30` / `durc_60` (без `cmd:`), добавить их обработку в `Switch cb`, и направить на существующую логику выбора длительности (или на Code-ноду, сохраняющую длительность в сессию/стейт).

### D3 — Пропущены кнопки навигации

Ноды без кнопки **📋 Меню**:
- `TG SH verify`
- `TG AU verify`
- `TG pfn`
- `TG pfn multi`
- `TG avv preview photo`
- `TG avv preview text`

Ноды без кнопки **🧹 Отмена**:
- `TG SH verify`
- `TG AU verify`
- `TG avv ask avatar`
- `TG avv preview photo`
- `TG avv preview text`
- `TG avv none`

Нужно добавить недостающие кнопки, сохранив существующие.

### D4 — `TG sh video` (sendVideo) не содержит replyMarkup

Сценарий shorts отправляет видео через `TG sh video`, а кнопки действий идут отдельным сообщением `TG sh buttons`. Пользователь согласовал «как удобно». Оставляем отдельным сообщением, но проверяем, что `TG sh buttons` приходит сразу после видео и содержит **📋 Меню**.

### D5 — Нет автоматической проверки

В `tests/test_wf_tg_bot.py` нет теста, который гарантирует наличие кнопок навигации у исходящих сообщений. Нужно добавить.

## Out of scope

- Платные вызовы creatify / scrapecreators — не проводятся.
- Редизайн текста сообщений.
- Изменение логики работы сценариев, не связанной с кнопками.

## Критерии приёмки

1. `TG avv ask avatar`, `TG avv preview photo`, `TG avv preview text` рендерят кнопки корректно.
2. Кнопки длительности обрабатываются и ведут в нужный сценарий.
3. Все исходящие сообщения (кроме исключений) имеют кнопки **📋 Меню** и **🧹 Отмена**.
4. `pytest tests/test_wf_tg_bot.py` проходит, включая новый тест на кнопки.
5. Перед правками сделан бэкап `workflows/` в `backups/<timestamp>/`.
6. После правок сделан `git diff --stat` и сохранён в отчёт.

## Исключения из правила «обязательны Меню + Отмена»

- `TG start` — только навигационные кнопки (Меню есть, Отмена не нужна).
- `TG cancel` — только Меню (сообщение само по себе — результат отмены).
- `TG ping` — только Меню.
- `TG status` — Меню есть, Отмена не нужна.
- `TG unknown` — только Меню.
- `TG sh video` — кнопки в отдельном `TG sh buttons`.
- Все `* answer` ноды (`CT answer`, `ET answer`, …) — это `answerCallbackQuery`, не исходящие сообщения.
