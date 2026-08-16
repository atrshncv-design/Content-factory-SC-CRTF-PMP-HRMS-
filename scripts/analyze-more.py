import json, sys

path = sys.argv[1]
with open(path, encoding='utf-8') as f:
    raw = json.load(f)

nodes = raw[0]['nodes']

# Find Switch MU section
for n in nodes:
    if n.get('type') == 'n8n-nodes-base.switch' and n.get('name') == 'Switch MU section':
        values = n.get('parameters', {}).get('rules', {}).get('values', [])
        print(f"=== Switch MU section rules ({len(values)}) ===")
        for i, v in enumerate(values):
            conds = v.get('conditions', {}).get('conditions', [])
            if conds:
                rv = conds[0].get('rightValue', '')
                print(f"  out[{i}] = '{rv}'")

# Check all callback_actions that go to UNKNOWN in Switch cb
# We need to find the default/fallback output for Switch cb
for n in nodes:
    if n.get('type') == 'n8n-nodes-base.switch' and n.get('name') == 'Switch cb':
        values = n.get('parameters', {}).get('rules', {}).get('values', [])
        print(f"\nSwitch cb has {len(values)} rules; any callback_action not matching these goes to default output")

# Find TG nodes without any keyboard (potential dead-ends without menu button)
print("\n=== TG nodes WITHOUT inline keyboard ===")
for n in nodes:
    if n.get('type') == 'n8n-nodes-base.telegram':
        params = n.get('parameters', {})
        keyboard = params.get('inlineKeyboard', {})
        rows = keyboard.get('rows', [])
        if not rows:
            print(f"  {n.get('name')} — NO KEYBOARD")

# Find any TG sendVideo or sendPhoto nodes
print("\n=== TG nodes sending video/photo ===")
for n in nodes:
    if n.get('type') == 'n8n-nodes-base.telegram':
        op = n.get('parameters', {}).get('operation', '')
        if op in ('sendVideo', 'sendPhoto', 'sendAnimation'):
            print(f"  {n.get('name')} — operation={op}")
