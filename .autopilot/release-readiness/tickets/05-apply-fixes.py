#!/usr/bin/env python3
import json, re
from pathlib import Path

ROOT = Path('/Users/aleksandrtrisenkov/Desktop/PROGRAMMING/РАБОЧИЕ ПРОЕКТЫ/КОНТЕНТ-ЗАВОД-API-MVP')
WF_DIR = ROOT / 'workflows'

SC_RE = re.compile(r'scrapecreators\.com')

def load(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    return data[0] if isinstance(data, list) else data

def save(path, wf):
    # n8n uses a list envelope
    data = [wf]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')

def is_sc_http(n):
    return n.get('type') == 'n8n-nodes-base.httpRequest' and SC_RE.search(str(n.get('parameters', {}).get('url', '')))

def fix_sc_http(n, timeout=45000):
    p = n['parameters']
    p['authentication'] = 'none'
    p['sendHeaders'] = True
    p['specifyHeaders'] = 'keypair'
    p['headerParameters'] = {"parameters": [{"name": "x-api-key", "value": "={{ $env.SCRAPECREATORS_API_KEY }}"}]}
    opts = p.setdefault('options', {})
    opts['timeout'] = timeout
    resp = opts.setdefault('response', {})
    resp['response'] = {'neverError': True}
    # remove credentials block
    n.pop('credentials', None)
    return n

def fix_low_credits_response_body(n):
    rb = n.get('parameters', {}).get('responseBody', '')
    if isinstance(rb, str) and '={ {' in rb:
        n['parameters']['responseBody'] = rb.replace('={ {', '={{ {').replace('} }', '} }}')
    return n

def add_data_parsing(js):
    # If js already parses $json.data, leave it
    if 'JSON.parse' in js and ('raw.data' in js or '$json.data' in js):
        return js
    # Insert defensive parser near top of function after const input = ...
    # Replace: const input = $input.all()[0] ? $input.all()[0].json : {};
    # With parsing wrapper
    if 'const input = $input.all()[0] ? $input.all()[0].json : {};' in js:
        js = js.replace(
            'const input = $input.all()[0] ? $input.all()[0].json : {};',
            "let input = $input.all()[0] ? $input.all()[0].json : {};\nif (typeof input === 'string') { try { input = JSON.parse(input); } catch (e) {} }\nif (input && typeof input === 'object' && typeof input.data === 'string') { try { const parsed = JSON.parse(input.data); if (parsed && typeof parsed === 'object') input = parsed; } catch (e) {} }\nif (!input) input = {};"
        )
    return js

def apply_to_file(name, extra=None):
    path = WF_DIR / name
    wf = load(path)
    nodes = wf['nodes']
    by_name = {n['name']: n for n in nodes}

    # 1. Fix SC HTTP nodes
    for n in nodes:
        if is_sc_http(n):
            timeout = 15000 if 'credit-balance' in str(n['parameters'].get('url', '')) else 45000
            fix_sc_http(n, timeout)

    # 2. Fix broken responseBody low_credits
    for n in nodes:
        if n.get('type') == 'n8n-nodes-base.respondToWebhook':
            rb = n.get('parameters', {}).get('responseBody', '')
            if isinstance(rb, str) and '={ {' in rb:
                # pattern: "={ {ok: false, error: 'low_credits', balance: ...} }"
                # We need expression object: "={{ {ok: false, ...} }}"
                fixed = re.sub(r'^=\{\s*\{', '={{ {', rb)
                fixed = re.sub(r'\s*\}\s*\}$', '} }}', fixed)
                n['parameters']['responseBody'] = fixed

    # 3. Normalize data-string parsing for Normalize code nodes
    for n in nodes:
        if n.get('type') == 'n8n-nodes-base.code' and 'Normalize' in n.get('name', ''):
            js = n['parameters'].get('jsCode', '')
            n['parameters']['jsCode'] = add_data_parsing(js)

    # 4. Specific bug: wf-creators-search Normalize YouTube uses c.handle instead of p.handle
    if name == 'wf-creators-search.json':
        n = by_name.get('Normalize YouTube')
        if n:
            n['parameters']['jsCode'] = n['parameters']['jsCode'].replace('c.handle', 'p.handle').replace('c.subscriberCountInt', 'p.subscriberCountInt').replace('c.channelName', 'p.channelName').replace('c.description', 'p.description').replace('c.thumbnail', 'p.thumbnail').replace('c.id', 'p.id')

    if extra:
        extra(wf, by_name)

    save(path, wf)
    print(f"applied fixes to {name}")

if __name__ == '__main__':
    for name in [
        'wf-audience.json',
        'wf-creators-search.json',
        'wf-creator-profile.json',
        'wf-creator-content.json',
        'wf-transcripts-comments.json',
    ]:
        apply_to_file(name)
    print("Base fixes done.")
