# Issue tracker: Local Markdown

Issues and specs (PRD) for this repo live as markdown files in `.scratch/`.

## Conventions

- One feature per directory: `.scratch/<feature-slug>/`
- The spec is `.scratch/<feature-slug>/spec.md`
- Implementation issues are one file per ticket at `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01` — never a single combined tickets file
- Triage state is recorded as a `Status:` line near the top of each issue file (`ready-for-agent` / `done` / `failed`)
- Comments and conversation history append to the bottom of the file under a `## Comments` heading

## When a skill says "publish to the issue tracker"

Create a new file under `.scratch/<feature-slug>/` (creating the directory if needed).

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user will normally pass the path or the issue number directly.

## Workflow notes for this repo (контент-завод)

- Source of truth for live workflows is the **server** (`~/factory/`), not the repo. Before reworking a workflow, find the newest version across all `.scratch/*/fixes/`; the repo `workflows/` is synced only at deploy time.
- Each ticket is implemented by a separate subagent on the live export in `.scratch/<feature-slug>/base/`.
- Every ticket ends with `Status: done` (or `failed` after one retry) in its own file; PROGRESS.md at the repo root tracks the wave.
- Hard rule: no paid API calls (creatify/scrapecreators) without explicit user consent — tests run «до точки списания».
