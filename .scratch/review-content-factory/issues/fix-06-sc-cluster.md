# FIX-06 — SC-кластер: валидация входов + mock/real-переключатели

**Status:** ready-for-agent
**Blocked by:** —

## Задача
Усилить 4 воркфлоу SC-кластера защитой от непреднамеренных трат.
Результат — 4 файла в `.scratch/review-content-factory/fixes/`:
`wf-creators-search.json`, `wf-creator-profile.json`, `wf-creator-content.json`, `wf-transcripts-comments.json`.

## Общие проблемы (все 4)
1. **Нет mock/real-переключателя**: при плейсхолдер-ключе (`PLACEHOLDER_UNTIL_TOMORROW`) пойдут реальные платные вызовы. Паттерн (как в wf-analytics): Switch `$env.SCRAPECREATORS_API_KEY === 'PLACEHOLDER_UNTIL_TOMORROW'` → mock-ветка (Code с фиктивным ответом по контракту воркфлоу) / real-ветка (существующие HTTP). `options: {"fallbackOutput":"extra"}`.
2. **Нет валидации входа**: пустой query/handle уходит в платный HTTP (~1 кред, без кэша).
   - creators-search: query обязателен (непустой после trim); platforms[] — если пуст → Error Respond `{ok:false, error:'no platforms'}` (сейчас поток обрывается в fallback Switch).
   - creator-profile / creator-content: handle обязателен; platform ∈ {instagram, youtube, tiktok, twitter} — иначе Error Respond.
   - transcripts-comments: url обязателен http(s); определение платформы из URL — по домену регуляркой `(^|\.)tiktok\.com$` и т.п., НЕ `url.includes('tiktok')` (сейчас подстрока в любом месте триггерит платный вызов).
3. Ошибки API (success:false, account_deactivated, 402 out of credits) — пробрасывать как `{ok:false, error:'api_error'|'account_deactivated'|'low_credits', status}` в Normalize (сейчас в creator-content/transcripts-comments теряются).

## По каждому воркфлоу
- **wf-creators-search**: добавить входной Switch mock + Code validate query; подключить fallback-выходы Switch IG/YT/TikTok к Error Respond.
- **wf-creator-profile**: входной Switch mock + Code validate (handle, platform).
- **wf-creator-content**: входной Switch mock + Code validate; account_deactivated/api_error в Normalize.
- **wf-transcripts-comments**: домен-парсинг платформы; Normalize проверяет body.success/statusCode → понятная ошибка.

## Ограничения
- Исходники НЕ менять. Никаких сетевых вызовов/SSH. Секреты не выводить.
- В отчёте: по каждому файлу таблица (нода | было | стало) + JSON новых нод.
- Язык: русский.
