# FIX-16..19 — Волна 4: безопасность и гигиена репо

**Status:** ready-for-agent
**Blocked by:** —

## Задача
4 фикса безопасности/репо. Часть — файлы репо, часть — серверные скрипты.
Результат: исправленные файлы в `.scratch/review-content-factory/fixes/` (для репо-файлов).

## FIX-16 — infra/db-bridge/server.js: fail-open → fail-closed
Сейчас: `if (TOKEN)` — при пустом FACTORY_DB_BRIDGE_TOKEN проверка пропускается (fail-open).
Правка: при пустом/отсутствующем токене — отвечать 500 `{ok:false, error:'bridge not configured'}`
(НЕ пропускать запросы). Также бинд: HOST по умолчанию 0.0.0.0 → 127.0.0.1 (или docker-сеть),
если докстринг обещает docker0 172.17.0.1.
Файл: `infra/db-bridge/server.js` → копия с правками в `.scratch/review-content-factory/fixes/db-bridge-server.js`.

## FIX-17 — docker-compose.yml → синхронизировать с live
В репо compose (n8n+hermes+caddy — спека 10) устарел относительно сервера
(n8n+db-bridge+cloudflared+hermes-bridge host-systemd). Правка:
- сервисы n8n (extra_hosts api.telegram.org → 149.154.167.220/.99, N8N_BLOCK_ENV_ACCESS_IN_NODE=false,
  env_file ~/factory/.env, volumes data/factory.db, media/, n8n data), db-bridge (порт 8787, X-BRIDGE-TOKEN),
  cloudflared (quick tunnel), убрать caddy/hermes (или пометить legacy).
- Зафиксировать версию n8n (2.34.4, не latest).
Файл: `docker-compose.yml` → копия в `.scratch/review-content-factory/fixes/docker-compose.yml`.
⚠️ ВАЖНО: это правка файла РЕПО для витрины/консистентности. На сервере НЕ перезапускать compose
(там живой стек работает) — только файл в fixes/ + в отчёте diff для ручного применения при следующем деплое.

## FIX-18 — гигиена репо
- `hermes/skills/` — добавить `caption-adapter.md` (скилл заявлен в DEPLOYMENT:465 и ALLOWED_SKILLS, но файла нет).
  Контент — по описанию из TICKETS-EXPANSION PM-3 и ссылки wf-publish-caption-adaptation-pm3.md
  (правила 17 платформ, вывод строго <CAPTION>...</CAPTION>) — создать в `.scratch/review-content-factory/fixes/caption-adapter.md`.
- DEPLOYMENT.md: исправить (в копии `.scratch/review-content-factory/fixes/DEPLOYMENT.md`):
  - :32 wf-credit-check — отметить как «встроено в CR-воркфлоу» или убрать строку;
  - :329 wf-creator-profile id `...015` → `...016`;
  - отметить, что история была переписана filter-repo (утечки вычищены, cc3b65d).

## FIX-19 — wf-creatify-webhook: mock-пометки (уже частично в FIX-10 — проверить дубли)
Проверить, что FIX-10 (Волна 2) уже убрал `local_path`/`mock:true`; если нет — убрать в этой волне.
Файл: `workflows/wf-creatify-webhook.json` → копия в fixes/.

## Ограничения
- Исходники репо НЕ менять напрямую — только копии в `.scratch/review-content-factory/fixes/`.
- Сервер НЕ перезапускать (compose — только diff). Никаких сетевых вызовов/SSH. Секреты не выводить.
- В отчёте: по каждому фиксу таблица (файл | было | стало) + diff-фрагменты.
- Язык: русский.
