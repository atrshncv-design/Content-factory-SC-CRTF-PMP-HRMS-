# 🏭 Контент-завод

Витринный демо-продукт для автоматизированной генерации и публикации короткого
вертикального видео-контента в соцсетях. Текущий демо-клиент — **Robotec**
(robotec.ru, B2B-интегратор промышленной робототехники KUKA).

## Архитектура

```
[TG юзер] ◄──────► [Hermes gateway (TG-бот)] ──► [Hermes agent (orchestrator)]
                                                         │  delegate_task → субагенты:
                                                         │    analyst / scriptwriter / json-builder / onboarding
                                                         │  memory: ~/.hermes/ (state machine в MEMORY.md)
                                                         │
                                                         ▼ terminal/curl
                                                  [n8n webhook ноды]
                                                         │
                                  ┌──────────────────────┼─────────────────────┐
                                  ▼                      ▼                     ▼
                          [wf-analytics]         [wf-creatify-*]        [wf-publish]
                                  │                      │                     │
                          ScrapeCreators API      Creatify API           Postmypost API
                                                         │
                                                  callback webhook
                                                         │
                                                  [n8n] → [wf-tg-alerts] → TG оператору
```

**Стек:**
- **Hermes Agent v0.20.0** (Nous Research) — мозг + TG-бот + cron.
- **n8n 2.34** — руки: HTTP, вебхуки, визуальные воркфлоу.
- **SQLite** (`factory.db`) — бизнес-данные.
- **LLM:** opencode zen → deepseek-v4-flash-free.
- **API:** ScrapeCreators (аналитика), Creatify (генерация видео), Postmypost (автопостинг).
- **Публичный доступ:** cloudflared tunnel.

## Структура репозитория

```
.
├── DEPLOYMENT.md              # статус среды на сервере (читать первым)
├── docker-compose.yml         # n8n + caddy + db-bridge + cloudflared
├── .env.example               # шаблон переменных окружения
├── specs/                     # спецификации (15 файлов)
│   ├── README.md              # индекс спек
│   ├── 00-architecture.md     # компоненты, развёртывание, потоки данных
│   ├── 01-database.md         # SQLite схема
│   ├── 02-analytics.md        # ScrapeCreators
│   ├── 03-agents.md           # субагенты Hermes
│   ├── 04-generation.md       # Creatify
│   ├── 05-publishing.md       # Postmypost
│   ├── 06-telegram-bot.md     # TG-бот
│   ├── 07-self-analytics.md   # метрики своих роликов (P2)
│   ├── 08-onboarding.md       # онбординг клиента из URL
│   ├── 09-dashboard.md        # веб-дашборд (P2)
│   ├── 10-hermes-runtime.md   # runtime Hermes
│   ├── 10-validation-report.md # отчёт спайка T-030
│   ├── 11-amendments.md       # поправки к спекам 03/06/10 (приоритет при конфликте)
│   ├── 12-telegram-ux.md      # UX/state machine/inline-кнопки
│   └── TICKETS.md             # тикеты по фазам (P0/P1/P2)
├── hermes/
│   ├── Dockerfile             # каркас (НЕ используется — Hermes в venv)
│   ├── config.yaml            # конфиг Hermes (без секретов)
│   └── skills/                # промпты субагентов (оригиналы, на VM в ~/.hermes/skills/)
├── infra/
│   ├── Caddyfile              # reverse-proxy (не используется — cloudflared)
│   ├── db-bridge/             # HTTP-мост к SQLite (server.js)
│   └── db/
│       ├── 001_init.sql       # миграция БД
│       └── migrate.sh         # скрипт миграций
├── workflows/                 # JSON-импорты n8n-воркфлоу (для воспроизведения)
└── docs/prompts/              # промпты для агента-разработчика по сессиям
```

## Развёртывание

Полная инструкция — в `DEPLOYMENT.md`. Кратко:

1. VPS (Ubuntu 24.04+, 2 vCPU, 4 GB RAM, 40 GB SSD).
2. Установить Docker + Compose.
3. Скопировать проект на сервер.
4. `cp .env.example .env` и заполнить секретами.
5. `docker compose up -d`.
6. Установить Hermes Agent в venv, настроить config + skills.
7. `systemd` для Hermes gateway.
8. cloudflared tunnel для публичного HTTPS.

## Фазы

- **P0 / Фаза 1** ✅ — инфраструктура, 11 n8n-воркфлоу (mock), Hermes gateway,
  state machine, Telegram UX. Завершена.
- **Фаза 2** ⏳ — подстановка ключей платных API, end-to-end тест.
- **P1** — автопилот (cron в 09:00 + автопостинг).
- **P2** — аналитика собственных роликов, веб-дашборд, мульти-тенантность.

## Документация

- `DEPLOYMENT.md` — статус среды, доступы, что работает.
- `specs/README.md` — индекс всех спецификаций.
- `specs/TICKETS.md` — гранулярные задачи по фазам.

## Безопасность

- Все секреты — только в `.env` (права 600), в git не попадают.
- Перед коммитом реальные ключи/пароли заменены на placeholder
  `PLACEHOLDER_REPLACE_*`.
- SSRF-защита в wf-onboard.
- Path-token на webhook'ах creatify.
- Whitelist Telegram user_id.

## Лицензия

Proprietary. © 2026
