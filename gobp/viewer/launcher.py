"""GoBP Graph Viewer Launcher.

Reads projects.json from repo root, starts HTTP server,
opens browser to project picker page.

Usage:
    python -m gobp.viewer.launcher
    python -m gobp.viewer.launcher --port 8080
    python -m gobp.viewer.launcher --projects /path/to/projects.json
"""

from __future__ import annotations

import argparse
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


def find_projects_json() -> Path | None:
    """Find projects.json — check repo root, cwd, user home."""
    candidates = [
        Path(__file__).parent.parent.parent / "projects.json",  # repo root
        Path.cwd() / "projects.json",
        Path.home() / ".gobp" / "projects.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def main() -> int:
    parser = argparse.ArgumentParser(prog="gobp.viewer.launcher")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--projects", default=None, help="Path to projects.json")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    # Find projects.json
    if args.projects:
        projects_path = Path(args.projects)
    else:
        projects_path = find_projects_json()

    if not projects_path or not projects_path.exists():
        # Create default projects.json
        projects_path = Path.cwd() / "projects.json"
        import json

        default = [{"name": "Current Project", "root": str(Path.cwd()), "description": ""}]
        projects_path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        _safe_print(f"Created default projects.json at {projects_path}")

    from gobp.viewer.server import run_server_with_projects

    url = f"http://localhost:{args.port}"
    _safe_print("◈ GoBP Graph Viewer")
    _safe_print(f"  Projects: {projects_path}")
    _safe_print(f"  URL:      {url}")
    _safe_print("\nPress Ctrl+C to stop.")

    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    run_server_with_projects(projects_path=projects_path, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
