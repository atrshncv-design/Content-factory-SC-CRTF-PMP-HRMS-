import json

with open('workflows/wf-tg-bot.json', encoding='utf-8') as f:
    raw = json.load(f)

nodes = raw[0]['nodes']
c = raw[0].get('connections', {})

# Find all telegram nodes that send to user and have NO outgoing connections
tg_dead_ends = []
for n in nodes:
    if n.get('type') == 'n8n-nodes-base.telegram':
        name = n.get('name', '')
        op = n.get('parameters', {}).get('operation', 'sendMessage')
        # skip answerCallbackQuery
        if op == 'answerCallbackQuery':
            continue
        conns = c.get(name, {})
        main_conns = conns.get('main', [])
        has_outgoing = False
        for branch in main_conns:
            if branch:
                has_outgoing = True
                break
        if not has_outgoing:
            tg_dead_ends.append((name, op))

print(f"=== Telegram dead-ends ({len(tg_dead_ends)}) ===")
for name, op in tg_dead_ends:
    print(f"  {name} (op={op}) — NO OUTGOING CONNECTIONS")
