import json

with open('workflows/wf-tg-bot.json', encoding='utf-8') as f:
    raw = json.load(f)

nodes = raw[0]['nodes']

for n in nodes:
    if n.get('type') == 'n8n-nodes-base.switch' and n.get('name') == 'Switch avv preview':
        values = n.get('parameters', {}).get('rules', {}).get('values', [])
        print(f"=== Switch avv preview rules ({len(values)}) ===")
        for i, v in enumerate(values):
            conds = v.get('conditions', {}).get('conditions', [])
            if conds:
                lv = conds[0].get('leftValue', '')
                rv = conds[0].get('rightValue', '')
                op = conds[0].get('operator', {}).get('operation', '')
                print(f"  out[{i}] condition: {lv} {op} {rv}")

# Also check AVV Build preview code
for n in nodes:
    if n.get('type') == 'n8n-nodes-base.code' and n.get('name') == 'AVV Build preview':
        print(f"\n=== {n.get('name')} ===")
        print(n.get('parameters', {}).get('jsCode', '')[:2000])
