#!/usr/bin/env python3
"""B2: валидация длительности 15-300с в DU Parse state (R2 fix).

База: .scratch/review-full-14aug/fixes/wf-tg-bot.json (результат B1, 500 нод).
Правки:
1. DU Parse state: durValid = dur >= 15 && dur <= 300;
   - dur_ok только если durValid (иначе режим остаётся dur_wrong -> существующая ветка
     Switch DU route out[dur_wrong] -> DU Format wrong -> TG du wrong);
   - quick = !!(url && durValid) - реген-путь (rg_ok) с невалидным qp.duration
     больше не попадает в платную цепочку (защита от обхода через quick_payload);
   - regen_gen + url + невалидный dur -> mode='dur_wrong' (явная ветка).
2. DU Format wrong: текст дополнен диапазоном 15-300 (ветка теперь обслуживает
   и "сценарий не начат", и "невалидная длительность").

Сериализация: json.dumps(ensure_ascii=False, indent=1), без trailing newline.
"""
import json
import sys

PATH = "/Users/aleksandrtrisenkov/Desktop/PROGRAMMING/РАБОЧИЕ ПРОЕКТЫ/КОНТЕНТ-ЗАВОД-API-MVP/.scratch/review-full-14aug/fixes/wf-tg-bot.json"

NEW_PARSE = """
const p = $('Parser').first().json;
const rows = $('DU HTTP state').first().json.rows || [];
const state = (rows[0] && rows[0].state) || 'IDLE';
let qp = {};
try { qp = JSON.parse((rows[0] && rows[0].quick_payload) || '{}'); } catch (e) { qp = {}; }
const url = String(qp.url || '');
const dur = Number(p.args.value) || Number(qp.duration) || 0;
const durValid = dur >= 15 && dur <= 300;
const quick = !!(url && durValid);
const topic = String(qp.topic || '');
let mode = 'dur_wrong';
if (state === 'QUICK_URL_AWAIT_DUR' && p.command === 'dur' && durValid) mode = 'dur_ok';
else if (p.callback_action === 'regen_gen' && topic) mode = 'rg_shorts';
else if (p.callback_action === 'regen_gen' && quick) mode = 'rg_ok';
else if (p.callback_action === 'regen_gen' && url) mode = 'dur_wrong';
else if (p.callback_action === 'regen_gen') mode = 'rg_cycle';
return [{ json: { mode: mode, state: state, url: url, dur: dur, quick: quick, topic: topic } }];
"""

NEW_FORMAT_WRONG = """
const p = $('Parser').first().json;
const esc = s => String(s ?? '').replace(/([_*[\\]`])/g, '\\\\$1');
const text = esc('⏱ Сначала начни сценарий: кнопка «URL → видео». Длительность ролика — 15–300 секунд.');
return [{ json: { chat_id: p.chat_id, text: text } }];
"""


def main():
    with open(PATH, encoding="utf-8") as f:
        data = json.load(f)
    wf = data[0] if isinstance(data, list) else data
    changed = []
    for n in wf["nodes"]:
        if n["name"] == "DU Parse state":
            old = n["parameters"]["jsCode"]
            assert "durValid" not in old, "уже пропатчено?"
            n["parameters"]["jsCode"] = NEW_PARSE
            changed.append(("DU Parse state", old, NEW_PARSE))
        elif n["name"] == "DU Format wrong":
            old = n["parameters"]["jsCode"]
            n["parameters"]["jsCode"] = NEW_FORMAT_WRONG
            changed.append(("DU Format wrong", old, NEW_FORMAT_WRONG))
    assert len(changed) == 2, f"найдено нод: {len(changed)}"
    # сериализация как в базе
    out = json.dumps(data, ensure_ascii=False, indent=1)
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(out)
    print("OK, записано:", PATH)
    for name, old, new in changed:
        print(f"- {name}: jsCode заменён ({len(old)} -> {len(new)} симв.)")


if __name__ == "__main__":
    main()
