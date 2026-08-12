# TG-LIVE-TEST — живой тест inline-кнопок в Telegram (P-2)

> Дата: 2026-08-12. Статус: PARTIAL — CLI-тесты state machine зелёные (U-7),
> живой roundtrip «кнопка → callback_query → Hermes → STATE» НЕ проверен.
> Требуется нажатие кнопки живым оператором (user_id 941296693).
> Бот: @contentzavod_bot (или как зарегистрирован, см. TELEGRAM_BOT_TOKEN в ~/.hermes/.env).

## Что уже подтверждено (делать НЕ надо)
- State machine и callback-обработка протестированы через CLI (`hermes chat -q`, U-7, 12.08):
  логи 27–32 в `~/factory/data/factory.db` (callback `edit:script:3`, state_change'и, script_updated).
- Сейчас STATE: `IDLE` (сброшен после теста). Сервис `hermes` — active, gateway в polling-режиме.
- Эмулировать нажатие кнопки через Bot API НЕЛЬЗЯ: `answerCallbackQuery` работает только
  в ответ на реальное нажатие, callback_query нельзя подделать, второй polling запускать запрещено.

## Задача оператора (≈ 3–5 минут)

1. **Открой чат с ботом в Telegram и отправь** `/start_cycle`.
   - Ожидание: бот ответит **«Этап 1/4 — Тема»** с карточкой темы и inline-кнопками:
     `[ ✅ Утвердить ]  [ ✏️ Изменить ]` / `[ ❌ Отклонить ]  [ 🔄 Другая тема ]`.

2. **Дождись карточку темы** (может занять 1–4 минуты: аналитика + генерация темы).

3. **Нажми кнопку `✅ Утвердить`** (нижняя строка, левая кнопка).
   - Ожидание: бот ответит **«✍️ Этап 2/4 — Сценарий»** с текстом сценария и кнопками
     `[ ✅ Утвердить ]  [ ✏️ Изменить ]  [ ❌ Отклонить ]`.

4. **Проверь, что STATE сменился** (по SSH на сервере 83.166.233.95):

   ```bash
   head -1 ~/.hermes/memories/MEMORY.md
   # Ожидание: STATE: CYCLE_SCRIPT_PENDING | updated_at=<свежее время>
   ```

   ```bash
   sqlite3 ~/factory/data/factory.db "SELECT event FROM logs ORDER BY id DESC LIMIT 5"
   # Ожидание: свежая запись state_change: CYCLE_ANALYTICS_PENDING → CYCLE_SCRIPT_PENDING
   # и запись callback: approve:topic:<id> → CYCLE_SCRIPT_PENDING
   ```

5. **Если всё сошлось** — roundtrip inline-кнопок РАБОТАЕТ. Можно продолжить цикл
   (нажать `✅ Утвердить` на сценарии → этап 3, и т.д.) или завершить тест: `/cancel` или `/status`.

## Что считать результатом
- **PASS**: STATE = CYCLE_SCRIPT_PENDING в MEMORY.md + в logs запись
  `callback|approve:topic:<id> → CYCLE_SCRIPT_PENDING` + сообщение «Этап 2/4» пришло в чат.
- **FAIL**: STATE не сменился / сообщение не пришло / кнопки не отрисовались →
  сохранить скриншоты, вывод `systemctl status hermes`, хвост `~/.hermes/logs/agent.log`,
  вернуть в P-2 как BLOCKED.

## Справочно: callback_data этапов (для сверки логов)
- Этап 1: `approve:topic:{id}` / `edit:topic:{id}` / `reject:topic:{id}` / `alt:topic:{id}`
- Этап 2: `approve:script:{id}` / `edit:script:{id}` / `reject:script:{id}`
- Этап 3: `publish:gen:{id}` / `regen:gen:{id}` / `reject:gen:{id}`
- Этап 4: `toggle:platform:{name}` / `schedule:{now|2h|tomorrow_12}` / `confirm:publish`
