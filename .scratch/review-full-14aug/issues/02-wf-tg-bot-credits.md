# 02 — Ревью wf-tg-bot: платные цепочки и кредитные гейты

**What to review:** построчное ревью платных веток `workflows/wf-tg-bot.json` (404 ноды): вызовы SC/creatify/publish, mock/real-переключатели, кредитные гейты, валидация входов, защита от трат.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

**Контекст субагенту:** файл `workflows/wf-tg-bot.json` в корне репо (рабочая копия = live 14.08, 404 ноды). Чек-лист `references/workflow-review-checklist.md` (12 пунктов: контракты webhook, mock/real, валидация, low_credits-гейты, typeVersion 4.5, jsonBody, SSRF, error-handling); цены — `references/api-pricing-budget.md` (audience=26, ads_clone=84, ai_shorts 5/30с, URL-to-video 5/30с); прецедент — `references/ux2-menu-t4.md` (гейт 10/50 на ВСЕХ входах платной цепочки), `references/ux2-menu-t5a.md` (AI Shorts). Сети нет, только чтение файлов репо.

- [ ] Все платные HTTP-вызовы (SC: creators-search/creator-profile/creator-content/audience/transcripts/comments; creatify: link/submit/shorts/ads_clone/asset; postmypost): есть ли validate → Switch valid → mock/real, никогда ли реальный вызов без гейта
- [ ] Кредитные гейты 10/50 на КАЖДОМ входе платной цепочки (direct-команда, callback, regen, shorts) — включая обходы (ветка в обход LB/gate)
- [ ] mock/real-переключатели: `$env.X === 'PLACEHOLDER...'` (строковое сравнение), fallbackOutput на Switch, real-ветка на out[1]
- [ ] typeVersion HTTP-нод (4.5 + keypair-заголовки + вложенный neverError), таймауты (сумма bridge-вызовов ≤ timeout вызывающего)
- [ ] Валидация входов (URL, длительность, платформы) до платных вызовов; SSRF-защита
- [ ] Хардкод tg_user_id 941296693 в SQL-нодах (должно быть `$('Parser').first().json.tg_user_id`)
- [ ] Балансы: живые GET (бесплатные), универсальный парсер (body→raw→JSON.parse(data))
- [ ] Отчёт: таблица находок (severity, нода, влияние, доказательство), раздел «проверено и работает», вердикт по платным цепочкам
