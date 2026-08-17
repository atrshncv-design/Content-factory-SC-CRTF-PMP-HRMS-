# 01 — Автотест покрытия кнопок

Blocked by: none
Status: ready-for-agent

## Что сделать

Добавить в `tests/test_wf_tg_bot.py` тест, который для каждой Telegram-ноды `wf-tg-bot.json` с `operation != answerCallbackQuery` проверяет:

1. `replyMarkup == "inlineKeyboard"`.
2. В клавиатуре есть кнопка с `callback_data`, содержащим `cmd:menu`.
3. В клавиатуре есть кнопка с `callback_data`, содержащим `cmd:cancel`, кроме явно перечисленных исключений.

Исключения (ноды, где кнопка Отмена не нужна):
- `TG start`
- `TG cancel`
- `TG ping`
- `TG status`
- `TG unknown`

Исключения полностью (нет replyMarkup):
- все `* answer` ноды (`CT answer`, `ET answer`, `RT answer`, `AS answer`, `ES answer`, `RS answer`, `PG answer`, `RG answer`, `JG answer`, `TP answer`, `SCH answer`, `CP answer`, `CB answer unknown`, `TX answer`, `TX answer pub`, `PSW answer`, `PX answer`, `PFS answer`, `PFN answer`, `PFE answer`, `PFL answer`, `PFD answer`, `PFN cb answer`, `PDL answer`, `PDY answer`, `PDN answer`, `RO answer`, `RON answer`, `PFN answer resume`, `PFN answer restart`, `PPM answer`, `PPM answer ok`, `SC OK answer`, `SC RG answer`, `SC ED answer`, `VD OK answer`, `VD RG answer`, `VD RJ answer`)

## Критерий приёмки

- Тест падает на текущей версии `workflows/wf-tg-bot.json`, показывая список нарушений.
- После выполнения остальных тикетов тест проходит.
- `pytest tests/test_wf_tg_bot.py` запускается без ошибок.
