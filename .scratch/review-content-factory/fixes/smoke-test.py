#!/usr/bin/env python3
"""Smoke-тест fail-closed/413/429 логики исправленных копий (только loopback, 0 внешней сети)."""
import http.client
import json
import os
import subprocess
import sys
import time

FIX = "/Users/aleksandrtrisenkov/Desktop/PROGRAMMING/РАБОЧИЕ ПРОЕКТЫ/КОНТЕНТ-ЗАВОД-API-MVP/.scratch/review-content-factory/fixes"


def http_req(port, method, path, headers=None, body=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    c.request(method, path, body=body, headers=headers or {})
    r = c.getresponse()
    data = r.read().decode()
    c.close()
    return r.status, data


def test_db_bridge(port, token_env):
    env = dict(os.environ, BRIDGE_PORT=str(port), BRIDGE_HOST="127.0.0.1",
               FACTORY_DB_PATH="/tmp/factory-smoke.db")
    if token_env is not None:
        env["FACTORY_DB_BRIDGE_TOKEN"] = token_env
    p = subprocess.Popen(["node", "db-bridge-server.js"], cwd=FIX, env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        time.sleep(1.2)
        if token_env is None:
            s, b = http_req(port, "POST", "/query", {"Content-Type": "application/json"},
                            json.dumps({"sql": "SELECT 1"}))
            print("[db-bridge] пустой токен, /query -> %d %s" % (s, b))
            assert s == 500 and "bridge not configured" in b, "fail-closed не сработал!"
        else:
            s, b = http_req(port, "POST", "/query", {"Content-Type": "application/json"},
                            json.dumps({"sql": "SELECT 1"}))
            print("[db-bridge] токен НЕ задан в заголовке -> %d %s" % (s, b[:50]))
            assert s == 401, "ожидался 401 без токена"
            s, b = http_req(port, "POST", "/query",
                            {"Content-Type": "application/json", "X-BRIDGE-TOKEN": "wrong"},
                            json.dumps({"sql": "SELECT 1"}))
            print("[db-bridge] неверный токен -> %d %s" % (s, b[:50]))
            assert s == 401, "ожидался 401 при неверном токене"
            s, b = http_req(port, "POST", "/query",
                            {"Content-Type": "application/json", "X-BRIDGE-TOKEN": token_env},
                            json.dumps({"sql": "SELECT 1"}))
            print("[db-bridge] верный токен, SELECT 1 -> %d %s" % (s, b[:80]))
            assert s == 200 and '"ok":true' in b, "валидный запрос должен пройти"
            s, b = http_req(port, "GET", "/health")
            print("[db-bridge] /health -> %d %s" % (s, b[:50]))
            assert s == 200, "health должен работать без токена"
    finally:
        p.terminate()
        p.wait(timeout=5)


def test_server_py(port, limit):
    env = dict(os.environ, HERMES_BRIDGE_PORT=str(port), HERMES_BRIDGE_HOST="127.0.0.1",
               HERMES_BRIDGE_TOKEN="smoke-sec", HERMES_BRIDGE_RATE_LIMIT=str(limit))
    p = subprocess.Popen([sys.executable, "server.py"], cwd=FIX, env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        time.sleep(1.2)
        # 413 решается по заголовку Content-Length (сервер тело не читает,
        # поэтому реальное тело шлём крошечное — иначе клиент ловит BrokenPipe
        # на закрытом сервером соединении, что тоже корректно)
        s, b = http_req(port, "POST", "/ask",
                        {"Content-Type": "application/json", "Content-Length": str(2 * 1024 * 1024),
                         "X-BRIDGE-TOKEN": "smoke-sec"}, b"{}")
        print("[server.py] Content-Length 2MB (лимит 1MB) -> %d %s" % (s, b[:60]))
        assert s == 413, "ожидался 413"
        s, b = http_req(port, "POST", "/ask",
                        {"Content-Type": "application/json", "Content-Length": "2"}, b"{}")
        print("[server.py] без токена -> %d %s" % (s, b[:60]))
        assert s == 401, "ожидался 401 (fail-closed сохранён)"
        codes = []
        for _ in range(limit + 2):
            s, b = http_req(port, "POST", "/ask",
                            {"Content-Type": "application/json", "X-BRIDGE-TOKEN": "smoke-sec"},
                            json.dumps({"skill": "nope", "prompt": "hi"}).encode())
            codes.append(s)
        print("[server.py] rate-limit(%d/мин): коды %s" % (limit, codes))
        # 2 слота уже потрачены тестами 413 и 401 выше (тот же IP, окно 60с)
        assert codes.count(400) == limit - 2, "rate-limit не сработал: %s" % codes
        assert codes[-1] == 429, "нет 429 после исчерпания лимита: %s" % codes
    finally:
        p.terminate()
        p.wait(timeout=5)


if __name__ == "__main__":
    test_db_bridge(18787, None)
    test_db_bridge(18788, "smoke-secret")
    test_server_py(18642, 3)
    print("SMOKE TESTS: ALL PASS")
