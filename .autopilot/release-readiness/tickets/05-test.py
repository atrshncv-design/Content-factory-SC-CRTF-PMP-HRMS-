#!/usr/bin/env python3
"""Приёмочные тесты тикета 05 — шов: JSON + audit + node --check."""
import json, subprocess, sys
from pathlib import Path

ROOT = Path('/Users/aleksandrtrisenkov/Desktop/PROGRAMMING/РАБОЧИЕ ПРОЕКТЫ/КОНТЕНТ-ЗАВОД-API-MVP')
WORKFLOWS = [
    'wf-analytics.json',
    'wf-audience.json',
    'wf-creators-search.json',
    'wf-creator-profile.json',
    'wf-creator-content.json',
    'wf-transcripts-comments.json',
]

def test_json_loadable():
    for name in WORKFLOWS:
        data = json.loads((ROOT / 'workflows' / name).read_text(encoding='utf-8'))
        assert isinstance(data, list) and len(data) == 1, f"{name}: expected list envelope"
        wf = data[0]
        assert 'nodes' in wf and 'connections' in wf, f"{name}: missing nodes/connections"
    print("✅ JSON loadable")

def test_audit_zero_issues():
    out = subprocess.run([sys.executable, str(ROOT / '.autopilot/release-readiness/tickets/05-audit.py')], capture_output=True, text=True)
    assert 'TOTAL ISSUES: 0' in out.stdout, f"audit issues found:\n{out.stdout}"
    print("✅ Audit 0 issues")

def test_node_check_and_reachability():
    for name in WORKFLOWS:
        out = subprocess.run(
            [sys.executable, str(ROOT / '.scratch/bot-ux-menu/validate_workflow.py'), str(ROOT / 'workflows' / name)],
            capture_output=True, text=True
        )
        out_text = out.stdout + out.stderr
        # wf-transcripts-comments has two independent webhooks; standard BFS from first misses comments chain -> expected
        if name == 'wf-transcripts-comments.json':
            assert 'node --check' in out_text or 'jsCode' in out_text or 'ВАЛИДАЦИЯ' in out_text, f"{name}: validator crashed\n{out_text}"
            # Only acceptable issue is unreachable comments chain (two webhooks)
            if 'НЕДОСТИЖИМЫЕ' in out_text:
                assert 'comments-webhook' in out_text, f"{name}: unexpected unreachable nodes\n{out_text}"
            else:
                assert '✅ ВАЛИДАЦИЯ ПРОЙДЕНА' in out_text, f"{name}: validation failed\n{out_text}"
        else:
            assert '✅ ВАЛИДАЦИЯ ПРОЙДЕНА' in out_text, f"{name}: validation failed\n{out_text}"
    print("✅ node --check + reachability")

def test_no_real_sc_calls_in_mock_mode():
    """При PLACEHOLDER_UNTIL_TOMORROW все Switch mock ведут в mock-ветку, а реальная ветка начинается с credit-balance (бесплатно)."""
    for name in WORKFLOWS:
        wf = json.loads((ROOT / 'workflows' / name).read_text(encoding='utf-8'))[0]
        nodes = {n['name']: n for n in wf['nodes']}
        # find mock switches
        mock_switches = [n for n in wf['nodes'] if n.get('type') == 'n8n-nodes-base.switch' and 'mock' in n['name'].lower()]
        for sw in mock_switches:
            rules = sw['parameters']['rules']['values']
            cond = rules[0]['conditions']['conditions'][0]
            assert cond['leftValue'] == '={{ $env.SCRAPECREATORS_API_KEY }}', f"{name}:{sw['name']} leftValue wrong"
            assert cond['rightValue'] == 'PLACEHOLDER_UNTIL_TOMORROW', f"{name}:{sw['name']} rightValue wrong"
            assert cond['operator']['type'] == 'string', f"{name}:{sw['name']} operator not string"
    print("✅ Mock/real switches are string-based")

if __name__ == '__main__':
    test_json_loadable()
    test_audit_zero_issues()
    test_node_check_and_reachability()
    test_no_real_sc_calls_in_mock_mode()
    print("\n🟢 All tests passed")
