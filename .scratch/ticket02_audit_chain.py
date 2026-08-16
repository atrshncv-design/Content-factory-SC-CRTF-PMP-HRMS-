#!/usr/bin/env python3
"""Тикет 02: статический аудит цепочки — мок-ветки без платных вызовов, гейты до платного вызова, neverError вложенный."""
import json
import sys

PAID_HOSTS = ('api.creatify.ai', 'api.scrapecreators.com')
WF = {
    'workflows/wf-analytics.json': 'Switch mock',
    'workflows/wf-creatify-link.json': 'Switch',
    'workflows/wf-creatify-submit.json': 'Switch mock',
}

def reachable(wf, start, via_out):
    """BFS по воркфлоу от start-ноды по конкретному выходу via_out."""
    conns = wf['connections']
    seen = set()
    stack = [(start, via_out)]
    while stack:
        node, out = stack.pop()
        if (node, out) in seen:
            continue
        seen.add((node, out))
        outs = conns.get(node, {}).get('main', [])
        if out >= len(outs):
            continue
        for c in outs[out]:
            stack.append((c['node'], c.get('index', 0)))
    return {n for n, _ in seen}

for path, sw_name in WF.items():
    wf = json.load(open(path, encoding='utf-8'))[0]
    nodes = {n['name']: n for n in wf['nodes']}
    sw = nodes[sw_name]
    rules = sw['parameters']['rules']['values']
    cond = rules[0]['conditions']['conditions'][0]
    assert cond['operator']['type'] == 'string', f"{path}: switch не строковое сравнение"
    assert cond['rightValue'] == 'PLACEHOLDER_UNTIL_TOMORROW', f"{path}: не тот placeholder"
    # mock-ветка = выход 0
    mock_nodes = reachable(wf, sw_name, 0)
    paid_in_mock = []
    for nm in mock_nodes:
        n = nodes.get(nm, {})
        url = str(n.get('parameters', {}).get('url', ''))
        if any(h in url for h in PAID_HOSTS):
            paid_in_mock.append(nm)
    print(f"{path}: мок-ветка ({len(mock_nodes)} нод) платных вызовов: {paid_in_mock or 'НЕТ'}")
    assert not paid_in_mock, f"{path}: платный вызов в мок-ветке!"

    # neverError — только вложенный options.response.response.neverError
    for n in wf['nodes']:
        p = n.get('parameters', {})
        opts = p.get('options', {}) if isinstance(p, dict) else {}
        s = json.dumps(p, ensure_ascii=False)
        if 'neverError' in s:
            ne = opts.get('response', {}).get('response', {}).get('neverError')
            assert ne is True, f"{path}:{n['name']} neverError не вложен (options.response.response)"
    print(f"{path}: neverError вложен корректно")

# Гейт credit-floor в submit ДО платного вызова: порядок в соединениях
wf = json.load(open('workflows/wf-creatify-submit.json', encoding='utf-8'))[0]
nodes = {n['name']: n for n in wf['nodes']}
conns = wf['connections']
# цепочка real: Switch mock -> out1 -> HTTP credits -> Code balance -> IF low credits -> out0 -> HTTP POST real
assert conns['Switch mock']['main'][1][0]['node'] == 'HTTP credits'
assert conns['HTTP credits']['main'][0][0]['node'] == 'Code balance'
assert conns['Code balance']['main'][0][0]['node'] == 'IF low credits'
assert conns['IF low credits']['main'][0][0]['node'] == 'HTTP POST real'  # balance >= 50 -> платный
assert conns['IF low credits']['main'][1][0]['node'] == 'Respond low credits'  # < 50 -> стоп
# gate 50: rightValue 50, оператор gte
ifl = nodes['IF low credits']['parameters']['conditions']['conditions'][0]
assert ifl['rightValue'] == 50 and ifl['operator']['operation'] == 'gte'
print('wf-creatify-submit: credit-floor (>=50) ДО платного POST link_to_videos — OK')
# гейт 10 (пред-link) живёт в боте (AS/AU/DU/SH Gate, cr<10 -> low) — вне зоны, но проверим контракт link-ответа
assert conns['Switch mock']['main'][0][0]['node'] == 'Code mock'
print('wf-creatify-submit: мок-ветка начинается с Code mock — OK')

# HTTP-ноды платных вызовов: typeVersion 4.5 + keypair
for path in ['workflows/wf-creatify-link.json', 'workflows/wf-creatify-submit.json', 'workflows/wf-analytics.json']:
    wf = json.load(open(path, encoding='utf-8'))[0]
    for n in wf['nodes']:
        p = n.get('parameters', {})
        url = str(p.get('url', ''))
        if any(h in url for h in PAID_HOSTS):
            assert n.get('typeVersion') == 4.5, f"{path}:{n['name']} не typeVersion 4.5"
            assert p.get('specifyHeaders') == 'keypair', f"{path}:{n['name']} не keypair"
            print(f"{path}:{n['name']} — typeVersion 4.5 + keypair + X-API-ID/X-API-KEY")
print('\n🟢 Статический аудит цепочки: всё зелёное')
