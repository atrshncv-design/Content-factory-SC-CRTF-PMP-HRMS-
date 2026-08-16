#!/usr/bin/env python3
import json, re
from pathlib import Path
from collections import defaultdict

ROOT = Path('/Users/aleksandrtrisenkov/Desktop/PROGRAMMING/РАБОЧИЕ ПРОЕКТЫ/КОНТЕНТ-ЗАВОД-API-MVP')
WORKFLOWS = [
    'wf-analytics.json',
    'wf-audience.json',
    'wf-creators-search.json',
    'wf-creator-profile.json',
    'wf-creator-content.json',
    'wf-transcripts-comments.json',
]

def load_wf(name):
    path = ROOT / 'workflows' / name
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        wf = data[0] if isinstance(data, list) else data
        return wf, []
    except Exception as e:
        return None, [f"{name}: JSON load error: {e}"]

def is_sc_http(node):
    if node.get('type') != 'n8n-nodes-base.httpRequest':
        return False
    url = str(node.get('parameters', {}).get('url', ''))
    # static SC URLs, or dynamic URLs built by Detect transcript/comments nodes (SC api_url)
    return ('scrapecreators.com' in url
            or "Detect transcript" in url
            or "Detect comments" in url)

def is_credit_balance(node):
    return is_sc_http(node) and 'credit-balance' in str(node.get('parameters', {}).get('url', ''))

def is_paid_sc_http(node):
    return is_sc_http(node) and not is_credit_balance(node)

def has_keypair_x_api_key(node):
    p = node.get('parameters', {})
    headers = p.get('headerParameters', {}).get('parameters', [])
    names = [h.get('name', '').lower() for h in headers]
    vals = [h.get('value', '') for h in headers]
    return (p.get('authentication') == 'none' and p.get('sendHeaders') == True and p.get('specifyHeaders') == 'keypair'
            and 'x-api-key' in names and any('$env.SCRAPECREATORS_API_KEY' in v for v in vals))

def has_never_error(node):
    try:
        return node['parameters']['options']['response']['response']['neverError'] == True
    except Exception:
        return False

def build_adj(conns):
    adj = defaultdict(list)
    for src, cm in conns.items():
        for arrs in cm.get('main', []):
            if isinstance(arrs, list):
                for a in arrs:
                    if isinstance(a, dict):
                        adj[src].append(a['node'])
    return adj

def paths_with_node(start, target, adj, nodes_by_name, node_name_substr):
    """Return True if every path from start to target passes through a node whose name contains node_name_substr."""
    found_any = False
    all_have = True
    stack = [(start, set())]
    visited_states = set()
    while stack:
        node, seen = stack.pop()
        if node == target:
            found_any = True
            continue
        if node in seen:
            continue
        new_seen = seen | {node}
        for nxt in adj.get(node, []):
            stack.append((nxt, new_seen))
    # simpler: find any path that misses gate
    stack = [(start, True)]
    memo = {}
    def dfs(n, gate_seen):
        if n == target:
            return gate_seen
        key = (n, gate_seen)
        if key in memo:
            return memo[key]
        res = True
        for nxt in adj.get(n, []):
            next_gate = gate_seen or (node_name_substr.lower() in n.lower())
            res = res and dfs(nxt, next_gate)
        memo[key] = res
        return res
    return dfs(start, False)

def find_trigger(wf):
    for n in wf.get('nodes', []):
        if n.get('type') == 'n8n-nodes-base.webhook':
            return n['name']
    return None

def check(name):
    wf, errs = load_wf(name)
    if wf is None:
        return {'name': name, 'valid': False, 'issues': errs}
    nodes = {n['name']: n for n in wf.get('nodes', [])}
    conns = wf.get('connections', {})
    adj = build_adj(conns)
    issues = []
    warnings = []

    trigger = find_trigger(wf)

    # 1. HTTP SC typeVersion 4.5, keypair, neverError
    sc_http = [n for n in wf.get('nodes', []) if is_sc_http(n)]
    for n in sc_http:
        if n.get('typeVersion') != 4.5:
            issues.append(f"{n['name']}: SC HTTP typeVersion != 4.5 ({n.get('typeVersion')})")
        if not has_keypair_x_api_key(n):
            issues.append(f"{n['name']}: SC HTTP не keypair x-api-key (auth={n.get('parameters',{}).get('authentication')})")
        if not has_never_error(n):
            issues.append(f"{n['name']}: neverError вложенный отсутствует")

    # 2. low_credits gate before every paid SC HTTP on all paths
    paid = [n for n in wf.get('nodes', []) if is_paid_sc_http(n)]
    for n in paid:
        if trigger is None:
            issues.append(f"{n['name']}: нет webhook trigger")
            continue
        if not paths_with_node(trigger, n['name'], adj, nodes, 'low credits'):
            issues.append(f"{n['name']}: есть путь от trigger без предшествующего IF low credits")

    # 3. mock/real switch string (nodes named Switch mock or similar)
    for n in wf.get('nodes', []):
        if n.get('type') != 'n8n-nodes-base.switch':
            continue
        if 'mock' not in n.get('name', '').lower():
            continue
        for rule in n.get('parameters', {}).get('rules', {}).get('values', []):
            cond = rule.get('conditions', {}).get('conditions', [])
            if cond:
                op = cond[0].get('operator', {})
                if op.get('type') != 'string':
                    issues.append(f"{n['name']}: mock-switch использует не string-оператор ({op.get('type')})")
                left = cond[0].get('leftValue', '')
                right = cond[0].get('rightValue', '')
                if 'PLACEHOLDER_UNTIL_TOMORROW' not in str(right) or '$env.SCRAPECREATORS_API_KEY' not in str(left):
                    issues.append(f"{n['name']}: mock-switch правило не на PLACEHOLDER_UNTIL_TOMORROW")

    # 4. low credits responseBody format
    for n in wf.get('nodes', []):
        if n.get('type') == 'n8n-nodes-base.respondToWebhook' and 'low credits' in n.get('name', '').lower():
            rb = n.get('parameters', {}).get('responseBody', '')
            if isinstance(rb, str):
                if '={ {' in rb:
                    issues.append(f"{n['name']}: сломанный responseBody ({rb[:80]})")
                elif 'low_credits' not in rb:
                    issues.append(f"{n['name']}: responseBody без low_credits")

    # 5. universal parser in normalize / balance code nodes
    for n in wf.get('nodes', []):
        if n.get('type') != 'n8n-nodes-base.code':
            continue
        js = n.get('parameters', {}).get('jsCode', '')
        has_universal = ('JSON.parse' in js) and (('raw.data' in js) or ('$json.data' in js))
        if 'balance' in n.get('name', '').lower() and not has_universal:
            issues.append(f"{n['name']}: парсер баланса не универсальный (нет JSON.parse(data))")
        if 'Normalize' in n.get('name', '') and not has_universal:
            warnings.append(f"{n['name']}: возможно, не универсальный парсер (нет JSON.parse(data))")

    # 6. respond low credits readable message
    for n in wf.get('nodes', []):
        if n.get('type') == 'n8n-nodes-base.respondToWebhook' and 'low credits' in n.get('name', '').lower():
            rb = n.get('parameters', {}).get('responseBody', '')
            if isinstance(rb, str) and ('ok: false' not in rb or 'error' not in rb or 'balance' not in rb):
                warnings.append(f"{n['name']}: low_credits ответ оператору может быть непонятным")

    return {'name': name, 'valid': not issues, 'issues': issues, 'warnings': warnings}

print("=== AUDIT 05 SC cluster ===\n")
all_issues = []
for name in WORKFLOWS:
    r = check(name)
    print(f"\n{name}")
    print(f"  valid: {r['valid']}")
    for i in r.get('issues', []):
        print(f"  ❌ {i}")
        all_issues.append(f"{name}: {i}")
    for w in r.get('warnings', []):
        print(f"  ⚠️ {w}")

print(f"\n\nTOTAL ISSUES: {len(all_issues)}")
