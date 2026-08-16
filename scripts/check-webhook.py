import json

with open('workflows/wf-creatify-webhook.json', encoding='utf-8') as f:
    raw = json.load(f)

nodes = raw[0]['nodes']

for n in nodes:
    if n.get('type') == 'n8n-nodes-base.telegram':
        params = n.get('parameters', {})
        keyboard = params.get('inlineKeyboard', {})
        rows = keyboard.get('rows', [])
        op = params.get('operation', 'sendMessage')
        name = n.get('name', '')
        cbs = []
        for r in rows:
            if not isinstance(r, dict): continue
            row = r.get('row', {})
            if not isinstance(row, dict): continue
            for btn in row.get('buttons', []):
                if not isinstance(btn, dict): continue
                cb = btn.get('additionalFields', {}).get('callback_data', '')
                cbs.append(cb)
        if rows:
            print(f"  {name} — op={op} — callbacks: {cbs}")
        else:
            print(f"  {name} — op={op} — NO KEYBOARD")
