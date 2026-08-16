#!/usr/bin/env python3
import json, re
from pathlib import Path

ROOT = Path('/Users/aleksandrtrisenkov/Desktop/PROGRAMMING/РАБОЧИЕ ПРОЕКТЫ/КОНТЕНТ-ЗАВОД-API-MVP')
WF_DIR = ROOT / 'workflows'

def load(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    return data[0] if isinstance(data, list) else data

def save(path, wf):
    path.write_text(json.dumps([wf], ensure_ascii=False, indent=1), encoding='utf-8')

def normalize_input_pattern(js):
    # wf-creators-search / wf-analytics style (already handled in round1)
    if 'let input = $input.all()[0] ? $input.all()[0].json : {};' in js:
        return js
    # wf-creator-content style: const resp = $input.first().json;
    if 'const resp = $input.first().json;' in js and 'let resp' not in js:
        js = js.replace(
            'const resp = $input.first().json;',
            "let resp = $input.first().json;\nif (typeof resp === 'string') { try { resp = JSON.parse(resp); } catch (e) {} }\nif (resp && typeof resp === 'object' && typeof resp.data === 'string') { try { const parsed = JSON.parse(resp.data); if (parsed && typeof parsed === 'object') resp = parsed; } catch (e) {} }"
        )
    # wf-audience style: const raw = $json;
    if re.search(r"^\s*const raw = \$json;", js, re.MULTILINE) and 'let raw' not in js:
        js = re.sub(
            r"^\s*const raw = \$json;",
            "let raw = $json;\nif (typeof raw === 'string') { try { raw = JSON.parse(raw); } catch (e) {} }\nif (raw && typeof raw === 'object' && typeof raw.data === 'string') { try { const parsed = JSON.parse(raw.data); if (parsed && typeof parsed === 'object') raw = parsed; } catch (e) {} }",
            js,
            count=1,
            flags=re.MULTILINE
        )
    # wf-transcripts-comments style: const body = ($json.body && typeof $json.body === 'object') ? $json.body : $json;
    if 'const body = ($json.body && typeof $json.body === \'object\') ? $json.body : $json;' in js and 'let body' not in js:
        js = js.replace(
            'const body = ($json.body && typeof $json.body === \'object\') ? $json.body : $json;',
            "let body = ($json.body && typeof $json.body === 'object') ? $json.body : $json;\nif (typeof body === 'string') { try { body = JSON.parse(body); } catch (e) {} }\nif (body && typeof body === 'object' && typeof body.data === 'string') { try { const parsed = JSON.parse(body.data); if (parsed && typeof parsed === 'object') body = parsed; } catch (e) {} }"
        )
    return js

def normalize_profile_input(js):
    # wf-creator-profile: build(p, h, raw) { const profile = ...
    if 'function build(p, h, raw) {' in js and 'data' not in js[:200]:
        js = js.replace(
            'function build(p, h, raw) {',
            "function build(p, h, raw) {\n  if (typeof raw === 'string') { try { raw = JSON.parse(raw); } catch (e) { raw = {}; } }\n  if (raw && typeof raw === 'object' && typeof raw.data === 'string') { try { const parsed = JSON.parse(raw.data); if (parsed && typeof parsed === 'object') raw = parsed; } catch (e) {} }"
        )
    return js

for name in ['wf-creator-profile.json', 'wf-creator-content.json', 'wf-transcripts-comments.json', 'wf-audience.json']:
    path = WF_DIR / name
    wf = load(path)
    for n in wf['nodes']:
        if n.get('type') == 'n8n-nodes-base.code' and 'Normalize' in n.get('name', ''):
            js = n['parameters'].get('jsCode', '')
            new_js = normalize_input_pattern(js)
            new_js = normalize_profile_input(new_js)
            if new_js != js:
                n['parameters']['jsCode'] = new_js
                print(f"patched {name} {n['name']}")
    save(path, wf)
