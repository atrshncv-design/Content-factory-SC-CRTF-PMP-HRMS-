# A1-fix2 — Сценарий текстового поста в wf-tg-bot

**Дата:** 14.08.2026 · **База:** `.scratch/review-full-14aug/base/wf-tg-bot.json` (404 ноды, live 14.08)
**Результат:** `.scratch/review-full-14aug/fixes/wf-tg-bot.json` (430 нод, +26)
**Тикет:** docs/CODE-REVIEW-2026-08-14.md, блокер п.3 (часть 2: команда в боте).
**Трансформер:** `.scratch/review-full-14aug/transform-A1-fix2-text-post.py` (python, читает base → мутирует → пишет fixes; перезапускаем).

## Что сделано (минимальные правки: 5 изменённых + 26 новых нод)

Изменены только 5 существующих нод:
| Нода | Правка |
|---|---|
| `Parser` | C-маппинг: `'text_post', 'текстовый пост', '/text_post', '/текстовый пост'` → `text_post`; обработка callback: `action==='tx_toggle' → cb='tx_toggle'`, `action==='tx_publish' → cb='tx_publish'` |
| `Switch cmd` | правило `text_post` в конец (34-е; out[33] → `TX Build`), fallback `Gate Build` уехал на out[34] |
| `Switch cb` | правила `tx_toggle` (out[13] → `TX answer`) и `tx_publish` (out[14] → `TX answer pub`), fallback `CB answer unknown` на out[15] |
| `Switch gate` | правило `quick_text` (out[5] → `TX Save text`), fallback `TG unknown` на out[6] |
| `Gate Check` | `p.command==='unknown' && state==='QUICK_TEXT_AWAIT' → { mode: 'quick_text' }` |

## Схема ветки

```
cmd:text_post / «текстовый пост» / /text_post
  → Parser (command=text_post) → Switch cmd out[33]
  → TX Build            (Code: UPDATE sessions SET state='QUICK_TEXT_AWAIT', quick_payload=NULL)
  → TX HTTP build       (db-bridge)
  → TX Format ask       (esc! «📝 Пришли текст поста») → TG tx ask [🧹 Отмена|📋 Меню]

[текст сообщения, command=unknown, state=QUICK_TEXT_AWAIT]
  → Switch cmd fallback → Gate Build → Gate HTTP → Gate Check (mode=quick_text) → Switch gate out[5]
  → TX Save text        (Code: UPDATE quick_payload=json({text}), state='QUICK_TEXT_PLATFORMS')
  → TX HTTP save
  → TX Format platforms (esc! «📤 Выбери площадки:» + ☐-список) → TG tx platforms
        [☐ Threads|☐ X] [☐ VK|☐ Telegram] [✅ Опубликовать] [🧹 Отмена|📋 Меню]

tx_toggle:platform:<p> → Switch cb out[13] → TX answer (☑️)
  → TX Toggle select → TX HTTP select → TX Toggle (Code: toggle в quick_payload.platforms, UPDATE)
  → TX HTTP update → TX Toggle Format (esc! «📤 Выбери площадки:» с ☑️/☐) → TG tx platforms

tx_publish → Switch cb out[14] → TX answer pub (📤)
  → TX Build select → TX HTTP select pub → TX Build body (Code, см. контракт)
  → Switch TX valid ({{ $json.ok }} == 'true'; fallback extra)
      ├─ ok    → TX HTTP publish (POST :5678/webhook/factory/publish, timeout 120s, neverError)
      │        → TX Format result (esc! try/catch: «✅ Опубликовано в: <pl>» / «❌ …»)
      │        → TX Reset (UPDATE state='IDLE', quick_payload=NULL) → TX HTTP reset → TG tx result [📝 Новый пост|📋 Меню]
      └─ error → TX Format err (esc! «☝️ <error>») → TG tx err [📋 Меню]   (state остаётся PLATFORMS — можно донажать)
```

Отмена на любом шаге: `cmd:cancel` / «🧹 Отмена» → существующий `CN Build` — полный сброс
(`state='IDLE', topic_id=NULL, script_id=NULL, generation_id=NULL, selected_platforms=NULL, post_at=NULL, quick_payload=NULL`)
→ QUICK_TEXT_* не виснут, достаточно (проверено: правок в CN Build не требуется).

## Состояния (sessions.state, quick_payload)

| state | quick_payload | смысл |
|---|---|---|
| `QUICK_TEXT_AWAIT` | NULL | ждём текст поста |
| `QUICK_TEXT_PLATFORMS` | `{"text": "...", "platforms": [...]}` | ждём выбор площадок / publish |
| `IDLE` | NULL | финал (TX Reset) или отмена (CN Build) |

`quick_payload` — JSON-объект `{text: string, platforms: string[]}` (threads/x/vk/telegram), пишется
через `json(?)` в SQLite.

## Контракт вызова wf-publish (fixes/wf-publish.json, text-only)

`TX Build body` собирает ровно контракт п.3 ревью:
```json
POST http://localhost:5678/webhook/factory/publish
{ "platforms": ["threads","x"], "content": "<текст>", "captions": {},
  "post_at": null, "generation_id": null, "file_ids": [] }
```
- `file_ids: []` → text-only маршрутизация (пусто → текстовая публикация напрямую, 0 кредитов).
- Валидация до вызова: `platforms` пусто → `{ok:false, error:'выбери платформу'}`; `content` пусто → `{ok:false, error:'текст поста не получен'}`.
- Успех определяется по ответу: `resp.post_id !== undefined` (wf-publish отвечает `{post_id, postmypost_id, status:'pending_publication'}`, поля `ok` НЕТ).
- `TX HTTP publish`: `options.timeout=120000`, вложенный `options.response.response.neverError=true` (эталон CRS HTTP, typeVersion 4.5); `jsonBody: "={{ $json.body }}"`.

## Проверки (все пройдены)

- `validate-workflow-json.py fixes/wf-tg-bot.json` → **0 issues** (430 нод, BFS от tg-trigger — все достижимы, `node --check` 189 jsCode — ок).
- `lint-workflow-json.py fixes/wf-tg-bot.json` → **0 находок**.
- `sim-code-node-both.py` — все 14 прогонов новых Code-нод OK:
  - TX Build / TX Save text / TX Toggle / TX Reset / TX Build select → корректные SQL+params;
  - TX Build body: platforms+text → ok-body; без platforms → `выбери платформу`; пустой text → `текст поста не получен`;
  - TX Format result: успех → «✅ Опубликовано в: threads, x»; HTTP-ошибка → «❌ … postmypost api down»; сетевой сбой (throw) → «❌ … сервис публикации не ответил»;
  - TX Toggle: добавил vk, platforms [threads,x] → [threads,x,vk]; TX Toggle Format: ☑️/☐ корректно.
- esc() во ВСЕХ новых Format-нодах (строка извлечена байт-точно из GD Format, не перенабрана); «📋 Меню» на всех новых экранах; сериализация как base (indent=1, ensure_ascii=False, без trailing newline).
- tg_user_id 941296693 не тронут (тикет D).

## Остатки / замечания для следующих субагентов (A2/B1/B2/C2)

1. **Текст в состоянии QUICK_TEXT_PLATFORMS** (не callback) → Gate Check вернёт `normal` → TG unknown («Не понял…»); state не сбрасывается, кнопки работают. Если нужно — добавить mode `quick_text_platforms` отдельным тикетом.
2. **`/text_post <текст>`** (с аргументом) сейчас тоже входит в AWAIT-режим (args.value игнорируется) — осознанно, минимально.
3. **TG tx platforms** — статичные кнопки «☐ Threads…»; актуальная отметка показывается в тексте сообщения (☑️/☐) из Format-ноды, а не в самих кнопках (паттерн как у stage4 toggle).
4. **Ответ wf-publish** без поля `ok` — детект по `post_id`; если wf-publish изменит формат — обновить TX Format result.
5. **«📝 Новый пост»** на финальном экране → `cmd:text_post` (реюз команды, безопасно).
6. Порядок правил Switch: `text_post` добавлен ПОСЛЕ `dur`, `quick_text` — ПОСЛЕ `quick_shorts_topic`, tx-правила — ПОСЛЕ `confirm_publish`; индексы out сдвинуты только у fallback'ов (проверено, остальные out-индексы не изменились).
