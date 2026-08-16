#!/usr/bin/env python3
import json
from pathlib import Path
import uuid

ROOT = Path('/Users/aleksandrtrisenkov/Desktop/PROGRAMMING/РАБОЧИЕ ПРОЕКТЫ/КОНТЕНТ-ЗАВОД-API-MVP')
path = ROOT / 'workflows' / 'wf-analytics.json'
data = json.loads(path.read_text(encoding='utf-8'))
wf = data[0]

nodes = {n['name']: n for n in wf['nodes']}
conns = wf['connections']

def uid(prefix=''):
    return (prefix + str(uuid.uuid4()))[:36]

# Remove old per-platform mock switches and their connections
old_switches = ['Switch IG', 'Switch TikTok', 'Switch YouTube']
for sw in old_switches:
    if sw in conns:
        del conns[sw]

# Remove old switch nodes
wf['nodes'] = [n for n in wf['nodes'] if n['name'] not in old_switches]
nodes = {n['name']: n for n in wf['nodes']}

# Fix SC HTTP nodes to keypair + neverError
for n in wf['nodes']:
    if n['type'] == 'n8n-nodes-base.httpRequest' and 'scrapecreators.com' in str(n.get('parameters', {}).get('url', '')):
        p = n['parameters']
        is_balance = 'credit-balance' in p.get('url', '')
        p['authentication'] = 'none'
        p['sendHeaders'] = True
        p['specifyHeaders'] = 'keypair'
        p['headerParameters'] = {"parameters": [{"name": "x-api-key", "value": "={{ $env.SCRAPECREATORS_API_KEY }}"}]}
        opts = p.setdefault('options', {})
        opts['timeout'] = 15000 if is_balance else 45000
        opts.setdefault('response', {})['response'] = {'neverError': True}
        n.pop('credentials', None)

# Add new nodes
switch_mock = {
    "parameters": {
        "mode": "rules",
        "rules": {
            "values": [{
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                    "conditions": [{
                        "leftValue": "={{ $env.SCRAPECREATORS_API_KEY }}",
                        "rightValue": "PLACEHOLDER_UNTIL_TOMORROW",
                        "operator": {"type": "string", "operation": "equals"}
                    }],
                    "combinator": "and"
                }
            }]
        },
        "options": {"fallbackOutput": "extra"}
    },
    "id": uid('switch-mock-'),
    "name": "Switch mock",
    "type": "n8n-nodes-base.switch",
    "typeVersion": 3.4,
    "position": [-560, 0]
}

http_balance = {
    "parameters": {
        "method": "GET",
        "url": "https://api.scrapecreators.com/v1/account/credit-balance",
        "authentication": "none",
        "sendHeaders": True,
        "specifyHeaders": "keypair",
        "headerParameters": {"parameters": [{"name": "x-api-key", "value": "={{ $env.SCRAPECREATORS_API_KEY }}"}]},
        "options": {"timeout": 15000, "response": {"response": {"neverError": True}}}
    },
    "id": uid('http-balance-'),
    "name": "HTTP Credit Balance",
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.5,
    "position": [-340, 160]
}

code_balance = {
    "parameters": {
        "mode": "runOnceForAllItems",
        "language": "javaScript",
        "jsCode": "const raw = ($json && typeof $json === 'object' && !Array.isArray($json)) ? $json : {};\nconst body = (raw.body && typeof raw.body === 'object' && !Array.isArray(raw.body)) ? raw.body : null;\nlet balance = null;\ntry {\n  if (body && body.creditCount != null) {\n    balance = Number(body.creditCount);\n  } else if (raw.creditCount != null) {\n    balance = Number(raw.creditCount);\n  } else if (typeof raw.data === 'string') {\n    balance = Number(JSON.parse(raw.data).creditCount);\n  }\n} catch (err) {\n  balance = null;\n}\nif (balance == null || !Number.isFinite(balance)) {\n  return [{ json: { balance: -1, creditCount: -1, balance_unavailable: true } }];\n}\nreturn [{ json: { balance: balance, creditCount: balance, balance_unavailable: false } }];"
    },
    "id": uid('code-balance-'),
    "name": "Code balance",
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [-140, 160]
}

if_low = {
    "parameters": {
        "conditions": {
            "combinator": "and",
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 3},
            "conditions": [
                {"leftValue": "={{ $json.balance }}", "rightValue": 5, "operator": {"type": "number", "operation": "lt"}},
                {"leftValue": "={{ $json.balance_unavailable }}", "rightValue": False, "operator": {"type": "boolean", "operation": "equals"}}
            ]
        }
    },
    "id": uid('if-low-'),
    "name": "IF low credits",
    "type": "n8n-nodes-base.if",
    "typeVersion": 2.3,
    "position": [60, 160]
}

respond_low = {
    "parameters": {
        "respondWith": "json",
        "responseBody": "={{ {ok: false, error: 'low_credits', balance: $('Code balance').first().json.balance} }}",
        "options": {}
    },
    "id": uid('respond-low-'),
    "name": "Respond low credits",
    "type": "n8n-nodes-base.respondToWebhook",
    "typeVersion": 1.5,
    "position": [300, 320]
}

wf['nodes'].extend([switch_mock, http_balance, code_balance, if_low, respond_low])

# Rebuild connections
# Webhook -> Switch mock
conns['Webhook'] = {"main": [[{"node": "Switch mock", "type": "main", "index": 0}]]}
# Switch mock out0 -> Mock nodes; out1 -> HTTP Credit Balance
conns['Switch mock'] = {
    "main": [
        [{"node": "Mock IG", "type": "main", "index": 0}, {"node": "Mock TikTok", "type": "main", "index": 0}, {"node": "Mock YouTube", "type": "main", "index": 0}],
        [{"node": "HTTP Credit Balance", "type": "main", "index": 0}]
    ]
}
conns['HTTP Credit Balance'] = {"main": [[{"node": "Code balance", "type": "main", "index": 0}]]}
conns['Code balance'] = {"main": [[{"node": "IF low credits", "type": "main", "index": 0}]]}
conns['IF low credits'] = {
    "main": [
        [{"node": "Respond low credits", "type": "main", "index": 0}],
        [{"node": "HTTP IG", "type": "main", "index": 0}, {"node": "HTTP TikTok", "type": "main", "index": 0}, {"node": "HTTP YouTube", "type": "main", "index": 0}]
    ]
}

# Normalize data-string parsing for Normalize code nodes
for n in wf['nodes']:
    if n['type'] == 'n8n-nodes-base.code' and 'Normalize' in n['name']:
        js = n['parameters'].get('jsCode', '')
        if 'const input = $input.all()[0] ? $input.all()[0].json : {};' in js:
            js = js.replace(
                'const input = $input.all()[0] ? $input.all()[0].json : {};',
                "let input = $input.all()[0] ? $input.all()[0].json : {};\nif (typeof input === 'string') { try { input = JSON.parse(input); } catch (e) {} }\nif (input && typeof input === 'object' && typeof input.data === 'string') { try { const parsed = JSON.parse(input.data); if (parsed && typeof parsed === 'object') input = parsed; } catch (e) {} }\nif (!input) input = {};"
            )
        n['parameters']['jsCode'] = js

# Save
path.write_text(json.dumps([wf], ensure_ascii=False, indent=1), encoding='utf-8')
print("wf-analytics fixed")
