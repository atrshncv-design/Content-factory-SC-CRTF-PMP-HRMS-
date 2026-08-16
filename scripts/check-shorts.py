import json

with open('workflows/wf-creatify-shorts.json', encoding='utf-8') as f:
    raw = json.load(f)

nodes = raw[0]['nodes']

# Check for expansion nodes (Exp Build prompt, Exp HTTP bridge, Exp parse)
for n in nodes:
    name = n.get('name', '')
    if 'expand' in name.lower() or 'Exp ' in name or 'scriptwriter' in name.lower():
        print(f"Node: {name} (type={n.get('type')})")

# Check if there is a Code node that checks for topic vs script
for n in nodes:
    if n.get('type') == 'n8n-nodes-base.code':
        code = n.get('parameters', {}).get('jsCode', '')
        if 'topic' in code.lower() and 'script' in code.lower() and ('expand' in code.lower() or 'need' in code.lower()):
            print(f"\n=== {n.get('name')} ===")
            print(code[:2000])
