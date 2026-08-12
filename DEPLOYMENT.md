# DEPLOYMENT — финальный статус среды на сервере

**Сервер:** `83.166.233.95` (VK Cloud, Ubuntu 24.04.4 LTS, STD3-2-4-50GB)
**Подготовил:** оркестратор (ZCode), 2026-08-11
**Статус среды:** ✅ **полностью готова к работе агента-разработчика**
**Spike T-030:** ✅ закрыт, архитектура NATIVE подтверждена

---

## 1. Что готово

| Компонент | Статус | Где |
|-----------|--------|-----|
| Docker 29.7.2 + Compose v5.4.0 | ✅ | — |
| Swap 4GB | ✅ | `/swapfile` |
| n8n 2.34.4 (healthy) | ✅ | docker `factory-n8n` |
| SQLite `factory.db` (13 таблиц + seed) | ✅ | `~/factory/data/factory.db` |
| Cloudflared tunnel (обход firewall VK) | ✅ | docker `factory-cloudflared-n8n` |
| Публичный HTTPS к n8n | ✅ | см. URL ниже |
| n8n owner-аккаунт | ✅ | см. доступы |
| **Hermes Agent v0.20.0** | ✅ установлен в venv | `~/hermes-agent/.venv/` |
| **LLM opencode zen / deepseek v4** | ✅ настроен и проверен | `~/.hermes/{config.yaml,.env}` |
| **systemd-юнит hermes.service** | ✅ создан, **не запущен** (ждёт TG-setup) | `/etc/systemd/system/hermes.service` |

## 2. Доступы

### SSH
```bash
ssh -i <путь-к-ключу>.pem ubuntu@83.166.233.95
```

### n8n UI (через cloudflared)
- URL: **https://assessment-fossil-assignments-alice.trycloudflare.com**
- Логин: `owner@factory.local`
- Пароль: `PLACEHOLDER_REPLACE_N8N_PASSWORD` ⚠️ сменить
- Узнать актуальный URL (если контейнер рестартился):
  ```bash
  docker logs factory-cloudflared-n8n 2>&1 | grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" | head -1
  ```

### Hermes
```bash
ssh ubuntu@83.166.233.95
export PATH="$HOME/.local/bin:$PATH"
source ~/hermes-agent/.venv/bin/activate
hermes <command>
```

### VNC-консоль (VK Cloud панель)
- Логин: `ubuntu`, пароль: `PLACEHOLDER_REPLACE_VNC_PASSWORD` ⚠️ сменить (`passwd`).

---

## 3. Архитектура (итог после spike T-030)

```
[TG юзер] ◄──────► [Hermes gateway (TG бот)] ──► [Hermes agent (orchestrator)]
                                                         │  delegate_task(Аналитик/Сценарист/JSON)
                                                         │  memory: ~/.hermes/
                                                         │
                                                         ▼ terminal/curl
                                                  [n8n webhook ноды]
                                                         │
                                  ┌──────────────────────┼─────────────────────┐
                                  ▼                      ▼                     ▼
                          [wf-analytics]         [wf-creatify-*]        [wf-publish]
                                  │                      │                     │
                          scrapecreators API       creatify API         postmypost API
                                                         │
                                                  callback webhook
                                                         │
                                                  [n8n] → [wf-tg-alerts] → TG оператору
```

**Ключевые точки:**
- Приём TG-сообщений: **только Hermes** (hermes gateway).
- n8n TG-ноды: **только Send** (алерты, через тот же токен бота).
- Hermes → n8n: через `terminal` (`curl http://n8n:5678/webhook/factory/<wf>`).
- n8n → оператор (алерты): через `wf-tg-alerts`.
- БД: `factory.db` для бизнес-данных, `~/.hermes/state.db` для agent-state.

Подробнее — **`specs/11-amendments.md`** (обязательно прочитать).

---

## 4. Файловая структура

```
~/factory/                       # проект
├── .env                         # переменные окружения (секреты)
├── docker-compose.yml           # n8n + caddy (Hermes в venv, не docker)
├── DEPLOYMENT.md                # этот файл
├── data/factory.db              # SQLite бизнес-данные
├── media/                       # MP4 от creatify
├── infra/
│   ├── Caddyfile
│   └── db/{001_init.sql, migrate.sh}
├── hermes/
│   ├── config.yaml              # ⚠️ УСТАРЕЛ — реальный в ~/.hermes/config.yaml
│   ├── Dockerfile               # ⚠️ УСТАРЕЛ — Hermes в venv, не docker
│   └── skills/                  # промпты субагентов (перенести в ~/.hermes/skills/)
└── specs/                       # все 15 спек + тикеты + отчёты
    ├── README.md                # стартовый индекс
    ├── 00-architecture.md
    ├── 01-database.md
    ├── 02-analytics.md
    ├── 03-agents.md             # ⚠️ раздел 7.1 устарел → 11-amendments
    ├── 04-generation.md
    ├── 05-publishing.md
    ├── 06-telegram-bot.md       # ⚠️ суперседится → 11-amendments
    ├── 07-self-analytics.md
    ├── 08-onboarding.md
    ├── 09-dashboard.md
    ├── 10-hermes-runtime.md     # ⚠️ разделы 3,5,8 устарели → 11-amendments
    ├── 10-validation-report.md  # отчёт спайка T-030
    ├── 11-amendments.md         # ⚠️ ПРИОРИТЕТ при конфликте
    └── TICKETS.md               # тикеты (T-030..T-035, T-080..T-081 уже обновлены)

~/hermes-agent/                  # клон репо Hermes
└── .venv/                       # Python 3.11 venv с установленным Hermes

~/.hermes/                       # данные Hermes
├── config.yaml                  # реальный config (provider: opencode-zen)
├── .env                         # ключи (chmod 600)
├── state.db                     # сессии/память Hermes
└── memories/                    # MEMORY.md, USER.md
```

---

## 5. Что нужно от заказчика

| Что | Статус | Применение |
|-----|--------|------------|
| LLM opencode zen (deepseek v4) | ✅ есть | Hermes |
| Telegram бот токен | ✅ есть | Hermes gateway |
| TG user_id оператора (941296693) | ✅ есть | whitelist |
| SCRAPECREATORS_API_KEY | ❌ | wf-analytics |
| CREATIFY_API_ID + CREATIFY_API_KEY | ❌ | wf-creatify-* |
| POSTMYPOST_TOKEN + POSTMYPOST_PROJECT_ID | ❌ | wf-publish* |
| Подключить Instagram/Threads в кабинете postmypost | ❌ | автопостинг |

`❌` — запросишь у заказчика, добавишь в `~/factory/.env` и в n8n Credentials.

---

## 6. Запущенные сервисы сейчас

```
$ docker ps
factory-n8n               Up (healthy)
factory-cloudflared-n8n   Up
factory-caddy             Up (можно остановить — не используется)
```

Hermes **не запущен** — ждёт, пока разработчик выполнит `hermes gateway setup`
(подключение Telegram). После этого:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now hermes
journalctl -u hermes -f
```

---

## 7. Что разработчик делает в первую очередь (T-031' и T-032')

1. **T-032'** — `hermes gateway setup` → выбрать Telegram → ввести токен → whitelist 941296693.
2. Проверить: написать боту `/start`, Hermes должен ответнуть.
3. `sudo systemctl enable --now hermes` — Hermes как сервис.
4. **T-033'** — скопировать skills из `~/factory/hermes/skills/*.md` в `~/.hermes/skills/`.
5. **T-034'** — в n8n UI добавить webhook-ноды `/webhook/factory/<wf>` в каждый воркфлоу.
6. Дальше — по `specs/TICKETS.md` от T-040 (онбординг) → T-050 (аналитика) → ... → T-092.

---

## 8. Известные проблемы и риски

1. **Firewall VK режет все входящие извне.** Решено через cloudflared (исходящее соединение).
2. **Quick-tunnel URL меняется при рестарте контейнера.** Для стабильного URL — named tunnel с доменом.
3. **RAM 4GB + swap 4GB.** n8n + Hermes хватает, но тяжёлые операции — мониторить `free -h`.
4. **Free-тир deepseek v4 — временная акция.** Запасной вариант: `deepseek-v4-flash` (платный).
5. **Спеки 03/06/10 частично устарели.** Перед стартом — `specs/11-amendments.md`.
6. **Ключи/пароли в открытом чате.** На прод — ротация (VNC пароль, TG токен, n8n пароль).

---

## 9. Поддержка

- Архитектурные вопросы — к оркестратору (ZCode).
- Все правки спек после spike — в `specs/11-amendments.md`.
- Логи: `docker logs`, `journalctl -u hermes`, `sqlite3 ~/factory/data/factory.db "SELECT * FROM logs ORDER BY ts DESC LIMIT 20;"`.

**Среда готова. Жду агента-разработчика.**
