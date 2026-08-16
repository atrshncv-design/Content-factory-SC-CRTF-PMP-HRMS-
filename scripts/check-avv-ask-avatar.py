import json

with open('workflows/wf-tg-bot.json', encoding='utf-8') as f:
    raw = json.load(f)

nodes = raw[0]['nodes']

# Find TG avv ask avatar and dump its keyboard
for n in nodes:
    if n.get('name') == 'TG avv ask avatar':
        params = n.get('parameters', {})
        keyboard = params.get('inlineKeyboard', {})
        rows = keyboard.get('rows', [])
        print(f"TG avv ask avatar keyboard:")
        for r in rows:
            if not isinstance(r, dict): continue
            row = r.get('row', {})
            if not isinstance(row, dict): continue
            for btn in row.get('buttons', []):
                if not isinstance(btn, dict): continue
                text = btn.get('text', '')
                cb = btn.get('additionalFields', {}).get('callback_data', '')
                print(f"  text='{text}' callback='{cb}'")
