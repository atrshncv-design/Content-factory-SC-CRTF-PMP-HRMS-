import json

with open('workflows/wf-tg-bot.json', encoding='utf-8') as f:
    raw = json.load(f)

c = raw[0].get('connections', {})
for name, conns in c.items():
    if 'TG sh video' in name or 'TG avv preview' in name or 'avv preview' in name:
        print(f"{name} -> {conns}")

# Also check all nodes that contain 'avv' or 'preview'
nodes = raw[0]['nodes']
for n in nodes:
    name = n.get('name', '')
    if 'avv' in name.lower() or 'preview' in name.lower():
        print(f"Node: {name} (type={n.get('type')})")
