# 08 — Системное: миграции, деплой-скрипты, DEPLOYMENT, секреты

**Требования:** R01 (довести до идеала), R09i (без багов, готовый к сдаче), R10i (весь scope)
**Blocked by:** —
**Зона:** `infra/db/`, `docker-compose.yml`, `DEPLOYMENT.md`, `register-tg-commands*.sh`, `.env.example`, `AGENTS.md`
**Волна:** 1
**Status:** done (16.08.2026)

## Что должно заработать

Инфра и документация соответствуют серверу; деплой не сломает команды; секреты в безопасности; восстановление с нуля возможно.

## Из брифа / манифеста, дословно

> «довести текущий проект контент-завода до идеала»
> «почти готова к сдаче»

## Разделы спецификации

История 10, 12.

## Критерии приёмки

- [x] Миграция v3 БД восстановлена в репо (файл + шаги). `infra/db/migrate-client-profiles-v3.py` в репо; `tests/test_migrations.py` — 4/4 PASSED (v1+v2+v3 поверх 001-init+002, повторный прогон идемпотентен, schema_version=5). `infra/db/migrate.sh` применён к свежей БД: v5 + idempotency подтверждены (2 прогона).
- [x] DEPLOYMENT.md приведён в соответствие серверу: правдивые id, имена воркфлоу, статус crontab, секреты — только имена переменных. Добавлен баннер «текущая архитектура §13» (n8n=оркестратор, Hermes через bridge, gateway остановлен), предупреждение о filter-repo (из fixes-версии ревью), поправлен счётчик команд 31→35; все id воркфлоу в тексте сверены с репо (0 расхождений); секретов со значениями нет (только имена переменных).
- [x] register-tg-commands.sh не затирает 35 команд (защита или удаление). Скрипт стал диспетчером: делегирует новейшему payload (35→31→25); собственная 28-командная логика — только при отсутствии новее. Проверено mock-прогоном: при наличии tg-commands-35.json вызывается register-tg-commands-35.sh, при только 25 — падение в свою логику с exit 0.
- [x] .env.example содержит все необходимые переменные, включая FACTORY_WEBHOOK_SECRET. Добавлены: FACTORY_WEBHOOK_SECRET, FACTORY_DB_BRIDGE_TOKEN, HERMES_BRIDGE_TOKEN, HERMES_BRIDGE_PORT, TELEGRAM_ALLOWED_USERS (маппинг). Сверено с $env.* в workflows/*.json — 0 пропусков.
- [x] docker-compose.yml актуален (не устаревший compose уровня 2.4). Заменён на версию из `.scratch/review-content-factory/fixes/docker-compose.yml` (FIX-17, live-архитектура: n8n 2.34.4 зафиксирована, db-bridge, cloudflared, extra_hosts, N8N_BLOCK_ENV_ACCESS_IN_NODE=false; hermes/caddy — legacy-комментарии). Витрина — на сервере НЕ применять.
- [x] Утечка секретов в git не повторяется. `.gitignore`: `.env`, `.env.*`, `!.env.example` (git check-ignore: .env/.env.production/.env.local → IGNORED; .env.example → НЕ игнорируется). История уже переписана filter-repo (13.08) — подтверждено в DEPLOYMENT/AGENTS.
- [x] AGENTS.md / CLAUDE.md содержат актуальные инструкции для следующей сессии. AGENTS.md: autopilot-блок сохранён, добавлен раздел «Инфраструктура (тикет 08, done 16.08)»: pytest-команда миграций, витрина compose, диспетчер register-скриптов, правила секретов. CLAUDE.md отсутствует (проект использует AGENTS.md — достаточно).

## Что сделано (16.08.2026)

1. `tests/test_migrations.py` — `python3 -m pytest tests/test_migrations.py -v` → **4 passed** (v1+v2+v3, идемпотентность).
2. `infra/db/migrate.sh` (прогон на свежей БД): v1→v2→v3 применяются, schema_version=v5, повторный запуск — no-op. Бэкап создаётся.
3. `DEPLOYMENT.md` — баннер текущей архитектуры + filter-repo-предупреждение + счётчик команд 35.
4. `register-tg-commands.sh` — диспетчер (35→31→25), не затирает 35-командное меню; bash -n OK.
5. `.env.example` — добавлены FACTORY_WEBHOOK_SECRET, FACTORY_DB_BRIDGE_TOKEN, HERMES_BRIDGE_TOKEN, HERMES_BRIDGE_PORT, TELEGRAM_ALLOWED_USERS.
6. `docker-compose.yml` — заменён на актуальную live-витрину (валидный YAML).
7. `.gitignore` — `.env.*` + `!.env.example`.
8. `AGENTS.md` — раздел «Инфраструктура» в autopilot-блоке.

## Что осталось на платный тест пользователя

- Ротация ключей (утечка 13.08) — действие пользователя (отложено им же).
- Реальные платные E2E (creatify/scrapecreators) — проводит пользователь после полной готовности (R07).
- `crontab -l` на сервере — сверка трёх строк обслуживания (в DEPLOYMENT §11 инструкция).
