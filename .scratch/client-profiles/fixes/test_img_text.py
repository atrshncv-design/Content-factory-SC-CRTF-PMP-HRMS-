#!/usr/bin/env python3
"""Unit tests for the /img-text endpoint of hermes-bridge (no network calls).

Covers:
  (а) no/missing X-BRIDGE-TOKEN -> 401
  (б) bad request (not JSON / missing fields / non-object) -> 400
  (в) hermes CLI error/timeout/binary missing -> 502
  (г) marker parsing (mocked hermes stdout) -> 200 {name, mime, text, chars},
      CLI flags + prompt contain the image path, HERMES_HOME env set
  (д) missing/empty TEXT markers -> 502 (text never fabricated)
  (е) telegram getFile/download errors -> 400/502
  (ж) text truncated to TEXT_LIMIT; mime by extension; tmp file removed

Run: python3 test_img_text.py
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack
from unittest import mock

DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_PATH = os.path.join(DIR, "hermes-bridge-server.py")

spec = importlib.util.spec_from_file_location("hermes_bridge_server", SERVER_PATH)
hbserver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hbserver)


class _Body(object):
    def __init__(self, data):
        self.data = data

    def read(self, n=-1):
        return self.data


class FakeHandler(hbserver.Handler):
    """Handler with socket I/O replaced by in-memory objects."""

    def __init__(self, body=b"{}", headers=None):
        self.rfile = _Body(body)
        self.headers = headers or {}
        self.sent = None

    def _send(self, code, obj):
        self.sent = (code, obj)


def make_handler(body=None, token="secret", extra_headers=None, path="/img-text"):
    body = json.dumps(body).encode("utf-8") if not isinstance(body, bytes) else body
    headers = {"X-BRIDGE-TOKEN": token, "Content-Length": str(len(body))}
    headers.update(extra_headers or {})
    h = FakeHandler(body, headers)
    h.path = path
    return h


class ImgTextValidationTests(unittest.TestCase):
    """(а) auth, (б) bad request, telegram not configured."""

    def setUp(self):
        self._old_token = hbserver.TOKEN
        hbserver.TOKEN = "secret"

    def tearDown(self):
        hbserver.TOKEN = self._old_token

    def test_no_token_401(self):
        hbserver.TOKEN = ""
        h = make_handler({"file_id": "f", "file_name": "photo.jpg"})
        h.do_POST()
        self.assertEqual(h.sent[0], 401)

    def test_wrong_token_401(self):
        h = make_handler({"file_id": "f", "file_name": "photo.jpg"}, token="nope")
        h.do_POST()
        self.assertEqual(h.sent[0], 401)

    def test_bad_json_400(self):
        h = make_handler(b"this is not json")
        h.do_POST()
        self.assertEqual(h.sent[0], 400)
        self.assertIn("bad request", h.sent[1]["error"])

    def test_json_array_400(self):
        # body parsed fine but is not an object -> 400, no network
        h = make_handler([1, 2, 3])
        h.do_POST()
        self.assertEqual(h.sent[0], 400)

    def test_missing_file_id_400(self):
        h = make_handler({"file_name": "photo.jpg"})
        h.do_POST()
        self.assertEqual(h.sent[0], 400)
        self.assertIn("file_id", h.sent[1]["error"])

    def test_missing_file_name_400(self):
        h = make_handler({"file_id": "f"})
        h.do_POST()
        self.assertEqual(h.sent[0], 400)
        self.assertIn("file_name", h.sent[1]["error"])

    def test_telegram_not_configured_503(self):
        with mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": ""}):
            h = make_handler({"file_id": "f", "file_name": "photo.jpg"})
            h.do_POST()
        self.assertEqual(h.sent[0], 503)
        self.assertEqual(h.sent[1]["error"], "telegram not configured")

    def test_unknown_path_404(self):
        h = make_handler({"file_id": "f", "file_name": "photo.jpg"}, path="/nope")
        h.do_POST()
        self.assertEqual(h.sent[0], 404)


class OcrTests(unittest.TestCase):
    """(в) hermes errors -> 502; (г) marker parsing; (д) missing markers."""

    def setUp(self):
        self._old_token = hbserver.TOKEN
        hbserver.TOKEN = "secret"
        self.tmpdir = tempfile.mkdtemp(prefix="img-text-test-")

    def tearDown(self):
        hbserver.TOKEN = self._old_token

    def _base_mocks(self, img_name="photo.jpg"):
        img_path = os.path.join(self.tmpdir, img_name)
        return [
            mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "tok"}),
            mock.patch.object(hbserver, "_telegram_get_file",
                              return_value="photos/" + img_name),
            mock.patch.object(hbserver, "_telegram_download"),
            mock.patch.object(hbserver, "_tmp_path", return_value=img_path),
        ]

    def _run(self, body=None, hermes_out=None, run_raise=None):
        body = body or {"file_id": "f", "file_name": "photo.jpg"}
        with ExitStack() as st:
            for p in self._base_mocks(body.get("file_name", "photo.jpg")):
                st.enter_context(p)
            if run_raise is not None:
                # subprocess.run itself must raise -> patch with side_effect
                run_patch = mock.patch.object(hbserver.subprocess, "run",
                                              side_effect=run_raise)
            else:
                fake = mock.Mock()
                fake.returncode = 0
                fake.stderr = ""
                fake.stdout = (
                    hermes_out if hermes_out is not None else "<TEXT>текст с фото</TEXT>"
                )
                run_patch = mock.patch.object(hbserver.subprocess, "run",
                                              return_value=fake)
            run_mock = run_patch.start()
            st.callback(run_patch.stop)
            h = make_handler(body)
            h.do_POST()
        return h.sent, run_mock

    def test_success_marker_parsing(self):
        sent, run = self._run(hermes_out=(
            "рассуждения перед ответом\n"
            "<TEXT>ВСЕ видимый текст: строка один\nстрока два</TEXT>\n"
            "хвост после маркера"
        ))
        self.assertEqual(sent[0], 200)
        body = sent[1]
        self.assertEqual(body["name"], "photo.jpg")
        self.assertEqual(body["mime"], "image/jpeg")
        self.assertEqual(body["text"], "ВСЕ видимый текст: строка один\nстрока два")
        self.assertEqual(body["chars"], len(body["text"]))
        self.assertNotIn("digested", body)

    def test_hermes_cli_flags_and_prompt(self):
        sent, run = self._run()
        self.assertEqual(sent[0], 200)
        cmd = run.call_args[0][0]
        self.assertEqual(cmd[0], hbserver.HERMES_BIN)
        self.assertEqual(cmd[1], "chat")
        self.assertIn("-q", cmd)
        self.assertIn("--cli", cmd)
        self.assertIn("-Q", cmd)
        self.assertIn("--reasoning", cmd)
        self.assertIn("none", cmd)
        self.assertNotIn("-s", cmd)  # no skill for vision OCR
        self.assertIn("Прочитай изображение", cmd[3])
        self.assertIn("TEXT-маркерах", cmd[3])
        self.assertIn("photo.jpg", cmd[3])  # image path is in the prompt
        env = run.call_args[1]["env"]
        self.assertEqual(env["HERMES_HOME"], hbserver.HERMES_HOME)

    def test_getfile_called_with_token_and_id(self):
        with ExitStack() as st:
            st.enter_context(mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "tok"}))
            getfile = mock.patch.object(hbserver, "_telegram_get_file",
                                        return_value="photos/photo.jpg").start()
            st.callback(getfile.stop)
            st.enter_context(mock.patch.object(hbserver, "_telegram_download"))
            st.enter_context(mock.patch.object(
                hbserver, "_tmp_path",
                return_value=os.path.join(self.tmpdir, "photo.jpg")))
            fake = mock.Mock()
            fake.returncode = 0
            fake.stderr = ""
            fake.stdout = "<TEXT>x</TEXT>"
            with mock.patch.object(hbserver.subprocess, "run", return_value=fake):
                h = make_handler({"file_id": "fid42", "file_name": "photo.jpg"})
                h.do_POST()
        self.assertEqual(h.sent[0], 200)
        getfile.assert_called_once_with("tok", "fid42")

    def test_success_mime_by_extension_png(self):
        sent, _ = self._run(body={"file_id": "f", "file_name": "scan.png"})
        self.assertEqual(sent[0], 200)
        self.assertEqual(sent[1]["mime"], "image/png")

    def test_success_mime_by_extension_webp(self):
        sent, _ = self._run(body={"file_id": "f", "file_name": "pic.webp"})
        self.assertEqual(sent[0], 200)
        self.assertEqual(sent[1]["mime"], "image/webp")

    def test_success_mime_default_jpeg_unknown_ext(self):
        sent, _ = self._run(body={"file_id": "f", "file_name": "telegram_photo"})
        self.assertEqual(sent[0], 200)
        self.assertEqual(sent[1]["mime"], "image/jpeg")

    def test_text_truncated_to_limit(self):
        sent, _ = self._run(hermes_out="<TEXT>%s</TEXT>" % ("с" * 40000))
        self.assertEqual(sent[0], 200)
        self.assertEqual(len(sent[1]["text"]), hbserver.TEXT_LIMIT)
        self.assertEqual(sent[1]["chars"], hbserver.TEXT_LIMIT)

    def test_hermes_timeout_502(self):
        sent, _ = self._run(run_raise=subprocess.TimeoutExpired(
            [hbserver.HERMES_BIN, "chat"], timeout=hbserver.OCR_TIMEOUT))
        self.assertEqual(sent[0], 502)
        self.assertIn("не удалось распознать текст на фото", sent[1]["error"])

    def test_hermes_binary_missing_502(self):
        sent, _ = self._run(run_raise=FileNotFoundError("hermes"))
        self.assertEqual(sent[0], 502)
        self.assertIn("не удалось распознать текст на фото", sent[1]["error"])

    def test_hermes_generic_error_502(self):
        sent, _ = self._run(run_raise=RuntimeError("boom"))
        self.assertEqual(sent[0], 502)
        self.assertIn("не удалось распознать текст на фото", sent[1]["error"])

    def test_no_markers_502(self):
        sent, _ = self._run(hermes_out="ответ без TEXT-маркеров")
        self.assertEqual(sent[0], 502)
        self.assertIn("не удалось распознать текст на фото", sent[1]["error"])
        self.assertNotIn("ответ без", sent[1]["error"])  # no fabricated text

    def test_empty_stdout_502(self):
        sent, _ = self._run(hermes_out="")
        self.assertEqual(sent[0], 502)

    def test_stdout_none_502(self):
        # hermes returns None stdout -> treated as no markers -> 502
        with ExitStack() as st:
            for p in self._base_mocks():
                st.enter_context(p)
            fake = mock.Mock()
            fake.returncode = 0
            fake.stderr = ""
            fake.stdout = None
            with mock.patch.object(hbserver.subprocess, "run", return_value=fake):
                h = make_handler({"file_id": "f", "file_name": "photo.jpg"})
                h.do_POST()
        self.assertEqual(h.sent[0], 502)
        self.assertIn("не удалось распознать текст на фото", h.sent[1]["error"])

    def test_empty_markers_502(self):
        sent, _ = self._run(hermes_out="<TEXT>  </TEXT>")
        self.assertEqual(sent[0], 502)
        self.assertIn("не удалось распознать текст на фото", sent[1]["error"])

    def test_tmp_file_removed_after_flow(self):
        img_path = os.path.join(self.tmpdir, "photo.jpg")
        with open(img_path, "wb") as f:
            f.write(b"\xff\xd8fake-jpeg")
        with ExitStack() as st:
            st.enter_context(mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "tok"}))
            st.enter_context(mock.patch.object(hbserver, "_telegram_get_file",
                                               return_value="photos/photo.jpg"))
            st.enter_context(mock.patch.object(hbserver, "_telegram_download"))
            st.enter_context(mock.patch.object(hbserver, "_tmp_path", return_value=img_path))
            fake = mock.Mock()
            fake.returncode = 0
            fake.stderr = ""
            fake.stdout = "<TEXT>текст</TEXT>"
            with mock.patch.object(hbserver.subprocess, "run", return_value=fake):
                h = make_handler({"file_id": "f", "file_name": "photo.jpg"})
                h.do_POST()
        self.assertEqual(h.sent[0], 200)
        self.assertFalse(os.path.exists(img_path))


class TelegramErrorTests(unittest.TestCase):
    """(е) getFile/download failure mapping (400/502), no network."""

    def setUp(self):
        self._old_token = hbserver.TOKEN
        hbserver.TOKEN = "secret"

    def tearDown(self):
        hbserver.TOKEN = self._old_token

    def _run_with_getfile_effect(self, exc):
        with ExitStack() as st:
            st.enter_context(mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "tok"}))
            st.enter_context(mock.patch.object(hbserver, "_telegram_get_file",
                                               side_effect=exc))
            st.enter_context(mock.patch.object(hbserver, "_telegram_download"))
            h = make_handler({"file_id": "f", "file_name": "photo.jpg"})
            h.do_POST()
        return h.sent

    def test_getfile_bad_request_400(self):
        sent = self._run_with_getfile_effect(
            hbserver.TelegramError("telegram getFile failed (HTTP 400): Bad Request", 400))
        self.assertEqual(sent[0], 400)
        self.assertIn("getFile", sent[1]["error"])

    def test_getfile_unreachable_502(self):
        sent = self._run_with_getfile_effect(
            hbserver.TelegramError("telegram unreachable: test", 502))
        self.assertEqual(sent[0], 502)
        self.assertIn("telegram unreachable", sent[1]["error"])

    def test_download_not_found_400(self):
        with ExitStack() as st:
            st.enter_context(mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "tok"}))
            st.enter_context(mock.patch.object(hbserver, "_telegram_get_file",
                                               return_value="photos/photo.jpg"))
            st.enter_context(mock.patch.object(
                hbserver, "_telegram_download",
                side_effect=hbserver.TelegramError("telegram file not found (HTTP 404)", 400)))
            h = make_handler({"file_id": "f", "file_name": "photo.jpg"})
            h.do_POST()
        self.assertEqual(h.sent[0], 400)
        self.assertIn("not found", h.sent[1]["error"])

    def test_download_http_500_502(self):
        with ExitStack() as st:
            st.enter_context(mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "tok"}))
            st.enter_context(mock.patch.object(hbserver, "_telegram_get_file",
                                               return_value="photos/photo.jpg"))
            st.enter_context(mock.patch.object(
                hbserver, "_telegram_download",
                side_effect=hbserver.TelegramError("telegram download failed (HTTP 500)", 502)))
            h = make_handler({"file_id": "f", "file_name": "photo.jpg"})
            h.do_POST()
        self.assertEqual(h.sent[0], 502)


class HelperTests(unittest.TestCase):
    """Unit tests for extracted image helpers."""

    def test_image_mime_map(self):
        self.assertEqual(hbserver._image_mime("jpg"), "image/jpeg")
        self.assertEqual(hbserver._image_mime("jpeg"), "image/jpeg")
        self.assertEqual(hbserver._image_mime("png"), "image/png")
        self.assertEqual(hbserver._image_mime("webp"), "image/webp")
        self.assertEqual(hbserver._image_mime("gif"), "image/gif")
        self.assertEqual(hbserver._image_mime("tiff"), "image/tiff")
        self.assertEqual(hbserver._image_mime(""), "image/jpeg")
        self.assertEqual(hbserver._image_mime("xyz"), "image/jpeg")

    def test_tmp_path_prefix_optional(self):
        p1 = hbserver._tmp_path("jpg", prefix="hermes-img-")
        self.assertTrue(os.path.basename(p1).startswith("hermes-img-"))
        self.assertTrue(p1.endswith(".jpg"))
        p2 = hbserver._tmp_path("txt")
        self.assertTrue(os.path.basename(p2).startswith("hermes-doc-"))
        self.assertTrue(p2.endswith(".txt"))

    def test_ocr_prompt_format(self):
        prompt = hbserver.OCR_PROMPT % "/tmp/img-1.jpg"
        self.assertIn("/tmp/img-1.jpg", prompt)
        self.assertIn("Прочитай изображение", prompt)
        self.assertIn("TEXT-маркерах", prompt)


class RouteRegressionTests(unittest.TestCase):
    """/ask, /health, /doc-text must stay unchanged."""

    def setUp(self):
        self._old_token = hbserver.TOKEN
        hbserver.TOKEN = "secret"

    def tearDown(self):
        hbserver.TOKEN = self._old_token

    def test_health_unchanged(self):
        h = FakeHandler(b"", {"X-BRIDGE-TOKEN": "secret"})
        h.path = "/health"
        h.do_GET()
        self.assertEqual(h.sent, (200, {"ok": True}))

    def test_doc_text_still_routes(self):
        fixture = os.path.join(tempfile.gettempdir(), "doc-text-regression.txt")
        with open(fixture, "w", encoding="utf-8") as f:
            f.write("hello doc-text")
        try:
            with ExitStack() as st:
                st.enter_context(mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "tok"}))
                st.enter_context(mock.patch.object(hbserver, "_telegram_get_file",
                                                   return_value="docs/a.txt"))
                st.enter_context(mock.patch.object(hbserver, "_telegram_download"))
                st.enter_context(mock.patch.object(hbserver, "_tmp_path", return_value=fixture))
                h = make_handler({"file_id": "f", "file_name": "a.txt"}, path="/doc-text")
                h.do_POST()
        finally:
            try:
                os.remove(fixture)
            except OSError:
                pass
        self.assertEqual(h.sent[0], 200)
        self.assertEqual(h.sent[1]["mime"], "text/plain")
        self.assertEqual(h.sent[1]["text"], "hello doc-text")
        self.assertTrue(h.sent[1]["digested"] is False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
