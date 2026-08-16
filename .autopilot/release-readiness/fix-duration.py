#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Фикс длительности роликов: строго <=30 сек (5 кредитов) для creatify ai_shorts.
1) hermes/skills/scriptwriter.md — норма 90-110 -> 55-62 слова
2) wf-creatify-shorts.json — Code validate (video_length), Exp Build prompt (55-60 слов),
   Code Build payload (жёсткая обрезка до 60 слов / 30 сек по границе предложения)
3) wf-tg-bot.json — CT/AU: words = dur * 60 / 30 (было dur * 65 / 30)
"""
import json, re, sys

SHORTS = 'workflows/wf-creatify-shorts.json'
TGBOT = 'workflows/wf-tg-bot.json'
SKILL = 'hermes/skills/scriptwriter.md'

# ---------- 1) scriptwriter.md ----------
skill = open(SKILL, encoding='utf-8').read()
old_norm = 'Для 30 секунд на русском ≈ **90–110 слов** (≈3–3.5 слова/сек). Сам считай и держись\nв лимите. Слишком длинный сценарий = обрезка в озвучке = брак.'
new_norm = ('Для 30 секунд на русском ≈ **55–62 слова** (≈2 слова/сек — замерено на реальной '
            'озвучке creatify: 86 слов = 40 сек = 10 кредитов). Сам считай и держись в лимите: '
            'длиннее ~60 слов — ролик уйдёт в 40 сек и будет стоить 10 кредитов вместо 5.')
assert old_norm in skill, 'scriptwriter.md: норма не найдена'
skill = skill.replace(old_norm, new_norm)
old_est = '"estimated_words": 65'
new_est = '"estimated_words": 60'
assert old_est in skill, 'scriptwriter.md: estimated_words не найден'
skill = skill.replace(old_est, new_est)
open(SKILL, 'w', encoding='utf-8').write(skill)
print('scriptwriter.md: OK')

# ---------- 2) wf-creatify-shorts.json ----------
raw = open(SHORTS, encoding='utf-8').read()
data = json.loads(raw)
data = data[0] if isinstance(data, list) else data

def node(name):
    return next(n for n in data['nodes'] if n['name'] == name)

# --- Code validate: добавить video_length ---
cv = node('Code validate')
js = cv['parameters']['jsCode']
old_style = """const style = (body.style !== undefined && body.style !== null && String(body.style).trim() !== '')
  ? String(body.style).trim() : 'Cinematic';"""
assert old_style in js, 'Code validate: style-блок не найден'
new_style = old_style + """
let videoLength = (body.video_length !== undefined && body.video_length !== null && String(body.video_length).trim() !== '')
  ? Number(body.video_length) : 30;
if (!Number.isFinite(videoLength) || ![15, 30, 45, 60].includes(videoLength)) videoLength = 30;"""
js = js.replace(old_style, new_style)
old_ret = "json: { ok: true, script: script, topic: topic, mode: mode, max_count: maxCount,\n          language: language, aspect_ratio: aspectRatio, style: style, webhook_url: webhookUrl }"
assert old_ret in js, 'Code validate: return-блок не найден'
new_ret = "json: { ok: true, script: script, topic: topic, mode: mode, max_count: maxCount,\n          language: language, aspect_ratio: aspectRatio, style: style, video_length: videoLength, webhook_url: webhookUrl }"
js = js.replace(old_ret, new_ret)
cv['parameters']['jsCode'] = js
print('Code validate: OK')

# --- Exp Build prompt: норма слов ---
eb = node('Exp Build prompt')
js = eb['parameters']['jsCode']
old_w = 'ровно на 30 секунд озвучки (90–110 слов на русском языке)'
assert old_w in js, 'Exp Build prompt: норма не найдена'
js = js.replace(old_w, 'ровно на 30 секунд озвучки (55–60 слов на русском языке)')
eb['parameters']['jsCode'] = js
print('Exp Build prompt: OK')

# --- Code Build payload: жёсткий лимит + обрезка ---
cb = node('Code Build payload')
js = cb['parameters']['jsCode']
old_tail = """const cleaned = cleanText(script);
const words = cleaned === '' ? 0 : cleaned.split(/\\s+/).length;
const BAD = /(\\{\\{|\\}\\}|note\\s*:|tags,|script|json)/i;
if (cleaned === '' || words < 60 || words > 150 || BAD.test(cleaned)) {
  return [{ json: { ok: false, error: 'Не удалось подготовить сценарий — попробуй ещё раз.' } }];
}
/* Creatify enum: aspect_ratio 9x16|16x9|1x1; style из фикс-списка */"""
new_tail = """const cleaned = cleanText(script);
const words = cleaned === '' ? 0 : cleaned.split(/\\s+/).length;
const BAD = /(\\{\\{|\\}\\}|note\\s*:|tags,|script|json)/i;
if (cleaned === '' || words < 50 || BAD.test(cleaned)) {
  return [{ json: { ok: false, error: 'Не удалось подготовить сценарий — попробуй ещё раз.' } }];
}
/* Жёсткий лимит длительности: creatify ai_shorts НЕ принимает video_length,
   длительность = длине скрипта (замер 16.08: 86 слов = 40 сек = 10 кредитов).
   Норма: 30 сек = ~60 слов (2 слова/сек). Обрезаем по границе предложения. */
const targetSec = (v.video_length !== undefined && [15, 30, 45, 60].includes(Number(v.video_length)))
  ? Number(v.video_length) : 30;
const MAX_WORDS = Math.round(targetSec * 2);
let final = cleaned;
let finalWords = words;
if (words > MAX_WORDS) {
  const parts = final.split(/(?<=[.!?…])\\s+/);
  let acc = '';
  let accWords = 0;
  for (const part of parts) {
    const w = part.split(/\\s+/).length;
    if (accWords + w > MAX_WORDS) break;
    acc = acc ? acc + ' ' + part : part;
    accWords += w;
  }
  if (!acc || accWords < Math.max(40, Math.round(MAX_WORDS * 0.6))) {
    acc = final.split(/\\s+/).slice(0, MAX_WORDS).join(' ');
    accWords = MAX_WORDS;
  }
  final = acc;
  finalWords = accWords;
}
/* Creatify enum: aspect_ratio 9x16|16x9|1x1; style из фикс-списка */"""
assert old_tail in js, 'Code Build payload: хвост не найден'
js = js.replace(old_tail, new_tail)
old_p = "const p = { script: cleaned, aspect_ratio: ar, style: st };\nif (v.webhook_url) { p.webhook_url = v.webhook_url; }\nreturn [{ json: { ok: true, payload: p, mode: (v.mode !== undefined && v.mode !== null) ? String(v.mode) : '' } }];"
assert old_p in js, 'Code Build payload: payload-блок не найден'
new_p = "const p = { script: final, aspect_ratio: ar, style: st };\nif (v.webhook_url) { p.webhook_url = v.webhook_url; }\nreturn [{ json: { ok: true, payload: p, words: finalWords, mode: (v.mode !== undefined && v.mode !== null) ? String(v.mode) : '' } }];"
js = js.replace(old_p, new_p)
cb['parameters']['jsCode'] = js
print('Code Build payload: OK')

out = json.dumps([data], ensure_ascii=False, indent=1) + '\n'
open(SHORTS, 'w', encoding='utf-8').write(out)
print('wf-creatify-shorts.json: OK')

# ---------- 3) wf-tg-bot.json ----------
raw = open(TGBOT, encoding='utf-8').read()
data = json.loads(raw)
data = data[0] if isinstance(data, list) else data
n = 0
for nd in data['nodes']:
    js = nd['parameters'].get('jsCode', '')
    if 'const words = Math.round(dur * 65 / 30);' in js:
        nd['parameters']['jsCode'] = js.replace('const words = Math.round(dur * 65 / 30);',
                                                'const words = Math.round(dur * 60 / 30);')
        n += 1
assert n == 3, f'wf-tg-bot: ожидалось 3 замены dur*65/30 (CT/AU/AU RG), найдено {n}'
out = json.dumps([data], ensure_ascii=False, indent=1) + '\n'
open(TGBOT, 'w', encoding='utf-8').write(out)
print('wf-tg-bot.json: OK (', n, 'замены )')

print('ALL DONE')
