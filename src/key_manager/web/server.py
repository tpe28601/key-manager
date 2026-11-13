r"""Key Manager - local HTTP server (Dev-Toolbox web mode, TOOL-SPEC v1).

Pure stdlib (ThreadingHTTPServer), binds 127.0.0.1 only. The pywebview desktop
app (launcher.py) is unchanged; this server exposes the same KeyManagerApi to
the bundled UI through a small JSON bridge (see static/web-adapter.js).

Usage:
    python web_server.py [--port 8730] [--open-browser] [--parent-pid <pid>] [--data-dir <path>] [--hub-origin <url>]

- Without --port: tries 8730..8750, then asks the OS for any free port (TOOL-SPEC 3).
- Prints "READY http://127.0.0.1:<port>" on stdout once listening (TOOL-SPEC 5).
- Exits when the parent process (Dev-Toolbox Hub) goes away.
- Settings live in --data-dir > %DEVTOOLBOX_DATA%\key-manager >
  %LOCALAPPDATA%\DevToolbox\key-manager; the legacy %LOCALAPPDATA%\KeyManager\
  settings.json is copied over on first run (never deleted).
"""

from __future__ import annotations

import argparse
import errno
import json
import os
import re
from pathlib import Path
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from key_manager import settings
from key_manager.metadata import APP_NAME, APP_VERSION
from key_manager.web.api_beta3 import KeyManagerApi

TOOL_ID = "key-manager"
DEFAULT_PORT = 8730
MAX_PORT_SCAN = 20
HUB_ORIGINS = ("http://127.0.0.1:8700", "http://localhost:8700")
MAX_BODY_BYTES = 1 * 1024 * 1024

STATIC_FILES = {
    "/app.css": ("app.css", "text/css; charset=utf-8"),
    "/beta3.css": ("beta3.css", "text/css; charset=utf-8"),
    "/beta4.css": ("beta4.css", "text/css; charset=utf-8"),
    "/beta5.css": ("beta5.css", "text/css; charset=utf-8"),
    "/icons.js": ("icons.js", "application/javascript; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
    "/beta3.js": ("beta3.js", "application/javascript; charset=utf-8"),
    "/web-adapter.js": ("web-adapter.js", "application/javascript; charset=utf-8"),
    "/web-embedded.css": ("web-embedded.css", "text/css; charset=utf-8"),
    "/ui-kit.css": ("ui-kit.css", "text/css; charset=utf-8"),
    "/tb-theme.js": ("tb-theme.js", "application/javascript; charset=utf-8"),
    "/tb-icons.js": ("tb-icons.js", "application/javascript; charset=utf-8"),
    "/tb-dirpicker.js": ("tb-dirpicker.js", "application/javascript; charset=utf-8"),
    "/tb-standalone-update.js": ("tb-standalone-update.js", "application/javascript; charset=utf-8"),
}
ADAPTER_TAG = '<script src="web-adapter.js"></script>'
INDEX_MARKER = '<script src="icons.js">'

CSP_HTML_BASE = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "connect-src 'self'; base-uri 'none'; form-action 'none'; "
)
HUB_ORIGIN_RE = re.compile(r"^http://(127\.0\.0\.1|localhost):(\d{1,5})$")


def hub_origins_from(value: str | None) -> tuple[str, ...]:
    """--hub-origin http://127.0.0.1:<p> -> both loopback spellings; otherwise the 8700 default."""
    m = HUB_ORIGIN_RE.match((value or "").strip().lower())
    if not m:
        return HUB_ORIGINS
    return (f"http://127.0.0.1:{m.group(2)}", f"http://localhost:{m.group(2)}")


class LocalServer(ThreadingHTTPServer):
    # On Windows SO_REUSEADDR lets a second socket bind a port that is already
    # listening, which would defeat the "find a free port" scan.
    allow_reuse_address = os.name != "nt"


class SpecError(Exception):
    """Request-level error carrying an HTTP status and TOOL-SPEC error code."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


# ---------------- data dir (TOOL-SPEC section 6) ----------------

def resolve_data_dir(override: str | None) -> Path:
    if override:
        data_dir = Path(override).expanduser().resolve()
    elif os.environ.get("DEVTOOLBOX_DATA", "").strip():
        data_dir = Path(os.environ["DEVTOOLBOX_DATA"].strip()) / TOOL_ID
    elif os.environ.get("LOCALAPPDATA", "").strip():
        data_dir = Path(os.environ["LOCALAPPDATA"].strip()) / "DevToolbox" / TOOL_ID
    else:
        data_dir = Path(os.environ.get("TEMP", str(Path.home()))) / "DevToolbox" / TOOL_ID
    data_dir.mkdir(parents=True, exist_ok=True)
    new_settings = data_dir / "settings.json"
    if not new_settings.exists():
        legacy = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / settings.APP_SETTINGS_DIR / settings.SETTINGS_FILE
        if legacy.is_file():
            try:
                new_settings.write_bytes(legacy.read_bytes())
            except OSError:
                pass
    settings.set_settings_dir(data_dir)
    return data_dir


# ---------------- api bridge ----------------

def build_api_map(managed: bool = False) -> dict:
    api = KeyManagerApi(window_getter=lambda: None)
    methods = {}
    for name in dir(api):
        if name.startswith("_") or (managed and name in {"check_update", "open_update"}):
            continue
        attr = getattr(api, name)
        if callable(attr):
            methods[name] = attr
    return methods


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "KeyManagerWeb/" + APP_VERSION
    timeout = 30  # idle keep-alive connections must not pin handler threads

    # shared state installed by main()
    port: int = DEFAULT_PORT
    api_map: dict = {}
    data_dir: Path = Path(".")
    started_at: float = 0.0
    shutdown_hook = None
    hub_origins: tuple[str, ...] = HUB_ORIGINS

    def log_message(self, fmt, *args):  # keep stdout clean (READY line contract)
        pass

    # ---- response helpers ----
    def _send(self, status: int, ctype: str, body: bytes, html: bool = False) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        ancestors = "frame-ancestors " + " ".join(["'self'", *self.hub_origins])
        self.send_header("Content-Security-Policy", CSP_HTML_BASE + ancestors if html else ancestors)
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_json(self, obj, status: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
        self._send(status, "application/json; charset=utf-8", body)

    def _send_error_json(self, status: int, code: str, message: str) -> None:
        # Force connection close on error paths so an unconsumed request body
        # can never desynchronise a pooled keep-alive connection.
        self.close_connection = True
        self._send_json({"ok": False, "error": {"code": code, "message": message, "detail": None}}, status)

    # ---- security (TOOL-SPEC section 5) ----
    def _check_allowed(self) -> bool:
        host = (self.headers.get("Host") or "").lower()
        if host not in (f"127.0.0.1:{self.port}", f"localhost:{self.port}"):
            self._send_error_json(403, "FORBIDDEN_HOST", f"不允許的 Host：{host}")
            return False
        method = self.command.upper()
        if method in ("GET", "HEAD"):
            return True
        if method != "POST":
            self._send_error_json(405, "METHOD_NOT_ALLOWED", f"不支援的方法：{method}")
            return False
        # Drain the body first (bounded): every later reject must leave the
        # stream positioned at the next request line.
        try:
            size = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            size = -1
        if size < 0 or size > MAX_BODY_BYTES:
            self._send_error_json(413, "PAYLOAD_TOO_LARGE", "請求內容超過 1 MB 或缺少 Content-Length")
            return False
        self._body_raw = self.rfile.read(size) if size else b""
        if self.headers.get("X-Toolbox-Request") != "1":
            self._send_error_json(403, "MISSING_TOOLBOX_HEADER", "缺少 X-Toolbox-Request 標頭")
            return False
        origin = (self.headers.get("Origin") or "").lower()
        if origin:
            allowed = {f"http://127.0.0.1:{self.port}", f"http://localhost:{self.port}", *self.hub_origins}
            if origin not in allowed:
                self._send_error_json(403, "FORBIDDEN_ORIGIN", f"不允許的來源：{origin}")
                return False
        ctype = (self.headers.get("Content-Type") or "").lower()
        if not ctype.startswith("application/json"):
            self._send_error_json(415, "UNSUPPORTED_MEDIA_TYPE", "Content-Type 必須是 application/json")
            return False
        return True

    def _read_json_body(self) -> dict:
        raw = getattr(self, "_body_raw", b"") or b""
        if not raw.strip():
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SpecError(400, "BAD_JSON", f"JSON 格式錯誤：{exc}") from exc
        if not isinstance(data, dict):
            raise SpecError(400, "BAD_ARGS", "請求本體必須是 JSON 物件")
        return data

    # ---- routes ----
    def do_GET(self) -> None:  # noqa: N802
        try:
            if not self._check_allowed():
                return
            path = self.path.split("?", 1)[0]
            if path == "/api/health":
                self._send_json({
                    "ok": True, "id": TOOL_ID, "version": APP_VERSION,
                    "pid": os.getpid(), "port": self.port,
                    "uptimeSec": int(time.time() - self.started_at),
                })
                return
            if path == "/api/info":
                self._send_json({
                    "ok": True,
                    "tool": {
                        "id": TOOL_ID, "name": APP_NAME, "version": APP_VERSION,
                        "description": "SSH & GPG Key Manager",
                    },
                    "dataDir": str(self.data_dir),
                })
                return
            if path in ("/", "/index.html"):
                html = (self.static_dir / "index.html").read_text(encoding="utf-8")
                if ADAPTER_TAG not in html:
                    html = html.replace(INDEX_MARKER, ADAPTER_TAG + "\n  " + INDEX_MARKER, 1)
                body = html.encode("utf-8")
                self._send(200, "text/html; charset=utf-8", body, html=True)
                return
            if path == "/favicon.ico":
                self._send(204, "image/x-icon", b"")
                return
            entry = STATIC_FILES.get(path)
            if entry:
                self._send(200, entry[1], (self.static_dir / entry[0]).read_bytes())
                return
            self._send_error_json(404, "NOT_FOUND", f"未知路徑：{path}")
        except BrokenPipeError:
            pass
        except Exception as exc:  # never leak a stack trace into the socket
            try:
                self._send_error_json(500, "INTERNAL", str(exc))
            except Exception:
                pass

    def do_POST(self) -> None:  # noqa: N802
        try:
            if not self._check_allowed():
                return
            path = self.path.split("?", 1)[0]
            if not path.startswith("/api/"):
                self._send_error_json(404, "NOT_FOUND", f"未知路徑：{path}")
                return
            name = path[len("/api/"):]
            if name == "shutdown":
                self._read_json_body()
                self._send_json({"ok": True, "result": {"closing": True}})
                if self.shutdown_hook:
                    threading.Thread(target=self.shutdown_hook, daemon=True).start()
                return
            method = self.api_map.get(name)
            if method is None:
                self._send_error_json(404, "METHOD_NOT_FOUND", f"未知的 API 方法：{name}")
                return
            body = self._read_json_body()
            args = body.get("args", [])
            if not isinstance(args, list):
                raise SpecError(400, "BAD_ARGS", "args 必須是陣列")
            try:
                result = method(*args)
            except TypeError as exc:
                raise SpecError(400, "BAD_ARGS", f"參數不正確：{exc}") from exc
            self._send_json(result if isinstance(result, dict) else {"ok": True, "result": result})
        except SpecError as exc:
            self._send_error_json(exc.status, exc.code, exc.message)
        except BrokenPipeError:
            pass
        except Exception as exc:
            try:
                self._send_error_json(500, "INTERNAL", str(exc))
            except Exception:
                pass

    # do_HEAD behaves like GET without a body (handled via self.command check)
    do_HEAD = do_GET


# ---------------- parent-pid watchdog ----------------

def _parent_alive(pid: int) -> bool:
    if os.name == "nt":
        import ctypes

        STILL_ACTIVE = 259
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def watch_parent(pid: int) -> None:
    while True:
        time.sleep(1.0)
        if not _parent_alive(pid):
            print("Parent process exited, closing.", flush=True)
            os._exit(0)


# ---------------- main ----------------

def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description="Key Manager local web server (127.0.0.1 only)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--open-browser", action="store_true")
    parser.add_argument("--parent-pid", type=int, default=0)
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--hub-origin", default=None)
    args = parser.parse_args(argv)
    port_explicit = any(a == "--port" or a.startswith("--port=") for a in argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    data_dir = resolve_data_dir(args.data_dir)
    static_dir = Path(__file__).resolve().parent / "static"
    for needed in ("index.html", "app.js", "web-adapter.js"):
        if not (static_dir / needed).is_file():
            print(f"missing static asset: {needed}", file=sys.stderr)
            return 1

    if args.parent_pid > 0 and not _parent_alive(args.parent_pid):
        print(f"parent process {args.parent_pid} not running, exiting", file=sys.stderr)
        return 1

    # explicit --port: only that one; otherwise default..+20, then port 0 (OS picks a free one)
    candidates = [args.port] if port_explicit else list(range(args.port, args.port + MAX_PORT_SCAN + 1)) + [0]
    httpd = None
    last_error: OSError | None = None
    reserved = in_use = 0
    for port in candidates:
        try:
            httpd = LocalServer(("127.0.0.1", port), Handler)
            break
        except OSError as exc:
            last_error = exc
            code = getattr(exc, "winerror", None) or exc.errno
            if code in (10013, errno.EACCES):
                reserved += 1
            elif code in (10048, errno.EADDRINUSE):
                in_use += 1
    if httpd is None:
        if reserved and not in_use:
            why = "port 被 Windows 保留（Hyper-V／WSL／Docker 常見），可用 netsh interface ipv4 show excludedportrange protocol=tcp 查看"
        elif in_use and not reserved:
            why = "port 已被其他程式佔用"
        else:
            why = str(last_error)
        print(f"無法監聽 127.0.0.1:{candidates[0]}：{why}", file=sys.stderr)
        return 5

    bound_port = httpd.server_address[1]
    Handler.port = bound_port
    Handler.hub_origins = hub_origins_from(args.hub_origin)
    Handler.api_map = build_api_map(managed=bool(args.parent_pid))
    Handler.data_dir = data_dir
    Handler.started_at = time.time()
    Handler.static_dir = static_dir
    httpd.daemon_threads = True

    def _shutdown() -> None:
        # /api/shutdown means "close now": release the listening socket once
        # the response has flushed, then exit. (ThreadingHTTPServer.shutdown()
        # proved unreliable when called from a handler thread on 3.14.)
        time.sleep(0.3)
        try:
            httpd.server_close()
        except Exception:
            pass
        os._exit(0)

    # staticmethod: a bare function in a class attribute would get bound as a
    # method and receive the handler instance as first argument.
    Handler.shutdown_hook = staticmethod(_shutdown)

    print(f"READY http://127.0.0.1:{bound_port}", flush=True)
    if args.open_browser:
        import webbrowser

        webbrowser.open(f"http://127.0.0.1:{bound_port}")
    if args.parent_pid > 0:
        threading.Thread(target=watch_parent, args=(args.parent_pid,), daemon=True).start()

    try:
        httpd.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0
