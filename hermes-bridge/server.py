#!/usr/bin/env python3
"""hermes-bridge: HTTP wrapper over Hermes CLI (stdlib only, no deps).

POST /ask       X-BRIDGE-TOKEN required; body {"skill": ..., "prompt": ...}
POST /doc-text  X-BRIDGE-TOKEN required; body {"file_id", "file_name", "digest"?}
                Telegram getFile -> download to /tmp -> extract text (txt/md/pdf/docx)
                -> optional LLM digest via hermes CLI (<TEXT>...</TEXT> markers).
POST /img-text  X-BRIDGE-TOKEN required; body {"file_id", "file_name"}
                Telegram getFile -> download to /tmp -> hermes vision OCR
                (<TEXT>...</TEXT> markers, --cli -Q --reasoning none).
GET  /health    -> {"ok": true}

Env: HERMES_BRIDGE_TOKEN (auth), TELEGRAM_BOT_TOKEN (Telegram Bot API),
     HERMES_BRIDGE_PORT (listen port, default 8642).
Secrets never appear in code — only env var names.
"""
import hmac
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERMES_BIN = "/home/ubuntu/hermes-agent/.venv/bin/hermes"
HERMES_HOME = "/home/ubuntu/.hermes"
ALLOWED_SKILLS = {"analyst", "scriptwriter", "json-builder", "onboarding", "caption-adapter"}
TOKEN = os.environ.get("HERMES_BRIDGE_TOKEN", "")

TEXT_LIMIT = 30000
DIGEST_FALLBACK_LIMIT = 2000
DIGEST_TIMEOUT = 120
DIGEST_PROMPT = (
    "прочитай текст документа и верни краткий дайджест 600-800 символов "
    "строго в открывающем и закрывающем TEXT-маркерах"
)
TEXT_MARKERS = re.compile(r"<TEXT>(.*?)</TEXT>", re.S)

OCR_TIMEOUT = 300
OCR_ERROR = "не удалось распознать текст на фото"
OCR_PROMPT = (
    "Прочитай изображение %s и верни ВЕСЬ видимый текст "
    "строго в открывающем и закрывающем TEXT-маркерах"
)

MIME = {
    "txt": "text/plain",
    "md": "text/markdown",
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

IMAGE_MIME = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
    "bmp": "image/bmp",
    "tif": "image/tiff",
    "tiff": "image/tiff",
    "heic": "image/heic",
    "heif": "image/heif",
    "svg": "image/svg+xml",
}
DEFAULT_IMAGE_MIME = "image/jpeg"


class TelegramError(Exception):
    """Telegram API/network failure, mapped to an HTTP status."""

    def __init__(self, message, code=502):
        super().__init__(message)
        self.message = message
        self.code = code


class UnsupportedType(Exception):
    pass


class ExtractionNotConfigured(Exception):
    pass


def _file_ext(name):
    return os.path.splitext(name or "")[1].lower().lstrip(".")


def _tmp_path(ext, prefix="hermes-doc-"):
    stamp = "%d-%d" % (int(time.time()), os.getpid())
    return os.path.join(tempfile.gettempdir(), "%s%s.%s" % (prefix, stamp, ext))


def _want_digest(value):
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes")
    return bool(value)


def _telegram_get_file(token, file_id):
    qs = urllib.parse.urlencode({"file_id": file_id})
    url = "https://api.telegram.org/bot%s/getFile?%s" % (token, qs)
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        code = 400 if e.code in (400, 404) else 502
        raise TelegramError("telegram getFile failed (HTTP %d): %s" % (e.code, e.reason), code)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise TelegramError("telegram unreachable: %s" % e, 502)
    except ValueError as e:
        raise TelegramError("telegram bad response: %s" % e, 502)
    if not data.get("ok"):
        raise TelegramError(
            "telegram getFile failed: %s" % data.get("description", "unknown error"), 400
        )
    try:
        return data["result"]["file_path"]
    except (KeyError, TypeError):
        raise TelegramError("telegram getFile: missing file_path", 502)


def _telegram_download(token, file_path, tmp_path):
    url = "https://api.telegram.org/file/bot%s/%s" % (token, file_path.lstrip("/"))
    try:
        with urllib.request.urlopen(url, timeout=60) as resp, open(tmp_path, "wb") as out:
            shutil.copyfileobj(resp, out)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise TelegramError("telegram file not found (HTTP 404)", 400)
        raise TelegramError("telegram download failed (HTTP %d)" % e.code, 502)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise TelegramError("telegram download failed: %s" % e, 502)


def _extract_text(path, ext):
    if ext in ("txt", "md"):
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    if ext == "pdf":
        try:
            import pypdf
        except ImportError:
            raise ExtractionNotConfigured("doc extraction not configured: pypdf missing")
        reader = pypdf.PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if ext == "docx":
        try:
            import docx
        except ImportError:
            raise ExtractionNotConfigured(
                "doc extraction not configured: python-docx missing"
            )
        document = docx.Document(path)
        return "\n".join(p.text for p in document.paragraphs)
    raise UnsupportedType("unsupported type")


def _hermes_digest(text):
    env = dict(os.environ)
    env["HERMES_HOME"] = HERMES_HOME
    env["PATH"] = "/home/ubuntu/.local/bin:" + env.get("PATH", "")
    prompt = DIGEST_PROMPT + "\n\n" + text
    cmd = [HERMES_BIN, "chat", "-q", prompt, "--cli", "-Q", "--reasoning", "none"]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=DIGEST_TIMEOUT, env=env
    )
    return proc.stdout


def _image_mime(ext):
    return IMAGE_MIME.get(ext, DEFAULT_IMAGE_MIME)


TEXT_MARKERS_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```")


def _normalize_json_answer(answer):
    """json-builder seam: strip markdown fences / prose around a JSON object.

    Гарантирует строгий JSON без обрамляющих markdown-блоков на выходе /ask.
    Возвращает исходную строку, если JSON не извлекается (парсит бот).
    """
    if not answer:
        return answer
    t = answer.strip()
    m = TEXT_MARKERS_JSON_FENCE.search(t)
    if m:
        inner = m.group(1).strip()
        try:
            json.loads(inner)
            return inner
        except ValueError:
            pass
    start = t.find("{")
    if start >= 0:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(t)):
            c = t[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    cand = t[start:i + 1]
                    try:
                        json.loads(cand)
                        return cand
                    except ValueError:
                        break
    return answer


def _hermes_ocr_image(tmp_path):
    """Ask hermes (vision) to OCR the image; return raw stdout (may raise)."""
    env = dict(os.environ)
    env["HERMES_HOME"] = HERMES_HOME
    env["PATH"] = "/home/ubuntu/.local/bin:" + env.get("PATH", "")
    prompt = OCR_PROMPT % tmp_path
    cmd = [HERMES_BIN, "chat", "-q", prompt, "--cli", "-Q", "--reasoning", "none"]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=OCR_TIMEOUT, env=env
    )
    return proc.stdout


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
        if self.path == "/ask":
            self._do_ask()
            return
        if self.path == "/doc-text":
            self._do_doc_text()
            return
        if self.path == "/img-text":
            self._do_img_text()
            return
        self._send(404, {"error": "not found"})

    def _do_ask(self):
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
            # Рассуждения (reasoning) в режиме -Q попадают в stdout и ломают
            # парсинг ответа (Exp Parse в shorts берёт первую пару <SCRIPT>...</SCRIPT>,
            # а reasoning LLM упоминает эти теги → «garbage»). Все скиллы отдают
            # чистый ответ: reasoning подавляем (промпты и так требуют чистый вывод).
            cmd += ["--reasoning", "none"]
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300, env=env
            )
            answer = proc.stdout.strip()
            if skill == "json-builder":
                # шов строгого JSON: снять markdown-обёртку, если LLM её добавил
                answer = _normalize_json_answer(answer)
            self._send(200, {
                "answer": answer,
                "stderr": proc.stderr.strip(),
                "returncode": proc.returncode,
            })
        except subprocess.TimeoutExpired:
            self._send(500, {"error": "hermes timeout after 300s"})
        except FileNotFoundError:
            self._send(500, {"error": "hermes binary not found"})
        except Exception as e:
            self._send(500, {"error": "hermes error: %s" % e})

    def _do_doc_text(self):
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
        file_id = data.get("file_id")
        file_name = data.get("file_name")
        if not isinstance(file_id, str) or not file_id.strip():
            self._send(400, {"error": "missing file_id"})
            return
        if not isinstance(file_name, str) or not file_name.strip():
            self._send(400, {"error": "missing file_name"})
            return
        ext = _file_ext(file_name)
        if ext not in MIME:
            self._send(400, {"error": "unsupported type"})
            return
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not token:
            self._send(503, {"error": "telegram not configured"})
            return
        tmp_path = None
        try:
            try:
                file_path = _telegram_get_file(token, file_id)
                tmp_path = _tmp_path(ext)
                _telegram_download(token, file_path, tmp_path)
            except TelegramError as e:
                self._send(e.code, {"error": e.message})
                return
            try:
                text = _extract_text(tmp_path, ext)
            except UnsupportedType as e:
                self._send(400, {"error": str(e)})
                return
            except ExtractionNotConfigured as e:
                self._send(503, {"error": str(e)})
                return
            except Exception as e:
                self._send(400, {"error": "extraction failed: %s" % e})
                return
        finally:
            if tmp_path:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
        text = text[:TEXT_LIMIT]
        result = {
            "name": file_name,
            "mime": MIME[ext],
            "text": text,
            "chars": len(text),
            "digested": False,
        }
        if _want_digest(data.get("digest")):
            try:
                out = _hermes_digest(text)
                m = TEXT_MARKERS.search(out or "")
                if m:
                    result["text"] = m.group(1).strip()
                    result["digested"] = True
                else:
                    result["text"] = text[:DIGEST_FALLBACK_LIMIT]
            except Exception:
                result["text"] = text[:DIGEST_FALLBACK_LIMIT]
            result["chars"] = len(result["text"])
        self._send(200, result)

    def _do_img_text(self):
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
        if not isinstance(data, dict):
            self._send(400, {"error": "bad request: JSON object expected"})
            return
        file_id = data.get("file_id")
        file_name = data.get("file_name")
        if not isinstance(file_id, str) or not file_id.strip():
            self._send(400, {"error": "missing file_id"})
            return
        if not isinstance(file_name, str) or not file_name.strip():
            self._send(400, {"error": "missing file_name"})
            return
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not token:
            self._send(503, {"error": "telegram not configured"})
            return
        tmp_path = None
        try:
            try:
                file_path = _telegram_get_file(token, file_id)
                tmp_path = _tmp_path(_file_ext(file_name), prefix="hermes-img-")
                _telegram_download(token, file_path, tmp_path)
            except TelegramError as e:
                self._send(e.code, {"error": e.message})
                return
            try:
                out = _hermes_ocr_image(tmp_path)
            except subprocess.TimeoutExpired:
                self._send(502, {"error": OCR_ERROR + ": hermes timeout"})
                return
            except FileNotFoundError:
                self._send(502, {"error": OCR_ERROR + ": hermes binary not found"})
                return
            except Exception as e:
                self._send(502, {"error": OCR_ERROR + ": %s" % e})
                return
            m = TEXT_MARKERS.search(out or "")
            if not m:
                self._send(502, {"error": OCR_ERROR + ": no TEXT markers in hermes output"})
                return
            text = m.group(1).strip()
            if not text:
                self._send(502, {"error": OCR_ERROR + ": empty TEXT markers"})
                return
        finally:
            if tmp_path:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
        text = text[:TEXT_LIMIT]
        self._send(200, {
            "name": file_name,
            "mime": _image_mime(_file_ext(file_name)),
            "text": text,
            "chars": len(text),
        })


def main():
    port = int(os.environ.get("HERMES_BRIDGE_PORT", "8642"))
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    srv.daemon_threads = True
    print("hermes-bridge listening on 0.0.0.0:%d" % port, flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
