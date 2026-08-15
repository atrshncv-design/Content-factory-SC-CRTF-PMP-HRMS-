#!/usr/bin/env python3
"""T1 sim-прогоны: все новые/изменённые Code-ноды wf-tg-bot.json (T1-duration-select)."""
import json
import subprocess
import sys

WF = "/Users/aleksandrtrisenkov/Desktop/PROGRAMMING/РАБОЧИЕ ПРОЕКТЫ/КОНТЕНТ-ЗАВОД-API-MVP/.scratch/review-full-14aug/fixes/wf-tg-bot.json"
SIM = "/Users/aleksandrtrisenkov/.hermes/skills/software-development/content-factory-development/scripts/sim-code-node-both.py"

CASES = [
    # DR Check: mode manual/auto/нет строки
    ("DR Check", {"nodes": {"DR HTTP settings": {"rows": [{"key": "mode", "value": "manual"}]}}, "json": {}}, {"mode": "manual"}),
    ("DR Check", {"nodes": {"DR HTTP settings": {"rows": [{"key": "mode", "value": "auto"}]}}, "json": {}}, {"mode": "auto"}),
    ("DR Check", {"nodes": {"DR HTTP settings": {"rows": []}}, "json": {}}, {"mode": "manual"}),

    # DR Parse: кнопки 30/60/90, своё число 45, невалидные 5/400/abc, custom, вне состояния
    ("DR Parse", {"nodes": {"Parser": {"command": "durc", "args": {"value": "30"}, "raw": "cmd:durc_30"},
                            "DR HTTP state": {"rows": [{"state": "CYCLE_DUR_AWAIT", "quick_payload": None}]}}, "json": {}},
     {"mode": "dur_ok", "dur": 30}),
    ("DR Parse", {"nodes": {"Parser": {"command": "durc", "args": {"value": "60"}, "raw": "cmd:durc_60"},
                            "DR HTTP state": {"rows": [{"state": "CYCLE_DUR_AWAIT", "quick_payload": None}]}}, "json": {}},
     {"mode": "dur_ok", "dur": 60}),
    ("DR Parse", {"nodes": {"Parser": {"command": "durc", "args": {"value": "90"}, "raw": "cmd:durc_90"},
                            "DR HTTP state": {"rows": [{"state": "CYCLE_DUR_AWAIT", "quick_payload": None}]}}, "json": {}},
     {"mode": "dur_ok", "dur": 90}),
    ("DR Parse", {"nodes": {"Parser": {"command": "unknown", "args": {}, "raw": "45"},
                            "DR HTTP state": {"rows": [{"state": "CYCLE_DUR_AWAIT", "quick_payload": None}]}}, "json": {}},
     {"mode": "dur_ok", "dur": 45}),
    ("DR Parse", {"nodes": {"Parser": {"command": "unknown", "args": {}, "raw": "5"},
                            "DR HTTP state": {"rows": [{"state": "CYCLE_DUR_AWAIT", "quick_payload": None}]}}, "json": {}},
     {"mode": "dur_wrong", "dur": 5}),
    ("DR Parse", {"nodes": {"Parser": {"command": "unknown", "args": {}, "raw": "400"},
                            "DR HTTP state": {"rows": [{"state": "CYCLE_DUR_AWAIT", "quick_payload": None}]}}, "json": {}},
     {"mode": "dur_wrong", "dur": 400}),
    ("DR Parse", {"nodes": {"Parser": {"command": "unknown", "args": {}, "raw": "abc"},
                            "DR HTTP state": {"rows": [{"state": "CYCLE_DUR_AWAIT", "quick_payload": None}]}}, "json": {}},
     {"mode": "dur_wrong", "dur": 0}),
    ("DR Parse", {"nodes": {"Parser": {"command": "durc", "args": {"value": "custom"}, "raw": "cmd:durc_custom"},
                            "DR HTTP state": {"rows": [{"state": "CYCLE_DUR_AWAIT", "quick_payload": None}]}}, "json": {}},
     {"mode": "ask_custom", "dur": 0}),
    ("DR Parse", {"nodes": {"Parser": {"command": "durc", "args": {"value": None}, "raw": "cmd:durc"},
                            "DR HTTP state": {"rows": [{"state": "CYCLE_DUR_AWAIT", "quick_payload": None}]}}, "json": {}},
     {"mode": "ask_custom", "dur": 0}),
    ("DR Parse", {"nodes": {"Parser": {"command": "durc", "args": {"value": "30"}, "raw": "cmd:durc_30"},
                            "DR HTTP state": {"rows": [{"state": "CYCLE_ANALYTICS_PENDING", "quick_payload": None}]}}, "json": {}},
     {"mode": "not_await", "dur": 0}),
    ("DR Parse", {"nodes": {"Parser": {"command": "durc", "args": {"value": "30"}, "raw": "cmd:durc_30"},
                            "DR HTTP state": {"rows": []}}, "json": {}},
     {"mode": "not_await", "dur": 0}),

    # DR Build save: qp {duration:60}
    ("DR Build save", {"nodes": {"Parser": {"tg_user_id": 941296693},
                                 "DR Parse": {"mode": "dur_ok", "dur": 60}}, "json": {}},
     {"sql": "UPDATE sessions SET state = 'CYCLE_ANALYTICS_PENDING', quick_payload = ?, updated_at = datetime('now') WHERE tg_user_id = ?",
      "params": ['{"duration":60}', 941296693]}),

    # Format-ноды (esc есть, текст собран)
    ("DR Format ask", {"nodes": {"Parser": {"chat_id": 1}}, "json": {}}, {"chat_id": 1, "text": "⏱ Выбери длительность ролика (15–300 сек). Сценарий и видео будут под неё."}),
    ("DR Format wrong", {"nodes": {"Parser": {"chat_id": 1}}, "json": {}}, {"chat_id": 1, "text": "⏱ Длительность ролика — от 15 до 300 секунд. Напиши число (например, 45) или выбери кнопкой."}),
    ("DR Format custom", {"nodes": {"Parser": {"chat_id": 1}}, "json": {}}, {"chat_id": 1, "text": "🔢 Напиши число секунд (15–300). Например: 45"}),
    ("DR Format ok", {"nodes": {"Parser": {"chat_id": 1}, "DR Parse": {"dur": 90}}, "json": {}}, {"chat_id": 1, "text": "✅ Длительность: 90 сек. Запускаю цикл…"}),

    # CT Build bridge prompt: qp.duration=90 -> (90 сек, ~195 слов); нет qp -> (30 сек, ~65 слов)
    ("CT Build bridge prompt", {"nodes": {"CT HTTP topic": {"rows": [{"title": "T", "source_url": "U", "rationale": "R"}]},
                                          "CT HTTP qp": {"rows": [{"quick_payload": '{"duration": 90}'}]}}, "json": {}},
     {"skill": "scriptwriter", "prompt": "Напиши сценарий короткого вертикального видео (90 сек, ~195 слов, русский) для клиента Robotec (промышленная робототехника, интегратор KUKA; тон: экспертно-деловой, ROI, окупаемость).\nТема: T\nИсточник: U\nРационале: R\n\nВерни строго JSON: {\"hook\", \"body\", \"cta\", \"full_text\", \"target_length_sec\", \"estimated_words\", \"format_tag\", \"notes\"}. Без markdown."}),
    ("CT Build bridge prompt", {"nodes": {"CT HTTP topic": {"rows": [{"title": "T", "source_url": "U", "rationale": "R"}]},
                                          "CT HTTP qp": {"rows": [{"quick_payload": None}]}}, "json": {}},
     {"skill": "scriptwriter", "prompt": "Напиши сценарий короткого вертикального видео (30 сек, ~65 слов, русский) для клиента Robotec (промышленная робототехника, интегратор KUKA; тон: экспертно-деловой, ROI, окупаемость).\nТема: T\nИсточник: U\nРационале: R\n\nВерни строго JSON: {\"hook\", \"body\", \"cta\", \"full_text\", \"target_length_sec\", \"estimated_words\", \"format_tag\", \"notes\"}. Без markdown."}),

    # AS Build bridge prompt: qp.duration=60 -> (длина 60 сек); нет qp -> 30
    ("AS Build bridge prompt", {"nodes": {"Parser": {"tg_user_id": 1},
                                          "AS HTTP creatify-link": {"link_id": "abc"},
                                          "AS HTTP select script": {"rows": [{"full_text": "FT"}]},
                                          "AS HTTP qp": {"rows": [{"quick_payload": '{"duration": 60}'}]}}, "json": {}},
     {"skill": "json-builder", "prompt": "Собери валидный JSON для POST /api/link_to_videos (creatify) по сценарию.\nСценарий: FT (длина 60 сек)\nlink (UUID): abc\nwebhook_url: __WEBHOOK_URL__/webhook/factory/creatify/6d8f2a41c9e7b3d5f0a1c4e8\nvoice: русский экспертный; avatar: не задан; язык: ru; aspect_ratio: 9x16; target_platform: Instagram; model_version: aurora_v1_fast.\nВерни ТОЛЬКО JSON payload (name, link, visual_style, script_style, aspect_ratio, video_length, language, target_audience, target_platform, model_version, override_script, webhook_url). Без markdown."}),
    ("AS Build bridge prompt", {"nodes": {"Parser": {"tg_user_id": 1},
                                          "AS HTTP creatify-link": {"link_id": "abc"},
                                          "AS HTTP select script": {"rows": [{"full_text": "FT"}]},
                                          "AS HTTP qp": {"rows": []}}, "json": {}},
     {"skill": "json-builder", "prompt": "Собери валидный JSON для POST /api/link_to_videos (creatify) по сценарию.\nСценарий: FT (длина 30 сек)\nlink (UUID): abc\nwebhook_url: __WEBHOOK_URL__/webhook/factory/creatify/6d8f2a41c9e7b3d5f0a1c4e8\nvoice: русский экспертный; avatar: не задан; язык: ru; aspect_ratio: 9x16; target_platform: Instagram; model_version: aurora_v1_fast.\nВерни ТОЛЬКО JSON payload (name, link, visual_style, script_style, aspect_ratio, video_length, language, target_audience, target_platform, model_version, override_script, webhook_url). Без markdown."}),

    # AS Build submit body: LLM вернул video_length=999 -> принудительно 60
    ("AS Build submit body", {"nodes": {"Parser": {"entity_id": "5"},
                                        "AS Parse payload": {"payload": {"name": "N", "video_length": 999}},
                                        "AS HTTP creatify-link": {"link_id": "x"},
                                        "AS HTTP qp": {"rows": [{"quick_payload": '{"duration": 60}'}]}}, "json": {}},
     {"script_id": 5, "client_id": 1, "json_payload": {"name": "N", "video_length": 60}, "link_id": "x"}),

    # Gate Check: CYCLE_DUR_AWAIT + unknown -> cycle_dur; регрессия остальных состояний
    ("Gate Check", {"nodes": {"Parser": {"command": "unknown"}, "Gate HTTP": {"rows": [{"state": "CYCLE_DUR_AWAIT"}]}}, "json": {}},
     {"mode": "cycle_dur"}),
    ("Gate Check", {"nodes": {"Parser": {"command": "unknown"}, "Gate HTTP": {"rows": [{"state": "QUICK_URL_AWAIT_DUR"}]}}, "json": {}},
     {"mode": "quick_url_dur"}),
    ("Gate Check", {"nodes": {"Parser": {"command": "unknown"}, "Gate HTTP": {"rows": [{"state": "IDLE"}]}}, "json": {}},
     {"mode": "normal"}),

    # Parser (через inline-харнесс: sim-code-node-both.py не стабит $input — питфолл C2)
]

fails = 0
for name, inputs, expect in CASES:
    if name == "Parser":
        continue  # Parser гоняется отдельно inline-харнессом ниже
    r = subprocess.run(["python3", SIM, WF, name, json.dumps(inputs, ensure_ascii=False)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL {name}: rc={r.returncode} {r.stderr.strip()[:300]}")
        fails += 1
        continue
    try:
        got = json.loads(r.stdout.strip())[0]["json"]
    except Exception as e:
        print(f"FAIL {name}: parse {e}: {r.stdout[:200]}")
        fails += 1
        continue
    ok = True
    for k, v in expect.items():
        if got.get(k) != v:
            ok = False
            print(f"FAIL {name}: {k} expected={v!r} got={got.get(k)!r}")
    if ok:
        print(f"ok   {name}: {json.dumps(got, ensure_ascii=False)[:140]}")
    else:
        fails += 1

# --- Parser: inline-харнесс с $input (питфолл C2) ---
data = json.load(open(WF, encoding="utf-8"))
wf = data[0] if isinstance(data, list) else data
by_name = {n["name"]: n for n in wf["nodes"]}


def inline_sim(node_name, item_json):
    js = by_name[node_name]["parameters"]["jsCode"]
    stub = ("const __ITEM = " + json.dumps(item_json, ensure_ascii=False) + ";\n"
            "const $input = { first: () => ({ json: __ITEM }) };\n"
            "const __M = {};\n"
            "const $ = (n) => ({ first: () => ({ json: __M[n] || {} }) });\n"
            "const $json = {};\n")
    code = stub + "const __R = (() => {\n" + js + "\n})();\nconsole.log(JSON.stringify(__R));"
    tmp = "/tmp/_sim_parser_t1.js"
    open(tmp, "w", encoding="utf-8").write(code)
    r = subprocess.run(["node", tmp], capture_output=True, text=True)
    if r.returncode != 0:
        return None, r.stderr[:300]
    return json.loads(r.stdout.strip())[0]["json"], None


def cq(data_str):
    return {"callback_query": {"from": {"id": 941296693}, "message": {"chat": {"id": 1}, "message_id": 7}, "data": data_str, "id": "q1"}}


def msg(text):
    return {"message": {"from": {"id": 941296693}, "chat": {"id": 1}, "message_id": 7, "text": text}}


PARSER_CASES = [
    (cq("cmd:durc_30"), "durc", "30"),
    (cq("cmd:durc_60"), "durc", "60"),
    (cq("cmd:durc_90"), "durc", "90"),
    (cq("cmd:durc_custom"), "durc", "custom"),
    (cq("cmd:durc"), "durc", None),
    (cq("cmd:dur_30"), "dur", "30"),
    (msg("dur_45"), "dur", "45"),
    (msg("45"), "unknown", None),
    (msg("45 сек"), "unknown", None),
    (cq("cmd:start_cycle"), "start_cycle", None),
    (cq("cmd:menu"), "menu", None),
    (cq("cmd:cancel"), "cancel", None),
    (msg("старт цикла"), "start_cycle", None),
]
for item, exp_cmd, exp_val in PARSER_CASES:
    label = item.get("callback_query", {}).get("data") or item.get("message", {}).get("text", "")
    got, err = inline_sim("Parser", item)
    if err:
        print(f"FAIL Parser {label!r}: {err}")
        fails += 1
        continue
    ok = got.get("command") == exp_cmd and got.get("args", {}).get("value") == exp_val
    print(("ok   " if ok else "FAIL ") + f"Parser {label!r}: command={got.get('command')} value={got.get('args', {}).get('value')}")
    if not ok:
        fails += 1

print(f"\nИтого: {len(CASES) - 4 + len(PARSER_CASES) - fails}/{len(CASES) - 4 + len(PARSER_CASES)} ok, fails={fails}")
sys.exit(1 if fails else 0)
