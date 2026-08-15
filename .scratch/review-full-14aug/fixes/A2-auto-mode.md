# A2 — auto-режим (п.4): РЕАЛИЗОВАНО (14.08.2026)

**Файл:** `.scratch/review-full-14aug/fixes/wf-tg-bot.json` — 430 → **486 нод (+56)**, 0 issues, lint 0 (верифицировано оркестратором 14.08).
**Трансформер:** `.scratch/review-full-14aug/transform-A2-auto-mode.py` (перезапускаемый, идемпотентный).
**База:** результат A1-fix2 (430 нод, text_post).

## Что сделано (по отчёту субагента sa-0-3f6644d4)

**Схема переходов в auto:**
```
start_cycle → SC-аналитика → SC HTTP wf-analytics
  → SC Check analytics (ok=false: HTTP-сбой/нет кандидатов → алерт + IDLE)
  ok=true → SC Parse topic → INSERT topic → SC HTTP set topic
    → AU Build settings → AU Check (mode)
      ├─ auto → AU Build approve topic (UPDATE approved) → AU Build session (CYCLE_SCRIPT_PENDING)
      │        → AU bridge scriptwriter → AU Parse script → INSERT script → AU approve script
      │        → AU Build session gen (CYCLE_GENERATION_PENDING) → AU creatify-link → AU json-builder
      │        → AU creatify-submit → (callback как обычно) → AUP Check (mode) → auto-публикация
      └─ manual → как было (TG stage1, кнопки approve:topic)
```

**Ключевые решения:**
- 48 нод AU-ветки (AU Build/AU HTTP/AU Check/AU Format): settings.mode читается в AU/AU2/AUP Build settings; Check-ноды ветвят auto/manual
- Автоподтверждение темы (INSERT topics → UPDATE approved) и сценария (INSERT scripts → UPDATE approved) — без кнопок
- Автопубликация: при отсутствии video_output_url — text-only в Threads (по решению субагента; live-контракт wf-publish text-only уже починен в A1-fix1)
- Ошибки в auto (wf-analytics сбой, нет кандидатов, creatify failed, LLM-сбой bridge) → алерт оператору + возврат в IDLE (не зависание)
- AU HTTP bridge json-builder/scriptwriter получили neverError — сбой LLM = алерт, не зависание
- Ручной режим не тронут (ветка manual = как было); гейты 10/50 работают в auto так же
- /cancel работает в auto (CN Build)

## Верификация оркестратора (14.08)
- `validate-workflow-json.py` → ✅ 0 issues (486 нод, 421 связей, 217 jsCode node --check)
- `lint-workflow-json.py` → ✅ 0 находок
- AU-ноды 48 шт на месте; mode-проверки в AU Check/AU2 Check/AUP Check

## Остатки / не проверено
- Live-проверка auto-цикла НЕ выполнялась (правило 0 кредитов; требуется импорт в n8n + тест с mode=auto — после деплоя)
- Решение «auto-публикация text-only в Threads при отсутствии видео» требует подтверждения пользователем при показе (альтернатива: в auto показывать stage4 как в manual)

## Порядок в серии
Следующие задачи (B1, B2, C2-часть, B3-часть, D2) берут ЭТУ версию (486 нод) за базу.
