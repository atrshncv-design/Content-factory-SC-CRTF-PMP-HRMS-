import json

with open('workflows/wf-tg-bot.json', encoding='utf-8') as f:
    raw = json.load(f)

nodes = raw[0]['nodes']
c = raw[0].get('connections', {})

# Find Switch cb and check what its default/fallback output connects to
sw_name = 'Switch cb'
sw_id = None
for n in nodes:
    if n.get('name') == sw_name:
        sw_id = n.get('id')
        break

if sw_id:
    # In n8n, the default output for Switch is the last output index
    # Let's check connections from Switch cb
    conns = c.get(sw_name, {})
    print(f"Switch cb connections: {conns}")
    
    # Find the node connected to the fallback output (largest index)
    max_idx = -1
    fallback_node = None
    for branch, targets in conns.items():
        if branch == 'main':
            for idx, target_list in enumerate(targets):
                if idx > max_idx and target_list:
                    max_idx = idx
                    fallback_node = target_list[0].get('node')
    print(f"Fallback output (index {max_idx}) -> {fallback_node}")
    
    # Find what node CB answer unknown is
    for n in nodes:
        if n.get('name') == 'CB answer unknown':
            print(f"CB answer unknown node found: {n.get('id')}")

# Check TG avv preview photo and TG avv preview text connections
for target in ['TG avv preview photo', 'TG avv preview text']:
    conns = c.get(target, {})
    print(f"\n{target} connections: {conns}")
