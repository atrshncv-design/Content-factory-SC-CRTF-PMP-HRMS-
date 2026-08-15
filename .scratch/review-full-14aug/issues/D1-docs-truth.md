# D1 — Правдивость документации: DEPLOYMENT.md + актуальный register-tg-commands-31.sh

**What to build:** DEPLOYMENT.md перестаёт врать (фантом wf-credit-check, перепутанные id), в репо появляется актуальный скрипт регистрации 31 команды (сейчас только устаревший 28-командный).

**Blocked by:** None — can start immediately (файлы не пересекаются с wf-tg-bot-серией)

**Status:** ready-for-agent

**Контекст:** фикс-волна по `docs/CODE-REVIEW-2026-08-14.md` (Y14, Y15, С3, С4, С6). Факты:
1. **DEPLOYMENT.md:32** заявляет воркфлоу `wf-credit-check` с live-тестом `{ok:true, balance:497}` — воркфлоу НЕ существует ни в репо, ни на сервере (баланс проверяется `GET /api/remaining_credits/`). Строку надо исправить/удалить.
2. **DEPLOYMENT.md:329 vs :360** — внутреннее противоречие: :329 пишет wf-creator-profile id `...015`, :360 пишет `...016`. Факт: `...015` = wf-creators-search, `...016` = wf-creator-profile (проверено на сервере).
3. **register-tg-commands.sh** в репо регистрирует 28 команд (tg-commands-25.json), а прод живёт на **31 команде** (tg-commands-31.json, есть в репо как untracked; register-tg-commands-31.sh на сервере, в репо НЕТ). Запуск репо-скрипта затрёт меню UX-2.
4. DEPLOYMENT.md:90 «id ...001..012» — устарело (реально до ...025 + wf-onboard UUID).

**Рабочие файлы:** `DEPLOYMENT.md`, `register-tg-commands.sh`, `tg-commands-31.json` (в корне репо). ЭТАЛОН 31-скрипта — на сервере `/home/ubuntu/factory/register-tg-commands-31.sh` (см. контекст оркестратора; если недоступен — восстановить по tg-commands-31.json + паттерну старого скрипта).

- [ ] DEPLOYMENT.md: убрать/переписать строку про wf-credit-check (с пометкой «баланс — GET /api/remaining_credits/, воркфлоу не требуется»); исправить :329 на ...016; обновить :90 (id до ...025, wf-onboard UUID); проверить остальные id в §16-23 на противоречия
- [ ] Создать `register-tg-commands-31.sh` по эталону сервера: PAYLOAD=tg-commands-31.json, verify=31, все 3 scope (default/all_private_chats/all_group_chats), ждать 20с, verify дважды, exit 0
- [ ] tg-commands-31.json: проверить, что в репо актуальный (31 команда — уже есть, untracked)
- [ ] Не трогать workflows/*.json (это не тикет синхронизации — он отдельно, после всех фиксов)
- [ ] Отчёт: write_file в `.scratch/review-full-14aug/fixes/D1-docs-truth.md` — что исправлено (строка → было → стало)
