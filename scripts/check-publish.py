import json

# Check wf-publish for text-only support (A1 issue)
with open('workflows/wf-publish.json', encoding='utf-8') as f:
    raw = json.load(f)

nodes = raw[0]['nodes']

# Find Switch upload needed
for n in nodes:
    if n.get('type') == 'n8n-nodes-base.switch' and 'upload' in n.get('name', '').lower():
        print(f"=== {n.get('name')} ===")
        values = n.get('parameters', {}).get('rules', {}).get('values', [])
        for i, v in enumerate(values):
            conds = v.get('conditions', {}).get('conditions', [])
            if conds:
                lv = conds[0].get('leftValue', '')
                rv = conds[0].get('rightValue', '')
                op = conds[0].get('operator', {}).get('operation', '')
                print(f"  out[{i}] condition: {lv} {op} {rv}")

# Check connections for text-only path
c = raw[0].get('connections', {})
for name, conns in c.items():
    if 'upload' in name.lower():
        print(f"\n{name} -> {conns}")
