import json

with open('workflows/wf-tg-bot.json', encoding='utf-8') as f:
    raw = json.load(f)

c = raw[0].get('connections', {})

# Check connections from SH HTTP dur state
print("=== Connections FROM SH HTTP dur state ===")
conns = c.get('SH HTTP dur state', {})
for branch, targets in conns.items():
    if branch != 'main': continue
    for idx, target_list in enumerate(targets):
        for t in target_list:
            if isinstance(t, dict):
                print(f"  out[{idx}] -> {t.get('node')}")

# Find the node between SH HTTP dur state and Switch SH dur
for src, conns in c.items():
    for branch, targets in conns.items():
        if branch != 'main': continue
        for idx, target_list in enumerate(targets):
            for t in target_list:
                if isinstance(t, dict) and t.get('node') == 'Switch SH dur':
                    print(f"\n{src} [out:{idx}] -> Switch SH dur")
