import json, sys

path = sys.argv[1]
with open(path, encoding='utf-8') as f:
    raw = json.load(f)

nodes = raw[0]['nodes'] if isinstance(raw, list) and len(raw)>0 and 'nodes' in raw[0] else raw

# Find telegram nodes with inlineKeyboard
callbacks = []
for n in nodes:
    if n.get('type') == 'n8n-nodes-base.telegram':
        params = n.get('parameters', {})
        keyboard = params.get('inlineKeyboard', {})
        rows = keyboard.get('rows', [])
        op = params.get('operation', 'sendMessage')
        has_menu = False
        for r in rows:
            if not isinstance(r, dict): continue
            row = r.get('row', {})
            if not isinstance(row, dict): continue
            for btn in row.get('buttons', []):
                if not isinstance(btn, dict): continue
                cb = btn.get('additionalFields', {}).get('callback_data', '')
                if 'cmd:menu' in cb:
                    has_menu = True
        if rows and not has_menu:
            print(f"  {n.get('name')} — HAS KEYBOARD BUT NO MENU BUTTON (op={op})")
        if not rows and op in ('sendMessage', 'sendVideo', 'sendPhoto'):
            print(f"  {n.get('name')} — NO KEYBOARD (op={op})")

print(f"\nTotal nodes: {len(nodes)}")
