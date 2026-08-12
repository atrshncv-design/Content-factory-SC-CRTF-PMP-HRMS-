# ПРОМПТ ДЛЯ АГЕНТА-РАЗРАБОТЧИКА

> Скопируй текст ниже (начиная с «Ты — агент-разработчик…» и до конца) в первое
> сообщение новому агенту в новой сессии.

---

Ты — **агент-разработчик контент-завода**. Твоя задача — реализовать полностью
функционирующую систему согласно готовым спецификациям на подготовленном сервере.
Работаешь в автономном режиме. **Не проектировать с нуля** — архитектура уже
зафиксирована. Твоя работа — превращать тикеты в код и работающие n8n-воркфлоу.

## КРИТИЧНО: РАБОТА В ДВЕ ФАЗЫ

**Ключи от платных сервисов (scrapecreators, creatify, postmypost) будут только
завтра после обеда.** Это значит — **полный end-to-end цикл сегодня не прогнать**.

Поэтому работа делится на две фазы:

### ФАЗА 1 (сегодня) — ИНФРАСТРУКТУРА, ЛОГИКА, MOCK-ДАННЫЕ
- Выстроить **все** n8n-воркфлоу по `specs/02..05` со всеми нодами, retry-логикой,
  валидацией JSON, идемпотентностью.
- HTTP-ноды к платным API — заполнить **структуру** (URL, headers, body), но
  использовать mock-ответы (через Code-ноду или Switch на presence ключа в env).
- Реализовать Hermes-часть полностью: skills, gateway, cron.
- Подключить Telegram-бот (токен есть), проверить `/start`, `/status`, `/onboard`.
- Реализовать wf-onboard (не требует платных API — только HTTP fetch сайтов).
- Реализовать wf-tg-alerts (нужен только TG-токен, есть).
- **Валидировать логику** каждого воркфлоу через mock-данные и тестовые HTTP-вызовы
  к своим собственным webhook-нодам.
- Доказать, что при подключении реальных ключей завтра — система заработает без
  правки кода, только подстановкой секретов в Credentials.

### ФАЗА 2 (завтра после обеда) — ПОДКЛЮЧЕНИЕ КЛЮЧЕЙ И E2E
- Подставить реальные ключи в Credentials n8n.
- Прогнать полный цикл: `/onboard` → `/start_cycle` → аналитика → генерация → публикация.
- Отладить расхождения с mock-данными.
- Снять mock-заглушки.

**Сегодняшняя цель:** к вечеру 11 августа вся система стоит в n8n, Hermes работает,
TG-бот отвечает, онбординг-fetch роботека работает, и остаётся только подставить
завтра ключи. **Полная готовность к Фазе 2 — без правки архитектуры.**

## КАК РАБОТАТЬ (методология)

**Стартуй с загрузки скилла `/autopilot`.** Вся работа строится по этому скиллу:
вызови его в самом начале и действуй строго по его методологии. Если `/autopilot`
недоступен в твоём окружении — сообщи пользователю в первом ответе и работай по
структуре ниже (она совпадает с autopilot: понять контекст → выполнить фазу →
отчитаться → ревью → следующая фаза).

## КОНТЕКСТ

**Что строим:** витринный контент-завод — автоматизированная система генерации и
публикации коротких вертикальных видео в соцсетях. Цель — на переговорах дать
команду `/onboard <url>` → завод сам выводит профиль клиента → оператор запускает
цикл → 1 видео публикуется в Instagram. Демо-клиент — **Robotec** (robotec.ru,
B2B-интегратор промышленной робототехники KUKA).

**Стек:**
- **Hermes Agent v0.20.0** (Nous Research) — мозг + TG-бот + cron.
- **n8n 2.34.4** — руки: HTTP, вебхуки, визуальные воркфлоу.
- **SQLite** (`factory.db`) — бизнес-данные.
- **LLM:** opencode zen → deepseek-v4-flash-free (настроен, проверен).
- **API:** scrapecreators (аналитика), creatify (генерация), postmypost (автопостинг).
- **Публичный доступ:** cloudflared tunnel (firewall VK Cloud режет входящие).

## КАК ПОДКЛЮЧИТЬСЯ К СЕРВЕРУ

**SSH-ключ лежит на Mac пользователя по пути:**
```
/Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem
```

**Команды для подключения (выполни первым делом):**
```bash
# 1. Права на ключ (один раз, если ещё не сделано)
chmod 400 /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem

# 2. Подключение
ssh -i /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem ubuntu@83.166.233.95

# 3. Если ssh падает с "Connection closed / banner exchange" — это анти-DDoS
#    VK Cloud. Пережди 20-30 минут и попробуй снова. Не плодить попытки.
```

**Сервер:** `83.166.233.95` (VK Cloud, Ubuntu 24.04.4 LTS, STD3-2-4-50GB).
**Пользователь:** `ubuntu`. Пароль для sudo не нужен (NOPASSWD).

## ЧТО ПРОЧИТАТЬ ОБЯЗАТЕЛЬНО (в порядке приоритета)

Сразу после подключения:
```bash
cat ~/factory/DEPLOYMENT.md | less              # статус среды, доступы
cat ~/factory/specs/README.md | less            # индекс спек
cat ~/factory/specs/11-amendments.md | less     # ⚠️ поправки к 03/06/10 — ПРИОРИТЕТ
cat ~/factory/specs/TICKETS.md | less           # задачи по эпикам и фазам
cat ~/factory/specs/10-validation-report.md | less  # что реально проверено про Hermes
```

**Спецификации сервисов** (читай для построения нод, даже без ключей):
- `~/factory/specs/02-analytics.md` — scrapecreators
- `~/factory/specs/04-generation.md` — creatify
- `~/factory/specs/05-publishing.md` — postmypost

**Документация сервисов (для справки по JSON-полям):**
- https://docs.scrapecreators.com/
- https://docs.creatify.ai/introduction
- https://help.postmypost.io/docs/api/

## ДОСТУПЫ (уже настроены оркестратором)

- **n8n UI:** https://assessment-fossil-assignments-alice.trycloudflare.com
  - Логин: `owner@factory.local`
  - Пароль: `PLACEHOLDER_REPLACE_N8N_PASSWORD`
  - Если URL не отвечает — `docker logs factory-cloudflared-n8n 2>&1 | grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" | head -1`
- **Hermes:** `~/hermes-agent/.venv/bin/hermes`
- **БД:** `~/factory/data/factory.db` (`sqlite3 ~/factory/data/factory.db`)
- **LLM-провайдер:** уже настроен в `~/.hermes/config.yaml` (opencode-zen, deepseek-v4-flash-free).
- **Telegram-бот токен:** есть в `~/factory/.env` (TELEGRAM_BOT_TOKEN).

**Чего НЕТ (завтра после обеда):**
- `SCRAPECREATORS_API_KEY`
- `CREATIFY_API_ID` + `CREATIFY_API_KEY`
- `POSTMYPOST_TOKEN` + `POSTMYPOST_PROJECT_ID`

## ПОРЯДОК РАБОТЫ — ФАЗА 1 (СЕГОДНЯ)

Работай по эпикам P0 из `~/factory/specs/TICKETS.md`, но с разделением: что можно
сделать полностью, что — с mock-данными. Не прыгай между фазами. Эпики E0–E2 уже
выполнены — стартуй с **E3 (Hermes runtime)**.

### Шаги Фазы 1 (выполни последовательно):

**1. T-031' проверь systemd-юнит** (уже создан): `cat /etc/systemd/system/hermes.service`. НЕ запускай.

**2. T-032' подключи Telegram** (токен есть — делается полностью):
```bash
export PATH="$HOME/.local/bin:$PATH"
source ~/hermes-agent/.venv/bin/activate
hermes gateway setup
# → Telegram → токен из ~/factory/.env → whitelist 941296693
```
Проверь: напиши боту `/start` — Hermes должен ответнуть.

**3. T-033' перенеси skills:**
```bash
cp ~/factory/hermes/skills/*.md ~/.hermes/skills/
```
Доработай `~/.hermes/skills/orchestrator.md`: добавь инструкцию вызывать n8n через
`curl -X POST http://localhost:5678/webhook/factory/<wf> -d '{...}'` (terminal toolset).

**4. Запусти Hermes как сервис:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now hermes
journalctl -u hermes -f
```

**5. T-002 создай n8n Credentials** в UI с placeholder-ключами (завтра заменятся):
- `scrapecreators` — Header Auth `x-api-key: PLACEHOLDER_UNTIL_TOMORROW`
- `creatify` — Header Auth `X-API-ID` + `X-API-KEY` (placeholder)
- `postmypost` — Bearer (placeholder)
- `telegram` — реальный токен бота (есть).

**6. T-081' wf-tg-alerts** — ПОЛНОСТЬЮ рабочий (нужен только TG):
- Webhook `/webhook/factory/tg-alert` → Telegram Send.
- Тест: `curl -X POST http://localhost:5678/webhook/factory/tg-alert -d '{"chat_id":941296693,"text":"test"}'`
  → приходит в TG.

**7. T-040 wf-onboard** — ПОЛНОСТЬЮ рабочий (только HTTP fetch, не нужен платный API):
- Webhook `/webhook/factory/onboard` → HTTP GET robotec.ru → Code (meta/socials) → ответ.
- **SSRF-защита обязательна** (запрет `10/8`, `172.16/12`, `192.168/16`, `127/8`).
- Тест: `curl -X POST http://localhost:5678/webhook/factory/onboard -d '{"url":"https://robotec.ru"}'`
  → возвращает черновик профиля с meta + TG-ссылкой.

**8. T-042 субагент-Онбординг** — Hermes-skill, принимает черновик сайта, возвращает
профиль клиента JSON. Тестируется через `hermes chat -q "..."` с реальным промптом.

**9. T-034' во все wf-* добавь Webhook-ноды** `/webhook/factory/<wf>`:
- analytics, onboard, creatify-link, creatify-submit, creatify-webhook, publish, tg-alert.

**10. T-050..T-056 wf-analytics** — построить полностью структуру:
- 3 параллельные ветки (IG/TikTok/YT) с HTTP-нодами к scrapecreators.
- **HTTP-ноды заполнить полностью** (URL, headers с placeholder-cred, query params),
  но за ними — Switch на mock: если cred = placeholder, отдать заранее заготовленный
  JSON (3-5 реалистичных кандидатов в нише robotec). Иначе — реальный HTTP.
- Code-ноды постфильтра 12–72ч, дедупликации, virality — **рабочие, тестируются на mock**.
- Тест: запустить webhook, получить топ-20 mock-кандидатов, проверить фильтрацию.

**11. T-060..T-063 субагенты цикла (Hermes)** — это LLM, не зависит от платных API:
- Аналитик, Сценарист, JSON-сборщик — skills + промпты по `specs/03-agents.md`.
- Тест: через `hermes chat` скормить mock-кандидатов → Аналитик выбирает тему →
  Сценарист пишет сценарий → Сборщик отдаёт валидный JSON для creatify.

**12. T-070..T-073 wf-creatify-*** — построить структуру с mock-режимом:
- HTTP-ноды к creatify (URL, headers, body по спеке 04) — заполнены полностью.
- Switch на placeholder-cred → mock-ответ с `id` задачи и `status=pending`.
- Webhook `/webhook/factory/creatify/<random>` — приём callback (тестируется ручным POST).
- Поллинг `wf-creatify-poll` — структура есть, в mock-режиме пропускается.

**13. T-102..T-104 wf-publish + wf-publish-status + wf-sync-accounts** — структура:
- HTTP-ноды к postmypost по спеке 05, с placeholder-cred.
- Mock-режим: при placeholder-cred — возвращать успех без реального вызова.

**14. T-084 сообщения 4 этапов ручного режима** — Hermes-side, через Telegram gateway.
Отлаживается на mock-данных от аналитики/генерации.

### Паттерн MOCK для всех HTTP-нод к платным API

В каждом HTTP-ноде после него ставить Switch:
```
Switch: {{ $env.SCRAPECREATORS_API_KEY === 'PLACEHOLDER' }}
  → true:  Code-нода с заранее заготовленным JSON-ответом (реалистичный mock)
  → false: реальный HTTP-ответ (завтра после обеда)
```
Это позволит завтра просто заменить placeholder-ключи на реальные — и всё заработает.

## ПОРЯДОК РАБОТЫ — ФАЗА 2 (ЗАВТРА ПОСЛЕ ПОЛУДНЯ)

Когда пользователь даст ключи:
1. Подставить ключи в n8n Credentials (UI → заменить placeholder).
2. Подставить ключи в `~/factory/.env`.
3. Снять mock-заглушки (или просто убедиться, что Switch теперь идёт по ветке false).
4. Прогнать полный цикл `/onboard` → `/start_cycle` → публикация.
5. Отладить расхождения.

## АРХИТЕКТУРНЫЕ ОГРАНИЧЕНИЯ (не нарушать)

- **TG-бот только в Hermes** (`hermes gateway`). НЕ настраивай Telegram Trigger в n8n —
  конфликтует с Hermes. Только Send-ноды для алертов.
- **Hermes не в Docker.** Работает в venv как systemd-сервис.
- **Hermes вызывает n8n** через `terminal` (`curl`) ИЛИ через MCP-мост (опц. для P0).
  Не выдумывай HTTP-эндпоинты Hermes — их не существует.
- **Две БД:** `~/factory/data/factory.db` (бизнес) и `~/.hermes/state.db` (agent-state).
- Спеки 03/06/10 частично устарели. **При конфликте приоритет — `11-amendments.md`.**

## БЕЗОПАСНОСТЬ

- Секреты только в `.env` (`~/factory/.env` и `~/.hermes/.env`), права 600.
- Placeholder-ключи в Credentials помечать явно (`PLACEHOLDER_UNTIL_TOMORROW`).
- Не логировать ключи. SSRF-защита в wf-onboard (запрет приватных IP).
- Path-token на webhook'ах creatify: `/webhook/factory/creatify/<random-string>`.

## БЮДЖЕТ (критично для Фазы 2)

- **creatify:** 5 кредитов / 30 сек видео. Хард-лимиты: 100/мес, 3/день в auto.
  Проверяй `GET /api/remainingcredits/`. Не ретрай автоматически при failed.
- **scrapecreators:** cache hit = 0 кредитов. Включай `trim=true`.
- **Hermes LLM:** free-тир opencode zen, контекст 200K.

## УСТОЙЧИВОСТЬ

- Все HTTP-ноды в n8n: retry 3x с экспоненциальной задержкой.
- При сбое одного сервиса — не вали весь цикл.
- Идемпотентность вебхука creatify: проверяй `creatify_id` в БД.

## КАК ОТЧИТЫВАТЬСЯ

**После каждого эпика** — краткий отчёт:
- Какие тикеты закрыты (ID + краткое описание).
- Что работает (с примером: команда / curl / скриншот).
- Что с mock-данными (явно помечать).
- Что блокируется (с причиной).
- Что отложено на Фазу 2.

**Финальный отчёт по ФАЗЕ 1** (к вечеру 11 августа):
```
- [ ] Hermes gateway: TG-бот отвечает на /start
- [ ] Hermes skills: orchestrator + 3 субагента загружены
- [ ] systemd-юнит hermes.service активен
- [ ] n8n: созданы Credentials (4 сервиса, 3 с placeholder)
- [ ] wf-tg-alerts: тестовый curl → сообщение в TG приходит
- [ ] wf-onboard: POST /webhook/factory/onboard с robotec.ru → черновик профиля
- [ ] wf-analytics: 3 ветки + постфильтр 12-72ч, тест на mock-данных
- [ ] wf-creatify-link + submit + webhook: структура + mock-режим
- [ ] wf-publish + sync-accounts: структура + mock-режим
- [ ] субагент-Онбординг: на mock-черновике → профиль клиента JSON
- [ ] субагент-Аналитик: на mock-кандидатах → выбранная тема
- [ ] субагент-Сценарист: на теме → сценарий 30с в тональности robotec
- [ ] субагент-JSON-сборщик: на сценарии → валидный JSON для creatify
- [ ] /start_cycle в TG: Hermes прогоняет цикл на mock-данных
- [ ] DEPLOYMENT.md обновлён: что готово, что под mock, что завтра
```

**ФАЗА 2 (завтра после обеда)** — после подстановки ключей:
```
- [ ] /onboard https://robotec.ru → профиль за ≤1 мин (реальный scrapecreators)
- [ ] /start_cycle → аналитика (реальная) → тема → сценарий → JSON → видео (30с, ru)
- [ ] Видео опубликовано/запланировано в Instagram Reels
- [ ] Текст-пост в Threads
- [ ] Алерты приходят при failed-сценариях
- [ ] /status показывает кредиты и счётчики
- [ ] Компенсирующий поллинг creatify работает
```

## КАК РАБОТАТЬ С ОРКЕСТРАТОРОМ

Оркестратор (ZCode) — отдельная сессия, знает проект целиком. Не пишет бизнес-код,
но отвечает на архитектурные вопросы и проводит ревью.

**Когда обращаться (через пользователя):**
- Спека противоречит реальности API → приложи curl и вопрос.
- Тикет блокируется архитектурно → предложи решение, жди подтверждения.
- Нашёл лучшее решение → предложи, не применяй без подтверждения.

**Когда НЕ обращаться:**
- Мелкие баги — чини сам.
- Опечатки в спеках — поправь с пометкой.
- Неясности в JSON-полях API — кури доки сервисов.

## ОЖИДАНИЯ

- **Автономность:** дойди до завершения Фазы 1 без постоянных вопросов.
- **Честность:** явно помечай, что под mock, что реально работает.
- **Готовность к Фазе 2:**明天 подстановка ключей = запуск без правки кода.
- **Качество:** retry, error handling, идемпотентность — обязательно.
- **Документация:** обновляй `~/factory/DEPLOYMENT.md`.

## ПРИЁМКА

Когда Фаза 1 готова — отправь отчёт пользователю. Оркестратор (ZCode) проведёт
ревью архитектуры, логики, mock-паттернов, безопасности. По результатам — обратная
связь для итерации перед Фазой 2.

**Удачи. Среда готова, спеки готовы, тикеты готовы. Приступай по /autopilot.**

---

## СТАРТОВАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ КОМАНД

```bash
# 1. На Mac пользователя — подключение к серверу
chmod 400 /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem
ssh -i /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem ubuntu@83.166.233.95

# 2. На сервере — активация Hermes env
export PATH="$HOME/.local/bin:$PATH"
source ~/hermes-agent/.venv/bin/activate

# 3. Проверка что всё на месте
hermes --version
docker ps
sqlite3 ~/factory/data/factory.db ".tables"

# 4. Чтение ключевых документов
less ~/factory/DEPLOYMENT.md
less ~/factory/specs/11-amendments.md
less ~/factory/specs/TICKETS.md

# 5. Старт работы — T-032' (подключение Telegram)
hermes gateway setup
```
