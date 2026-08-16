# 11 — Убрать дорогие механики из бота (меню, команды, ветки) + деактивация

**Спека:** spec-3formats.md §1–4
**Blocked by:** —
**Status:** ready-for-agent

## Что сделать

1. `workflows/wf-tg-bot.json`:
   - Меню (нода TG menu gen и её форматтер): убрать кнопки «🖼️ Ассет», «📦 Product», «🪧 Баннеры», «👥 Мои аватары» (персоны остаются, но через /my_avatars команду; в меню их не показывать). Оставить: 🔗 URL→видео, 🎬 AI Shorts, 🎭 Видео с аватаром (появится в тикете 15 — пока можно без неё), 🔄 Запустить цикл, 🧹 Отмена, 📋 Меню.
   - Switch cmd: ветки hint_asset / hint_product / hint_banner и обработчики команд asset/product/banner — ответ «⚠️ Формат отключён. Доступны: URL→видео, AI Shorts, Видео с аватаром» (или удалить ветки — на выбор, главное не вызывать платные воркфлоу).
   - `asset`, `product`, `banner` не должны вести к платным HTTP-вызовам creatify.
2. Команды: `tg-commands-35.json` — удалить `asset`, `product`, `banner` (оставить upload_avatar/my_avatars). Зарегистрировать обновлённый список на сервере (register-tg-commands-35.sh).
3. Сервер: деактивировать воркфлоу wf-creatify-asset, wf-creatify-product, wf-creatify-banner, wf-creatify-adclone, wf-creatify-text (n8n update:workflow --active=false). Файлы в репо НЕ удалять.

## Критерии приёмки

- В меню нет Ассет/Product/Баннеры.
- Команды asset/product/banner отвечают «отключено» (или не зарегистрированы).
- На сервере 5 воркфлоу неактивны; shorts/link/submit/webhook/poll — активны.
- Валидатор 0 issues, pytest зелёный.
