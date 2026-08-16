import json, sys
path = sys.argv[1]
with open(path, encoding='utf-8') as f:
    d = json.load(f)
print(type(d))
if isinstance(d, dict):
    print("Keys:", list(d.keys())[:20])
    if 'nodes' in d:
        print(f"Nodes: {len(d['nodes'])}")
        for n in d['nodes'][:3]:
            print(f"  Node type={n.get('type')} name={n.get('name')}")
