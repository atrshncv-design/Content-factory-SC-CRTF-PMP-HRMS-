# 15 — Бот: «🎭 Видео с аватаром» (выбор аватара → сценарий → 30/60 → submit)

**Спека:** spec-3formats.md §6–7
**Blocked by:** 14 (нужен wf-creatify-lipsync)
**Status:** ready-for-agent

## Что сделать

1. wf-tg-bot.json — новый путь (команда /avatar_video + кнопка меню «🎭 Видео с аватаром»):
   - Выбор аватара: список персон из БД (avatars, status=approved) — кнопки по одной; если нет — «сначала создай аватар: /upload_avatar».
   - Затем тема (текст пользователя) → сценарий (scriptwriter, слова = dur×2).
   - Длительность 30/60 (кнопки, строго).
   - Submit: POST factory/lipsync {text: full_text, creator: <id>, video_length: dur, mode: 'video'} → {lipsync_id} → INSERT generations (type='lipsync', creatify_id) + привязка сессии (generation_id) → сообщение «✅ Генерация запущена».
2. Доставка: поллер (тикет 14) при done → download + Telegram sendVideo + кнопки (vd_ok/vd_regenerate/vd_reject/menu), как в stage3.
3. Меню: добавить кнопку «🎭 Видео с аватаром».

## Критерии приёмки

- /avatar_video: аватар → тема → 30/60 → «✅ Генерация запущена»; сессия привязана.
- Без аватаров — подсказка /upload_avatar.
- Валидатор 0 issues; генерация через script_only/mock-проверку до точки списания.
