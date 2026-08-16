window.STATE =
{
  "slug": "release-readiness",
  "title": "Контент-завод: доводка к сдаче (release readiness)",
  "mode": "interview",
  "depth": "normal",
  "polish": null,
  "tier": "T3",
  "briefFile": "2026-08-16-brief.md",
  "memoryFile": "AGENTS.md",
  "startedAt": "2026-08-16T08:09:59+04:00",
  "updatedAt": "2026-08-16T12:15:00+04:00",
  "finishedAt": null,
  "stages": [
    {
      "id": "preflight",
      "status": "done",
      "startedAt": "2026-08-16T08:09:59+04:00",
      "finishedAt": "2026-08-16T08:13:00+04:00"
    },
    {
      "id": "manifest",
      "status": "done",
      "startedAt": "2026-08-16T08:13:00+04:00",
      "finishedAt": "2026-08-16T08:14:00+04:00"
    },
    {
      "id": "briefing",
      "status": "done",
      "startedAt": "2026-08-16T08:14:00+04:00",
      "finishedAt": "2026-08-16T08:55:33+04:00",
      "note": "9 вопросов"
    },
    {
      "id": "spec",
      "status": "done",
      "startedAt": "2026-08-16T08:55:33+04:00",
      "finishedAt": "2026-08-16T09:15:00+04:00",
      "note": "G2: 4 полупокрытия, исправлено"
    },
    {
      "id": "plan",
      "status": "done",
      "startedAt": "2026-08-16T09:15:00+04:00",
      "finishedAt": "2026-08-16T09:44:19+04:00",
      "note": "9 тасок, ярус T3"
    },
    {
      "id": "build",
      "status": "active",
      "startedAt": "2026-08-16T09:44:19+04:00"
    },
    {
      "id": "review",
      "status": "pending"
    },
    {
      "id": "final",
      "status": "pending"
    }
  ],
  "requirements": {
    "total": 19,
    "done": 12,
    "inTicket": 5,
    "inSpec": 0,
    "placeholder": 1,
    "deferred": 1,
    "dropped": 0
  },
  "tickets": [
    {
      "id": "01",
      "title": "TG-бот: команды, кнопки и доставка видео",
      "requirements": [
        "G09",
        "G03",
        "G05"
      ],
      "blockedBy": [],
      "wave": 1,
      "zone": [
        "workflows/wf-tg-bot.json",
        "workflows/wf-creatify-webhook.json",
        "tg-commands-35.json",
        "register-tg-commands-35.sh"
      ],
      "status": "done",
      "retries": 0,
      "startedAt": "2026-08-16T09:48:25+04:00"
    },
    {
      "id": "02",
      "title": "Полный цикл: аналитика → тема → сценарий → JSON → submit",
      "requirements": [
        "G03",
        "G09",
        "G04"
      ],
      "blockedBy": [
        "04"
      ],
      "wave": 2,
      "zone": [
        "workflows/wf-analytics.json",
        "workflows/wf-creatify-link.json",
        "workflows/wf-creatify-submit.json",
        "hermes/skills/analyst.md",
        "hermes/skills/scriptwriter.md",
        "hermes/skills/json-builder.md",
        "hermes-bridge/server.py"
      ],
      "status": "done",
      "retries": 0
    },
    {
      "id": "03",
      "title": "Премиум-воркфлоу Creatify: avatar, banner, product, asset, adclone, inspiration, text",
      "requirements": [
        "R10i",
        "G09"
      ],
      "blockedBy": [
        "01"
      ],
      "wave": 2,
      "zone": [
        "workflows/wf-tg-bot.json",
        "workflows/wf-creatify-avatar.json",
        "workflows/wf-creatify-banner.json",
        "workflows/wf-creatify-product.json",
        "workflows/wf-creatify-asset.json",
        "workflows/wf-creatify-adclone.json",
        "workflows/wf-creatify-text.json"
      ],
      "status": "done",
      "retries": 0
    },
    {
      "id": "04",
      "title": "Качество контента: промпты hermes-скиллов",
      "requirements": [
        "G08",
        "G09"
      ],
      "blockedBy": [],
      "wave": 1,
      "zone": [
        "hermes/skills/analyst.md",
        "hermes/skills/scriptwriter.md",
        "hermes/skills/json-builder.md",
        "hermes/skills/onboarding.md",
        "hermes/skills/orchestrator.md"
      ],
      "status": "done",
      "retries": 0,
      "startedAt": "2026-08-16T09:48:25+04:00"
    },
    {
      "id": "05",
      "title": "ScrapeCreators: аналитика, поиск авторов, профили, аудитория, контент, транскрипты",
      "requirements": [
        "R10i",
        "G09"
      ],
      "blockedBy": [],
      "wave": 1,
      "zone": [
        "workflows/wf-analytics.json",
        "workflows/wf-audience.json",
        "workflows/wf-creators-search.json",
        "workflows/wf-creator-profile.json",
        "workflows/wf-creator-content.json",
        "workflows/wf-transcripts-comments.json"
      ],
      "status": "done",
      "retries": 0,
      "startedAt": "2026-08-16T09:48:25+04:00"
    },
    {
      "id": "06",
      "title": "Публикация: wf-publish, publish-status, sync-accounts, 7 платформ",
      "requirements": [
        "G07",
        "G09"
      ],
      "blockedBy": [],
      "wave": 2,
      "zone": [
        "workflows/wf-publish.json",
        "workflows/wf-publish-status.json",
        "workflows/wf-sync-accounts.json"
      ],
      "status": "done",
      "retries": 0
    },
    {
      "id": "07",
      "title": "Клиентские профили, роли и hermes-bridge",
      "requirements": [
        "G05",
        "G04",
        "R01"
      ],
      "blockedBy": [],
      "wave": 1,
      "zone": [
        "workflows/wf-tg-bot.json",
        "hermes-bridge/server.py",
        "infra/db/migrate-client-profiles*.py"
      ],
      "status": "done",
      "retries": 0,
      "startedAt": "2026-08-16T09:50:00+04:00"
    },
    {
      "id": "08",
      "title": "Системное: миграции, деплой-скрипты, DEPLOYMENT, секреты",
      "requirements": [
        "R01",
        "R09i",
        "R10i"
      ],
      "blockedBy": [],
      "wave": 1,
      "zone": [
        "infra/db/",
        "docker-compose.yml",
        "DEPLOYMENT.md",
        "register-tg-commands*.sh",
        ".env.example",
        "AGENTS.md"
      ],
      "status": "done",
      "retries": 0
    },
    {
      "id": "09",
      "title": "Полный E2E smoke (0 кредитов)",
      "requirements": [
        "R01",
        "R06",
        "G09"
      ],
      "blockedBy": [
        "01",
        "02",
        "03",
        "04",
        "05",
        "06",
        "07",
        "08"
      ],
      "wave": 3,
      "zone": [
        "workflows/",
        "hermes/",
        "infra/"
      ],
      "status": "done",
      "retries": 0
    }
  ],
  "singlePass": null,
  "tests": null,
  "debt": {
    "placeholders": [
      "G01 — postmypost-аккаунты подключит пользователь перед платными тестами"
    ],
    "assumptions": [
      "дедлайн — конец дня 17.08.2026"
    ],
    "emptyEnv": [
      "POSTMYPOST_TOKEN",
      "SCRAPECREATORS_API_KEY",
      "CREATIFY_API_ID",
      "CREATIFY_API_KEY",
      "TELEGRAM_BOT_TOKEN",
      "FACTORY_WEBHOOK_SECRET"
    ]
  },
  "additions": [
    "10 — ревью-фиксы безопасности (кросс-ревью волн 1+2): header-auth X-FACTORY-TOKEN на 21 webhook, fail-closed колбэк creatify, хардкод 941296693 убран, LB sc-ноды добавлены — done 16.08"
  ],
  "coverage": {
    "g2At": "2026-08-16T09:10:00+04:00",
    "findings": 4,
    "missing": [],
    "halfCovered": [
      "G04 — Robotec/БД не упоминалось в Решениях (исправлено)",
      "История 6 — 'впаяны' не определён (исправлено)",
      "История 7 — формат 30с не привязан к скиллам (исправлено)",
      "История 8 — VK-особенности не конкретизированы (исправлено)"
    ],
    "inSpecNotBrief": [
      "G-rows из интервью",
      "G09 — дословные симптомы пользователя",
      "контракт аудитора",
      "деплой-гейт",
      "миграция v3"
    ]
  },
  "blind": null
}