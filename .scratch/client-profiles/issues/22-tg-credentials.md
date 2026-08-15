# 22 — TG-credentials всем нодам (корневой фикс доставки)

**What to build:** Все TG-ноды без credentials получают ссылку на существующий telegramApi-credential; проверяются и другие credential-типы. После фикса start_cycle и ветки URL→видео реально шлют сообщения.

**Blocked by:** None — can start immediately (известный фикс, файл fixes/wf-tg-bot.json)

**Status:** done (15.08, верифицировано оркестратором)

- [ ] fixes/wf-tg-bot.json: всем нодам `n8n-nodes-base.telegram` без поля credentials проставить `{"telegramApi": {"id": "10000000-0000-4000-8000-000000000004", "name": "telegram"}}` (эталон — TG pf / TG start)
- [ ] Скан других credential-типов: найти все node.types, у которых у каких-то нод есть credentials, и проверить, что у ВСЕХ нод этого типа credentials есть (иначе — разобрать, нужны ли они; для HTTP-нод с заголовками credentials не нужны)
- [ ] validate 0 issues / lint 0 / BFS; node --check не затронут (TG-ноды без jsCode)
- [ ] Передеплой apply_fix + ретест: start_cycle → вопрос длительности ДОХОДИТ до чата (exec success, lastNodeExecuted ≠ TG DR ask, либо success)

Примечания: credential id 10000000-0000-4000-8000-000000000004 существует на сервере (все рабочие TG-ноды ссылаются на него). Формат файла — JSON-массив из 1 элемента, ensure_ascii=False.
