# C2+B3+части — Финальные правки wf-tg-bot (после B2)

**Файл:** `.scratch/review-full-14aug/fixes/wf-tg-bot.json` (база = результат B2)
**Что входит (мелкие правки одного файла, объединены чтобы не гонять 3 субагента):**

1. **C2-часть (Y4):** `DU Gate` — формула `Math.round(5*dur/30)` → `5 * Math.ceil(dur/30)` (эталон SH Gate; округление creatify вверх)
2. **B3-часть (Y10):** Parser — добавить `'/instruction': 'instruction'` в C-маппинг (единственная из 31 без латинского слеша)
3. **C1-AS-часть (Y2):** AS-цепочка (approve:script → creatify-link/submit) — кредитный гейт: при approve:script проверить баланс creatify (переиспользовать паттерн DU LB creatify → parse → gate; минимально: если balance < 10 → сообщение «недостаточно кредитов» + отказ, НЕ вызывать link) — ЕСЛИ не сделано в B1 (B1 добавлял neverError; проверить, есть ли уже гейт на AS-пути; если AS Check link/submit уже блокируют при error — гейт по балансу может быть избыточен, решить и описать)

**Контекст для субагента:** 0 кредитов; esc-эталон MO Format (байт-точно); сериализация indent=1/ensure_ascii=False/без trailing newline; tg_user_id 941296693 не трогать; BFS обязателен; минимальные правки; validate 0 issues + lint 0 + sim.
