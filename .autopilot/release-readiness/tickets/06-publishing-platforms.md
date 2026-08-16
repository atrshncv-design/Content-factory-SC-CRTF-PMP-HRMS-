# 06 — Публикация: wf-publish, publish-status, sync-accounts, 7 платформ

**Требования:** G07 (7 платформ), G09 (полный цикл до автопостинга)
**Blocked by:** —
**Зона:** `workflows/wf-publish.json`, `workflows/wf-publish-status.json`, `workflows/wf-sync-accounts.json`
**Волна:** 2
**Status:** pending

## Что должно заработать

Публикация корректна для IG/TikTok/YouTube (видео) и TG/X/Threads/VK (текст). Text-only маршрут работает. Status-сron и sync-accounts cron живы.

## Из брифа / манифеста, дословно

> «+ текстовые: TG, X, Threads, VK»
> «аккаунты postmypost подключит пользователь перед платными тестами»

## Разделы спецификации

История 8.

## Критерии приёмки

- [ ] wf-publish Switch upload_needed корректен (не перевёрнут); text-only маршрут работает.
- [ ] Для 7 платформ заданы publication_type/platform_id и адаптация caption (X ≤280, Threads длинный, TG без markdown, VK-особенности задокументированы).
- [ ] wf-publish-status cron `*/2` работает без мёртвых IF any?/NoOp + (mock)-текстовых пометок.
- [ ] wf-sync-accounts cron синкает аккаунты; в БД 5 соцаккаунтов (IG/YT/Threads/X/TikTok), отсутствие VK-аккаунта — задокументировано.
- [ ] Валидатор + sim зелёные; 0 платных postmypost-вызовов на списание.
