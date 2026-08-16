# Тикет 17: Стоковые аватары creatify + фикс persona_id в выборе аватара

Spec: `.autopilot/release-readiness/spec-stock-avatars.md`
Статус: done (16.08, локально; деплой — после «ок» пользователя)

## Что сделать (3 правки в ветке AVV wf-tg-bot.json)

### 1. Фикс бага: кнопки своих аватаров несут persona_id (UUID), не локальный id
Сейчас `AVV Ask avatar` строит кнопки `avv_sel:<r.id>` (локальный id custom_avatars),
а lipsync-валидатор требует UUID персоны → выбор своего аватара даёт
`{"ok":false,"error":"creator — невалидный UUID персоны"}`.
- `AVV Build avatars`: SELECT уже возвращает `persona_id` — без изменений.
- `AVV Ask avatar`: кнопка `callback_data: 'avv_sel:' + String(r.persona_id)` (НЕ r.id).
- `AVV Save avatar`: `avatar_id` = UUID из кнопки (уже так — entity_type), без изменений.
- Проверка: `AVV Build submit` → `creator: r.avatar_id` = UUID → lipsync-валидатор проходит.

### 2. Стоковые аватары: 15 кураторских id (8 ж + 7 м), после своих
Константа в `AVV Ask avatar`:
```js
const STOCKS = [
  {id: '009f502d-3649-4624-a438-80b126f1fa30', name: 'Camila'},
  {id: '018a97ef-4fba-4a34-8097-5e60e6e36ffe', name: 'Chloé'},
  {id: '285923a8-25b1-4ad1-a5ea-40ad8cbcaf9d', name: 'Bianca'},
  {id: '745fef08-8eee-4e3b-873d-c39b9791c4cd', name: 'Sylvia'},
  {id: '74686a1c-040c-4783-a2e2-a54367fbf998', name: 'Olivia'},
  {id: 'e40f0f2f-c280-4a35-af40-54ffaee3c67b', name: 'Priya'},
  {id: 'fb40e95f-c907-45f9-a0ef-2d2ab981aa00', name: 'Carmen'},
  {id: '6fdf53cb-ac28-4487-96d2-3eae073ece26', name: 'Lily'},
  {id: '0251876f-0da4-4c61-8320-8955d8be1f98', name: 'Diego'},
  {id: '0587591d-54cc-4d8d-867d-cc82de168f61', name: 'Sam'},
  {id: '5a711072-4cef-49de-b82c-282e4f1e5a7d', name: 'Leo'},
  {id: '85ff68b3-2a6f-4e5c-9534-db0fbc18fdb9', name: 'Quentin'},
  {id: 'bf384605-a98d-4bad-828a-f3fd8825f5f6', name: 'Santiago'},
  {id: 'f8b1e966-f8df-4441-b426-66c0e61fb6cf', name: 'Kaito'},
  {id: '7b9482cd-7717-4202-9fc0-69b9c635b785', name: 'Aryan'},
];
```
- Свои (approved) — первыми (как сейчас), затем разделитель
  «🎭 Стоковые аватары creatify:» и 15 кнопок стоковых.
- Если своих нет — НЕ показывать «Сначала создай аватар», а сразу стоковых.
- `mode` ответа: 'list' (кнопки), при необходимости 'preview' + 'list' двумя сообщениями.

### 3. Превью-фото стоковых перед кнопками
Перед кнопками — фото стоковых (`preview_image_9_16`, прямые URL CDN, бесплатно).
- Механика: отправка фото отдельным сообщением (sendPhoto, URL) — до 10 фото,
  затем сообщение с кнопками. Telegram-ноды n8n: photo = URL в параметре (уточнить
  схему sendPhoto-ноды в сборке; если mediaGroup недоступен — по одному sendPhoto).
- Реализация: 2 сообщения-фото (по 8 и 7, первое с подписью «Вот стоковые аватары —
  выбери по имени в меню ниже») + сообщение с кнопками выбора (свои + стоковые).
- Превью ТОЛЬКО для стоковых (свои без фото — их и так видно в my_avatars).

## 🔥 Найден корень «бот не реагирует» (16.08, post-deploy)
- **Причина**: callback_data кнопок имел ДВОЙНОЙ бэкслеш перед кавычками —
  `={{ \\"cmd:avatar_video\\" }}` вместо рабочего `={{ "cmd:avatar_video" }}`.
  n8n `Expression.renderExpression` → `invalid syntax` → нода падает молча.
- **Пострадало**: TG start / TG menu gen / TG gen rejected / TG published (кнопка
  аватара, добавлена в этом тикете) + **10 кнопок AVV-ветки из тикета 15**
  (TG avv none / TG avv ask topic / TG avv ask dur / TG AVV verify / TG avv ok) —
  поэтому «Видео с аватаром» в меню молча не работало (жалоба «команд нет в меню»).
- **Фикс**: fix-all-callback-backslash.py — убраны бэкслеши во всех 14 кнопках;
  контрольный скрипт: 0 битых (92 на позиции 4), валидаторы 0 issues, pytest 25/25.
- **ПИТФОЛЛ**: транспорт write_file/patch может удваивать бэкслеши в jsCode/JSON —
  проверять ордами callback_data после записи (`cb[4] == 34`, не 92).

## Проверки (обязательно)
1. `python3 -c "import json; json.load(open('workflows/wf-tg-bot.json'))"` — валиден.
2. `python3 .scratch/bot-ux-menu/validate_workflow.py workflows/wf-tg-bot.json` — 0 issues.
3. Греп: кнопки своих несут `persona_id`, НЕ `r.id` (в AVV Ask avatar).
4. Платных вызовов в фиче нет (превью = URL CDN, стоковые id захардкожены).

## Вне скоупа
- Пагинация/фильтры/поиск по 514 стоковым; динамическая подгрузка из API;
- BYOA-персоны в общем списке; модерация; правки wf-creatify-lipsync.json.
