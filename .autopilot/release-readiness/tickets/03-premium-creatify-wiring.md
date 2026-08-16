# 03 — Премиум-воркфлоу Creatify: avatar, banner, product, asset, adclone, inspiration, text

**Требования:** R10i (полный приём всего scope), G09 (кнопки)
**Blocked by:** 01 (TG-структура команд/меню)
**Зона:** `workflows/wf-tg-bot.json` (команды/кнопки), `workflows/wf-creatify-{avatar,banner,product,asset,adclone,text}.json`
**Волна:** 2
**Status:** pending

## Что должно заработать

Все премиум-воркфлоу, существующие в репо, впаяны в бота и корректны до точки списания: для каждого есть команда в tg-commands-35, маршрут в Switch cmd wf-tg-bot, экран/кнопки, webhook path реально вызывается.

## Из брифа / манифеста, дословно

> «Полный приём всего scope» → «Всё из плана расширения» (AUDIT-AND-EXPANSION-PLAN, включая Спринт 3: avatar/adclone/banner)

## Разделы спецификации

История 6.

## Критерии приёмки

- [ ] Проверены все premium-воркфлоу: avatar, banner, product, asset, adclone, text, inspiration.
- [ ] Для каждого заявленного в tg-commands-35 маршрута: webhook path совпадает с именем в JSON, HTTP-нода настроена (typeVersion 4.5, keypair-заголовки, credit-гейт, neverError вложенный).
- [ ] Для отсутствующих/нереализованных команд: либо впаяны, либо в отчёт как deferred с причиной.
- [ ] wf-creatify-avatar обрабатывает загрузку видео и статус модерации (GET /personas/{id}).
- [ ] wf-creatify-text/inspiration подключены к боту или отложены.
- [ ] Валидатор + sim зелёные; 0 платных вызовов.
