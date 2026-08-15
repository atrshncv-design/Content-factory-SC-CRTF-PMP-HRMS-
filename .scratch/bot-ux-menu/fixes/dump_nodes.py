#!/usr/bin/env python3
"""Dump selected nodes from wf-tg-bot.json for T5a analysis."""
import json, sys

path = '.scratch/bot-ux-menu/fixes/wf-tg-bot.json'
d = json.load(open(path))
if isinstance(d, list): d = d[0]
wf = d.get('workflow', d)
nodes = wf['nodes']
conns = wf.get('connections', {})

by_name = {n['name']: n for n in nodes}

targets = sys.argv[1:] or ['SHT Build', 'SHT Switch', 'SHT HTTP', 'SHT Format', 'TG shorts',
                           'Gate Check', 'Switch gate', 'Switch cmd', 'RG answer', 'CN Build',
                           'MO Format', 'DU Check state', 'DU Parse state', 'DU Gate', 'DU Format gen',
                           'TG du gen', 'DU Update state', 'DU Build link body', 'DU HTTP link',
                           'DU Parse link', 'DU Build submit', 'DU HTTP submit', 'DU Parse submit',
                           'Switch DU submit', 'UV Parse url', 'ST LB creatify', 'ST LB parse',
                           'Parser', 'TG regen', 'TG gen rejected']

def dump(name):
    if name not in by_name:
        print(f'=== {name}: NOT FOUND ==='); return
    n = by_name[name]
    print(f'=== {name} (type={n["type"]}, v={n.get("typeVersion")}) ===')
    print(json.dumps(n.get('parameters', {}), ensure_ascii=False, indent=1)[:3500])
    c = conns.get(name)
    if c is not None:
        print('-- connections:')
        for i, outs in enumerate(c.get('main', [])):
            print(f'   out[{i}] ->', [o['node'] for o in outs])
    print()

for t in targets:
    dump(t)
