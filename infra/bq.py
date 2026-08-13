#!/usr/bin/env python3
"""Хелпер: выполнить один SQL через db-bridge контент-завода.
Использование: bq.py 'SELECT ...' [--params '{"k":"v"}']
Печатает JSON-ответ bridge."""
import json, os, subprocess, sys, urllib.request

sql = sys.argv[1]
params = {}
if len(sys.argv) > 2 and sys.argv[2] != '':
    params = json.loads(sys.argv[2])

# получить IP контейнера db-bridge
try:
    ip = subprocess.check_output(
        ["docker", "inspect", "-f", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}", "factory-db-bridge"],
        text=True).strip()
except Exception:
    ip = "172.18.0.3"
token = os.environ.get("FACTORY_DB_BRIDGE_TOKEN", "")

body = json.dumps({"sql": sql, "params": params}).encode()
req = urllib.request.Request(
    f"http://{ip}:8787/query", data=body,
    headers={"Content-Type": "application/json", "X-BRIDGE-TOKEN": token})
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print(r.read().decode())
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read().decode()}")
except Exception as e:
    print(f"ERR: {e}")