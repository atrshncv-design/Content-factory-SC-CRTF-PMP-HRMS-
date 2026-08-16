# Smoke-чек-лист: контент-завод, готовность к сдаче (16.08.2026)

**Тикет 09 — E2E smoke (0 кредитов).** Два блока: **✅ проверено бесплатно** (уже доказано
статикой/симами/тестами — перепроверять не нужно) и **🔴 проверить платно** (только
пользователь, реальные ключи и подключённые аккаунты postmypost — списания возможны).
Порядок: сначала deploy-гейт, затем платный прогон по порядку.

---

## 0. Deploy-гейт (сервер, после деплоя волны 3) — ⚠️ обязательно до платных тестов

| # | Пункт | Статус | Доказательство / команда пользователю |
|---|---|---|---|
| 0.1 | 23 воркфлоу активны после деплоя (кроме zz-test-sqlite) | 🔴 deploy-гate | Репо: 24 JSON валидны, все active=true (док. в тикете 09). Сервер: n8n UI → Workflows → 23 active (выключить/не включать zz-test-sqlite). |
| 0.2 | В executions — 0 новых ошибок после smoke | 🔴 deploy-гate | n8n UI → Executions: прогон шагов 1–2 ниже, затем фильтр по error — 0 новых. |
| 0.3 | FACTORY_WEBHOOK_SECRET задан в ~/factory/.env | 🔴 deploy-гate | Сейчас fail-open (осознанный FIX-10). `grep -c FACTORY_WEBHOOK_SECRET ~/factory/.env` → 1 (не PLACEHOLDER). |
| 0.4 | Балансы: creatify и scrapecreators до тестов | 🔴 deploy-гate | `curl -H "X-API-ID: $CREATIFY_API_ID" -H "X-API-KEY: $CREATIFY_API_KEY" https://api.creatify.ai/api/remaining_credits/` (GET бесплатен) + SC `/v1/account/credit-balance`. Записать числа до/после. |

---

## 1. Бесплатная цепочка (✅ проверено локально — повторять не нужно, только live-контроль)

| # | Пункт | Статус | Доказательство |
|---|---|---|---|
| 1.1 | /start в TG: бот отвечает меню/статусом | ✅ | sim Parser: /start → command=start, tg_user_id проброшен (ticket09 30/30); Switch cmd 45 ветвей, ни одна не в fallback |
| 1.2 | Профиль Robotec (client_id=1) подхватывается | ✅ | sim GPF (SQL sessions/profile); GPF Check ac_id>0; тикет 07 done |
| 1.3 | /start_cycle: аналитика → темы (контракт candidates[]) | ✅ | sim SC: Build analytics body client_id=1, Check analytics ok/err, bridge prompt (analyst), Parse topic, INSERT topics; тикет 02/05 done |
| 1.4 | Сценарий 30 сек, 90–110 слов, без markdown | ✅ | sim AU Parse script (full_text чистый); тикет 04 test-04 6/6 |
| 1.5 | link → submit: валидация payload, гейты 10/50 до списания | ✅ | sim link Code assemble (3 формы), submit Code validate (6 сценариев); тикет 02 done |
| 1.6 | Webhook creatify done → БД done + видео в чат | ✅ | sim webhook: Code done build, UPDATE done, session VIDEO_AWAIT, stage3 (chat_id/видео/«Этап 3/4»); тикет 01 done (sendVideo v1.2) |
| 1.7 | Publish-ветка собирает payload (platforms + file_ids) | ✅ | sim AU Build publish body; AU Check result post_id→ok / error→текст; тикет 06 done (26 нод, upload_needed, text-only, 7 платформ) |
| 1.8 | Все webhook-пути зарегистрированы (23) | ✅ | grep путей: все вызываемые из бота 17/17 зарегистрированы, webhookId у всех, POST; 0 хардкодов туннеля |
| 1.9 | Секреты: только имена переменных, значений в репо нет | ✅ | сканы: 0 sk-/xoxb-/eyJ-совпадений; .env.example полный (08 done); db-bridge/hermes-bridge X-BRIDGE-TOKEN fail-closed |
| 1.10 | Валидаторы и pytest зелёные | ✅ | validate_workflow.py 0 issues (21 воркфлоу) + multi-trigger BFS 24/24; pytest 25/25; test-04 6/6 |
| 1.11 | 0 списаний за ревью | ✅ | ни одного HTTP-вызова; mock-переключатели PLACEHOLDER; платные POST только в real-ветках |

---

## 2. Платный прогон пользователя (🔴 — списания возможны; команды точные)

### 2.1 Генерация URL→видео (дешёвый путь, 5 кред/30с)
| # | Шаг | Ожидание | Если нет |
|---|---|---|---|
| 2.1.1 | В TG: `/start_cycle` (или «запуск цикла») при реальных ключах SC/Creatify | аналитика тянет 3 платформы, темы → сценарий → approve | см. 2.1.3 |
| 2.1.2 | Approve темы → approve сценария → «Генерирую…» → видео в чат (Этап 3/4) | видео приходит sendVideo; кнопки publish/regen | тикет 01: failed/unknown алертят оператора; проверь executions |
| 2.1.3 | Если аналитика пустая | баланс SC ≥ 5; `/status` показывает бюджет | пополнить SC; повторить |

### 2.2 AI Shorts (5 кред/30с)
| # | Шаг | Ожидание |
|---|---|---|
| 2.2.1 | `/shorts <тема>` | тема разворачивается в сценарий (бесплатно, hermes), затем ai_shorts; видео в чат |

### 2.3 Публикация (postmypost — аккаунты подключает пользователь, спека G01)
| # | Шаг | Ожидание |
|---|---|---|
| 2.3.1 | Подключить аккаунты в кабинете postmypost: IG/TikTok/YT/Threads/X + TG + VK | wf-sync-accounts (hourly) наполнит social_accounts, включая VK |
| 2.3.2 | POSTMYPOST_TOKEN / POSTMYPOST_PROJECT_ID — реальные (не PLACEHOLDER) | публикация доходит до postmypost |
| 2.3.3 | После видео в чате: publish → выбрать платформы → confirm | пост уходит; «Опубликовано #id» в TG (без (mock)); IG type=4 REELS |
| 2.3.4 | Text-only: `text_post` → платформы threads/x/vk → публикация | без 422 upload/init; TG caption без markdown-символов; X ≤ 280 символов |
| 2.3.5 | wf-publish-status (cron */2) | post → published/error + tg-алерт |
| 2.3.6 | VK: пост от подключённого сообщества/страницы | VK-ограничения из DEPLOYMENT.md §21a |

### 2.4 Premium (апсейл-фичи; цены проверены — см. скилл creatify-credits-budget.md)
| # | Шаг | Ожидание | Цена |
|---|---|---|---|
| 2.4.1 | /asset <промпт> | изображение asset_generator | 1 кред/шт |
| 2.4.2 | /product <url товара> | gen_image → gen_video | 1 + 3 кред |
| 2.4.3 | /banner <url> | iab_images (12 размеров) | 2 кред |
| 2.4.4 | /audience <ник> | демография (дорого!) | **26 кред/запрос** — только при необходимости |
| 2.4.5 | /upload_avatar /my_avatars | persona создаётся (модерация 1–2 дня) | 0 кред, лимит 3 |
| 2.4.6 | /creators, /creator, /creator_content, /transcript, /comments | SC-поиск/профили/контент | ≈1 кред/запрос, кэш только на точном повторе search |
| 2.4.7 | adclone / inspiration / creatify-text (script) | **не впаяны в бот** (спека История 6, на 16.08) | не вызывать через бот |

### 2.5 Контроль бюджета (обязательно)
| # | Шаг | Ожидание |
|---|---|---|
| 2.5.1 | Баланс creatify до/после каждого сценария | списание отложенное: credits_used=0 при POST, падает при завершении джоба — сверять через 2–3 мин |
| 2.5.2 | Леджер расходов: `GET /api/link_to_videos/` и др. | id/status/credits_used/video_output — полная картина |
| 2.5.3 | SC: повторный запрос profile/videos = снова списание | кэш только на search/keyword точным повтором; не дёргать лишний раз |

---

## 3. Что НЕ вошло / осознанно отложено

- **adclone, inspiration, creatify-text** — премиум, не впаяны (спека История 6, вне рамок R08).
- **P2-дашборд, self-analytics, мульти-тенантность** — вне рамок (G02).
- **Нишевые платформы postmypost** (Pinterest/Rutube/OK) — вне рамок (G07).
- **Ротация ключей** (утечка 13.08) — действие пользователя.
- **secret_token tg-trigger** — осознанно пуст (D2 Y5), включение одной строкой + переактивация webhook.
- **FACTORY_WEBHOOK_SECRET fail-open** — FIX-10 (creatify не шлёт кастомный заголовок); задать в .env и включить после согласования с отправителем колбэков.

---

## 4. Итог

- **Бесплатно доказано (16.08, 0 кредитов):** цепочка /start → publish трассируется без
  разрывов, все webhook-пути зарегистрированы, секреты защищены (имена переменных),
  валидаторы/pytest/sims зелёные, 24 JSON воркфлоу валидны.
- **Deploy-гейт:** активность 23 воркфлоу, executions 0 ошибок, FACTORY_WEBHOOK_SECRET в .env.
- **Платно (пользователь):** генерация URL→видео / shorts, публикация на 7 платформ,
  premium-эндпоинты, контроль балансов (2.1–2.5).
