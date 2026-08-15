# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root, or
- **`CONTEXT-MAP.md`** at the repo root if it exists — it points at one `CONTEXT.md` per context.
- **`docs/adr/`** — read ADRs that touch the area you're about to work in.

If any of these files don't exist, **proceed silently**.

## File structure

Single-context repo:

```
/
├── CONTEXT.md
├── docs/adr/
│   └── 0001-per-chat-client-profiles.md
├── specs/           ← project specs 00–13 (architecture, DB, TG UX, n8n orchestration)
├── workflows/       ← n8n workflow exports (synced from server at deploy time)
└── .scratch/        ← feature work dirs: spec.md + issues/ per feature
```

## Use the glossary's vocabulary

Use the terms defined in `CONTEXT.md` (клиент, профиль, активный профиль, цикл, сессия, поколение и т.д.). Don't drift to synonyms the glossary avoids.

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding.
