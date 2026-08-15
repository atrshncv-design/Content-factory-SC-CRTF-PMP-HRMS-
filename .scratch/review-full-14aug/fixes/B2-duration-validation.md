# B2 — Валидация длительности 15–300с (R2) в wf-tg-bot.json

Дата: 2026-08-14 · База: результат B1 (`fixes/wf-tg-bot.json`, 500 нод, 0 issues, lint 0)
Трансформер: `transform-B2-duration-validation.py` (перезапускаемый, читает → мутирует → пишет `fixes/`)

## Что изменено (2 ноды, только jsCode)

### 1. `DU Parse state` (Code, id `4e85601d-b136-40c8-8b01-11edd51a8727`)
Добавлена проверка диапазона ДО маршрутизации:

```js
const dur = Number(p.args.value) || Number(qp.duration) || 0;
const durValid = dur >= 15 && dur <= 300;
const quick = !!(url && durValid);                       // было: !!(url && dur)
let mode = 'dur_wrong';
if (state === 'QUICK_URL_AWAIT_DUR' && p.command === 'dur' && durValid) mode = 'dur_ok';
else if (p.callback_action === 'regen_gen' && topic) mode = 'rg_shorts';
else if (p.callback_action === 'regen_gen' && quick) mode = 'rg_ok';
else if (p.callback_action === 'regen_gen' && url) mode = 'dur_wrong';   // НОВОЕ: реген с невалидным qp.duration
else if (p.callback_action === 'regen_gen') mode = 'rg_cycle';
```

Логика:
- **dur_ok только при 15 ≤ dur ≤ 300**. Невалидный dur (dur<15, dur>300, NaN→0) → mode остаётся
  `dur_wrong` → существующая ветка `Switch DU route out[dur_wrong]` → `DU Format wrong` → `TG du wrong`.
  Платные ноды (`DU LB creatify`→гейт→`DU HTTP link`/`DU HTTP submit`) НЕ вызываются.
- **NaN**: `Number('abc')` = NaN → `NaN || ... || 0` → 0 → `durValid=false` → dur_wrong.

### 2. `DU Format wrong` (Code, id `db4095eb-13f8-4f46-b0a0-26a44db8c33f`)
Текст расширен (ветка теперь обслуживает и «сценарий не начат», и «невалидная длительность»):
- было: `'⏱ Сначала начни сценарий: кнопка «URL → видео»'`
- стало: `'⏱ Сначала начни сценарий: кнопка «URL → видео». Длительность ролика — 15–300 секунд.'`

Формат вывода НЕ менялся (shape совместим): `{ json: { chat_id: p.chat_id, text: text } }`, читает
`$('Parser')`. `Switch DU route` проверяет только `$json.mode` → возврат `mode='dur_wrong'` из
`DU Parse state` — ровно тот же shape, что ожидает ветка.

## (3) Проверка обхода через quick_payload (qp.duration)

**Найдена реальная дыра — закрыта в `DU Parse state`, отдельных правок в Build-нодах не требуется:**

- `DU Build link body` и `DU Build submit` читают `st.dur` из `$('DU Parse state').first().json`,
  НЕ читают qp напрямую → единственная точка входа невалидного dur — вывод `DU Parse state`.
- Обратный BFS от платных нод (`DU HTTP link`, `DU HTTP submit`) подтверждает: платная цепочка
  достижима ТОЛЬКО через `Switch DU route` out[0] (dur_ok) и out[2] (rg_ok) → `DU LB creatify` → гейт.
  Других входов нет (проверено скриптом backward-BFS по `connections`).
- **Реген-обход (был)**: `rg_ok` срабатывал при `quick = !!(url && dur)` — при повторном вводе
  (`callback_action='regen_gen'`) dur брался из `qp.duration`, сохранённого БАЗОВОЙ версией
  (`DU Update state` пишет `{url, duration}` без валидации). Легаси-строка с `duration: 5` в БД
  → rg_ok → платный вызов с невалидной длительностью. Теперь `quick = !!(url && durValid)` и
  явная ветка `regen_gen && url` → `dur_wrong` (пользователю — сообщение о диапазоне, платных вызовов нет).
- **Защита в Build-нодах не добавлялась осознанно**: они не могут получить невалидный dur в обход
  `DU Parse state` (единственный источник `st.dur`), а добавление дублирующего чека там не дало бы
  корректного UX-ответа без новой ветки. Решение: валидация в единственной точке входа — минимально и достаточно.

## Валидация (все зелёные)

| Проверка | Результат |
|---|---|
| `validate-workflow-json.py` (BFS, 500 нод) | ✅ 0 issues |
| `lint-workflow-json.py` | ✅ 0 находок |
| `node --check` (обе изменённые jsCode) | ✅ OK |
| Сериализация | ✅ byte-identical roundtrip (indent=1, ensure_ascii=False, без trailing NL) |
| Структура | ✅ 500 нод / 435 conns — не менялись, правки только в jsCode |

## Sim-прогон `sim-code-node-both.py` (DU Parse state)

| Кейс | Вход | Результат |
|---|---|---|
| dur=5 | cmd dur, args.value=5, state=QUICK_URL_AWAIT_DUR | ✅ `dur_wrong` |
| dur=30 | cmd dur, args.value=30 | ✅ `dur_ok` |
| dur=400 | cmd dur, args.value=400 | ✅ `dur_wrong` |
| dur=60 | cmd dur, args.value=60 | ✅ `dur_ok` |
| dur=abc (NaN) | args.value=abc | ✅ `dur_wrong` (dur=0) |
| dur=30 вне сценария | state=IDLE | ✅ `dur_wrong` (поведение не изменено) |
| реген + qp.duration=5 (легаси) | regen_gen, qp={url,duration:5} | ✅ `dur_wrong` (обход закрыт; раньше был бы rg_ok) |
| реген + qp.duration=60 | regen_gen, qp={url,duration:60} | ✅ `rg_ok` (валидный путь работает) |

`DU Format wrong` sim: возвращает `{chat_id, text}` с новым текстом — shape совместим с `TG du wrong`.

## Остатки / замечания

- **`DU Gate` не менялся** (только считает cost=round(5*dur/30)) — он недостижим с невалидным dur
  после фикса, т.к. оба входа в его цепочку (dur_ok, rg_ok) уже валидированы в `DU Parse state`.
- **Легаси-строки БД** с невалидным `quick_payload.duration` (записаны базовой версией до фикса):
  при следующем регене пользователь получит `dur_wrong` с сообщением о диапазоне вместо платного
  вызова — чистка БД не требуется, фикс перехватывает.
- Текстовый ввод длительности (`/dur 45`) в Parser НЕ мапится (`dur_` — только callback-префикс
  кнопок 30/60/90; `C[words[0]]` не содержит `dur`) — вне скоупа B2, отмечено как наблюдение
  (кнопки 30/60/90 — единственный легальный путь ввода; он теперь валидируется).
- `tg_user_id 941296693` не трогался (тикет D).

## Файлы

- Изменён: `/Users/aleksandrtrisenkov/Desktop/PROGRAMMING/РАБОЧИЕ ПРОЕКТЫ/КОНТЕНТ-ЗАВОД-API-MVP/.scratch/review-full-14aug/fixes/wf-tg-bot.json`
- Трансформер: `/Users/aleksandrtrisenkov/Desktop/PROGRAMMING/РАБОЧИЕ ПРОЕКТЫ/КОНТЕНТ-ЗАВОД-API-MVP/.scratch/review-full-14aug/transform-B2-duration-validation.py`
- Отчёт: этот файл (`fixes/B2-duration-validation.md`)
