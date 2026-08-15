# T2 — Полный автомат + длина из настроек в auto-режиме: РЕАЛИЗОВАНО (14.08.2026)

**Файл:** `.scratch/review-full-14aug/fixes/wf-tg-bot.json` — 533 ноды (база = результат T1), 0 issues, lint 0, BFS 533/533.
**Правило:** 0 кредитов, только файлы. typeVersion: telegram v1.2 / switch v3.4 (не менялись). Сериализация indent=1 / ensure_ascii=False / без trailing newline (подтверждено побайтово).

## Что параметризовано (AU-цепочка, auto-режим)

До T2 AU-цепочка была жёстко «30 сек, ~65 слов» (T1 не трогал AU). Теперь длина в auto берётся ТОЛЬКО из `settings.video_length`:

| Нода | Было | Стало |
|---|---|---|
| `AU Build settings` (code) | `SELECT key, value FROM settings WHERE key = 'mode'` | `SELECT key, value FROM settings WHERE key IN ('video_length','mode')` |
| `AU Check` (code) | `mode = rows[0].value` (одна строка) | map по ключам: `mode` (дефолт manual) + `video_length` (дефолт **30**) |
| `AU Build prompt` (code, scriptwriter) | жёстко `30 сек, ~65 слов` | `dur = settings.video_length` (дефолт 30), слова = `Math.round(dur*65/30)` → «(N сек, ~M слов, русский)»; `target_length_sec` в JSON-схеме ответа остался |
| `AU Build prompt json` (code, json-builder) | `(script.target_length \|\| 30)` — длина из LLM-ответа | `dur = settings.video_length` (дефолт 30); в промпте `video_length: N (строго из настроек, не менять)` — **НЕ target_length из LLM** |
| `AU Build submit body` (code) | `json_payload: pl.payload` как есть | `Object.assign({}, pl.payload, { video_length: dur })` — форс длины из настроек в фактическом payload (зеркало AS-цепочки manual) |

`AU Parse script` (code) по-прежнему парсит `target_length_sec` из ответа scriptwriter (дефолт 30) — это метаданные сценария в БД, не влияет на payload генерации; фактическая `video_length` в creatify-submit форсится из настроек в `AU Build submit body`.

## Как auto пропускает выбор длины (DR-ветка) — проверено, правок не потребовалось

- Цепочка: `SC HTTP setstate → DR Build settings → DR HTTP settings → DR Check → Switch DR gate`.
- `DR Check`: `mode` из settings (дефолт manual).
- `Switch DR gate`: одно правило `$json.mode == manual` → выход 0 → `DR Build ask state` (экран выбора); `fallbackOutput: extra` → выход 1 → **`SC Build analytics body`** (сразу дальше, без выбора).
- BFS подтверждён: обе ветки достижимы, 533/533. В auto (`mode != manual`) гейт падает в fallback → выбор НЕ показывается, цикл идёт в SC Build analytics body → AU-цепочку.
- `AU Check` → `Switch AU topic` (правило `mode == auto` → AU Build approve topic; fallback → SC Stage1 Format) — auto не попадает на выбор длины нигде.

## Manual vs auto — пути не смешиваются (проверено)

- **manual → AS-цепочка** (выбор длины): `CT Build bridge prompt` и `AS Build bridge prompt` читают `quick_payload.duration` (из DR-сохранения, дефолт 30); `AS Build submit body` форсит `video_length` из `quick_payload.duration`.
- **auto → AU-цепочка** (настройки): `AU Build prompt` / `AU Build prompt json` / `AU Build submit body` читают `$('AU Check').json.video_length` (settings), `quick_payload` не используется.
- Ни одна AU-нода не обращается к `quick_payload`; ни одна CT/AS-нода не читает `settings.video_length`. Смешивания нет.

## Верификация

- `validate-workflow-json.py`: **0 issues** (533 нод, 466 связей-источников, node --check 243 jsCode)
- `lint-workflow-json.py`: **0 находок**
- BFS: 533/533, недостижимых нет
- node --check: пройден в составе validate (243 jsCode)
- Сериализация: `json.dumps(indent=1, ensure_ascii=False)`, без trailing newline — побайтовое совпадение

### sim-результаты (sim-code-node.py)

| Сценарий | Вход | Результат |
|---|---|---|
| AU Build prompt, settings.video_length=45 | `AU Check: {mode:auto, video_length:45}` | `«Напиши сценарий короткого вертикального видео (45 сек, ~98 слов, русский)...»` ✅ |
| AU Build prompt, без ключа | `AU Check: {mode:auto}` (нет video_length) | `«(30 сек, ~65 слов, русский)...»` ✅ |
| AU Check, ключ video_length=45 есть | rows: video_length=45, mode=auto | `{mode: auto, video_length: 45}` ✅ |
| AU Check, ключа нет | rows: mode=auto | `{mode: auto, video_length: 30}` ✅ |
| AU Build prompt json, settings 45, LLM вернул target_length=999 | script.target_length=999 | промпт: `(длина 45 сек)` + `video_length: 45 (строго из настроек, не менять)` — 999 проигнорирован ✅ |
| AU Build submit body, settings 45, LLM payload video_length=999 | payload.video_length=999 | `json_payload.video_length = 45` (форс из настроек) ✅ |

## Файлы

- Изменён: `.scratch/review-full-14aug/fixes/wf-tg-bot.json` (533 ноды, 0 issues)
- Создан: `.scratch/review-full-14aug/fixes/T2-auto-duration.md` (этот отчёт)

## Остатки

- Ключ `settings.video_length` на сервере ещё НЕ создан (создаётся командой; код уже работает с дефолтом 30 при отсутствии ключа).
- Скриптwriter по-прежнему возвращает `target_length_sec` (дефолт 30) — используется только как метаданные сценария, на длину видео не влияет.
