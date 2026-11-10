"""Dev-Toolbox entry: run the Key Manager web server (stdlib only, 127.0.0.1).

Usage: python web_server.py [--port 8730] [--open-browser] [--parent-pid <pid>] [--data-dir <path>]
The pywebview desktop app stays available via run_windows.bat / key-manager.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from key_manager.web.server import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
