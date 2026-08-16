import json

with open('workflows/wf-tg-bot.json', encoding='utf-8') as f:
    raw = json.load(f)

c = raw[0].get('connections', {})

# Find all nodes that connect TO TG sh ask dur
for src, conns in c.items():
    for branch, targets in conns.items():
        if branch != 'main': continue
        for idx, target_list in enumerate(targets):
            for t in target_list:
                if isinstance(t, dict) and t.get('node') == 'TG sh ask dur':
                    print(f"{src} [out:{idx}] -> TG sh ask dur")

# Also check TG DR ask
for src, conns in c.items():
    for branch, targets in conns.items():
        if branch != 'main': continue
        for idx, target_list in enumerate(targets):
            for t in target_list:
                if isinstance(t, dict) and t.get('node') == 'TG DR ask':
                    print(f"{src} [out:{idx}] -> TG DR ask")
