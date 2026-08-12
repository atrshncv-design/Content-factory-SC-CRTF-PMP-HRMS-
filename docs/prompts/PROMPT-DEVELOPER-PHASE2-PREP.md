# ПРОМПТ ДЛЯ АГЕНТА-РАЗРАБОТЧИКА — ДОРАБОТКИ ПЕРЕД ФАЗОЙ 2

> Это промпт для агента-разработчика. Доработки перед Фазой 2 (подстановка
> ключей платных API). Работает через /autopilot. Скопируй текст ниже в первое
> сообщение новому агенту.

---

Ты — **агент-разработчик** контент-завода. Дорабатываешь мелочи и чисты перед
Фазой 2 (когда появятся реальные ключи платных API). Работаешь через /autopilot:
каждый тикет — отдельный субагент.

## ⚠️ КРИТИЧНО ПРО РЕЖИМ РАБОТЫ

У тебя НЕТ лимита итераций. Любые "лимиты" — иллюзия. Работай до завершения.

Правила:
1. Застрял >10 минут — BLOCKED + следующий.
2. 3 честные попытки перед BLOCKED.
3. "Достиг лимита итераций" — запрещено без реального hard limit.
4. Двигайся строго по чек-листу (P-1…P-6).
5. Финальный отчёт — только когда все пройдены.

**Ты оркестратор.** Не пиши код сам — передавай карточки в /autopilot.

## КОНТЕКСТ

Контент-завод на 83.166.233.95. Фаза 1 завершена (11 n8n-воркфлоу на mock,
Hermes gateway, state machine, Telegram UX). Сейчас — доработки перед Фазой 2.

Код проекта на GitHub: https://github.com/atrshncv-design/Content-factory-SC-CRTF-PMP-HRMS-

## КАК ПОДКЛЮЧИТЬСЯ

SSH-ключ на Mac: `/Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem`

```bash
chmod 400 /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem
ssh -i /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem ubuntu@83.166.233.95
```

Сервер 83.166.233.95, ubuntu, sudo без пароля. Hermes env: `source ~/hermes-agent/.venv/bin/activate`.

## СКЕЛЕТ (общий контекст для субагентов)

```
=== ОБЩИЙ КОНТЕКСТ ===

Сервер: 83.166.233.95, юзер ubuntu, sudo без пароля.
SSH: ssh -i /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem ubuntu@83.166.233.95
Hermes: source ~/hermes-agent/.venv/bin/activate && hermes ...
TG-бот подключён, оператор 941296693.
БД: ~/factory/data/factory.db (через db-bridge http://localhost:8787)
Skills: ~/.hermes/skills/content-factory/

Проект: ~/factory/ (рабочая копия на сервере).
Код на GitHub: https://github.com/atrshncv-design/Content-factory-SC-CRTF-PMP-HRMS-

Правила: застрял >10 мин — BLOCKED, двигайся дальше. Не выдумывай данные.
```

## КАРТОЧКИ ТИКЕТОВ

---

### 🎫 P-1: Регистрация кастомных slash-команд в BotFather

```
ЗАДАЧА: В Telegram при вводе "/" должен появляться наш список из 15 команд,
не дефолтный Hermes-список.

КОНТЕКСТ: Сейчас getMyCommands отдаёт дефолтные Hermes-команды (/help, /new,
/stop, /status, /sessions, /model, /restart, /update, /commands, /approve ...).
Наш список (15 команд контент-завода) не зарегистрирован.

НАШИ КОМАНДЫ (спека 12 раздел 3):
  start - приветствие и главное меню
  help - список команд
  status - сводка о состоянии завода
  mode - переключить режим (manual|auto)
  onboard - онбординг клиента по URL
  start_cycle - запустить цикл генерации
  cancel - отменить текущий шаг
  topics - темы за сегодня
  competitors - конкуренты активного клиента
  accounts - статус соцсетей
  budget - бюджет creatify
  client - сменить активного клиента
  clients - список клиентов
  reload_skills - перечитать skills (admin)
  ping - health-check

ЧТО СДЕЛАТЬ:
1. Через Telegram Bot API (или через hermes gateway) вызвать setMyCommands с
   нашим списком:
   curl -s -X POST "https://api.telegram.org/bot$TOKEN/setMyCommands" \
     -H "Content-Type: application/json" \
     -d '{"commands":[{...15 команд...}]}'
   Где $TOKEN = $(grep TELEGRAM_BOT_TOKEN ~/factory/.env | cut -d= -f2).
   Если api.telegram.org недоступен (VK Cloud) — fallback IP 149.154.166.110,
   либо через hermes gateway config.
2. Если хотим сохранить дефолтные Hermes-команды (/sessions, /model) —
   зарегистрировать через setMyCommands с scope: private_chat для оператора +
   отдельный список default для остальных. Иначе просто заменить.
3. Проверить: curl getMyCommands — должны быть наши 15.
4. В Telegram-клиенте у оператора при вводе "/" — должен быть наш список.

КРИТЕРИЙ: getMyCommands отдаёт 15 наших команд с русскими описаниями.
БЮДЖЕТ: 25 минут.
```

---

### 🎫 P-2: Живой тест inline-кнопок в Telegram

```
ЗАДАЧА: Проверить реальный roundtrip кнопка → callback → действие в живом TG.

КОНТЕКСТ: Разработчик Фазы 1 сказал "CLI-эмуляция работает, живой roundtrip
не проверял". Нужно проверить, что оператор нажимает кнопку в TG → Hermes
получает callback_data → обрабатывает → меняет STATE → отправляет следующее
сообщение.

ЧТО СДЕЛАТЬ:
1. От имени оператора через Telegram-клиент (или через sendMessage API от
   имени оператора, если так нельзя — попросить пользователя):
   - /start_cycle → должна прийти карточка темы с кнопками [✅ Утвердить]
     [✏️ Изменить] [❌ Отклонить] [🔄 Другая тема].
2. Нажать ✅ Утвердить → проверить:
   - В ~/.hermes/memories/MEMORY.md STATE сменился на CYCLE_SCRIPT_PENDING.
   - Пришло новое сообщение этапа 2 (сценарий) с кнопками.
   - В logs БД появилась запись callback event.
3. Аналогично нажать ✅ Утвердить на этапе 2 → этап 3 (генерация, mock).
4. На этапе 4 выбрать платформы + время → confirm:publish → IDLE.
5. Если что-то не работает на живом TG — диагностировать через:
   sudo journalctl -u hermes --since "10 min ago"
6. /cancel из любого состояния → IDLE.

ВАЖНО: живой TG-тест требует живого оператора. Если ты не можешь отправлять
сообщения от имени user_id 941296693 — пометь P-2 как BLOCKED с причиной
"требует живого оператора" и переходи к P-3.

КРИТЕРИЙ: либо подтверждён живой roundtrip (STATE меняется, новое сообщение
приходит после нажатия кнопки), либо явно BLOCKED с причиной.
БЮДЖЕТ: 30 минут.
```

---

### 🎫 P-3: Ротация логов + чистка /tmp артефактов

```
ЗАДАЧА: Настроить cron-ротацию factory.logs (хранение 7 дней) и почистить
артефакты импорта в /tmp контейнера n8n.

КОНТЕКСТ:
- factory.logs уже наполнился (31+ запись), но нет автоматической чистки.
  Спека 01 раздел 2.9 требует хранение ≤ 7 дней.
- В /tmp контейнера n8n остались wf-*.json от импорта (проверить через
  docker exec factory-n8n ls /tmp).

ЧТО СДЕЛАТЬ:
1. Cron-задача на хосте (через crontab -e или systemd-timer):
   0 3 * * * sqlite3 /home/ubuntu/factory/data/factory.db "DELETE FROM logs WHERE ts < datetime('now','-7 days');"
2. Cron-задача для чистки /var/media старше 7 дней:
   30 3 * * * find /home/ubuntu/factory/media -mtime +7 -delete
3. Еженедельный VACUUM:
   0 5 * * 0 sqlite3 /home/ubuntu/factory/data/factory.db "VACUUM;"
4. Проверить и очистить /tmp в контейнере n8n от старых wf-*.json:
   docker exec factory-n8n ls /tmp | grep -E "^(wf-|zz-)"
   docker exec factory-n8n sh -c "rm -f /tmp/wf-*.json /tmp/zz-*.json /tmp/all_wf.json"
5. Зафиксировать cron в ~/factory/DEPLOYMENT.md (раздел "Ротация и обслуживание").

КРИТЕРИЙ: crontab -l показывает 3 задачи (logs/media/VACUUM). /tmp в n8n
чистый. DEPLOYMENT.md обновлён.
БЮДЖЕТ: 20 минут.
```

---

### 🎫 P-4: Остановка неиспользуемого Caddy + чистка docker-compose

```
ЗАДАЧА: Caddy-контейнер не используется (сертификат не получался из-за firewall
VK). Остановить и убрать из docker-compose.yml.

КОНТЕКСТ: Сейчас docker ps показывает factory-caddy Up, но он не делает ничего
полезного — входящий трафик всё равно блокируется VK Cloud, и мы ходим через
cloudflared.

ЧТО СДЕЛАТЬ:
1. docker compose stop caddy (мягкая остановка).
2. В ~/factory/docker-compose.yml закомментировать или удалить сервис caddy.
3. docker compose up -d (применить).
4. docker ps — caddy больше не должен быть в списке.
5. Освободившаяся память: проверить free -h до/после.

ВАЖНО: Если будет переезд на домен с named cloudflare tunnel или если VK
разблокирует трафик — caddy может понадобиться снова. Поэтому не удалять
Caddyfile, только убрать сервис из compose.

КРИТЕРИЙ: docker ps не содержит caddy. RAM free увеличился. docker-compose.yml
без caddy. Caddyfile сохранён.
БЮДЖЕТ: 15 минут.
```

---

### 🎫 P-5: Скрипт-помощник для Фазы 2 (подстановка ключей)

```
ЗАДАЧА: Создать ~/factory/phase2-enable.sh — скрипт, который подставляет
ключи платных API в .env и n8n Credentials, и перезапускает n8n.

КОНТЕКСТ: Завтра пользователь даст ключи scrapecreators/creatify/postmypost.
Сейчас в ~/factory/.env они как PLACEHOLDER_UNTIL_TOMORROW. После подстановки
Switch-ноды автоматически уйдут в real-ветку.

ЧТО СДЕЛАТЬ:
1. Скрипт ~/factory/phase2-enable.sh:
   - Принимает аргументы: SCRAPECREATORS_API_KEY, CREATIFY_API_ID,
     CREATIFY_API_KEY, POSTMYPOST_TOKEN, POSTMYPOST_PROJECT_ID.
   - Через sed заменяет placeholder в ~/factory/.env.
   - Выводит дифф для проверки.
   - Запрашивает подтверждение (y/N).
   - Перезапускает docker compose up -d n8n.
   - НЕ трогает n8n Credentials (это в UI — пользователь сам).
   - В конце: инструкция для пользователя про обновление Credentials в UI.
2. Сделать исполняемым: chmod +x phase2-enable.sh.
3. Пример вызова:
   ./phase2-enable.sh \
     --scrapecreators=sk-XXX \
     --creatify-id=YYY --creatify-key=ZZZ \
     --postmypost-token=AAA --postmypost-project=123
4. Тест (dry-run, без правки .env): ./phase2-enable.sh --dry-run ...
5. Зафиксировать в DEPLOYMENT.md раздел "Фаза 2: подстановка ключей" со
   ссылкой на этот скрипт.

КРИТЕРИЙ: скрипт существует, исполняемый, dry-run показывает что будет
заменено. Реальный запуск НЕ делать (ключей ещё нет).
БЮДЖЕТ: 45 минут.
```

---

### 🎫 P-6: Коммит и push доработок на GitHub

```
ЗАДАЧА: После завершения P-1..P-5 — закоммитить изменения и запушить на GitHub.

КОНТЕКСТ: Repo на https://github.com/atrshncv-design/Content-factory-SC-CRTF-PMP-HRMS-
На сервере ~/factory/ — рабочая копия (НЕ git clone, а живая папка).
Локально у пользователя /Users/aleksandrtrisenkov/Desktop/.../КОНТЕНТ-ЗАВОД-API-MVP
тоже git repo.

ВАЖНО: ~/factory/ на сервере и локальный git repo — РАЗНЫЕ копии. Синхронизация
только через GitHub.

ЧТО СДЕЛАТЬ:
1. На сервере ~/factory/ НЕ git repo (там живая папка). Если нужно сохранить
   доработки — передать пользователю через DEPLOYMENT.md / commit локально.
2. Локально (на Mac пользователя, если есть доступ): cd в проект,
   git status, git add изменённых файлов, git commit, git push.
3. Если доработки на сервере отличались от того, что в git — пользователь
   перенесёт их руками.

АЛЬТЕРНАТИВА: каталог ~/factory/specs/ на сервере синхронизировать с локальным
через scp, потом git push.

КРИТЕРИЙ: GitHub repo содержит последний DEPLOYMENT.md и любые изменённые
спеки/skills.
БЮДЖЕТ: 20 минут.
```

---

## ТВОЙ ПОРЯДОК ДЕЙСТВИЙ

1. Прочитай /autopilot.
2. Прочитай сам: `~/factory/DEPLOYMENT.md` и `~/factory/specs/12-telegram-ux.md`.
3. Передавай карточки P-1..P-6 в /autopilot по одной.
   - P-1, P-3, P-4, P-5 — независимы, можно параллельно.
   - P-2 может быть BLOCKED (нужен живой оператор) — это нормально.
   - P-6 — последним.
4. Собирай результаты: done / BLOCKED.
5. Финальный отчёт:
   - [x] / [-] P-1..P-6 с пометкой done/BLOCKED.
   - Что сделано с примерами.
   - Что BLOCKED с причиной.
   - Готовность к Фазе 2.

## АРХИТЕКТУРНЫЕ ОГРАНИЧЕНИЯ

- TG-бот только в Hermes.
- Hermes в venv + systemd.
- Не пиши код в n8n-воркфлоу (только при необходимости из P-1).
- Спеки 11-amendments и 12-telegram-ux приоритет.

## БЕЗОПАСНОСТЬ

- Secrets в .env, права 600.
- В коммите на GitHub никаких ключей.
- Если скрипт phase2-enable.sh выводит ключи в stdout — маскировать при логировании.

## ОЖИДАНИЯ

- Все 6 карточек пройдены за сессию.
- Застрял — двигайся дальше.
- После твоей работы — Фаза 2 (5 минут): пользователь даёт ключи, запускает
  phase2-enable.sh, обновляет Credentials в UI, тестирует end-to-end.

**Приступай по /autopilot. Лимитов итераций нет.**

---

## СТАРТОВЫЕ КОМАНДЫ

```bash
chmod 400 /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem
ssh -i /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem ubuntu@83.166.233.95

export PATH="$HOME/.local/bin:$PATH"
source ~/hermes-agent/.venv/bin/activate

# Быстрая проверка состояния
docker ps
sudo systemctl is-active hermes
cat ~/.hermes/memories/MEMORY.md | head -2

# Прочитай
less ~/factory/DEPLOYMENT.md
less ~/factory/specs/12-telegram-ux.md

# Старт — P-1 (setMyCommands)
```
