# 14 — hermes-bridge /img-text (фото → OCR через Hermes-зрение)

**What to build:** Новый эндпоинт hermes-bridge: по file_id фото из Telegram скачивает изображение и через Hermes-агента (зрение) извлекает текст (OCR) для контекста профиля.

**Blocked by:** None — can start immediately (disjoint: `hermes-bridge/server.py`)

**Status:** done (15.08, верифицировано оркестратором)

- [ ] `POST /img-text` (auth X-BRIDGE-TOKEN, как /doc-text): body {file_id, file_name} → getFile → download (urllib) в /tmp → вызов hermes CLI: «Прочитай изображение <путь> и верни ВЕСЬ видимый текст строго в открывающем и закрывающем TEXT-маркерах» (--cli -Q --reasoning none, HERMES_BIN как в /ask; путь к файлу в промпте — hermes-агент сам прочитает изображение vision-инструментом)
- [ ] Парсинг маркеров regex; при ошибке/таймауте/отсутствии маркеров → 502 с понятной ошибкой (не выдумывать текст!)
- [ ] Ответ: {name, mime: 'image/…', text, chars}; text обрезан до 30000
- [ ] Не менять /ask, /health, /doc-text
- [ ] Локальные тесты с mock: auth 401, bad request 400, hermes-ошибка → 502, маркерный парсинг (mock stdout), отсутствие маркеров → ошибка. 0 сетевых вызовов в тестах.
- [ ] Живой OCR-тест (реальное фото в TG) — НЕ в этом тикете (деплой-гейт 21, согласие)

Примечания: стиль кода — как в fixes/hermes-bridge-server.py (существующий сервер с /doc-text); маркерный контракт как в digest-ветке /doc-text. Секретов не писать — только имена env.
