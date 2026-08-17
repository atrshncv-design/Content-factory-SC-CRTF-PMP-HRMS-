window.STATE =
{
  "slug": "avatar-carousel",
  "title": "TG-бот: карусель стоковых аватаров + аудит кнопок",
  "mode": "semi",
  "depth": "normal",
  "polish": null,
  "tier": null,
  "briefFile": "2026-08-17-brief.md",
  "memoryFile": "AGENTS.md",
  "startedAt": "2026-08-17T09:03:34+04:00",
  "updatedAt": "2026-08-17T09:26:40+04:00",
  "finishedAt": null,
  "stages": [
    { "id": "preflight", "status": "done", "startedAt": "2026-08-17T09:03:34+04:00", "finishedAt": "2026-08-17T09:05:50+04:00" },
    { "id": "manifest",  "status": "done", "startedAt": "2026-08-17T09:05:50+04:00", "finishedAt": "2026-08-17T09:06:05+04:00", "note": "7 требований" },
    { "id": "briefing",  "status": "done", "startedAt": "2026-08-17T09:06:10+04:00", "finishedAt": "2026-08-17T09:08:00+04:00", "note": "2 вопроса: одна карусель М→Ж; GET /api/personas/ + сверка" },
    { "id": "spec",      "status": "done", "startedAt": "2026-08-17T09:08:00+04:00", "finishedAt": "2026-08-17T09:26:40+04:00", "note": "G2: 8 находок, все внесены" },
    { "id": "plan",      "status": "active", "startedAt": "2026-08-17T09:26:40+04:00" },
    { "id": "build",     "status": "pending" },
    { "id": "review",    "status": "pending" },
    { "id": "final",     "status": "pending" }
  ],
  "requirements": {
    "total": 7, "done": 0, "inTicket": 0, "inSpec": 7,
    "placeholder": 0, "deferred": 0, "dropped": 0
  },
  "tickets": [],
  "singlePass": null,
  "tests": null,
  "debt": { "placeholders": [], "assumptions": [], "emptyEnv": [] },
  "additions": ["A01 → R05 — кнопка «Мои аватары» в карусели (сохранение входа к своим BYOA)"],
  "coverage": { "findings": 8, "fixed": 7, "explained": 1, "note": "«подборки М/Ж отдельными сообщениями» — закрыто решением брифинга (одна карусель), остальное внесено в спеку" },
  "blind": null
}
