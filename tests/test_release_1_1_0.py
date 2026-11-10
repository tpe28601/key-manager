"""v1.1.0 added the Dev-Toolbox web server (stdlib HTTP, TOOL-SPEC v1)."""

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def test_tool_manifest_matches_release():
    manifest = json.loads((ROOT / "tool.json").read_text(encoding="utf-8"))

    assert manifest["specVersion"] == 1
    assert manifest["id"] == "key-manager"
    assert manifest["version"] == "1.1.1"
    assert manifest["runtime"]["kind"] == "python"
    assert manifest["web"]["entry"] == "web_server.py"
    assert manifest["web"]["defaultPort"] == 8730
    assert manifest["web"]["health"] == "/api/health"
    assert "key-manager" in manifest["dataDir"]


def test_web_entry_and_server_exist():
    assert (ROOT / "web_server.py").is_file()
    server = (ROOT / "src" / "key_manager" / "web" / "server.py").read_text(encoding="utf-8")
    assert "READY http://127.0.0.1:" in server
    assert "X-Toolbox-Request" in server
    assert "FORBIDDEN_ORIGIN" in server


def test_web_adapter_bridges_pywebview_without_cdn():
    adapter = (ROOT / "src" / "key_manager" / "web" / "static" / "web-adapter.js").read_text(encoding="utf-8")
    assert "pywebviewready" in adapter
    assert "X-Toolbox-Request" in adapter
    assert "http://" not in adapter.replace("http://127.0.0.1", "")
    index = (ROOT / "src" / "key_manager" / "web" / "static" / "index.html").read_text(encoding="utf-8")
    assert "http://" not in index


def test_server_imports_without_cryptography(monkeypatch):
    """Web mode must run on a stdlib-only interpreter."""
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("cryptography"):
            raise ImportError("cryptography is not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    import importlib

    import key_manager.ssh.generation as generation

    importlib.reload(generation)
    assert callable(generation.generate_ssh_key)


def test_ui_kit_linked_and_served():
    """Dev-Toolbox design system: ui-kit.css copy lives next to the other static assets."""
    index = (ROOT / "src" / "key_manager" / "web" / "static" / "index.html").read_text(encoding="utf-8")
    assert '<link rel="stylesheet" href="ui-kit.css">' in index

    server = (ROOT / "src" / "key_manager" / "web" / "server.py").read_text(encoding="utf-8")
    assert '"/ui-kit.css"' in server

    manifest = json.loads((ROOT / "tool.json").read_text(encoding="utf-8"))
    assert manifest["uiKitTarget"] == "src/key_manager/web/static"
