# 04 — Добавить недостающие кнопки Меню/Отмена

Blocked by: 01-button-coverage-test
Status: done

## Что сделать

Добавить в статические inline-клавиатуры недостающие кнопки:

### Добавить «📋 Меню»

- `TG SH verify`
- `TG AU verify`
- `TG pfn`
- `TG pfn multi`
- `TG avv preview photo` (после тикета 02)
- `TG avv preview text` (после тикета 02)

### Добавить «🧹 Отмена»

- `TG SH verify`
- `TG AU verify`
- `TG avv ask avatar` (после тикета 02)
- `TG avv preview photo` (после тикета 02)
- `TG avv preview text` (после тикета 02)
- `TG avv none`

### Особые случаи

- `TG sh video` — не добавлять replyMarkup (кнопки остаются в `TG sh buttons`).
- `TG pfn multi` — сохранить существующие кнопки «Пропустить», «Готово», «Отмена»; добавить «Меню».

## Критерий приёмки

- Автотест из тикета 01 проходит.
- Все перечисленные ноды имеют и кнопку Меню, и кнопку Отмена (кроме исключений из теста).
