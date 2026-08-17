# Interfaces — avatar-carousel

## Правила проекта (выводятся из AGENTS.md/DEPLOYMENT.md, субагент не может их вывести сам)

- Стек: n8n 2.34.4 (Docker, сервер `ssh factory`, алиас `83.166.233.95`), SQLite factory.db через db-bridge, репо — источник для деплоя, сервер — источник правды.
- Тесты: `python3 -m pytest tests/ -q` (локально, 0 кредитов). Изменения воркфлоу валидны только с зелёным suite.
- Telegram-ноды: typeVersion **1.2**; switch-ноды **v3.4**; `neverError` — вложенный `options.response.response.neverError`; HTTP-ноды — typeVersion 4.x, платные вызовы (creatify/scrapecreators) — **запрещены** в этом прогоне (GET /api/personas/ — бесплатный, разрешён).
- Секреты — ТОЛЬКО имена переменных в `$env.<NAME>` (значения в `~/factory/.env` на сервере, никогда в коде/коммитах). TG-токен: `$env.TELEGRAM_BOT_TOKEN`.
- TG-тексты: экранирование Markdown (`esc()`), статические тексты без `_`; callback_data только как `={{ expr }}`.
- Форма n8n-клавиатуры: `{rows: [{row: {buttons: [{text, additionalFields: {callback_data}}]}]}]}` (как в `TG start`). Форма Telegram Bot API (editMessageMedia): `reply_markup.inline_keyboard = [[{text, callback_data}]]`.
- Рабочее дерево: правки `workflows/wf-tg-bot.json` — только с бэкапом `workflows/` в `backups/<timestamp>/` перед правкой.
- Отсутствующая зависимость/данные = `BLOCKED` в ответе, НЕ установка пакетов и НЕ выдумка данных.

## Границы, решённые в спецификации

| Модуль | Владеет | Выставляет | Прячет |
|---|---|---|---|
| `AVV_STOCKS` константа | список 20 (id/имя/пол/возраст/ниша/фото) | массив в jsCode Code-нод | источник (API-вытяжка), порядок чередования |
| `AVV Carousel build` (Code) | сборка payload карусели | `{photo, caption, index, kbN8n, kbApi}` по входному index | форматирование подписи, экранирование |
| `AVV Carousel edit` (HTTP) | editMessageMedia | — | neverError, тело Telegram API |
| `TG avv carousel` (Telegram) | первое сообщение карусели | sendPhoto + inlineKeyboard | — |
| Роутер `Switch cb` | маршрутизация callback | выходы avv_next, avv_sel, avv_my_avatars | — |
| Тест-шов (единственный) | `pytest tests/` | структурные проверки wf JSON + исполнение jsCode | — |

Контракт данных карусели ( Consumed тикетом 02, produced тикетом 01):
`avatars-20.json`: массив 20 объектов `{id: UUID, name, gender: 'm'|'f', age_label, niche, img}` в порядке показа: чередование m/f, элемент [0] — мужчина.

## Из таска 03 — аудит маршрутизации + alerts

- `tests/test_tg_callback_routing.py` — таблица «префикс → обработчик» (~80 семейств): ROUTED (все маршрутизируются), TASK2_PENDING (avv_next/avv_select/avv_my_avatars — sentinel/xfail до таска 02), EXTERNAL_UNROUTED (пуст), KNOWN_BROKEN_NODES (5 мёртвых кнопок — чинит таск 02, новые вне списка = красный тест), ALERTS_MENU_EXCEPTIONS (пуст).
- wf-tg-alerts.json: исходящие несут «📋 Меню» (cmd:menu); alerts-бот = ТОТ ЖЕ токен, вебхук → tg-trigger, callback обрабатывается Switch cmd (паттерн vd_* из wf-creatify-webhook).
- Мёртвые кнопки (зона 02): TG avv ask topic, TG AVV verify, TG avv ok — литералы `'={{ \"cmd:cancel\" }}'` с лже-слешем (незакрытая JS-строка).
- Вне зоны: wf-creatify-webhook «Telegram stage3 auto» — sendVideo без клавиатуры (проверит таск 02).
- Мутационная проверка: мёртвая кнопка / потеря правила → тест красный.

## Из таска 01 — данные аватаров

- `avatars-20.json` — финальные 20 (10М+10Ж, чередование, [0]=М Sam); все id из дампа, фото CDN проверены (HEAD 200). Возраст — оценка «≈NN» (в API полей возраста нет, только adult/senior).
- `personas-raw.json` — полный дамп стоковых персон (822: 788 realistic + 34 styled), для будущих переборов; секретов нет.
- Новые 5 против прошлой подборки: Carter/Thomas/Peter (М), Celeste/Leonora (Ж); все прежние 15 сохранены.
- Список на сверке с пользователем (avatars-20.md); до «ок» пользователя тикет 02 не впаяет данные.

