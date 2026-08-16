import json

with open('workflows/wf-tg-bot.json', encoding='utf-8') as f:
    raw = json.load(f)

nodes = raw[0]['nodes']
connections = raw[0].get('connections', {})

# Find TG avv preview nodes and check what comes after them
targets = ['TG avv preview1', 'TG avv preview2', 'TG sh video']
for target in targets:
    # Find the node id
    node_id = None
    for n in nodes:
        if n.get('name') == target:
            node_id = n.get('id')
            break
    if not node_id:
        print(f"{target}: NODE NOT FOUND")
        continue
    # Check connections FROM this node
    out_conns = []
    for src_id, conns in connections.items():
        if src_id == node_id:
            for branch, targets_list in conns.items():
                for t in targets_list:
                    out_conns.append(t.get('node', '?'))
    # Find node names for connected ids
    conn_names = []
    for cid in out_conns:
        for n in nodes:
            if n.get('id') == cid:
                conn_names.append(n.get('name'))
    print(f"{target} (id={node_id}) → {conn_names}")
