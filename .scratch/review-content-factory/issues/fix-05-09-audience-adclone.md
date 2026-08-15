# FIX-05+09 — wf-audience (гейт 26 кред) + wf-creatify-adclone (порог 90)

**Status:** ready-for-agent
**Blocked by:** —

## Задача
Исправить защиту трат в двух воркфлоу. Результат — два файла:
`.scratch/review-content-factory/fixes/wf-audience.json` и `.scratch/review-content-factory/fixes/wf-creatify-adclone.json`.

## A. wf-audience (сейчас 6 нод: audience-webhook → Switch platform → HTTP TikTok Audience → Normalize → Respond/Error Respond)
Проблемы: (1) эндпоинт `/v1/tiktok/user/audience` стоит **26 кредитов/запрос** — нет гейта; (2) нет валидации handle; (3) нет mock/real-переключателя.
Правки:
1. Валидация входа: `{platform, handle}` — handle обязателен и непуст; platform='tiktok' (остальное → Error Respond, как сейчас).
2. mock/real-переключатель: Switch `$env.SCRAPECREATORS_API_KEY === 'PLACEHOLDER_UNTIL_TOMORROW'` → mock-ветка (Code, фиктивный ответ `{ok:true, audience:{...top_countries:[{country:'RU',percent:50}]}}`) / real-ветка (существующий HTTP). fallbackOutput:"extra".
3. low_credits-гейт: перед HTTP — GET `/v1/account/credit-balance` (бесплатный, тот же кред httpHeaderAuth ...001) → Code: если `credits_remaining < 30` → Error Respond `{ok:false, error:'low_credits', balance}` без вызова дорогого эндпоинта.
4. ВАЖНО: HTTP-ноды n8n НЕ прокидывают входной item — для веток после двух Switch использовать кросс-нод-ссылки `$('Code validate').first().json.handle` (как в wf-creatify-banner/CR-6).
Эталон кросс-нод-ссылки: wf-creatify-banner — `$('Code validate banner').first().json.payload`.

## B. wf-creatify-adclone (сейчас 15 нод)
Проблема: порог low_credits = 20, а реальная цена **84 кредита** → запрос при балансе 21–83 уведёт в минус.
Правки:
1. Порог в Code balance / IF low credits: `balance < 20` → `balance < 90` (84 + запас).
2. В ответе успешного запуска добавить предупреждение о стоимости: поле `cost_warning: 'ad_clone стоит ~84 кредита'` (в Normalize).

## Ограничения
- Исходники `workflows/wf-audience.json`, `workflows/wf-creatify-adclone.json` НЕ менять.
- Никаких сетевых вызовов/SSH. Секреты не выводить.
- В отчёте: по каждому файлу таблица (нода | было | стало) + JSON новых нод.
- Язык: русский.
