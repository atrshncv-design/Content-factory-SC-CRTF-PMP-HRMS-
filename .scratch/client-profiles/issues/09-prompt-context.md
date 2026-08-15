# 09 — Контекст активного профиля в промптах генерации (ядро «не путать контекст»)

**What to build:** Промпты генерации (аналитик, сценарист, ретрай) строятся из контекста АКТИВНОГО профиля per-чат вместо хардкода «Клиент: Robotec (промышленная робототехника, интегратор KUKA…)». Контекст включает описание, ЦА, ссылки и дайджесты документов профиля.

**Blocked by:** 05 (нужен per-чат резолв активного клиента)

**Status:** done (14.08, верифицировано оркестратором)

- [x] 4 цепочки CTX (SC/CT/ET/AU): CTX Build (SELECT name/niche/description/audience_json/tone/context_links/context_docs FROM clients WHERE id=(резолв T5 бит-в-бит из PF Build)) → CTX HTTP (db-bridge) → CTX Format (ctx-блок: название(ниша), описание, ЦА (raw/type), тон, ссылки ≤5, документы ≤2000; пусто → «Клиент: не указан (…)»)
- [x] Вставлены в пути веток ПЕРЕД промпт-билдерами (SC: Switch SC analytics → SC CTX* → SC Build bridge prompt; CT: CT HTTP qp → CT CTX* → CT Build bridge prompt; ET: ET HTTP reject old → ET CTX*; AU: AU HTTP session → AU CTX*)
- [x] Промпт-билдеры используют ctx вместо хардкода; grep: 0 вхождений «Клиент: Robotec» / «для клиента Robotec»
- [x] Валидации (ОРКЕСТРАТОР): validate 0 issues (712 нод), lint 0, node --check 12/12, sim (SC CTX Format с клиентом → все фрагменты в ctx; пусто → «не указан»; SC Build bridge prompt использует ctx, Robotec отсутствует); wiring SC CTX HTTP → SC CTX Format ($json-чтение — корректно)

Артефакт: `.scratch/client-profiles/fixes/wf-tg-bot.json` (712 нод; снапшот `wf-tg-bot.09.json`)

Примечания: доки-дайджесты могут отсутствовать (поле NULL) — блок «документы» опускается. Обрезки: links ≤5, docs ≤2000 симв. Ссылки в контексте — это ресурсы компании (сайт/соцсети/статьи), не source_url темы.
