# ПРОМПТ — ФИКС АКТИВАЦИИ ОРКЕСТРАТОР-СКИЛЛА В GATEWAY (P-9, КРИТИЧНО)

> Скопируй текст ниже в первое сообщение новому агенту.

---

Ты — **агент-разработчик** контент-завода. Фиксишь КРИТИЧНЫЙ баг: Hermes gateway
не активирует orchestrator-skill для входящих TG-сообщений. Работаешь через
/autopilot.

== ⚠️ КРИТИЧНО ПРО РЕЖИМ РАБОТЫ ==

У тебя НЕТ лимита итераций. Работай до завершения.
Застрял >10 минут — BLOCKED. 3 попытки. Финальный отчёт — только когда всё пройдено.

== ПРОБЛЕМА ==

В живом Telegram бот ведёт себя как обычный chat-assistant, а не как
оркестратор контент-завода. Симптомы:
- "cancel" → "Отменяю — ничего не запускал..." (LLM импровизирует)
- "/status" → отдаёт дефолтный Hermes /status (Session ID, tokens billed)
- "напиши стих" → отвечает стихом (не отказом!)
- "/start_cycle" → Unknown command

== КОРНЕВАЯ ПРИЧИНА ==

В ~/.hermes/config.yaml НЕТ настройки автозагрузки orchestrator-skill для
gateway. Каждое входящее TG-сообщение уходит в LLM как чистый текст — без
контекста скилла. Hermes skills list показывает orchestrator как enabled, но
enabled ≠ автоматически загружается в сессию.

Доказательство: при `hermes chat -q "..."` через CLI скилл подхватывается
(тесты проходили), а в live gateway-режиме для TG — нет.

== ЧТО НАЙТИ И ИСПРАВИТЬ ==

1. **Изучи Hermes-документацию и исходники**, как настроить автоматическую
   загрузку skill для gateway-сессий. Возможные пути:
   - `agent.skills_preload` или `gateway.skills_default` в config.yaml
   - `hermes config set` для preload
   - аргумент `--skills` для `hermes gateway run`
   - системный промпт / persona для gateway
   - команда `hermes gateway setup` для конфигурации platform-specific skills

   Ищи в:
   - `~/hermes-agent/gateway/run.py` и `slash_commands.py`
   - `~/hermes-agent/cli.py` — `build_preloaded_skills_prompt`
   - `~/hermes-agent/agent/skill_commands.py`
   - `hermes-agent.nousresearch.com/docs/user-guide/features/skills`
   - `hermes-agent.nousresearch.com/docs/user-guide/messaging`

2. **Найди точную настройку** (например `gateway.preloaded_skills:
   [content-factory/orchestrator]` или подобное). Примени через `hermes config
   set` или прямой записью в config.yaml.

3. **Очисти контекст разработчика** из памяти Hermes:
   - Создай USER.md с профилем оператора (а не разработчика):
     "Оператор контент-завода. Общается через Telegram. Не разработчик.
      Используй текстовые триггеры (см. ~/factory/specs/12-telegram-ux.md)."
   - В MEMORY.md убедись, что STATE: IDLE (не CYCLE_ANALYTICS_PENDING).
   - Если в прошлых сессиях накопился контекст — сбрось через `hermes sessions`
     (закрой все старые TG-сессии, чтобы новая стартовала чистой).

4. **Дополнительно — system prompt / persona**: возможно, для gateway нужна
   явная persona. Проверь `hermes config set agent.persona` или
   `gateway.system_prompt`. Если есть — задай:
   "Ты — оркестратор контент-завода (Robotec). Следуй skill content-factory/orchestrator
   дословно. Отвечай только на команды из ~/factory/specs/12-telegram-ux.md.
   На любые другие темы — отказ."

5. **Перезапусти Hermes**: `sudo systemctl restart hermes`.

6. **Проверь через live TG** (если возможно тестировать через шлюз Telegram,
   не через CLI). Симптомы правильной работы:
   - "cancel" → "Состояние сброшено в IDLE" (НЕ свободный ответ LLM)
   - "status" → сводка из DB (НЕ Hermes /status)
   - "напиши стих" → канонический отказ
   - "start_cycle" → запуск цикла, REAL inline-кнопки в TG

== КАК ПОДКЛЮЧИТЬСЯ ==

chmod 400 /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem
ssh -i /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem ubuntu@83.166.233.95
export PATH="$HOME/.local/bin:$PATH"
source ~/hermes-agent/.venv/bin/activate

== КОНТЕКСТ ПРОЕКТА ==

- ~/factory/specs/12-telegram-ux.md — UX/state machine/триггеры
- ~/.hermes/skills/content-factory/orchestrator/SKILL.md — сам skill (303 строки, в порядке)
- ~/.hermes/config.yaml — ТУТ НАДО ДОБАВИТЬ настройку preload
- ~/.hermes/memories/{MEMORY.md, USER.md} — память агента
- systemd hermes.service — ExecStart=/home/ubuntu/hermes-agent/.venv/bin/hermes gateway run

== КРИТЕРИИ ГОТОВНОСТИ ==

1. В config.yaml есть явная настройка автозагрузки orchestrator-skill.
2. После `sudo systemctl restart hermes`:
   - journalctl -u hermes | grep "skill" — видно, что orchestrator подгружен.
3. Live TG-тест (попросить пользователя): cancel / status / напиши стих / start_cycle
   работают как предписано в спеке 12, а НЕ как chat-assistant.
4. Если live-тест недоступен — подтверди хотя бы через `hermes chat` с флагом
   имитации gateway-режима, что skill подгружается в свежей сессии.

== ЧТО ДЕЛАТЬ ЕСЛИ НЕ НАХОДИШЬ НАСТРОЙКУ ==

Альтернативные пути (если preload-skill настройки нет):
- **System prompt через `agent.system_prompt` в config.yaml** — задай жёсткий
  промпт, дословно дублирующий orchestrator/SKILL.md.
- **Команда `hermes config set agent.persona`** — задай persona "Оркестратор
  контент-завода".
- **Wrapper-скрипт для gateway** — systemd ExecStart запускает скрипт, который
  форкает `hermes gateway run` и параллельно каждые N секунд проверяет активные
  сессии и в нужные инжектит skill (хакерский путь, но работает).
- **Чтение исходников gateway/run.py и сSee典故 как там сессии создаются** —
  возможно, через `gateway.sessions.skills_default` или подобное.

== БЮДЖЕТ ==

60-90 минут. Это критичный фикс — без него весь UX не работает.

== ОЖИДАНИЯ ==

- После твоего фикса live TG-тест должен пройти ВСЕ 4 команды как в спеке.
- Если нашёл несколько вариантов — выбери самый чистый (через config), не хак.
- Если фикс требует рестарта всех TG-сессий — предупреди пользователя.

== ОТЧЁТ ==

- Что за настройка найдена (точный ключ в config.yaml или флаг CLI).
- Какие команды применил.
- Как тестировал (live TG или CLI-эмуляция).
- Что работает / BLOCKED.

Приступай по /autopilot. Лимитов итераций нет.

== СТАРТОВЫЕ КОМАНДЫ ==

chmod 400 /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem
ssh -i /Users/aleksandrtrisenkov/Downloads/ubuntu-STD3-2-4-50GB-E6QEKqcS.pem ubuntu@83.166.233.95
export PATH="$HOME/.local/bin:$PATH"
source ~/hermes-agent/.venv/bin/activate

# Изучи текущий конфиг
cat ~/.hermes/config.yaml
hermes config show
hermes skills list | grep content-factory

# Найди в исходниках как активируется skill для gateway
grep -rn "preloaded_skills\|skills_default\|gateway_skills" ~/hermes-agent/gateway ~/hermes-agent/cli.py 2>/dev/null | head -20

# Проверь что бот сейчас делает НЕ так
hermes chat -q "cancel" --cli -Q 2>&1 | tail -5  # через CLI работает
# в live TG — НЕ работает
sudo journalctl -u hermes -n 30 --no-pager
