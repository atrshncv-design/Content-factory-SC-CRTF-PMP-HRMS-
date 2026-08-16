# 01 — TG-бот: команды, кнопки и доставка видео

**Требования:** G09 (кнопки не все работают, видео не всегда приходят), G03 (полный цикл не проверен), G05 (операторский UX)
**Blocked by:** —
**Зона:** `workflows/wf-tg-bot.json`, `workflows/wf-creatify-webhook.json`, `tg-commands-35.json`, `register-tg-commands-35.sh`
**Волна:** 1
**Status:** done

## Что должно заработать

Все 35 TG-команд и inline-кнопки ведут себя предсказуемо: нет ветвлений в default-«не понял», нет битых callback_data, нет мёртвых кнопок, видео приходит в чат стабильно.

## Из брифа / манифеста, дословно

> «кнопки не все работают правильно»
> «видео не всегда приходят в чат»
> «Только я (оператор)»

## Разделы спецификации

Истории 2, 5; Решения (TG-версии, neverError, esc(), sendVideo schema v1.2).

## Критерии приёмки

- [x] Все 35 команд из tg-commands-35.json есть в Switch cmd wf-tg-bot; каждая ветвь отвечает (не default).
      Проверено скриптом: 35/35 rightValues найдены в правилах Switch cmd, каждая ветвь ведёт в реальную Build-ноду
      (ST/HL/ST2/CN/TG ping/GPF/OB/MO/TP/CM/AC/BG/CL/CS/TG reload/CRS/CRP/CRC/AUD/TR/CMT/AVA/AVL/PT/MU/IN/HINT/DU/DR/AO/OP/PF/PS/PD/PH/PV/RO/QS/AUT), ни одна не уходит в fallback (Gate Build, out[45]).
      Parser покрывает все 35 команд (C-мап или startsWith-ветки).
- [x] Все callback_data-ноды валидны: формат `={{ }}`, не boolean-string, не пустые.
      Скрипт-аудит обеих файлов: 0 пустых, 0 boolean-строк, 0 литералов без `={{ }}`; validate_workflow.py «Проверка callback_data: OK».
      В этой волне исправлено 60+ литералов `"cmd:menu"` → `={{ "cmd:menu" }}` и т.п. в обоих файлах (в т.ч. `toggle:platform:*`, `schedule:*`, `confirm:publish`).
- [x] wf-creatify-webhook отправляет видео корректной схемой TG v1.2: resource='message' + параметр `file` + caption.
      `Telegram stage3`: `{"resource":"message","operation":"sendVideo","chatId":"={{ $json.chat_id }}","file":"={{ $json.video }}","replyMarkup":"inlineKeyboard",...,"additionalFields":{"caption":"={{ $json.text }}"}}` — эталон совпадает с references/n8n-telegram-sendvideo-schema.md.
      `Telegram stage3 auto` (auto-approve): та же схема sendVideo без клавиатуры. Fallback-ветка `Telegram stage3 fallback` — sendMessage c `text_legacy`.
- [x] Обработка failed/unknown creatify-статусов в webhook: оператор получает понятное сообщение, а не молчание.
      failed → Build update failed → HTTP UPDATE failed → HTTP tg-alert failed → оператору «Генерация #N failed: <reason>».
      unknown → (НОВОЕ) Build update unknown → HTTP UPDATE unknown (webhook_received=1) → HTTP tg-alert unknown → оператору
      «Генерация #N: неизвестный статус вебхука creatify «<status>». Видео не отправлено — проверь вручную.» → Respond unknown.
      Sim-проверка Build update unknown: alert_text собран корректно, esc эталонный.
- [x] Валидатор проекта: 0 issues по index/type/replyMarkup; BFS с триггеров достигает всех отправок.
      validate_workflow.py: 0 issues (932 ноды); validate-workflow-json.py: 0 issues; lint-workflow-json.py: 0 находок;
      check-esc-lines.py: 137/137 esc == эталон (исправлено 11 нод, из них SH Text async — реальный no-op esc).
      Аудит index/type/replyMarkup: 0 issues; BFS от tg-trigger достигает 142/142 TG-send; webhook: 3/3.
- [x] Sim-прогон мок-ответов по веткам video/shorts/text — зелёный.
      sim_ticket01_green.py: 35/35 PASS (SH Topic/Gate/SHT Format/Format gen/rlow/rerr/async/Update state/Reset; UV Parse/DU Gate/Format gen/low/cap/fail/Parse state dur_ok/rg_shorts; TX Format ask/Save/platforms/result ok/err/Format err/Reset; Gate Check).
      (t5a_sim.py: 3 FAIL — устаревшие ожидания относительно текущей семантики нод, код не виноват: SH Format async теперь SQL-билдер, SH Update state добавил auto_approve, DU Parse state dur_ok требует валидный dur — проверено корректными входами, все PASS.)
- [x] Нет вызовов creatify/scrapecreators на списание (только моки).
      Все HTTP-ноды creatify в wf-tg-bot — pre-existing (LB remaining_credits GET + localhost webhook-прокси), никогдаError вложенный `options.response.response.neverError` подтверждён; новых платных вызовов не добавлено. Правки тикета — только callback_data/esc/парсер/ветки webhook на db-bridge + локальный tg-alert.

## Итог волны

- wf-tg-bot.json: 932 ноды; все 35 команд маршрутизируются, callback_data валидны, esc эталонный (137/137), BFS зелёный.
- wf-creatify-webhook.json: 32 ноды; sendVideo v1.2, failed/unknown-статусы алертят оператора, валидаторы 0 issues.
- Осталось на платный тест пользователя: реальная генерация creatify (URL→видео / shorts / start_cycle) до точки списания — ветки ready.
