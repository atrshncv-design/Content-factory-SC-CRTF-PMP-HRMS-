import json
with open('workflows/wf-tg-bot.json', encoding='utf-8') as f:
    d = json.load(f)
nodes = d[0]['nodes']
# Find first telegram node with inlineKeyboard
for n in nodes:
    if n.get('type') == 'n8n-nodes-base.telegram':
        params = n.get('parameters', {})
        keyboard = params.get('inlineKeyboard', [])
        if keyboard:
            print(f"Node: {n.get('name')}")
            print(f"Keyboard type: {type(keyboard)}")
            print(json.dumps(keyboard, indent=2, ensure_ascii=False)[:2000])
            break
