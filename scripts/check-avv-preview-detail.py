import json

with open('workflows/wf-tg-bot.json', encoding='utf-8') as f:
    raw = json.load(f)

nodes = raw[0]['nodes']
c = raw[0].get('connections', {})

# Check AVV Preview sel
for n in nodes:
    if n.get('name') == 'AVV Preview sel':
        print(f"=== {n.get('name')} ===")
        print(n.get('parameters', {}).get('jsCode', '')[:2000])

# Check connections from AVV Preview sel
print(f"\nAVV Preview sel -> {c.get('AVV Preview sel', {})}")

# Check what TG avv preview photo/text parameters contain
for target in ['TG avv preview photo', 'TG avv preview text']:
    for n in nodes:
        if n.get('name') == target:
            params = n.get('parameters', {})
            print(f"\n=== {target} ===")
            print(f"  operation={params.get('operation')}")
            print(f"  text={params.get('text', '')[:200]}")
            print(f"  additionalOptions={params.get('additionalOptions', {})}")
