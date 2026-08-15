# 06 — Ревью системного: onboard/tg-alerts/скрипты/инфра/спеки/секреты

**What to review:** ревью системного слоя: `wf-onboard`, `wf-tg-alerts`, `zz-test-sqlite`, скрипты, инфраструктура, спеки, DEPLOYMENT, git-история на секреты.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

**Контекст субагенту:** файлы репо: `workflows/wf-onboard.json`, `workflows/wf-tg-alerts.json`, `workflows/zz-test-sqlite.json`, `register-tg-commands.sh`, `register-tg-commands-31.sh` (если есть), `phase2-enable.sh`, `infra/**`, `scripts/**`, `specs/**`, `DEPLOYMENT.md`, `tg-commands-*.json`. Чек-лист `references/workflow-review-checklist.md`; прецедент — `docs/CODE-REVIEW-2026-08-13.md` (К1 утечка секретов, FIX-16/17 db-bridge, DEPLOYMENT:329 опечатка), `references/security-audit-offline-13aug.md`. Сети нет, только чтение файлов репо (git log/grep — можно локально).

- [ ] wf-onboard: SSRF-защита (запрет 10/8, 172.16/12, 192.168/16, 127/8), валидация URL, error-ветка
- [ ] wf-tg-alerts: контракт webhook, экранирование Markdown, доставка
- [ ] Скрипты: register-tg-commands (setMyCommands 31, все scope, verify), phase2-enable.sh (--dry-run, маскирование, chmod 600)
- [ ] Секреты: строгий grep по всему дереву + git-истории (паттерны с длинами: `sk-w[A-Za-z0-9_-]{40,}`, `FactoryOwner`, ключи по 32-64 симв.) — НЕ выводить найденные значения, только факт и место
- [ ] docker-compose.yml (если в репо): устаревший/актуальный, extra_hosts, BLOCK_ENV, db-bridge fail-closed
- [ ] DEPLOYMENT.md: сверка заявленного с фактами в репо (active, id воркфлоу, опечатки), соответствие фактическому состоянию
- [ ] Спеки: контракты webhook в спеках vs фактические воркфлоу (расхождения, как с creatify-путями)
- [ ] Отчёт: таблица находок (severity, файл:строка, влияние, доказательство), раздел «проверено и работает», вердикт по системному слою
