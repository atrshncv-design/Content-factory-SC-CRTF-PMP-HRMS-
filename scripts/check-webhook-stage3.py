import json, re

with open('workflows/wf-creatify-webhook.json', encoding='utf-8') as f:
    raw = json.load(f)

nodes = raw[0]['nodes']

# Find Build stage3 node
for n in nodes:
    if n.get('type') == 'n8n-nodes-base.code' and 'stage3' in n.get('name', '').lower():
        name = n.get('name', '')
        code = n.get('parameters', {}).get('jsCode', '')
        print(f"=== {name} ===")
        print(code[:3000])
        print("...")
        # Check for esc() usage
        if 'esc(' in code:
            print("  ✓ esc() FOUND")
        else:
            print("  ✗ esc() NOT FOUND")
        # Check for static underscores in text
        static_text = re.findall(r"['\"]([^'\"]*_[^'\"]*)['\"]", code)
        if static_text:
            print(f"  ⚠ Static texts with underscore: {static_text[:10]}")
