#!/usr/bin/env python3
"""Seam tests for hermes-bridge/server.py public HTTP interface.

Public surface:
  GET  /health -> {"ok": bool}
  POST /ask    -> X-BRIDGE-TOKEN required; body {skill, prompt}
  POST /doc-text -> X-BRIDGE-TOKEN required; body {file_id, file_name, digest?}
  POST /img-text -> X-BRIDGE-TOKEN required; body {file_id, file_name}

Run: python3 -m pytest tests/test_hermes_bridge.py -v
"""
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_PATH = os.path.join(ROOT, "hermes-bridge", "server.py")

spec = importlib.util.spec_from_file_location("hermes_bridge_server", SERVER_PATH)
hbserver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hbserver)


class _Body:
    def __init__(self, data):
        self.data = data

    def read(self, n=-1):
        return self.data


class FakeHandler(hbserver.Handler):
    def __init__(self, body=b"{}", headers=None):
        self.rfile = _Body(body)
        self.headers = headers or {}
        self.sent = None

    def _send(self, code, obj):
        self.sent = (code, obj)


def make_handler(body=None, token="secret", extra_headers=None, path="/ask"):
    body = json.dumps(body).encode("utf-8") if not isinstance(body, bytes) else body
    headers = {"X-BRIDGE-TOKEN": token, "Content-Length": str(len(body))}
    headers.update(extra_headers or {})
    h = FakeHandler(body, headers)
    h.path = path
    return h


class HealthTests(unittest.TestCase):
    """Public seam: GET /health always returns {"ok": true}."""

    def test_health(self):
        h = FakeHandler(b"", {})
        h.path = "/health"
        h.do_GET()
        self.assertEqual(h.sent, (200, {"ok": True}))


class AskTests(unittest.TestCase):
    """Public seam: POST /ask auth, validation, skill whitelist, hermes call."""

    def setUp(self):
        self._old_token = hbserver.TOKEN
        hbserver.TOKEN = "secret"

    def tearDown(self):
        hbserver.TOKEN = self._old_token

    def test_no_token_401(self):
        hbserver.TOKEN = ""
        h = make_handler({"skill": "analyst", "prompt": "test"})
        h.do_POST()
        self.assertEqual(h.sent[0], 401)

    def test_wrong_token_401(self):
        h = make_handler({"skill": "analyst", "prompt": "test"}, token="nope")
        h.do_POST()
        self.assertEqual(h.sent[0], 401)

    def test_invalid_skill_400(self):
        h = make_handler({"skill": "not-allowed", "prompt": "test"})
        h.do_POST()
        self.assertEqual(h.sent[0], 400)
        self.assertIn("invalid skill", h.sent[1]["error"])

    def test_empty_prompt_400(self):
        h = make_handler({"skill": "analyst", "prompt": "  "})
        h.do_POST()
        self.assertEqual(h.sent[0], 400)

    def test_ask_calls_hermes_with_correct_skill(self):
        fake = mock.Mock(returncode=0, stdout="ответ", stderr="")
        with mock.patch.object(hbserver.subprocess, "run", return_value=fake) as run:
            h = make_handler({"skill": "analyst", "prompt": "вопрос"}, path="/ask")
            h.do_POST()
        self.assertEqual(h.sent[0], 200)
        self.assertEqual(h.sent[1]["answer"], "ответ")
        cmd = run.call_args[0][0]
        self.assertIn("content-factory/analyst", cmd)


class DocTextTests(unittest.TestCase):
    """Public seam: POST /doc-text auth, validation, extraction, no /ask break."""

    def setUp(self):
        self._old_token = hbserver.TOKEN
        hbserver.TOKEN = "secret"
        self.tmpdir = tempfile.mkdtemp(prefix="doc-text-test-")

    def tearDown(self):
        hbserver.TOKEN = self._old_token

    def test_unsupported_type_400(self):
        h = make_handler({"file_id": "f", "file_name": "x.zip"}, path="/doc-text")
        h.do_POST()
        self.assertEqual(h.sent[0], 400)
        self.assertEqual(h.sent[1]["error"], "unsupported type")

    def test_telegram_not_configured_503(self):
        with mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": ""}):
            h = make_handler({"file_id": "f", "file_name": "a.txt"}, path="/doc-text")
            h.do_POST()
        self.assertEqual(h.sent[0], 503)

    def test_txt_extraction_full_flow(self):
        content = "Привет, контент-завод!"
        fixture = os.path.join(self.tmpdir, "sample.txt")
        with open(fixture, "w", encoding="utf-8") as f:
            f.write(content)
        with ExitStack() as st:
            st.enter_context(mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "tok"}))
            st.enter_context(mock.patch.object(hbserver, "_telegram_get_file",
                                               return_value="docs/sample.txt"))
            st.enter_context(mock.patch.object(hbserver, "_telegram_download"))
            st.enter_context(mock.patch.object(hbserver, "_tmp_path", return_value=fixture))
            h = make_handler({"file_id": "f", "file_name": "sample.txt"}, path="/doc-text")
            h.do_POST()
        self.assertEqual(h.sent[0], 200)
        self.assertEqual(h.sent[1]["text"], content)
        self.assertEqual(h.sent[1]["mime"], "text/plain")


class ImgTextTests(unittest.TestCase):
    """Public seam: POST /img-text OCR flow and error handling."""

    def setUp(self):
        self._old_token = hbserver.TOKEN
        hbserver.TOKEN = "secret"
        self.tmpdir = tempfile.mkdtemp(prefix="img-text-test-")

    def tearDown(self):
        hbserver.TOKEN = self._old_token

    def test_missing_file_id_400(self):
        h = make_handler({"file_name": "photo.jpg"}, path="/img-text")
        h.do_POST()
        self.assertEqual(h.sent[0], 400)

    def test_ocr_marker_parsing(self):
        img_path = os.path.join(self.tmpdir, "photo.jpg")
        with open(img_path, "wb") as f:
            f.write(b"\xff\xd8fake")
        with ExitStack() as st:
            st.enter_context(mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "tok"}))
            st.enter_context(mock.patch.object(hbserver, "_telegram_get_file",
                                               return_value="photos/photo.jpg"))
            st.enter_context(mock.patch.object(hbserver, "_telegram_download"))
            st.enter_context(mock.patch.object(hbserver, "_tmp_path", return_value=img_path))
            fake = mock.Mock(returncode=0, stdout="<TEXT>текст с фото</TEXT>", stderr="")
            st.enter_context(mock.patch.object(hbserver.subprocess, "run", return_value=fake))
            h = make_handler({"file_id": "f", "file_name": "photo.jpg"}, path="/img-text")
            h.do_POST()
        self.assertEqual(h.sent[0], 200)
        self.assertEqual(h.sent[1]["text"], "текст с фото")


if __name__ == "__main__":
    unittest.main(verbosity=2)
