# A1 — Фикс 1: wf-publish маршрутизация text-only (R3)

**Файл:** `.scratch/review-full-14aug/fixes/wf-publish.json` (26 нод, база = live-экспорт 14.08 из `base/wf-publish.json`)
**Дата:** 14.08.2026
**Статус:** готово, валидация 0 issues / 0 находок / node --check 10/10, симуляции 3/3

## Проблема (R3, CODE-REVIEW-2026-08-14.md §4 п.3)

`Switch upload needed` (switch 3.4, rules-режим, `fallbackOutput: extra`) был перевёрнут относительно требуемого поведения:

- **Было:** условие `{{ Array.isArray($('Webhook').first().json.body.file_ids) && ...length > 0 }}` матчило **НЕПУСТЫЕ** file_ids → out0 (`NoOp skip upload`); пустой file_ids (текстовый пост) → fallback out1 → `Switch mock upload` → `HTTP real upload` POST `/v4.1/upload/init` c URL `$env.WEBHOOK_URL + 'media/' + generation_id + '.mp4'` → 422 «Не удалось загрузить файл по ссылке» → execution умирал ДО `Code build details` → текстовый пост невозможен (даже в mock: text шёл через `Code mock upload` с фейковым `file_id: 67890`).

## Что изменено (минимальный дифф — 1 строка)

**Нода `Switch upload needed`** — перевёрнуто УСЛОВИЕ (соединения не трогались, out0 = текстовый skip, out1 = upload-ветка):

```jsonc
// БЫЛО (матчил НЕПУСТОЙ file_ids → out0 skip — инверсия)
"leftValue": "={{ Array.isArray($('Webhook').first().json.body.file_ids) && $('Webhook').first().json.body.file_ids.length > 0 }}",

// СТАЛО (матчит ПУСТОЙ/отсутствующий file_ids → out0 skip/text)
"leftValue": "={{ !Array.isArray($('Webhook').first().json.body.file_ids) || $('Webhook').first().json.body.file_ids.length === 0 }}",
```

`rightValue: true`, `operator: {type: "boolean", operation: "true"}`, `options.fallbackOutput: "extra"` — без изменений (эталонный паттерн из `references/wf-publish-all-platforms.md` питфолл 3).

Итоговая маршрутизация (сверено с connections, обе ветки):

| file_ids запроса | Ветка | Путь |
|---|---|---|
| пуст / отсутствует (text-only) | **ТЕКСТОВАЯ, БЕЗ upload/init** | out0 → `NoOp skip upload` → `Code build details` → (цепочка адаптации caption) → `Merge` → `Switch mock publication` → mock: `Code mock publication` / real: `HTTP real accounts` → `Code filter accounts` → **`HTTP real publication`** |
| непуст (медиа) | upload-ветка как сейчас | out1 → `Switch mock upload` → mock: `Code mock upload` / real: `HTTP real upload` → `Code build details` → … → `HTTP real publication` |

`Code build details`, `Code mock upload`, `Code mock publication`, `Switch mock upload`, `Switch mock publication` и все connections — **НЕ изменялись**.

## Как text-only проходит до HTTP real publication (проверено симуляцией на node)

Сценарий: `platforms: [threads, x, vk, telegram]`, `content: '…'`, `file_ids: []`, `publication_type: 1`, `account_ids: [104,105,107,109]`.

1. `Switch upload needed`: `!Array.isArray([]) || [].length === 0` → `true` → out0 → `NoOp skip upload` (pass-through, `$json.file_id` НЕ появляется).
2. `Code build details`: `fileIds = []` → для threads/x/vk/telegram details[] = `{account_id, publication_type: 1, content}` — **только content, без file_ids** (логика `if (fileIds.length > 0) d.file_ids = …` сохранилась и при пустом массиве не срабатывает). `file_ids: []` на топ-левеле, `publication_type: 1`.
3. Mock-режим: `Code mock publication` → `{...$json, id: 999, status: 'PENDING_PUBLICATION', mock: true}` — details остаются чисто текстовыми, **фейковый `file_id: 67890` НЕ создаётся** (нода `Code mock upload` достижима только через out1, т.е. только при непустых file_ids).
4. Real-режим: `HTTP real accounts` → `Code filter accounts` → details без file_ids → **`HTTP real publication`** (`jsonBody: {project_id, post_at, account_ids, publication_status: 5, details}`).

Контрольный сценарий MEDIA (`file_ids: [42]`, instagram/youtube/tiktok/threads): out1 → mock-upload → details несут `file_ids: [42]` для ig/yt/tt (приоритет `wh.file_ids` над `$json.file_id` — 67890 игнорируется), threads остаётся текстовым. Media-путь не сломан.

## Что проверено

- `python3 …/scripts/validate-workflow-json.py fixes/wf-publish.json` → **✅ 0 issues** (26 нод, 25 источников связей, BFS-достижимость всех нод, node --check всех 10 jsCode — все ок).
- `python3 …/scripts/lint-workflow-json.py fixes/wf-publish.json` → **✅ 0 находок** (exit 0).
- Симуляция jsCode дословно в node (паттерн питфолла 7 из references): 3/3 зелёные (text-only mock, media через upload-ветку, text-only real до Code filter accounts / HTTP real publication).
- Дифф base→fix: 1 строка (только leftValue свитча), формат/отступы JSON не тронуты.

## Остатки / риски

1. **Документация устарела:** `references/wf-publish-all-platforms.md` (питфоллы 3, 6 и «Цепочка нод») описывает старую маршрутизацию («file_ids непуст → out0 skip / fallback out1 upload»). Нужно обновить на: «file_ids пуст/нет → out0 skip (text); file_ids непуст → out1 upload». Не трогал — файл может правиться параллельной волной.
2. **Real-режим, непустые file_ids:** теперь попадают в upload-ветку → `HTTP real upload` POST `/v4.1/upload/init` с URL `$env.WEBHOOK_URL + 'media/' + generation_id + '.mp4'`. Если этот URL мёртв → 422 (та же смерть, что была у text). В mock-режиме безвредно (`Code mock upload`). Задача предписывает «upload-ветка как сейчас» — так и оставлено; если нужна защита — следующей волной: правило «file_ids пуст И generation_id непуст → upload», иначе skip (или выкинуть real-upload из ветки, т.к. details берут `wh.file_ids`).
3. **Медиа с пустым file_ids и заполненным generation_id** (видео не загружено в postmypost) теперь уходит в текстовую ветку и теряет медиа. В базе этот случай и так умирал с 422 (питфолл PM-2 «reels без file_ids → 422»), т.е. живого регресса нет, но сценарий «дозагрузка .mp4 по generation_id» теперь не выполняется вообще — см. п.2.
4. **Фикс 2 (A1, wf-tg-bot text_post):** контракт вызова wf-publish для текста обязан слать `file_ids: []` + `content` (или `captions`), `publication_type: 1` — тогда текст проходит без единого upload/init.
5. **Применение к live:** фикс в файл; перенос в БД n8n (UPDATE workflow_history активной baa89f73 и черновика 4b4276ca + workflow_entity, restart, экспорт) — вне рамок этого тикета, по DEPLOYMENT.md.
