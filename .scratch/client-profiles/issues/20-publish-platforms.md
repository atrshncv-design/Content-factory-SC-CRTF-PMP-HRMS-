# 20 — Per-профильные платформы публикации

**What to build:** Профиль хранит дефолтные платформы публикации (clients.publish_platforms); шаг публикации открывается с предвыбранными платформами профиля (можно поменять); платформы редактируются из карточки профиля.

**Blocked by:** 19 (файловая серия). Контракт: clients.publish_platforms (JSON-массив) из тикета 13.

**Status:** done (15.08, верифицировано оркестратором)

- [ ] Карточка профиля (PF Format): строка «📱 Платформы: <список или «не заданы»>» + кнопка «📱 Платформы» (pf_platforms) — литерал
- [ ] Switch cb: правило pf_platforms (перед fallback; снапшот connections)
- [ ] Ветка pf_platforms (для активного профиля чата): 'PPM Build' (SELECT id, name, publish_platforms FROM clients WHERE id=<резолв T5>) → 'PPM HTTP' → 'PPM Format' («Платформы профиля <name> (предвыбранные на публикации):» + подсказка) → 'TG ppm' с кнопками-переключателями: «☑️/⬜️ Instagram» toggle:ppm:instagram, YouTube, TikTok, Telegram, Threads, X (callback_action toggle, entity_type 'ppm', entity_id платформа — маппинг в Parser: toggle {platform: 'toggle_platform', ppm: 'toggle_ppm'} или action.startsWith('toggle') → 'toggle_ppm' при entityType ppm) + «✅ Готово» ppm_done + Меню
- [ ] toggle_ppm:{platform} ветка: 'PPM Build toggle' (Code: читает publish_platforms, toggle платформу в массиве, UPDATE clients SET publish_platforms=? WHERE id=?) → 'PPM HTTP toggle' → 'PPM Format' (обновлённый список) → 'TG ppm' (ответ-подтверждение через editMessage? — упрощение: новое сообщение со списком; НЕ редактировать старое)
- [ ] ppm_done: 'PPM Format ok' («✅ Платформы сохранены: …» + Профиль/Меню) → 'TG ppm ok'
- [ ] Шаг публикации (stage4): инициализация selected_platforms из профиля — найти ноду, где stage4 показывает выбранные платформы (TG stage4 / 'ST4' цепочка: сейчас selected_platforms из сессии); добавить: при старте публикации (publish_gen → PG Build session) — если sessions.selected_platforms пуст и у профиля есть publish_platforms → проинициализировать selected_platforms=профильные (UPDATE sessions SET selected_platforms=<JSON профиля> — нода 'PG Build session' или соседняя; SQL-подзапрос из clients по резолву) — ПРОВЕРИТЬ фактическую цепочку stage4 и вставить минимально
- [ ] Валидации: validate 0 issues, lint 0, node --check, sim (PPM Build toggle — toggle в JSON-массиве; PG инициализация — selected_platforms из профиля)

Примечания: платформы-значения как в stage4 (instagram/youtube/tiktok/telegram/threads/x); toggle — parse→toggle→stringify (try/catch, битый JSON → []). Переключение кнопок — новым сообщением (не editMessage — проще и надёжнее).
