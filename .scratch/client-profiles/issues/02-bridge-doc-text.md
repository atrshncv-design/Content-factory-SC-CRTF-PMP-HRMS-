# 02 — hermes-bridge: эндпоинт /doc-text (документы профиля)

**What to build:** Новый эндпоинт hermes-bridge для обработки документов профиля: по file_id из Telegram скачивает файл, извлекает текст (txt/pdf/docx), при digest=true возвращает LLM-дайджест. n8n сможет принимать файлы от пользователя и складывать текст в профиль.

**Blocked by:** None — can start immediately (disjoint: `hermes-bridge/server.py`)

**Status:** done (14.08, верифицировано оркестратором)

- [x] `POST /doc-text` (auth X-BRIDGE-TOKEN, как /ask): body {file_id, file_name, digest} → getFile → download file/bot{token}/{file_path} (urllib, stdlib) в /tmp → извлечение текста по типу (txt/md — raw; pdf — pypdf; docx — python-docx; иное → 400 «unsupported type»)
- [x] Если pypdf/python-docx не установлены — ответ 503 «doc extraction not configured» (установка — только с согласия пользователя в деплой-тикете 12)
- [x] Ответ: {name, mime, text, chars, digested}; text обрезан до 30000; digest=true → LLM-дайджест ~800 симв. (TEXT-маркеры, --reasoning none, hermes CLI), fallback при ошибке — text[:2000], digested=false
- [x] Локальные тесты (0 сетевых вызовов): 30 unittest (auth 401, bad request 400, unsupported type 400, 503 при отсутствии pypdf, txt-экстракция, digest-парсинг маркеров с mock) — `python3 .scratch/client-profiles/fixes/test_doc_text.py` → OK (skipped=1: pypdf не установлен локально)
- [x] /ask и /health — поведение сохранено (маркеры проверены; do_POST теперь маршрутизирует /ask vs /doc-text)
- [ ] Тест с реальным Telegram-документом — НЕ в этом тикете (деплой-гейт 12)

Артефакты: `.scratch/client-profiles/fixes/hermes-bridge-server.py`, `.scratch/client-profiles/fixes/test_doc_text.py`
