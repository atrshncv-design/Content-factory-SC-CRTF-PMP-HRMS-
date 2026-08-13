#!/usr/bin/env python3
"""hermes-bridge: HTTP wrapper over Hermes CLI (stdlib only, no deps).

POST /ask   X-BRIDGE-TOKEN required; body {"skill": ..., "prompt": ...}
GET  /health -> {"ok": true}
"""
import hmac
import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERMES_BIN = "/home/ubuntu/hermes-agent/.venv/bin/hermes"
HERMES_HOME = "/home/ubuntu/.hermes"
ALLOWED_SKILLS = {"analyst", "scriptwriter", "json-builder", "onboarding"}
TOKEN = os.environ.get("HERMES_BRIDGE_TOKEN", "")


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
        provided = self.headers.get("X-BRIDGE-TOKEN", "")
        if not TOKEN or not hmac.compare_digest(provided, TOKEN):
            self._send(401, {"error": "unauthorized"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
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
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    srv.daemon_threads = True
    print("hermes-bridge listening on 0.0.0.0:%d" % port, flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
