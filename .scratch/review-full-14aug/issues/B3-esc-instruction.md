# B3 — Надёжность: esc() в Build stage3 (wf-creatify-webhook) + слеш /instruction (wf-tg-bot)

**What to build:** (1) Telegram-текст этапа 3 wf-creatify-webhook экранируется от Markdown (динамический script_excerpt); (2) команда `instruction` получает слеш-форму `/instruction` в Parser.

**Blocked by:** None — can start immediately (база = live-экспорт `.scratch/review-full-14aug/base/`)

**Status:** ready-for-agent

**Контекст:** фикс-волна по `docs/CODE-REVIEW-2026-08-14.md` (Y6, Y10). Ревью:
1. `Build stage3` (wf-creatify-webhook) собирает `'Сценарий: ' + excerpt` БЕЗ esc() — `_`/`*` в сценарии → Telegram 400 Markdown (питфолл F-4). Эталон esc: `MO Format` в wf-tg-bot (`const esc = s => String(s ?? '').replace(/([_*[\\]`])/g, '\\\\$1')` — КОПИРОВАТЬ дословно, не перенабирать; программно извлечь regex'ом).
2. Parser (wf-tg-bot): `'instruction': 'instruction', 'инструкция': 'instruction', 'инструкции': 'instruction', '/инструкция': 'instruction'` — нет ключа `'/instruction'` (единственная из 31 без латинского слеша; setMyCommands предлагает `/instruction` → «Не понял»).

**Рабочие файлы (только база):**
- `.scratch/review-full-14aug/base/wf-creatify-webhook.json` (25 нод)
- `.scratch/review-full-14aug/base/wf-tg-bot.json` (404 нод)

- [ ] wf-creatify-webhook Build stage3: обернуть динамические куски (excerpt, video) в esc() (строка скопирована из эталона)
- [ ] wf-tg-bot Parser: добавить `'/instruction': 'instruction'` в C-маппинг
- [ ] Валидация: `validate-workflow-json.py` 0 issues, `lint-workflow-json.py` 0 находок (проверит esc-покрытие), node --check, sim (esc-поведение через `sim-code-node.py`)
- [ ] Отчёт: write_file в `.scratch/review-full-14aug/fixes/B3-esc-instruction.md`
