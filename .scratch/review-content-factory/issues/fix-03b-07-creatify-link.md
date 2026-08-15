# FIX-03b+07 — wf-creatify-link: туннель + приоритет link_id

**Status:** ready-for-agent
**Blocked by:** —

## Задача
Исправить 2 бага в `workflows/wf-creatify-link.json` (исходник — файл репо).
Результат: обновлённый JSON в `.scratch/review-content-factory/fixes/wf-creatify-link.json`.

## Правки
1. **К5 — хардкод туннеля:** нода `HTTP Request` (или где формируется webhook_url):
   `https://assessment-fossil-assignments-alice.trycloudflare.com/...` → собрать из
   `$env.WEBHOOK_URL` + путь (как сделано в wf-creatify-submit). Проверить trailing slash:
   нормализовать (`$env.WEBHOOK_URL.replace(/\/$/, '') + '/webhook/...'`).

2. **В6 — приоритет link_id:** нода `Code assemble` (или аналог): сейчас
   `($json.link && $json.link.id) || $json.id` — берёт ВЛОЖЕННЫЙ link.id (невалидный).
   Проверенный контракт: валиден ВЕРХНИЙ id ответа POST /api/links/. Поменять на
   `$json.id || ($json.link && $json.link.id)` (как в wf-creatify-adclone «Extract link»).

## Ограничения
- Только чтение исходника + запись результата в `.scratch/review-content-factory/fixes/wf-creatify-link.json`.
- Исходный `workflows/wf-creatify-link.json` НЕ менять.
- Никаких сетевых вызовов/SSH. Секреты не выводить.
- В отчёте: изменённые ноды, было → стало.
- Язык: русский.
