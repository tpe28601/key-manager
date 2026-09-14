from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from key_manager.metadata import APP_NAME, APP_VERSION_LABEL
from .api_beta3 import KeyManagerApi


def _static_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "key_manager" / "web" / "static"  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent / "static"


def run() -> None:
    try:
        import webview
    except ImportError as exc:
        raise SystemExit("pywebview is not installed. Run: pip install -e .") from exc

    holder: dict[str, Any] = {"window": None}
    api = KeyManagerApi(window_getter=lambda: holder["window"])
    index = (_static_dir() / "index.html").resolve()
    window = webview.create_window(
        f"{APP_NAME} {APP_VERSION_LABEL}",
        url=index.as_uri(),
        js_api=api,
        width=1180,
        height=760,
        min_size=(1000, 650),
        resizable=True,
        text_select=True,
    )
    holder["window"] = window
    webview.start(debug=False, private_mode=True)
