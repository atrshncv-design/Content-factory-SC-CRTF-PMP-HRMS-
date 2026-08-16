import json

with open('workflows/wf-tg-bot.json', encoding='utf-8') as f:
    raw = json.load(f)

c = raw[0].get('connections', {})

# Check connections from Switch cmd for out[32] (dur)
# In n8n, Switch connections are by index
switch_cmd_conns = c.get('Switch cmd', {})
print("Switch cmd connections:")
for branch, targets in switch_cmd_conns.items():
    if branch != 'main': continue
    for idx, target_list in enumerate(targets):
        for t in target_list:
            if isinstance(t, dict):
                print(f"  out[{idx}] -> {t.get('node')}")
