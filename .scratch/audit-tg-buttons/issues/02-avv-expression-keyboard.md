# 02 — Починить expression-клавиатуры в сценарии «Видео с аватаром»

Blocked by: 01-button-coverage-test
Status: ready-for-agent

## Что сделать

Исправить Code-ноды `AVV Build preview` и `AVV Preview sel` в `workflows/wf-tg-bot.json`.

Проблема: они формируют `callback_data` как строки вида `={{ 'prefix:value' }}`. Когда весь `inlineKeyboard` передаётся через expression `={{ {rows: $json.rows} }}`, вложенные `={{ }}` внутри строк ломают рендеринг клавиатуры.

### AVV Build preview

Генерирует список аватаров для `TG avv ask avatar`.

- `btnsOwn` и `btnsStock`: `callback_data` должен быть простой строкой `'avv_sel:' + persona_id`, без обёртки `={{ }}`.
- Добавить в `rows` кнопки **🧹 Отмена** (`cmd:cancel`) и **📋 Меню** (`cmd:menu`) — в отдельном ряду.

### AVV Preview sel

Генерирует кнопки для `TG avv preview photo` и `TG avv preview text`.

- `okCb` должен быть строкой `'avv_ok:' + avatarId`.
- `againCb` должен быть строкой `'avv_again'`.
- Кнопки **🧹 Отмена** и **📋 Меню** уже есть в `rows`, проверить что они остаются.

## Критерий приёмки

- `TG avv ask avatar` получает `rows` с корректными callback_data и кнопками Отмена/Меню.
- `TG avv preview photo` и `TG avv preview text` получают `rows` с корректными callback_data.
- Автотест из тикета 01 проходит после выполнения всех тикетов.
