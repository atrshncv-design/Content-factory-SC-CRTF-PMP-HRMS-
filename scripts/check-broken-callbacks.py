import json, re

with open('workflows/wf-tg-bot.json', encoding='utf-8') as f:
    raw = json.load(f)

nodes = raw[0]['nodes']

# Find ALL broken callbacks (escaped quotes) across ALL nodes
broken = []
for n in nodes:
    if n.get('type') == 'n8n-nodes-base.telegram':
        params = n.get('parameters', {})
        keyboard = params.get('inlineKeyboard', {})
        rows = keyboard.get('rows', [])
        for r in rows:
            if not isinstance(r, dict): continue
            row = r.get('row', {})
            if not isinstance(row, dict): continue
            for btn in row.get('buttons', []):
                if not isinstance(btn, dict): continue
                cb = btn.get('additionalFields', {}).get('callback_data', '')
                # Check for trailing escaped quote or uneven quotes
                if '\\"' in cb:
                    broken.append((n.get('name', ''), btn.get('text', ''), cb))

print(f"=== BROKEN CALLBACKS ({len(broken)}) ===")
for name, text, cb in broken:
    print(f"  [{name}] text='{text}' callback='{cb}'")

# Find any callback_data that uses single quotes instead of double quotes inside ={{ }}
# ={{ 'cmd:menu' }} is OK, but ={{ 'cmd:menu" }} is NOT
print("\n=== CALLBACKS WITH ODD QUOTES ===")
for n in nodes:
    if n.get('type') == 'n8n-nodes-base.telegram':
        params = n.get('parameters', {})
        keyboard = params.get('inlineKeyboard', {})
        rows = keyboard.get('rows', [])
        for r in rows:
            if not isinstance(r, dict): continue
            row = r.get('row', {})
            if not isinstance(row, dict): continue
            for btn in row.get('buttons', []):
                if not isinstance(btn, dict): continue
                cb = btn.get('additionalFields', {}).get('callback_data', '')
                if cb.startswith("={{ '") and cb.endswith('" }}'):
                    print(f"  MISMATCHED QUOTES: [{n.get('name')}] text='{btn.get('text')}' callback='{cb}'")
                if cb.startswith('={{ "') and cb.endswith("' }}"):
                    print(f"  MISMATCHED QUOTES: [{n.get('name')}] text='{btn.get('text')}' callback='{cb}'")
