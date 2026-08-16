import json

with open('workflows/wf-tg-bot.json', encoding='utf-8') as f:
    raw = json.load(f)

nodes = raw[0]['nodes']

for n in nodes:
    if n.get('name') == 'SH Dur dispatch':
        print(f"=== {n.get('name')} ===")
        print(n.get('parameters', {}).get('jsCode', '')[:2000])
