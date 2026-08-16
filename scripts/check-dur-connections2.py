import json

with open('workflows/wf-tg-bot.json', encoding='utf-8') as f:
    raw = json.load(f)

c = raw[0].get('connections', {})

# Check connections from SH Dur check
print("=== Connections FROM SH Dur check ===")
conns = c.get('SH Dur check', {})
for branch, targets in conns.items():
    if branch != 'main': continue
    for idx, target_list in enumerate(targets):
        for t in target_list:
            if isinstance(t, dict):
                print(f"  out[{idx}] -> {t.get('node')}")

# Check connections from DR Build state
print("\n=== Connections FROM DR Build state ===")
conns = c.get('DR Build state', {})
for branch, targets in conns.items():
    if branch != 'main': continue
    for idx, target_list in enumerate(targets):
        for t in target_list:
            if isinstance(t, dict):
                print(f"  out[{idx}] -> {t.get('node')}")
