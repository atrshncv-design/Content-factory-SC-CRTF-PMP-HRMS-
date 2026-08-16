import json, sys, re

path = sys.argv[1]
with open(path, encoding='utf-8') as f:
    raw = json.load(f)

nodes = raw[0]['nodes']
print(f"Nodes: {len(nodes)}")

# Extract callback_data
callbacks = []
for n in nodes:
    if n.get('type') == 'n8n-nodes-base.telegram':
        params = n.get('parameters', {})
        keyboard = params.get('inlineKeyboard', {})
        rows = keyboard.get('rows', [])
        for r in rows:
            if not isinstance(r, dict):
                continue
            row = r.get('row', {})
            if not isinstance(row, dict):
                continue
            for btn in row.get('buttons', []):
                if not isinstance(btn, dict):
                    continue
                cb = btn.get('additionalFields', {}).get('callback_data', '')
                text = btn.get('text', '')
                if cb:
                    callbacks.append((n.get('name', ''), text, cb))

print(f"\n=== Inline keyboard callback_data ({len(callbacks)} buttons) ===")
for name, text, cb in callbacks:
    print(f"  [{name}] text='{text}' callback='{cb}'")

# Find all Switch nodes
switches = []
for n in nodes:
    if n.get('type') == 'n8n-nodes-base.switch':
        switches.append(n)

print(f"\n=== Switch nodes ({len(switches)}) ===")
for sw in switches:
    name = sw.get('name', '')
    rules = sw.get('parameters', {}).get('rules', {}).get('rules', [])
    print(f"\nSwitch: {name} (rules={len(rules)})")
    for r in rules:
        val = r.get('value', '')
        out = r.get('output', '?')
        print(f"  out[{out}] = '{val}'")

# Find Parser Code node
for n in nodes:
    if n.get('type') == 'n8n-nodes-base.code':
        name = n.get('name', '')
        code = n.get('parameters', {}).get('jsCode', '')
        if 'parseCommand' in code or "'menu'" in code:
            print(f"\n--- {name} ---")
            m = re.search(r"const\s+C\s*=\s*\{([^}]+)\}", code, re.DOTALL)
            if m:
                print(f"  C-map found (len={len(m.group(0))})")
                print(m.group(0)[:2000])
            m2 = re.search(r"function\s+parseCommand[^(]*\([^)]*\)[^\{]*\{.*?\n\}", code, re.DOTALL)
            if m2:
                print(f"\n  parseCommand found (len={len(m2.group(0))})")
                print(m2.group(0)[:2000])

# All node names
names = [n.get('name', '') for n in nodes]
print(f"\n=== All node names ({len(names)}) ===")
for n in sorted(set(names)):
    if n:
        print(f"  {n}")
