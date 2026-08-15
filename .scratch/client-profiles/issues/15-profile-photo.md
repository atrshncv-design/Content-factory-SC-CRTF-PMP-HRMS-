# 15 — Фото в профиль (OCR) и отклонение видео

**What to build:** Пользователь может приложить фото к профилю (в шаге 6 интервью и в режиме «Добавить документ»): фото → hermes-bridge /img-text → извлечённый текст в контекст. Видео отклоняется с подсказкой.

**Blocked by:** 14 (контракт /img-text; сам bridge может быть не задеплоен — E2E в деплой-тикете 21). Файловая серия: база = результат 15+ (см. примечание).

**Status:** done (15.08, верифицировано оркестратором)

- [ ] Parser: `if (item.message && item.message.photo)` → command='profile_photo', args {file_id: <наибольший размер: photo[last].file_id>, file_name: 'photo_<message_id>.jpg'}; `if (item.message && item.message.video)` → command='profile_video', args {file_id, file_name}
- [ ] Switch cmd: правила profile_photo, profile_video (перед fallback; снапшот connections до мутаций)
- [ ] profile_photo ветка: 'PH Check' (state/draft как PD Check: PROFILE_AWAIT+step6 → interview_photo; PROFILE_ADD_DOC → add_photo; иначе outside → «Фото принимаются в профиле: Профиль → Добавить документ» + Меню) → interview/add: 'PH Build state' (PROFILE_DOCS_SUBMITTING — переиспользовать общее состояние) → 'PH Build bridge' ({file_id, file_name, digest:false} → /img-text) → 'PH HTTP bridge' (стиль PD HTTP bridge: host.docker.internal:8642/img-text, X-BRIDGE-TOKEN $env.HERMES_BRIDGE_TOKEN, timeout 300000, вложенный neverError) → 'PH Parse' (ошибка → fail «Не смог прочитать фото»; ok → {name, mime:'image/…', text, chars} → append в draft.docs (интервью, state→PROFILE_AWAIT) или в clients.context_docs (add_doc, state→PROFILE_ADD_DOC — 2 SQL как PD Parse) → «✅ Добавлено: <name> (N симв.)») → TG ph ok / TG ph fail (esc(), кнопки: Готово/Пропустить/Отмена для интервью; Отмена/Меню для add_doc)
- [ ] profile_video ветка: 'PV Format' (esc: «🎬 Видео пока не поддерживаем. Пришли PDF/DOCX/TXT, фото или ссылку на документ») → 'TG pv' (Меню) — без обращения к bridge
- [ ] Валидации: validate 0 issues, lint 0, node --check, sim (PH Check 3 режима; PH Parse ok/error; Parser photo/video)

Примечания: файловая серия — каждый тикет = трансформация полного файла от результата предыдущего. База: `.scratch/client-profiles/fixes/wf-tg-bot.json` (719 нод, волна 1, снапшот wf-tg-bot.11.json). Результат — в тот же файл (list len 1, ensure_ascii=False).
