#!/usr/bin/env python3
"""Combined sim harness: stubs both $('Node') and $json for a Code node."""
import json, subprocess, sys, tempfile, os

wf_path, node_name, inputs_json = sys.argv[1], sys.argv[2], sys.argv[3]
inputs = json.loads(inputs_json)
data = json.load(open(wf_path))
wf = data[0] if isinstance(data, list) else data
node = next(n for n in wf['nodes'] if n['name'] == node_name)
js = node['parameters']['jsCode']

stub = (
    "const __M = " + json.dumps(inputs.get('nodes', {}), ensure_ascii=False) + ";\n"
    "const $ = (n) => ({ first: () => ({ json: __M[n] || {} }) });\n"
    "const $json = " + json.dumps(inputs.get('json', {}), ensure_ascii=False) + ";\n"
)
code = stub + "const __R = (() => {\n" + js + "\n})();\nconsole.log(JSON.stringify(__R));"
tmp = "/tmp/_sim_combined.js"
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(code)
r = subprocess.run(['node', tmp], capture_output=True, text=True)
if r.returncode != 0:
    print(f"NODE ERROR: {r.stderr[:600]}")
    sys.exit(1)
print(r.stdout.strip())
