# ПРОМПТ ДЛЯ АГЕНТА-РАЗРАБОТЧИКА — ФИКС SLASH-КОМАНД (P-7)

> Это быстрый фикс проблемы: /start_cycle не работает в живом TG, потому что
> Hermes перехватывает slash-команды на своём уровне. Скопируй текст ниже в
> первое сообщение новому агенту.

---

Ты — **агент-разработчик** контент-завода. Быстрый фикс проблемы со slash-командами
в Telegram. Работаешь через /autopilot.

## ⚠️ КРИТИЧНО ПРО РЕЖИМ РАБОТЫ

У тебя НЕТ лимита итераций. Любые "лимиты" — иллюзия. Работай до завершения.
Застрял >10 минут — BLOCKED. 3 попытки перед BLOCKED. Финальный отчёт — только
когда всё пройдено.

## ПРОБЛЕМА

Оператор пишет в Telegram `/start_cycle` → Hermes отвечает:
> "Unknown command /start_cycle. Type /commands to see what's available..."

**Причина:** Hermes-gateway перехватывает ВСЕ slash-команды на своём уровне.
В логе: `WARNING gateway.run: Unrecognized slash command /start_cycle from telegram — replying with unknown-command notice`.

Наш orchestrator-skill НИКОГДА не получает `/start_cycle` — Hermes его реджектит
 ДО skill'а. Telegram `setMyCommands` (P-1) добавил только автокомплит в чат,
но не сделал команду рабочей.

Зарегистрировать кастомные slash-команды в Hermes можно только через написание
Python-плагина (`hermes_cli.plugins.get_plugin_commands`) — это сложно.

## РЕШЕНИЕ

**Текстовые триггеры без слеша.** Оператор пишет `start_cycle`, `status`, `cancel`
(или `старт`, `статус`, `отмена`) — Hermes-skill парсит как обычный текст и
обрабатывает. Это работает, потому что обычный текст не перехватывается
gateway-эм — идёт прямо в agent loop, где orchestrator-skill его парсит.

Дополнительно — настроить **Menu Button** (кнопка «Меню» слева от поля ввода в TG)
со списком команд. При нажатии команды из меню **текст отправится без слеша**
→ обработается как триггер.

## КАК ПОДКЛЮЧИТЬСЯ

SSH: `ssh -i /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem ubuntu@83.166.233.95`
Hermes: `export PATH="$HOME/.local/bin:$PATH" && source ~/hermes-agent/.venv/bin/activate`

## КАРТОЧКА P-7: Текстовые триггеры + Menu Button

```
ЗАДАЧА: Переделать обработку команд бота с slash на текстовые триггеры +
настроить Telegram Menu Button.

ЧАСТЬ 1 — ОБНОВИТЬ orchestrator/SKILL.md:
В файле ~/.hermes/skills/content-factory/orchestrator/SKILL.md заменить
раздел "SLASH-КОМАНДЫ" на раздел "ТЕКСТОВЫЕ ТРИГГЕРЫ КОМАНД". Логика:

Оператор присылает текстовое сообщение. Если текст (в нижнем регистре, trimmed)
совпадает с одним из триггеров — обрабатывай как команду. Иначе — отказ по
правилу 1 (не контент-завод).

ТАБЛИЦА ТРИГГЕРОВ (для каждого — английский + русский + optional slash-форма
для устойчивости):
| Триггеры | Что делает |
|----------|------------|
| start, старт, /start | Приветствие + меню |
| help, помощь, /help | Список команд |
| status, статус, /status | Сводка (через db-bridge) |
| mode manual, mode auto, режим | Переключение режима (admin) |
| onboard <url>, онбординг <url>, /onboard <url> | Онбординг клиента |
| start_cycle, start cycle, запуск цикла, старт цикла, /start_cycle | Запуск цикла |
| cancel, отмена, стоп, /cancel | Отмена текущего шага |
| topics, темы, /topics | Темы за сегодня |
| competitors, конкуренты, /competitors | Конкуренты |
| accounts, соцсети, /accounts | Статус соцсетей |
| budget, бюджет, /budget | Бюджет creatify |
| ping, пинг, /ping | Health-check |
| clients, клиенты, /clients | Список клиентов (admin) |

ВАЖНО:
- Парсер case-insensitive: "START_CYCLE" и "start_cycle" эквивалентны.
- Для onboard/start_cycle — парсить аргумент (URL) после ключевого слова.
- Если активный шаг CYCLE_SCRIPT_EDITING — любой текст интерпретируется как
  новый сценарий (не как команда), КРОМЕ "cancel" / "отмена" / "/cancel".
- Для неизвестного текста — отказ: "Я — бот контент-завода. Работаю только
  с командами из /help. По другим вопросам обратись к человеку."

ЧАСТЬ 2 — TELEGRAM MENU BUTTON:
Через setChatMenuButton сделать кнопку "Меню" с web_app/menu_commands.
Идеально — использовать Bot API setChatMenuButton с type "web_app", но проще:
через setMyCommands с командами БЕЗ слеша (если Bot API это разрешает в field
command), либо просто оставить setMyCommands как есть (для показа в подсказке),
и обучить оператора писать без слеша.

Проверить:
curl -s "https://api.telegram.org/bot$TOKEN/getMyCommands" | head
curl -s -X POST "https://api.telegram.org/bot$TOKEN/setChatMenuButton" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": 941296693, "menu_button": {"type": "commands"}}'

Если setChatMenuButton с type:"commands" работает — оператор увидит кнопку
"Меню" со списком наших 15 команд, при нажатии TG предложит отправить
сообщение с текстом "/command". Это не решает проблему (всё равно slash).

АЛЬТЕРНАТИВА: использовать menu_button type "web_app" с простым веб-интерфейсом
(HTML список кнопок, при нажатии которых через Telegram.WebApp.sendData или
window.location отправляется текст в чат). Но это сложно.

ПРОЩЕ ВСЕГО: оставить setMyCommands (для подсказки при вводе "/") + обновить
orchestrator-skill понимать ОБЕ формы (с slash И без). Если Hermes перехватывает
slash и не пускает в skill — тогда slash не работает, но текст без слеша работает.

ЧАСТЬ 3 — ТЕСТ:
1. hermes chat -q "start_cycle" --cli -Q → должен запустить цикл (mock).
2. hermes chat -q "status" --cli -Q → должен дать сводку.
3. hermes chat -q "стоп" --cli -Q → должен отменить.
4. hermes chat -q "напиши стих" --cli -Q → отказ.
5. hermes chat -q "onboard https://robotec.ru" --cli -Q → запуск онбординга.

КРИТЕРИЙ: все триггеры (с slash и без, en+ru) работают через hermes chat.
В живом TG оператор пишет "start_cycle" (без слеша) → бот запускает цикл.
Меню команд (через setMyCommands) — на ваше усмотрение.

БЮДЖЕТ: 60 минут.
```

## ДОПОЛНИТЕЛЬНО (P-8 если успеешь): Rate limit opencode zen

```
ЗАДАЧА: При тестах заметен HTTP 429 от opencode zen (free-тир rate limit).
Нужно сделать fallback в Hermes config.

ЧТО СДЕЛАТЬ:
1. Проверить ~/.hermes/config.yaml — есть ли fallback_chain.
2. Если нет — добавить auxiliary-модель или fallback на платный deepseek-v4-flash:
   fallback:
     - provider: opencode-zen
       model: deepseek-v4-flash  # платный, но стабильный
3. Альтернатива — добавить retry с backoff в skills.
4. Тест: запустить 5 раз подряд /start_cycle → не должно падать с 429.

КРИТЕРИЙ: при 429 от free — fallback срабатывает, цикл продолжает работу.
БЮДЖЕТ: 30 минут (опционально).
```

## ТВОЙ ПОРЯДОК ДЕЙСТВИЙ

1. Прочитай /autopilot.
2. Прочитай сам: `~/.hermes/skills/content-factory/orchestrator/SKILL.md` и
   `~/factory/specs/12-telegram-ux.md` (раздел 3 — команды).
3. Передай карточку P-7 в /autopilot (главная задача).
4. Если останется время — P-8 (rate limit fallback).
5. После P-7 — тестируй через `hermes chat -q "<триггер>"` все команды.
6. Перезапусти Hermes: `sudo systemctl restart hermes`.
7. Финальный отчёт:
   - P-7 done/BLOCKED + список работающих триггеров.
   - P-8 done/BLOCKED (если делался).
   - Готовность к живому TG-тесту оператором.

## ОЖИДАНИЯ

- Фикс P-7 — КРИТИЧНЫЙ. Без него оператор не может управлять ботом в TG.
- P-8 — желательный, но не блокирующий.
- Застрял — двигайся дальше.
- Честность: если menu_button не работает как хочется — пометить и оставить
  setMyCommands + обучить оператора писать без слеша.

**Приступай по /autopilot. Лимитов итераций нет.**

---

## СТАРТОВЫЕ КОМАНДЫ

```bash
chmod 400 /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem
ssh -i /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem ubuntu@83.166.233.95

export PATH="$HOME/.local/bin:$PATH"
source ~/hermes-agent/.venv/bin/activate

# Прочитай текущий skill
less ~/.hermes/skills/content-factory/orchestrator/SKILL.md

# Проверь текущее состояние — повтори баг
hermes chat -q "/start_cycle" --cli -Q 2>&1 | tail -5  # должен отказать
hermes chat -q "start_cycle" --cli -Q 2>&1 | tail -5   # сейчас тоже не работает, после фикса заработает

# Старт P-7
```
