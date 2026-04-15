"""GoBP 3D Graph Viewer — CLI entry point.

Usage:
    python -m gobp.viewer
    python -m gobp.viewer --root D:/MIHOS-v1
    python -m gobp.viewer --root D:/GoBP --port 8080

Opens browser automatically at http://localhost:8080
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import webbrowser
from pathlib import Path


def _safe_print(line: str) -> None:
    """Print Unicode text with ASCII fallback for limited consoles."""
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.replace("◈", "*"))


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="gobp.viewer",
        description="GoBP 3D Graph Viewer",
    )
    parser.add_argument(
        "--root",
        default=os.environ.get("GOBP_PROJECT_ROOT", str(Path.cwd())),
        help="Project root containing .gobp/ folder",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="HTTP server port (default: 8080)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open browser automatically",
    )
    args = parser.parse_args()

    project_root = Path(args.root).resolve()
    gobp_dir = project_root / ".gobp"

    if not gobp_dir.exists():
        print(
            f"Error: No .gobp/ folder at {project_root}",
            file=sys.stderr,
        )
        print(
            "Run `python -m gobp.cli init` first to initialize a GoBP project.",
            file=sys.stderr,
        )
        return 1

    from gobp.viewer.server import run_server

    url = f"http://localhost:{args.port}"
    _safe_print("◈ GoBP Graph Viewer")
    _safe_print(f"  Project: {project_root.name}")
    _safe_print(f"  Root:    {project_root}")
    _safe_print(f"  URL:     {url}")
    _safe_print("\nPress Ctrl+C to stop.")

    if not args.no_browser:
        # Open browser after short delay to let server start
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    run_server(project_root=project_root, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
