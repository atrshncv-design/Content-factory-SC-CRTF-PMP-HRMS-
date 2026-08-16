# AGENTS.md

Проект: контент-завод — фабрика коротких вертикальных видео (n8n 2.34.4 в Docker + Hermes Agent + SQLite factory.db).

## Agent skills

### Issue tracker

Local markdown: one feature per directory `.scratch/<feature-slug>/` with `spec.md` and one file per ticket in `issues/`. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: `CONTEXT.md` (глоссарий и инварианты) + `docs/adr/` (решения). Спеки проекта — в `specs/`. See `docs/agents/domain.md`.

## Правила работы

- Источник правды для воркфлоу — сервер `~/factory/`; репо `workflows/` синхронизируется при деплое. Новейшую версию воркфлоу искать по всем `.scratch/*/fixes/`.
- Платные вызовы (creatify/scrapecreators) — только с явного согласия пользователя; тесты «до точки списания».
- TG-тексты: экранирование Markdown (`esc()`), статика без `_`, callback_data только `={{ expr }}`.
- Секреты — только имена переменных; значения в `.env` сервера (никогда в коде/чате/коммитах).
- Telegram-ноды: typeVersion telegram v1.2, switch v3.4; neverError — вложенный `options.response.response.neverError`; HTTP-ноды платных вызовов — typeVersion 4.5 + keypair-заголовки.

<!-- autopilot:start -->
# Контент-завод: доводка к сдаче

Прогон навыком `/autopilot` (slug: release-readiness, 16.08.2026): полный аудит дыр, спека, таски, фиксы без траты платных API (scrapecreators/creatify).

## Как здесь работает Autopilot

Сборка ведётся навыком `/autopilot`. Требования, спецификация и таски — в `.autopilot/release-readiness/`.
Прогресс — `.autopilot/dashboard.html`. Правило: требование из `manifest.md`
может снять только пользователь.

Если работа продолжается — скажи «продолжи автопилот»: состояние поднимется
из `.autopilot/state.js`, переспрашивать ничего не нужно.

## Инфраструктура (тикет 08, done 16.08)

- Миграции БД воспроизводимы из репо: `python3 -m pytest tests/test_migrations.py`
  (v1+v2+v3 поверх 001-init+002, идемпотентно; схема v5). Запуск вручную:
  `infra/db/migrate.sh` (или каждый `migrate-client-profiles*.py <db> --apply`).
- `docker-compose.yml` — витрина live-стека (n8n 2.34.4 + db-bridge + cloudflared),
  НЕ применять на сервере вслепую.
- Регистрация TG-команд: `register-tg-commands-35.sh` (35 команд, tg-commands-35.json);
  `register-tg-commands.sh` — диспетчер, делегирует новейшему payload (не затирает 35).
- Секреты — только имена переменных (`.env.example` — полный шаблон); `.env`/`.env.*`
  в `.gitignore`; история переписана `git filter-repo` (13.08), ротация ключей — за
  пользователем.
<!-- autopilot:end -->
