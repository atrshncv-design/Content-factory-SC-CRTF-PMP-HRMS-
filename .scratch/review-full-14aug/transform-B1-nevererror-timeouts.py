#!/usr/bin/env python3
"""B1: neverError + timeouts + минимальные error-ветки (wf-tg-bot, база = A2).

Читает fixes/wf-tg-bot.json (486 нод, 0 issues), мутирует, пишет обратно
(indent=1, ensure_ascii=False, без trailing newline — байт-точно как base).

Правки:
  1. neverError (вложенный options.response.response.neverError=true) —
     OB HTTP wf-onboard, CP HTTP wf-publish, AS HTTP creatify-link,
     AS HTTP creatify-submit (SC HTTP wf-analytics уже имеет — не трогаем).
  2. Таймауты: AS creatify-link 30000->300000, AS creatify-submit 60000->300000,
     SHT HTTP 300000->450000; CP wf-publish остаётся 300000.
  3. Error-ветки после neverError (эталон: CRS Format / Switch OB parse / AU alert):
     - OB:  OB Check onboard -> Switch OB http -> [OB Build bridge prompt | TG ob fail]
     - CP:  CP Check pub -> Switch CP pub -> [CP Build final | CP Build pub err ->
            CP HTTP pub err -> CP Format pub err -> TG CP refuse]
     - AS link:   AS Check link -> Switch AS link -> [AS Build select script | AS Build err -> ...]
     - AS submit: AS Check submit -> Switch AS submit -> [TG generating | AS Build err -> ...]
     Общий AS-ошибка-чейн: AS Build err -> AS HTTP err -> AS Format err -> TG AS fail.
"""
import json
import re
import sys
import uuid

PATH = "/Users/aleksandrtrisenkov/Desktop/PROGRAMMING/РАБОЧИЕ ПРОЕКТЫ/КОНТЕНТ-ЗАВОД-API-MVP/.scratch/review-full-14aug/fixes/wf-tg-bot.json"


def esc_line_from(node):
    m = re.search(r"const esc = s =>[^\n]*", node["parameters"]["jsCode"])
    assert m, f"esc line not found in {node['name']}"
    return m.group(0)


def main():
    with open(PATH, encoding="utf-8") as f:
        data = json.load(f)
    wf = data[0]
    nodes = wf["nodes"]
    conns = wf["connections"]
    by_name = {n["name"]: n for n in nodes}
    existing = set(by_name.keys())

    esc_line = esc_line_from(by_name["CRS Format"])
    switch_params = json.loads(json.dumps(by_name["Switch OB parse"]["parameters"]))
    tg_refuse_params = json.loads(json.dumps(by_name["TG CP refuse"]["parameters"]))
    cp_final_sql = by_name["CP Build final"]["parameters"]["jsCode"]
    au_alert_sql = by_name["AU Build alert"]["parameters"]["jsCode"]
    cp_http_final = json.loads(json.dumps(by_name["CP HTTP final"]))
    as_http_session = json.loads(json.dumps(by_name["AS HTTP session"]))

    def new_code(name, js):
        assert name not in existing, f"DUPLICATE node name: {name}"
        existing.add(name)
        return {
            "parameters": {"mode": "runOnceForAllItems", "language": "javaScript", "jsCode": js},
            "id": str(uuid.uuid4()),
            "name": name,
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [0, 0],
        }

    def new_switch(name, params):
        assert name not in existing, f"DUPLICATE node name: {name}"
        existing.add(name)
        return {
            "parameters": params,
            "id": str(uuid.uuid4()),
            "name": name,
            "type": "n8n-nodes-base.switch",
            "typeVersion": 3.4,
            "position": [0, 0],
        }

    def new_http(name, template_node):
        assert name not in existing, f"DUPLICATE node name: {name}"
        existing.add(name)
        n = json.loads(json.dumps(template_node))
        n["name"] = name
        n["id"] = str(uuid.uuid4())
        n["position"] = [0, 0]
        return n

    def add_connection(src, dst):
        conns.setdefault(src, {}).setdefault("main", []).append([{"node": dst}])

    def replace_first_edge(src, dst):
        """Заменить ЕДИНСТВЕННОЕ исходящее main-ребро src -> dst (источник был на main[0])."""
        assert src in conns, f"{src} has no connections"
        main = conns[src]["main"]
        assert len(main) == 1 and len(main[0]) == 1, f"{src} main shape unexpected: {main}"
        main[0] = [{"node": dst}]

    # ---------- 1+2. neverError + timeouts ----------
    def add_never_error(name):
        opts = by_name[name]["parameters"].setdefault("options", {})
        opts["response"] = {"response": {"neverError": True}}

    def set_timeout(name, ms):
        by_name[name]["parameters"].setdefault("options", {})["timeout"] = ms

    add_never_error("OB HTTP wf-onboard")
    add_never_error("CP HTTP wf-publish")
    add_never_error("AS HTTP creatify-link")
    add_never_error("AS HTTP creatify-submit")
    set_timeout("AS HTTP creatify-link", 300000)
    set_timeout("AS HTTP creatify-submit", 300000)
    set_timeout("SHT HTTP", 450000)
    # SC HTTP wf-analytics: neverError уже есть (проверка)
    assert by_name["SC HTTP wf-analytics"]["parameters"]["options"]["response"]["response"]["neverError"] is True

    # ---------- 3. Error-ветки ----------

    # --- OB: OB Check onboard -> Switch OB http -> [OB Build bridge prompt | TG ob fail]
    ob_check_js = (
        "\n"
        "const p = $('Parser').first().json;\n"
        + esc_line
        + "\n"
        "let r = {};\n"
        "try { r = $('OB HTTP wf-onboard').first().json; } catch (e) { r = { error: e }; }\n"
        "const body = (r && r.body && typeof r.body === 'object') ? r.body : (r || {});\n"
        "if (r.error || body.ok === false) {\n"
        "  const e = (body && body.error) || (r && r.error);\n"
        "  const msg = (typeof e === 'string' && e) ? e : (e && e.message) || 'сервис онбординга не ответил';\n"
        "  return [{ json: { ok: false, text: '⚠️ Онбординг не удался: ' + esc(msg) } }];\n"
        "}\n"
        "return [{ json: { ok: true } }];\n"
    )
    ob_check = new_code("OB Check onboard", ob_check_js)
    ob_switch = new_switch("Switch OB http", switch_params)
    ob_check["position"] = [1900, 60]
    ob_switch["position"] = [1900, 120]
    nodes.append(ob_check)
    nodes.append(ob_switch)
    replace_first_edge("OB HTTP wf-onboard", "OB Check onboard")
    add_connection("OB Check onboard", "Switch OB http")
    conns["Switch OB http"] = {"main": [[{"node": "OB Build bridge prompt"}], [{"node": "TG ob fail"}]]}

    # --- CP: CP Check pub -> Switch CP pub -> [CP Build final | CP Build pub err -> CP HTTP pub err -> CP Format pub err -> TG CP refuse]
    cp_check_js = (
        "\n"
        "const p = $('Parser').first().json;\n"
        + esc_line
        + "\n"
        "let r = {};\n"
        "try { r = $('CP HTTP wf-publish').first().json; } catch (e) { r = { error: e }; }\n"
        "const body = (r && r.body && typeof r.body === 'object') ? r.body : (r || {});\n"
        "if (r.error || body.ok === false || body.post_id == null) {\n"
        "  const e = (body && body.error) || (r && r.error);\n"
        "  const msg = (typeof e === 'string' && e) ? e : (e && e.message) || 'сервис публикации не ответил';\n"
        "  return [{ json: { ok: false, text: '❌ Публикация не удалась: ' + esc(msg) } }];\n"
        "}\n"
        "return [{ json: { ok: true } }];\n"
    )
    cp_check = new_code("CP Check pub", cp_check_js)
    cp_switch = new_switch("Switch CP pub", switch_params)
    # SQL байт-точно из CP Build final
    m_sql = re.search(r'sql: "(UPDATE[^"]+)"', cp_final_sql)
    assert m_sql, "CP final SQL not found"
    cp_build_err = new_code(
        "CP Build pub err",
        "\nconst t = $json.text || '❌ Публикация не удалась';\n"
        f'return [{{ json: {{ sql: "{m_sql.group(1)}", params: [941296693], text: t }} }}];\n',
    )
    cp_http_err = new_http("CP HTTP pub err", cp_http_final)
    cp_format_err = new_code(
        "CP Format pub err",
        "\n"
        "const p = $('Parser').first().json;\n"
        + esc_line
        + "\n"
        "const t = $('CP Build pub err').first().json.text || '❌ Публикация не удалась';\n"
        "return [{ json: { chat_id: p.chat_id, text: esc(t) } }];\n",
    )
    cp_check["position"] = [6960, 60]
    cp_switch["position"] = [6960, 120]
    cp_build_err["position"] = [6960, 220]
    cp_http_err["position"] = [6960, 280]
    cp_format_err["position"] = [6960, 340]
    nodes.extend([cp_check, cp_switch, cp_build_err, cp_http_err, cp_format_err])
    replace_first_edge("CP HTTP wf-publish", "CP Check pub")
    add_connection("CP Check pub", "Switch CP pub")
    conns["Switch CP pub"] = {"main": [[{"node": "CP Build final"}], [{"node": "CP Build pub err"}]]}
    add_connection("CP Build pub err", "CP HTTP pub err")
    add_connection("CP HTTP pub err", "CP Format pub err")
    add_connection("CP Format pub err", "TG CP refuse")

    # --- AS общий error-чейн: AS Build err -> AS HTTP err -> AS Format err -> TG AS fail
    m_sql_au = re.search(r'sql: "(UPDATE[^"]+)"', au_alert_sql)
    assert m_sql_au, "AU alert SQL not found"
    as_build_err = new_code(
        "AS Build err",
        "\n"
        "const t = $json.text || '❌ Ошибка генерации. Состояние сброшено в IDLE.';\n"
        f'return [{{ json: {{ sql: "{m_sql_au.group(1)}", params: [941296693], text: t }} }}];\n',
    )
    as_http_err = new_http("AS HTTP err", as_http_session)
    as_format_err = new_code(
        "AS Format err",
        "\n"
        "const p = $('Parser').first().json;\n"
        + esc_line
        + "\n"
        "const t = $('AS Build err').first().json.text || '❌ Ошибка генерации';\n"
        "return [{ json: { chat_id: p.chat_id, text: esc(t) } }];\n",
    )
    as_build_err["position"] = [4640, 520]
    as_http_err["position"] = [4640, 580]
    as_format_err["position"] = [4640, 640]
    nodes.extend([as_build_err, as_http_err, as_format_err])
    add_connection("AS Build err", "AS HTTP err")
    add_connection("AS HTTP err", "AS Format err")
    add_connection("AS Format err", "TG AS fail")

    # --- AS link: AS Check link -> Switch AS link -> [AS Build select script | AS Build err]
    as_link_check_js = (
        "\n"
        "const p = $('Parser').first().json;\n"
        + esc_line
        + "\n"
        "let r = {};\n"
        "try { r = $('AS HTTP creatify-link').first().json; } catch (e) { r = { error: e }; }\n"
        "const body = (r && r.body && typeof r.body === 'object') ? r.body : (r || {});\n"
        "const linkId = (body && (body.link_id || (body.raw && body.raw.link_id))) || '';\n"
        "if (r.error || body.ok === false || !linkId) {\n"
        "  const e = (body && body.error) || (r && r.error);\n"
        "  const msg = (typeof e === 'string' && e) ? e : (e && e.message) || 'creatify не вернул link_id';\n"
        "  return [{ json: { ok: false, text: '❌ Не удалось создать ссылку creatify: ' + esc(msg) } }];\n"
        "}\n"
        "return [{ json: { ok: true } }];\n"
    )
    as_link_check = new_code("AS Check link", as_link_check_js)
    as_link_switch = new_switch("Switch AS link", switch_params)
    as_link_check["position"] = [4680, 60]
    as_link_switch["position"] = [4680, 120]
    nodes.extend([as_link_check, as_link_switch])
    replace_first_edge("AS HTTP creatify-link", "AS Check link")
    add_connection("AS Check link", "Switch AS link")
    conns["Switch AS link"] = {"main": [[{"node": "AS Build select script"}], [{"node": "AS Build err"}]]}

    # --- AS submit: AS Check submit -> Switch AS submit -> [TG generating | AS Build err]
    as_submit_check_js = (
        "\n"
        "const p = $('Parser').first().json;\n"
        + esc_line
        + "\n"
        "let r = {};\n"
        "try { r = $('AS HTTP creatify-submit').first().json; } catch (e) { r = { error: e }; }\n"
        "const body = (r && r.body && typeof r.body === 'object') ? r.body : (r || {});\n"
        "if (r.error || body.ok === false || (body.creatify_id === undefined && body.id === undefined)) {\n"
        "  const e = (body && body.error) || (r && r.error);\n"
        "  const msg = (typeof e === 'string' && e) ? e : (e && e.message) || 'creatify не принял задачу';\n"
        "  const low = (msg === 'low_credits') ? 'Недостаточно кредитов creatify' : msg;\n"
        "  return [{ json: { ok: false, text: '❌ Запуск генерации не удался: ' + esc(low) } }];\n"
        "}\n"
        "return [{ json: { ok: true } }];\n"
    )
    as_submit_check = new_code("AS Check submit", as_submit_check_js)
    as_submit_switch = new_switch("Switch AS submit", switch_params)
    as_submit_check["position"] = [5040, 60]
    as_submit_switch["position"] = [5040, 120]
    nodes.extend([as_submit_check, as_submit_switch])
    replace_first_edge("AS HTTP creatify-submit", "AS Check submit")
    add_connection("AS Check submit", "Switch AS submit")
    conns["Switch AS submit"] = {"main": [[{"node": "TG generating"}], [{"node": "AS Build err"}]]}

    # ---------- Serialize ----------
    out = json.dumps(data, ensure_ascii=False, indent=1)
    assert not out.endswith("\n"), "trailing newline!"
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"OK: {len(nodes)} nodes written to {PATH}")


if __name__ == "__main__":
    main()
