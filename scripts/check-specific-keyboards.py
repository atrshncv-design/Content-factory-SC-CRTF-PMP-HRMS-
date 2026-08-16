import json

with open('workflows/wf-tg-bot.json', encoding='utf-8') as f:
    raw = json.load(f)

nodes = raw[0]['nodes']

targets = ['TG pfn', 'TG pfn multi', 'TG SH verify', 'TG AU verify', 'TG pd ok', 'TG ph ok', 'TG avv ask avatar']
for target in targets:
    for n in nodes:
        if n.get('name') == target:
            params = n.get('parameters', {})
            keyboard = params.get('inlineKeyboard', {})
            rows = keyboard.get('rows', [])
            print(f"\n=== {target} ===")
            if not rows:
                print("  NO KEYBOARD")
            for r in rows:
                if not isinstance(r, dict): continue
                row = r.get('row', {})
                if not isinstance(row, dict): continue
                for btn in row.get('buttons', []):
                    if not isinstance(btn, dict): continue
                    text = btn.get('text', '')
                    cb = btn.get('additionalFields', {}).get('callback_data', '')
                    print(f"  text='{text}' callback='{cb}'")
