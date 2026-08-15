# T3 — Видео файлом в TG (sendVideo): РЕАЛИЗОВАНО (14.08.2026)

**Файл:** `.scratch/review-full-14aug/fixes/wf-creatify-webhook.json` — 25 → **27 нод**, 0 issues, lint 0 (верифицировано оркестратором).
**Отчёт по данным субагента sa-1-02f7510d** (файл отчёта не дописан из-за лимита итераций; воркфлоу-json записан).

## Критичное открытие (проверено по исходникам n8n 2.34.4)
telegram-нода v1.2:
- Валидные resource: `chat/callback/file/message` — **`video` НЕ существует** → «The resource "video" is not known!»
- sendVideo: параметр **`file`** (displayName 'Video', name 'file'; execute: `body.video = getNodeParameter('file')`)
- Подпись: **`additionalFields.caption`** (text sendVideo не читает)
- `appendAttribution` — только для sendMessage, в sendVideo НЕ включать
- replyMarkup inlineKeyboard + кнопки — поддерживаются

**Следствие: существовавшая нода `TG sh video` в wf-tg-bot (AI Shorts, resource:'video'+video) была сломана — ИСПРАВЛЕНА оркестратором отдельно** (resource='message', file, caption; 533 нод, 0 issues).

## Что сделано в wf-creatify-webhook (25 → 27 нод)
1. `Build stage3`: в json добавлено `video = d.video_output_url || wb.video_output_url || wb.video_output` (пусто → ''); текст «🎬 Этап 3/4 — Видео готово. Что делаем?» + esc(script_excerpt), БЕЗ ссылки на видео в тексте
2. `Telegram stage3` → sendVideo по правильной схеме v1.2: resource='message', operation=sendVideo, chatId, **file='={{ $json.video }}'**, подпись additionalFields.caption='={{ $json.text }}', кнопки publish:gen/regen:gen/reject:gen + 📋 Меню
3. Fallback: Switch перед Telegram stage3 — video непуст → sendVideo; пуст → sendMessage со старым текстом (ссылка) + те же кнопки

## Верификация
- validate 0 issues (27 нод, BFS, node --check 6 jsCode); lint 0; sim OK (Build stage3 с video / без video)
- Питфолл по пути (решён): дубль ключа file / остаточный text — удалены; esc-регекс через chr(92) с ord-сверкой с эталоном ST Format

## Остатки
- Отчёт субагента не дописан (лимит) — восстановлен оркестратором
- `TG sh video` фикс — в wf-tg-bot (в составе деплоя волны 2)
