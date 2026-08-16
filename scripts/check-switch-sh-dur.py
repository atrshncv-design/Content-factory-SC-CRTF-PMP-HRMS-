import json

with open('workflows/wf-tg-bot.json', encoding='utf-8') as f:
    raw = json.load(f)

c = raw[0].get('connections', {})

# Check ALL connections FROM Switch SH dur
print("=== Connections FROM Switch SH dur ===")
conns = c.get('Switch SH dur', {})
for branch, targets in conns.items():
    if branch != 'main': continue
    for idx, target_list in enumerate(targets):
        for t in target_list:
            if isinstance(t, dict):
                print(f"  out[{idx}] -> {t.get('node')}")
