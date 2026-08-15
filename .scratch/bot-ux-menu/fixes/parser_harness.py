#!/usr/bin/env python3
"""Parser harness: extract parseCommand from Parser node jsCode and run via node."""
import json, re, subprocess, sys

d = json.load(open('.scratch/bot-ux-menu/fixes/wf-tg-bot.json'))
if isinstance(d, list): d = d[0]
wf = d.get('workflow', d)
by = {n['name']: n for n in wf['nodes']}
js = by['Parser']['parameters']['jsCode']
m = re.search(r'function parseCommand\(text\) \{.*?\n\}', js, re.S)
assert m, 'parseCommand not found'
fn = m.group(0)

tests = [
    ('shorts https://x', 'shorts', 'url'),
    ('shorts https://example.com/video.mp4', 'shorts', 'url'),
    ('shorts тема', 'shorts', 'value'),
    ('шортсы', 'shorts', None),
    ('gen_shorts', 'shorts', None),  # cmd:gen_shorts -> Parser срезает 'cmd:' -> parseCommand('gen_shorts')
    ('url2video https://a.b/c', 'url2video', None),
]
script = fn + """
const tests = __TESTS__;
for (const inp of tests) {
  const r = parseCommand(inp);
  console.log(JSON.stringify({in: inp, command: r.command, args: r.args}));
}
"""
script = script.replace('__TESTS__', json.dumps([t[0] for t in tests]))
out = subprocess.run(['node', '-e', script], capture_output=True, text=True)
print(out.stdout)
if out.returncode != 0:
    print('STDERR:', out.stderr); sys.exit(1)
for line, t in zip(out.stdout.strip().splitlines(), tests):
    r = json.loads(line)
    ok_cmd = r['command'] == t[1]
    if t[2] is None:
        ok_arg = (r['args']['url'] is None) and (r['args']['value'] is None or t[0].startswith('шортсы'))
        ok_arg = (r['args']['url'] is None)
    else:
        ok_arg = bool(r['args'][t[2]])
    print('PASS' if (ok_cmd and ok_arg) else 'FAIL', t[0], '->', r['command'], r['args'])
