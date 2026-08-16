# 05-findings — аудит кластера ScrapeCreators

## Дыры вне тикета 05

Явных дыр **вне scope тикета 05** (другие кластеры / инфра / бот) не обнаружено. Все находки ограничены 6 воркфлоу SC-аналитики и закрыты в рамках тикета.

## Найденные и исправленные находки в рамках тикета 05

| id | кластер | severity | файл:нода | доказательство | гипотеза фикса | платный_риск |
|---|---|---|---|---|---|---|
| 05-01 | SC-analytics | 🔴 | wf-analytics.json:HTTP IG/HTTP TikTok/HTTP YouTube | Отсутствовал гейт `low_credits` до платных вызовов; при реальном ключе 3 параллельных SC-запроса шли без проверки баланса | Заменить 3 per-platform mock-switch на общий `Switch mock` → `HTTP Credit Balance` → `Code balance` → `IF low credits` → платные HTTP; при `<5` кредитов — `Respond low credits` | да |
| 05-02 | SC-analytics | 🟠 | wf-analytics.json:HTTP IG/HTTP TikTok/HTTP YouTube | SC HTTP-ноды использовали `credentials.httpHeaderAuth` вместо keypair-заголовка `x-api-key` | Перевести на `authentication:none` + `sendHeaders:true` + `specifyHeaders:keypair` + `x-api-key: {{ $env.SCRAPECREATORS_API_KEY }}` | да (утечка/неправильная авторизация) |
| 05-03 | SC-all | 🟠 | все 6 wf:* HTTP ScrapeCreators | Отсутствовал вложенный `options.response.response.neverError` на SC HTTP-нодах | Добавить `neverError:true` в `options.response.response` всем SC HTTP (credit-balance + платные) | да (падение на 4xx) |
| 05-04 | SC-search | 🔴 | wf-creators-search.json:Normalize YouTube | jsCode использует `c.handle`, `c.subscriberCountInt` и др., хотя итерирует `for (const p of items)` | Заменить `c.*` на `p.*` внутри цикла | нет (баг данных) |
| 05-05 | SC-cluster | 🔴 | wf-creators-search.json:Respond low credits, wf-creator-profile.json:Respond low credits, wf-creator-content.json:Respond low credits, wf-transcripts-comments.json:Respond low credits transcript/comments | `responseBody` содержал `={ { ... } }` (пробел внутри выражения) — n8n не оценит объект, оператор не получит понятное сообщение при `low_credits` | Исправить на `={{ { ... } }}` | нет (UX) |
| 05-06 | SC-cluster | 🟡 | wf-creator-content.json:HTTP IG/HTTP TikTok/HTTP YouTube/HTTP Twitter | Все 4 HTTP-ноды имеют одинаковую позицию `[0,0]` — рабочий, но нечитаемый canvas | Расставить позиции при следующем редизайне (функционально не критично) | нет |

## Примечания

- Все 6 воркфлоу проходят JSON-валидацию и `node --check` для jsCode.
- В `wf-transcripts-comments.json` валидатор BFS сообщает о "недостижимых" comments-нодах — это ложная тревога: воркфлоу содержит два независимых webhook (`transcript-webhook` и `comments-webhook`), и BFS валидации запускается только от первого.
- Mock/real-переключатели везде реализованы через `Switch` с `string-equals` на `$env.SCRAPECREATORS_API_KEY === 'PLACEHOLDER_UNTIL_TOMORROW'` и `fallbackOutput: "extra"`.
- Парсеры `credit-balance` и нормализаторы дополнены обработкой JSON-строки в `input.data` / `resp.data` / `body.data`.
