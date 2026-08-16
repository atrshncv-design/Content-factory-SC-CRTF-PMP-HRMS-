import json, sys, re

path = sys.argv[1]
with open(path, encoding='utf-8') as f:
    raw = json.load(f)

nodes = raw[0]['nodes']

# Extract Switch cmd rules
for n in nodes:
    if n.get('type') == 'n8n-nodes-base.switch' and n.get('name') == 'Switch cmd':
        values = n.get('parameters', {}).get('rules', {}).get('values', [])
        print(f"=== Switch cmd rules ({len(values)}) ===")
        for i, v in enumerate(values):
            conds = v.get('conditions', {}).get('conditions', [])
            if conds:
                rv = conds[0].get('rightValue', '')
                print(f"  out[{i}] = '{rv}'")

# Extract Switch cb rules
for n in nodes:
    if n.get('type') == 'n8n-nodes-base.switch' and n.get('name') == 'Switch cb':
        values = n.get('parameters', {}).get('rules', {}).get('values', [])
        print(f"\n=== Switch cb rules ({len(values)}) ===")
        for i, v in enumerate(values):
            conds = v.get('conditions', {}).get('conditions', [])
            if conds:
                rv = conds[0].get('rightValue', '')
                print(f"  out[{i}] = '{rv}'")

# Extract Parser full code
for n in nodes:
    if n.get('type') == 'n8n-nodes-base.code' and n.get('name') == 'Parser':
        code = n.get('parameters', {}).get('jsCode', '')
        print(f"\n=== Parser (len={len(code)}) ===")
        print(code)
