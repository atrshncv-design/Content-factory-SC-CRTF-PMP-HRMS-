import json

with open('workflows/wf-tg-bot.json', encoding='utf-8') as f:
    raw = json.load(f)

nodes = raw[0]['nodes']

# Check SH Dur check
for n in nodes:
    if n.get('name') == 'SH Dur check':
        print(f"=== {n.get('name')} ({n.get('type')}) ===")
        if n.get('type') == 'n8n-nodes-base.code':
            print(n.get('parameters', {}).get('jsCode', '')[:2000])
        elif n.get('type') == 'n8n-nodes-base.switch':
            values = n.get('parameters', {}).get('rules', {}).get('values', [])
            for i, v in enumerate(values):
                conds = v.get('conditions', {}).get('conditions', [])
                if conds:
                    print(f"  out[{i}] condition: {conds[0].get('leftValue')} {conds[0].get('operator',{}).get('operation')} {conds[0].get('rightValue')}")

# Check DR Build state
for n in nodes:
    if n.get('name') == 'DR Build state':
        print(f"\n=== {n.get('name')} ===")
        print(n.get('parameters', {}).get('jsCode', '')[:2000])
