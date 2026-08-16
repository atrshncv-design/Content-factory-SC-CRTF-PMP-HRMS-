#!/usr/bin/env python3
"""Тикет 02: ремонт envelope (list) + фиксы value-level для обоих воркфлоу."""
import json

def load_envelope(p):
    d = json.load(open(p, encoding='utf-8'))
    if isinstance(d, list):
        return d
    return [d]

def save_envelope(p, data):
    open(p, 'w', encoding='utf-8').write(json.dumps(data, ensure_ascii=False, indent=1))

# ---------- wf-creatify-submit.json ----------
p = 'workflows/wf-creatify-submit.json'
wf = load_envelope(p)[0]
for n in wf['nodes']:
    if n['name'] == 'HTTP POST real':
        n['parameters']['jsonBody'] = (
            "{{ JSON.stringify(Object.assign({}, $('Code validate').first().json.body.json_payload, "
            "{webhook_url: ($env.WEBHOOK_URL || '').replace(/\\/$/, '') "
            "+ '/webhook/factory/creatify/6d8f2a41c9e7b3d5f0a1c4e8'})) }}"
        )
save_envelope(p, [wf])
wf = load_envelope(p)[0]
for n in wf['nodes']:
    if n['name'] == 'HTTP POST real':
        v = n['parameters']['jsonBody']
        assert "replace(/\\/$/, '')" in v, v
        print('OK submit jsonBody:', repr(v))
    if n['name'] == 'Code validate':
        js = n['parameters']['jsCode']
        assert 'errors' in js and 'missing link' in js
        print('OK submit Code validate: %d символов' % len(js))

# ---------- wf-creatify-link.json ----------
p2 = 'workflows/wf-creatify-link.json'
wf2 = load_envelope(p2)[0]
for n in wf2['nodes']:
    if n['name'] == 'Code assemble':
        n['parameters']['jsCode'] = (
            "const link_id = $json.id || ($json.link && $json.link.id) "
            "|| ($json.data && $json.data.id) || $json.link_id || '';\n"
            "return [{ json: { link_id: link_id, raw: $json } }];"
        )
save_envelope(p2, [wf2])
wf2 = load_envelope(p2)[0]
for n in wf2['nodes']:
    if n['name'] == 'Code assemble':
        print('OK link Code assemble:', repr(n['parameters']['jsCode']))
print('DONE')
