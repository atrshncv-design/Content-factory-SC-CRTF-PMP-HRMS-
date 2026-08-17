window.STATE =
{
  "slug": "avatar-carousel",
  "title": "TG-бот: карусель стоковых аватаров + аудит кнопок",
  "mode": "semi",
  "depth": "normal",
  "polish": null,
  "tier": "T1",
  "briefFile": "2026-08-17-brief.md",
  "memoryFile": "AGENTS.md",
  "startedAt": "2026-08-17T09:03:34+04:00",
  "updatedAt": "2026-08-17T10:32:00+04:00",
  "finishedAt": null,
  "stages": [
    { "id": "preflight", "status": "done", "startedAt": "2026-08-17T09:03:34+04:00", "finishedAt": "2026-08-17T09:05:50+04:00" },
    { "id": "manifest",  "status": "done", "startedAt": "2026-08-17T09:05:50+04:00", "finishedAt": "2026-08-17T09:06:05+04:00", "note": "7 требований" },
    { "id": "briefing",  "status": "done", "startedAt": "2026-08-17T09:06:10+04:00", "finishedAt": "2026-08-17T09:08:00+04:00", "note": "2 вопроса: одна карусель М→Ж; GET /api/personas/ + сверка" },
    { "id": "spec",      "status": "done", "startedAt": "2026-08-17T09:08:00+04:00", "finishedAt": "2026-08-17T09:26:40+04:00", "note": "G2: 8 находок, все внесены" },
    { "id": "plan",      "status": "done", "startedAt": "2026-08-17T09:26:40+04:00", "finishedAt": "2026-08-17T09:45:10+04:00", "note": "T1: 3 таска, 2 волны (01+03 параллельно)" },
    { "id": "build",     "status": "active", "startedAt": "2026-08-17T09:45:10+04:00" },
    { "id": "review",    "status": "pending" },
    { "id": "final",     "status": "pending" }
  ],
  "requirements": {
    "total": 7, "done": 0, "inTicket": 7, "inSpec": 0,
    "placeholder": 0, "deferred": 0, "dropped": 0
  },
  "tickets": [
    { "id": "01", "title": "Данные: 20 стоковых аватаров из /api/personas/", "requirements": ["R03"], "blockedBy": [], "wave": 1, "zone": [".autopilot/avatar-carousel/"], "status": "done", "startedAt": "2026-08-17T09:52:00+04:00", "finishedAt": "2026-08-17T10:14:30+04:00", "tests": "самопроверка скриптом: 20/10м/10ж/чередование/[0]=m ok; ревью: manifest clean, spec clean, 2 non-blocking", "commit": "bb578ca", "retries": 0 },
    { "id": "03", "title": "Аудит: маршрутизация кнопок + wf-tg-alerts", "requirements": ["R01"], "blockedBy": [], "wave": 1, "zone": ["tests/", "workflows/wf-tg-alerts.json"], "status": "review", "startedAt": "2026-08-17T09:52:00+04:00", "retries": 0 },
    { "id": "02", "title": "Карусель аватаров в wf-tg-bot.json", "requirements": ["R02", "R04", "R05", "R06", "R07"], "blockedBy": ["01", "03"], "wave": 2, "zone": ["workflows/wf-tg-bot.json", "tests/"], "status": "in-progress", "startedAt": "2026-08-17T10:32:00+04:00", "retries": 0 }
  ],
  "singlePass": null,
  "tests": null,
  "debt": { "placeholders": [], "assumptions": [], "emptyEnv": [] },
  "additions": ["A01 → R05 — кнопка «Мои аватары» в карусели (сохранение входа к своим BYOA)"],
  "coverage": { "findings": 8, "fixed": 7, "explained": 1, "note": "«подборки М/Ж отдельными сообщениями» — закрыто решением брифинга (одна карусель), остальное внесено в спеку" },
  "blind": null
}
