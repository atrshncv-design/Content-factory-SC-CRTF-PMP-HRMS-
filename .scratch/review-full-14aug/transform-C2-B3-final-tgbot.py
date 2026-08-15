#!/usr/bin/env python3
"""C2-B3 (14.08.2026): финальные правки wf-tg-bot (база = B2, 500 нод).

1. DU Gate: Math.round(5*dur/30) -> 5 * Math.ceil(dur/30) (паттерн SH Gate, округление ВВЕРХ).
2. Parser: '/instruction': 'instruction' в C-маппинг (Y10).
3. AS-кредитный гейт ДО AS HTTP creatify-link (Y2):
   AS Build link body -> AS LB creatify -> AS LB parse -> AS Gate -> Switch AS gate
     main[0] -> AS HTTP creatify-link (как раньше)
     main[1] -> AS Format low -> TG AS fail (reuse, multi-input)
   Решение: 'AS Check link' ловит low_credits-ошибку ПОСЛЕ вызова (защита от зависания),
   но НЕ защищает от списания — нужен гейт ДО (fail-closed как DU/SH Gate).
"""
import json
import uuid
import sys
import copy

BASE = "wf-tg-bot.json"

def esc_line():
    """esc-строка байт-точно из MO Format (эталон)."""
    wf = json.load(open(BASE))[0]
    for n in wf["nodes"]:
        if n["name"] == "MO Format":
            code = n["parameters"]["jsCode"]
            import re
            m = re.search(r"const esc = s =>[^\n]*", code)
            if m:
                return m.group(0)
    raise SystemExit("esc-эталон MO Format не найден")

def main():
    with open(BASE, encoding="utf-8") as f:
        raw = f.read()
    data = json.loads(raw)
    # контроль сериализации исходника
    assert json.dumps(data, ensure_ascii=False, indent=1) == raw, "reserialized != raw (база)"
    wf = data[0]
    nodes = wf["nodes"]
    conns = wf["connections"]
    by_name = {n["name"]: n for n in nodes}

    def get(name):
        return by_name[name]

    # ---------- 1. DU Gate: ceil ----------
    g = get("DU Gate")
    js = g["parameters"]["jsCode"]
    old = "const cost = Math.round(5 * dur / 30);"
    new = "const cost = 5 * Math.ceil(dur / 30);"
    assert old in js, "DU Gate: паттерн round не найден"
    assert new not in js, "DU Gate: уже ceil?"
    g["parameters"]["jsCode"] = js.replace(old, new)

    # ---------- 2. Parser: /instruction ----------
    p = get("Parser")
    pjs = p["parameters"]["jsCode"]
    old_map = "'инструкции': 'instruction', '/инструкция': 'instruction',"
    new_map = "'инструкции': 'instruction', '/instruction': 'instruction', '/инструкция': 'instruction',"
    assert old_map in pjs, "Parser: маппинг instruction не найден"
    assert "/instruction': 'instruction'" not in pjs, "Parser: /instruction уже есть?"
    p["parameters"]["jsCode"] = pjs.replace(old_map, new_map)

    # ---------- 3. AS credit gate ----------
    esc = esc_line()
    def new_node(name, ntype, typeVersion, params, pos):
        assert name not in by_name, f"дубль имени {name}"
        n = {
            "parameters": params,
            "id": str(uuid.uuid4()),
            "name": name,
            "type": ntype,
            "typeVersion": typeVersion,
            "position": pos,
        }
        nodes.append(n)
        by_name[name] = n
        return n

    # 3a. AS LB creatify — HTTP GET remaining_credits (копия DU LB creatify)
    du_lb = get("DU LB creatify")
    as_lb_params = copy.deepcopy(du_lb["parameters"])
    new_node("AS LB creatify", "n8n-nodes-base.httpRequest", 4.5, as_lb_params, [4760, 0])

    # 3b. AS LB parse — парсер body->raw->JSON.parse(data) + pass-through url
    as_lb_parse_js = (
        "\nconst __c = (() => { try { return $('AS LB creatify').first().json; } catch (e) { return {}; } })();\n"
        "const src = (() => { try { return $('AS Build link body').first().json; } catch (e) { return {}; } })();\n"
        "const cb = (__c.body && typeof __c.body === 'object') ? __c.body : __c;\n"
        "const cdata = (cb && typeof cb.data === 'string') ? cb.data : (typeof __c.data === 'string' ? __c.data : null);\n"
        "let cr = null;\n"
        "try {\n"
        "  if (cb.remaining_credits != null) cr = Number(cb.remaining_credits);\n"
        "  else if (__c.remaining_credits != null) cr = Number(__c.remaining_credits);\n"
        "  else if (cdata) cr = Number(JSON.parse(cdata).remaining_credits);\n"
        "} catch (e) {}\n"
        "return [{ json: Object.assign({}, src, { creatify: cr }) }];\n"
    )
    new_node("AS LB parse", "n8n-nodes-base.code", 2,
             {"mode": "runOnceForAllItems", "language": "javaScript", "jsCode": as_lb_parse_js}, [4820, 0])

    # 3c. AS Gate — fail-closed как DU Gate (cr == null || cr < 10 -> low)
    as_gate_js = (
        "\nconst lb = $('AS LB parse').first().json;\n"
        "const cr = lb.creatify != null ? Number(lb.creatify) : null;\n"
        "const url = String(lb.url || '');\n"
        "if (cr == null || cr < 10) return [{ json: { ok: false, reason: 'low', cr: cr, url: url } }];\n"
        "return [{ json: { ok: true, cr: cr, url: url } }];\n"
    )
    new_node("AS Gate", "n8n-nodes-base.code", 2,
             {"mode": "runOnceForAllItems", "language": "javaScript", "jsCode": as_gate_js}, [4880, 0])

    # 3d. Switch AS gate — boolean/equals (эталон Switch CL allow, A2 pitfall #4)
    sw_params = {
        "mode": "rules",
        "rules": {
            "values": [
                {
                    "conditions": {
                        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                        "conditions": [
                            {"leftValue": "={{ $json.ok }}", "rightValue": True,
                             "operator": {"type": "boolean", "operation": "equals"}}
                        ],
                        "combinator": "and",
                    }
                }
            ]
        },
        "options": {"fallbackOutput": "extra"},
    }
    new_node("Switch AS gate", "n8n-nodes-base.switch", 3.4, sw_params, [4940, 0])

    # 3e. AS Format low — esc, сообщение по ТЗ
    as_fmt_low_js = (
        "\nconst p = $('Parser').first().json;\n"
        "const g = $('AS Gate').first().json;\n"
        f"{esc}\n"
        "const cr = g.cr != null ? g.cr : '?';\n"
        "const text = '❌ Недостаточно кредитов creatify (' + esc(cr) + '). Минимум 10.';\n"
        "return [{ json: { chat_id: p.chat_id, text: text } }];\n"
    )
    new_node("AS Format low", "n8n-nodes-base.code", 2,
             {"mode": "runOnceForAllItems", "language": "javaScript", "jsCode": as_fmt_low_js}, [4940, 100])

    # ---------- перекоммутация ----------
    edge = lambda name: {"node": name, "type": "main", "index": 0}
    # AS Build link body: main[0] теперь -> AS LB creatify (было -> AS HTTP creatify-link)
    old_target = conns["AS Build link body"]["main"][0][0]
    assert old_target["node"] == "AS HTTP creatify-link", "неожиданный приёмник AS Build link body"
    conns["AS Build link body"] = {"main": [[edge("AS LB creatify")]]}
    conns["AS LB creatify"] = {"main": [[edge("AS LB parse")]]}
    conns["AS LB parse"] = {"main": [[edge("AS Gate")]]}
    conns["AS Gate"] = {"main": [[edge("Switch AS gate")]]}
    conns["Switch AS gate"] = {"main": [[edge("AS HTTP creatify-link")], [edge("AS Format low")]]}
    conns["AS Format low"] = {"main": [[edge("TG AS fail")]]}

    # ---------- сериализация ----------
    out = json.dumps(data, ensure_ascii=False, indent=1)
    with open(BASE, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"OK: {BASE} — нод: {len(nodes)} (было 500, +5)")

if __name__ == "__main__":
    main()
