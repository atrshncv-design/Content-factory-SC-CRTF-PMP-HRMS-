# B3 — esc()-покрытие в wf-creatify-webhook (Build stage3) — Y6

**Статус:** DONE
**База:** `.scratch/review-full-14aug/base/wf-creatify-webhook.json` (live 14.08, 25 нод)
**Фикс:** `.scratch/review-full-14aug/fixes/wf-creatify-webhook.json`
**Тикет:** `docs/CODE-REVIEW-2026-08-14.md` Y6; пересекается с `issues/B3-esc-instruction.md` (п.1)

## Проблема (Y6)

Нода `Build stage3` собирала TG-текст без экранирования:

```js
const text = '🎬 Этап 3/4 — Видео готово\n\n'
  + 'Сценарий: ' + excerpt + '\n\n'          // ← script_excerpt БЕЗ esc()
  + (video ? 'Видео: ' + video + '\n\n' : '') // ← video URL БЕЗ esc()
  + 'Что делаем с видео?';
```

Динамический `script_excerpt` (LLM-сценарий) и `video_output_url` могут содержать `_`, `*`, `[`, `]`, `` ` `` →
при принудительном `parse_mode='Markdown'` Telegram-ноды (питфолл F-4) → `400 Bad Request: can't parse entities` —
сообщение этапа 3 теряется (consistency-ветка спасает только от дублей, не от потери текста).

## Что сделано

### 1. `Build stage3` — esc() для динамики

- Строка `const esc = ...` извлечена **программно** из эталона `MO Format` (`base/wf-tg-bot.json`, `[0]/nodes[182]`,
  regex `const esc = .*?;`) и вставлена дословно (64 байта, байт-точность подтверждена `assert`).
- Динамические куски обёрнуты: `esc(excerpt)`, `esc(video)`. Статичные части (эмодзи 🎬, тире —) не тронуты.
- Эмодзи проверены: `esc` заменяет только `[_*[\]`]` — эмодзи не экранируются, безопасно (подтверждено симуляцией).

Итоговый jsCode:

```js
const d = $('Code done build').first().json;
const genId = String(d.id);
const esc = s => String(s ?? '').replace(/([_*[\]`])/g, '\\$1');
const excerpt = (d.script_excerpt || '…').slice(0, 200);
const wb = $('Webhook').first().json.body || {};
const video = String(d.video_output_url || wb.video_output_url || wb.video_output || '');
const text = '🎬 Этап 3/4 — Видео готово\n\n'
  + 'Сценарий: ' + esc(excerpt) + '\n\n'
  + (video ? 'Видео: ' + esc(video) + '\n\n' : '')
  + 'Что делаем с видео?';
return [{ json: { chat_id: 941296693, text: text, gen_id: genId } }];
```

### 2. Аудит остальных TG-текстов воркфлоу — найден и исправлен `Build update failed`

Проверены все ноды с jsCode и TG-пути доставки (прямые Telegram-ноды + HTTP `factory/tg-alert`):

| Нода | TG-текст? | Динамика | Вердикт |
|---|---|---|---|
| `Build stage3` | да (`Telegram stage3`) | `excerpt`, `video` | **исправлено** (esc) |
| `Build update failed` | да (alert_text → `HTTP tg-alert failed` → wf-tg-alerts `Telegram` нода, Markdown) | `reason` (failed_reason из вебхука) | **исправлено** (esc) |
| `Build session update` | нет (только SQL) | — | чисто |
| `Build session reset` | нет (только SQL) | — | чисто |
| `Code done build` | нет (промежуточный JSON) | — | чисто |
| `Build update done` | нет (только SQL) | — | чисто |

`Build update failed` — дополнительная находка того же класса Y6/F-4: `alert_text` с динамическим
`reason` уходит в Telegram (принудительный Markdown). Исправлено тем же паттерном:
`'Генерация #' + String(r.id) + ' failed: ' + esc(reason)`.
`params[0]` в SQL **оставлен сырым** `reason` (экранирование только для отображения, не для БД).

### 3. НЕ тронуто

- `chat_id: 941296693` (хардкод в `Build stage3`, `Build session update/reset`, `HTTP tg-alert failed`) — отдельный тикет D, вне скоупа.
- Ноды `Build session update` / `Build session reset` — SQL без TG-текста.
- Все остальные 19 нод воркфлоу без изменений (diff = только 2 поля `jsCode`).

## Валидация

| Проверка | Результат |
|---|---|
| `validate-workflow-json.py` | ✅ 0 issues (25 нод, 19 связей, jsCode проверено 6) |
| `lint-workflow-json.py` | ✅ 0 находок |
| `node --check` (все 6 jsCode-нод) | ✅ PASS |
| Симуляция `Build stage3` (node, hostile `_ * [ ] \`` + эмодзи 🎬🚀 в excerpt, `_` в video URL) | ✅ все спецсимволы экранированы (`\_ \* \[ \] \``), эмодзи сохранены, неэкранированных спецсимволов 0 |
| Симуляция `Build update failed` (reason с `_`) | ✅ alert_text экранирован, SQL params[0] = сырой reason |
| Минимальность diff vs base | ✅ изменены только 2 строки `jsCode` (4 строки unified-diff), сериализация идентична base (indent=1, ensure_ascii=False) |

## Файлы

- Исправленный воркфлоу: `/Users/aleksandrtrisenkov/Desktop/PROGRAMMING/РАБОЧИЕ ПРОЕКТЫ/КОНТЕНТ-ЗАВОД-API-MVP/.scratch/review-full-14aug/fixes/wf-creatify-webhook.json`
- Эталон esc(): `/Users/aleksandrtrisenkov/Desktop/PROGRAMMING/РАБОЧИЕ ПРОЕКТЫ/КОНТЕНТ-ЗАВОД-API-MVP/.scratch/review-full-14aug/base/wf-tg-bot.json` (нода `MO Format`)
