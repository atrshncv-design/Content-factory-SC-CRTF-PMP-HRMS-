#!/usr/bin/env python3
"""hermes-bridge: HTTP wrapper over Hermes CLI (stdlib only, no deps).

POST /ask   X-BRIDGE-TOKEN required; body {"skill": ..., "prompt": ...}
GET  /health -> {"ok": true}

Безопасность (13.08, Волна 4):
- bind docker0 172.17.0.1:8642 (НЕ 0.0.0.0): n8n-контейнер ходит на
  host.docker.internal (= 172.17.0.1). 127.0.0.1 НЕ подойдёт: процесс хоста
  на loopback из контейнера через docker0 недостижим. Наружу не слушаем.
- лимит тела: Content-Length > MAX_BODY -> 413 (payload too large).
- rate-limit: > HERMES_BRIDGE_RATE_LIMIT запросов/мин с одного IP -> 429.
- токен fail-closed: пустой HERMES_BRIDGE_TOKEN -> 401 (как и раньше).
"""
import hmac
import json
import os
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERMES_BIN = "/home/ubuntu/hermes-agent/.venv/bin/hermes"
HERMES_HOME = "/home/ubuntu/.hermes"
ALLOWED_SKILLS = {"analyst", "scriptwriter", "json-builder", "onboarding", "caption-adapter"}
TOKEN = os.environ.get("HERMES_BRIDGE_TOKEN", "")

# --- безопасность: лимит тела и rate-limit ---
MAX_BODY = 1024 * 1024  # 1 MB; Content-Length больше -> 413
try:
    RATE_LIMIT = int(os.environ.get("HERMES_BRIDGE_RATE_LIMIT", "30"))  # запросов/мин с IP
except ValueError:
    RATE_LIMIT = 30
RATE_WINDOW = 60.0

_rate = {}          # ip -> [timestamps]
_rate_lock = threading.Lock()


def _rate_ok(ip):
    """Простой скользящий счётчик запросов в минуту на IP (thread-safe)."""
    now = time.monotonic()
    with _rate_lock:
        ts = _rate.setdefault(ip, [])
        ts[:] = [t for t in ts if now - t < RATE_WINDOW]
        if len(ts) >= RATE_LIMIT:
            return False
        ts.append(now)
        return True


class Handler(BaseHTTPRequestHandler):
    server_version = "hermes-bridge/1.0"

    def log_message(self, fmt, *args):  # keep systemd journal clean-ish
        pass

    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"ok": True})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/ask":
            self._send(404, {"error": "not found"})
            return
        if not _rate_ok(self.client_address[0]):
            self._send(429, {"error": "rate limit exceeded"})
            return
        provided = self.headers.get("X-BRIDGE-TOKEN", "")
        if not TOKEN or not hmac.compare_digest(provided, TOKEN):
            self._send(401, {"error": "unauthorized"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                self._send(413, {"error": "payload too large (max %d bytes)" % MAX_BODY})
                return
            raw = self.rfile.read(length) if length else b"{}"
            data = json.loads(raw.decode("utf-8"))
        except Exception as e:
            self._send(400, {"error": "bad request: %s" % e})
            return
        skill = data.get("skill")
        prompt = data.get("prompt")
        if skill not in ALLOWED_SKILLS:
            self._send(400, {"error": "invalid skill: %r" % skill})
            return
        if not isinstance(prompt, str) or not prompt.strip():
            self._send(400, {"error": "empty prompt"})
            return
        try:
            env = dict(os.environ)
            env["HERMES_HOME"] = HERMES_HOME
            env["PATH"] = "/home/ubuntu/.local/bin:" + env.get("PATH", "")
            cmd = [
                HERMES_BIN, "chat", "-q", prompt, "--cli", "-Q",
                "-s", "content-factory/" + skill,
            ]
            if skill == "caption-adapter":
                # free-text output: suppress reasoning block noise
                cmd += ["--reasoning", "none"]
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300, env=env
            )
            self._send(200, {
                "answer": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
                "returncode": proc.returncode,
            })
        except subprocess.TimeoutExpired:
            self._send(500, {"error": "hermes timeout after 300s"})
        except FileNotFoundError:
            self._send(500, {"error": "hermes binary not found"})
        except Exception as e:
            self._send(500, {"error": "hermes error: %s" % e})


def main():
    port = int(os.environ.get("HERMES_BRIDGE_PORT", "8642"))
    # bind docker0 172.17.0.1: n8n-контейнер обращается через host.docker.internal.
    # НЕ 127.0.0.1 (процесс хоста на loopback из контейнера через docker0 недостижим)
    # и НЕ 0.0.0.0 (публичный интерфейс — было уязвимостью).
    host = os.environ.get("HERMES_BRIDGE_HOST", "172.17.0.1")
    srv = ThreadingHTTPServer((host, port), Handler)
    srv.daemon_threads = True
    print("hermes-bridge listening on %s:%d" % (host, port), flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
