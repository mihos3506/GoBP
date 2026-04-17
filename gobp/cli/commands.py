"""GoBP command-line interface.

Usage:
    python -m gobp.cli init [--name NAME] [--force]
    python -m gobp.cli seed-universal [--rewrite --confirm CEO] [--skip-id-groups]
    python -m gobp.cli validate [--scope SCOPE]
    python -m gobp.cli status

Uses GOBP_PROJECT_ROOT env var or current directory.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any


def _get_project_root() -> Path:
    """Get project root from env var or current directory."""
    env_root = os.environ.get("GOBP_PROJECT_ROOT")
    if env_root:
        return Path(env_root)
    return Path.cwd()


def cmd_init(args: argparse.Namespace) -> int:
    """Handle `gobp init` command."""
    from gobp.core.init import init_project

    root = _get_project_root()
    result = init_project(project_root=root, project_name=args.name, force=args.force)

    if result["ok"]:
        print(result["message"])
        seeded = result.get("seeded_nodes", [])
        print(f"Seeded {len(seeded)} universal nodes (TestKind + Concept)")
        print("\nCreated:")
        for path in result["created"]:
            print(f"  {path}")
        print(f"\nNext: set GOBP_PROJECT_ROOT={root} in your MCP client config.")
        return 0

    print(f"Error: {result['message']}", file=sys.stderr)
    return 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Handle `gobp validate` command."""
    from gobp.core.graph import GraphIndex
    from gobp.mcp.tools.maintain import validate

    root = _get_project_root()
    if not (root / ".gobp").exists():
        print(
            f"Error: No .gobp/ at {root}. Run `python -m gobp.cli init` first.",
            file=sys.stderr,
        )
        return 1

    if args.reindex:
        from gobp.core.db_config import is_postgres_available

        postgres_ready = is_postgres_available(root)
        if postgres_ready:
            print("Rebuilding PostgreSQL index...")
        else:
            print("Warning: PostgreSQL not available. Index rebuild skipped.")
            print("Set GOBP_DB_URL environment variable to enable PostgreSQL.")
        if postgres_ready:
            try:
                from gobp.core import db as _db

                index_for_rebuild = GraphIndex.load_from_disk(root)
                result = _db.rebuild_index(root, index_for_rebuild)
                print(f"  {result['message']}")
            except Exception as e:
                print(f"  Warning: reindex failed: {e}", file=sys.stderr)

    print(f"Validating {root}...")
    try:
        index = GraphIndex.load_from_disk(root)
    except Exception as e:
        print(f"Error loading graph: {e}", file=sys.stderr)
        return 1

    result = validate(index, root, {"scope": args.scope, "severity_filter": "all"})
    if not result["ok"] and "issues" not in result:
        print(f"Error: {result.get('error', 'unknown')}", file=sys.stderr)
        return 1

    issues = result.get("issues", [])
    hard = [i for i in issues if i.get("severity") == "hard"]
    warnings = [i for i in issues if i.get("severity") == "warning"]

    if not issues:
        print(
            f"Graph valid — {len(index.all_nodes())} nodes, {len(index.all_edges())} edges, 0 issues"
        )
        return 0

    print(f"Found {len(hard)} hard errors, {len(warnings)} warnings:\n")
    for issue in hard:
        nid = issue.get("node_id", issue.get("edge", "?"))
        print(f"  [ERROR] {nid}: {issue['message']}")
    for issue in warnings:
        nid = issue.get("node_id", issue.get("edge", "?"))
        print(f"  [WARN]  {nid}: {issue['message']}")
    return 1 if hard else 0


def cmd_status(args: argparse.Namespace) -> int:
    """Handle `gobp status` command."""
    import yaml

    from gobp.core.graph import GraphIndex

    root = _get_project_root()
    if not (root / ".gobp").exists():
        print(
            f"Error: No .gobp/ at {root}. Run `python -m gobp.cli init` first.",
            file=sys.stderr,
        )
        return 1

    config: dict[str, Any] = {}
    config_path = root / ".gobp" / "config.yaml"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    try:
        index = GraphIndex.load_from_disk(root)
        nodes = index.all_nodes()
        edges = index.all_edges()
    except Exception as e:
        print(f"Error loading graph: {e}", file=sys.stderr)
        return 1

    type_counts: dict[str, int] = {}
    for node in nodes:
        node_type = node.get("type", "Unknown")
        type_counts[node_type] = type_counts.get(node_type, 0) + 1

    sessions = sorted(
        [n for n in nodes if n.get("type") == "Session"],
        key=lambda s: s.get("updated", ""),
        reverse=True,
    )
    last = sessions[0] if sessions else None
    created_at = str(config.get("created_at", "?"))[:10]

    print(f"\nGoBP Project: {config.get('project_name', root.name)}")
    print(f"Root:         {root}")
    print(f"Schema:       v{config.get('schema_version', '?')}  |  Created: {created_at}")
    print(f"\nGraph: {len(nodes)} nodes, {len(edges)} edges")
    for node_type, count in sorted(type_counts.items()):
        print(f"  {node_type}: {count}")
    if last:
        print(f"\nLast session: {last.get('id', '?')}")
        print(f"  Goal:   {last.get('goal', '?')[:60]}")
        print(f"  Status: {last.get('status', '?')}  Actor: {last.get('actor', '?')}")
    else:
        print("\nNo sessions yet.")
    print()
    return 0


def cmd_seed_universal(args: argparse.Namespace) -> int:
    """Restore canonical TestKind + Concept node files (and optionally id_groups)."""
    from gobp.core.id_config import merge_id_groups_with_defaults
    from gobp.core.init import seed_universal_nodes, sync_config_schema_version

    root = _get_project_root()
    if not (root / ".gobp").exists():
        print(
            f"Error: No .gobp/ at {root}. Run `python -m gobp.cli init` first.",
            file=sys.stderr,
        )
        return 1

    if not args.skip_id_groups:
        mg = merge_id_groups_with_defaults(root)
        if not mg.get("ok"):
            print(mg.get("error", "id_groups merge failed"), file=sys.stderr)
            return 1
        print(f"id_groups: merged defaults (config changed={mg.get('changed')})")

    if args.rewrite:
        if args.confirm != "CEO":
            print(
                "Error: --rewrite overwrites all seed files. Re-run with --confirm CEO "
                "(human approval gate).",
                file=sys.stderr,
            )
            return 1
        only_missing = False
    else:
        only_missing = True

    out = seed_universal_nodes(root, only_missing=only_missing)
    created = out.get("created", [])
    skipped = out.get("skipped", [])
    preview = ", ".join(created[:8])
    if len(created) > 8:
        preview += ", ..."
    print(f"seed-universal: wrote {len(created)} file(s){(' — ' + preview) if created else ''}")
    print(f"seed-universal: skipped {len(skipped)} existing file(s)")

    if not getattr(args, "skip_schema_version", False):
        sv = sync_config_schema_version(root)
        if not sv.get("ok"):
            print(sv.get("error", "schema_version sync failed"), file=sys.stderr)
            return 1
        print(
            f"config schema_version: changed={sv.get('changed')}"
            + (f" ({sv.get('previous')} → {sv.get('set_to')})" if sv.get("changed") else "")
        )
    return 0


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(prog="gobp", description="GoBP CLI")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    p_init = sub.add_parser("init", help="Initialize a new GoBP project")
    p_init.add_argument("--name", default=None)
    p_init.add_argument("--force", action="store_true")
    p_init.set_defaults(func=cmd_init)

    p_val = sub.add_parser("validate", help="Validate graph schema")
    p_val.add_argument(
        "--scope",
        choices=["all", "nodes", "edges", "references"],
        default="all",
    )
    p_val.add_argument(
        "--reindex",
        action="store_true",
        help="Rebuild SQLite index from scratch before validating",
    )
    p_val.set_defaults(func=cmd_validate)

    p_stat = sub.add_parser("status", help="Show project summary")
    p_stat.set_defaults(func=cmd_status)

    p_seed = sub.add_parser(
        "seed-universal",
        help="Restore canonical TestKind + Concept seeds (after DB/file cleanup)",
    )
    p_seed.add_argument(
        "--rewrite",
        action="store_true",
        help="Overwrite every built-in seed file (requires --confirm CEO)",
    )
    p_seed.add_argument(
        "--confirm",
        default="",
        metavar="TEXT",
        help="Must be exactly CEO when using --rewrite",
    )
    p_seed.add_argument(
        "--skip-id-groups",
        action="store_true",
        help="Skip merging default id_groups into .gobp/config.yaml",
    )
    p_seed.add_argument(
        "--skip-schema-version",
        action="store_true",
        help="Do not bump .gobp/config.yaml schema_version to packaged baseline",
    )
    p_seed.set_defaults(func=cmd_seed_universal)

    args = parser.parse_args()
    return args.func(args)
