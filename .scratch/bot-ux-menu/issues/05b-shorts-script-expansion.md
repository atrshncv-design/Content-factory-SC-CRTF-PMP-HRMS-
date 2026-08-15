# T5b: wf-creatify-shorts — расширение темы→сценарий через hermes-bridge (бесплатно)

Status: done
Blocked by: —
Файл: `.scratch/bot-ux-menu/fixes/wf-creatify-shorts.json` (база: `.scratch/bot-ux-menu/base/wf-creatify-shorts.json`)
Спека: `.scratch/bot-ux-menu/spec.md` §4.9, §8

## Задача
wf-creatify-shorts (webhook `factory/shorts`) сейчас шлёт `{topic}`/`{script}` напрямую в POST /api/ai_shorts/. По cr5: ai_shorts генерит видео из script, длина ролика = длине текста → короткая тема даёт 3-сек ролик за 5 кред. Нужно: если пришёл `topic` (не `script`) — развернуть в полный сценарий через hermes-bridge (скилл scriptwriter, БЕСПЛАТНО), затем ai_shorts с script. И гарантировать в ответе `video_output` (creatify отдаёт его синхронно при status=done).

## Что сделать (все правки в JSON wf-creatify-shorts)

1. **Сохранить существующий контракт входа**: {script} | {topic} | {source_video_url}? — НЕТ: source_video_url убрать из валидации (поля нет в схеме ai_shorts, D8); если пришёл source_video_url — вернуть ошибку `{ok:false, error:'source_video_url не поддерживается — используй URL→видео сценарий'}`. Остальное (aspect_ratio, style, max_count, webhook_url) — сохранить.
2. **Новая ветка расширения** (только когда есть topic и нет script):
   - `Code need expand` (Switch/Code: body.script пуст и body.topic непуст → expand; иначе → как сейчас).
   - `Exp Build prompt` (Code: промпт scriptwriter'у: тема → сценарий шортса на ~30–60 сек чтения, 200–400 слов, вертикальный ролик, экспертный тон; плейсхолдер `__WEBHOOK_URL__` не нужен — bridge вызывается из n8n напрямую).
   - `Exp HTTP bridge` (HTTP POST `http://host.docker.internal:8642/ask`, заголовок `X-BRIDGE-TOKEN: {{ $env.HERMES_BRIDGE_TOKEN }}`, jsonBody `={{ {skill: 'scriptwriter', prompt: $json.prompt} }}` — выражение-объект; options.timeout 300000, options.response.response.neverError true). Параметры скилла: скилл scriptwriter существует в hermes-bridge whitelist (PM-3). ⚠️ deepseek отдаёт reasoning-блок — парсить первый `{...}` JSON (extractJSON) ИЛИ маркерный контракт `<SCRIPT>...</SCRIPT>` (fallback — весь текст).
   - `Exp parse` (Code: извлечь script из ответа; пусто → error-ответ `{ok:false, error:'не удалось сгенерировать сценарий'}`).
   - Соединить: Build payload → script = (расширенный, если был topic) | (исходный script) → POST /api/ai_shorts/ (существующая HTTP-нода).
3. **Ответ**: в `Code Normalize` убедиться, что `video_output` пробрасывается в ответ (`{ok:true, shorts_id, status, video_output, items:[...]}`) — он уже есть; добавить `topic`/`script` эхо не нужно. Статус-контракт: если creatify вернул status=done + video_output — отдать сразу; иначе status + progress (асинхронная ветка остаётся, webhook_url сохраняется).
4. **Не менять**: HTTP credits-гейт (порог 30 → оставить 30? Спека §5.2: гейт в wf-tg-bot (10/50); здесь порог 30 — внутренний, ОСТАВИТЬ как есть), auth, ответы Respond.
5. ВАЖНО: никаких реальных вызовов ai_shorts при тестах (тесты — статические: node --check, sim-code-node с фейковыми входами bridge/ai_shorts).

## Валидация перед сдачей
- node --check; BFS; sim-code-node для Exp-цепочки (вход: topic; вход: script; вход: source_video_url → error).
- lint — 0 новых.
- Контракт ответа: {ok, shorts_id, status, video_output, items} — проверить соответствие T5a.

## Вывод
Полный JSON → `.scratch/bot-ux-menu/fixes/wf-creatify-shorts.json`. Ответ: ноды, валидации, подтверждение контракта ответа.
