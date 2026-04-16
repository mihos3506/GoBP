"""Migration script: old IDs -> new group-namespaced IDs.

Migrates .gobp/nodes/*.md files to use new external ID format.
Creates ID mapping file for backward compatibility.
Updates all edges to use new IDs.

Usage:
    python -m gobp.core.migrate_ids --root D:/GoBP --dry-run
    python -m gobp.core.migrate_ids --root D:/GoBP
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml


def _load_node_file(path: Path) -> dict[str, Any]:
    """Load node from markdown file with YAML front-matter."""
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        return {}
    end = content.find("\n---\n", 4)
    if end == -1:
        return {}
    fm_text = content[4:end]
    return yaml.safe_load(fm_text) or {}


def _write_node_file(path: Path, node: dict[str, Any], body: str = "") -> None:
    """Write node back to markdown file."""
    fm = yaml.safe_dump(node, allow_unicode=True, default_flow_style=False)
    content = f"---\n{fm}---\n{body}"
    path.write_text(content, encoding="utf-8")


def _needs_migration(node_id: str, node_name: str = "", node_type: str = "") -> bool:
    """Check if ID needs migration to new format."""
    from gobp.core.id_config import make_id_slug, parse_external_id, get_type_prefix

    if ":" in node_id:
        return True

    parsed = parse_external_id(node_id)
    if parsed["format"] == "new":
        current_slug = parsed.get("slug", "")
        default_slug = get_type_prefix(node_type or "Node")
        if current_slug and current_slug != default_slug:
            return False
        if node_name:
            expected_slug = make_id_slug(node_name)
            if expected_slug and expected_slug != current_slug:
                return True

    return False


def migrate_project(gobp_root: Path, dry_run: bool = True) -> dict[str, Any]:
    """Migrate all nodes in a project to new ID format.

    Returns:
        {migrated, skipped, errors, id_mapping}
    """
    from gobp.core.id_config import generate_external_id, load_groups

    nodes_dir = gobp_root / ".gobp" / "nodes"
    edges_dir = gobp_root / ".gobp" / "edges"

    if not nodes_dir.exists():
        return {"migrated": 0, "skipped": 0, "errors": [], "id_mapping": {}}

    groups = load_groups(gobp_root)
    id_mapping: dict[str, str] = {}
    migrated = 0
    skipped = 0
    errors: list[str] = []

    node_files = list(nodes_dir.glob("**/*.md"))
    for node_file in sorted(node_files):
        try:
            node = _load_node_file(node_file)
            old_id = node.get("id", "")
            if not old_id:
                errors.append(f"{node_file.name}: no id field")
                continue

            node_name = str(node.get("name", ""))
            node_type = str(node.get("type", "Node"))
            if not _needs_migration(old_id, node_name=node_name, node_type=node_type):
                skipped += 1
                id_mapping[old_id] = old_id
                continue

            testkind = str(node.get("kind_id", ""))
            new_id = generate_external_id(
                node_type,
                name=node_name,
                testkind=testkind,
                gobp_root=gobp_root,
                groups=groups,
            )
            id_mapping[old_id] = new_id
        except Exception as e:
            errors.append(f"{node_file.name}: {e}")

    if dry_run:
        return {
            "migrated": len([v for k, v in id_mapping.items() if k != v]),
            "skipped": skipped,
            "errors": errors,
            "id_mapping": id_mapping,
            "dry_run": True,
        }

    for node_file in node_files:
        try:
            content = node_file.read_text(encoding="utf-8")
            node = _load_node_file(node_file)
            old_id = node.get("id", "")

            if old_id not in id_mapping or id_mapping[old_id] == old_id:
                continue

            new_id = id_mapping[old_id]
            node["id"] = new_id
            node["legacy_id"] = old_id

            body = ""
            if content.startswith("---\n"):
                end = content.find("\n---\n", 4)
                if end != -1:
                    body = content[end + 5 :]

            _write_node_file(node_file, node, body)

            new_filename = new_id.replace(".", "_").replace(":", "_") + ".md"
            new_path = node_file.parent / new_filename
            if new_path != node_file:
                node_file.rename(new_path)

            migrated += 1
        except Exception as e:
            errors.append(f"{node_file.name}: {e}")

    if edges_dir.exists():
        for edge_file in edges_dir.glob("**/*.yaml"):
            try:
                edges = yaml.safe_load(edge_file.read_text(encoding="utf-8")) or []
                updated = False
                for edge in edges:
                    old_from = edge.get("from", "")
                    old_to = edge.get("to", "")
                    if old_from in id_mapping and id_mapping[old_from] != old_from:
                        edge["from"] = id_mapping[old_from]
                        edge["legacy_from"] = old_from
                        updated = True
                    if old_to in id_mapping and id_mapping[old_to] != old_to:
                        edge["to"] = id_mapping[old_to]
                        edge["legacy_to"] = old_to
                        updated = True
                if updated:
                    edge_file.write_text(
                        yaml.safe_dump(edges, allow_unicode=True, default_flow_style=False),
                        encoding="utf-8",
                    )
            except Exception as e:
                errors.append(f"edge {edge_file.name}: {e}")

    mapping_file = gobp_root / ".gobp" / "id_mapping.json"
    mapping_file.write_text(
        json.dumps(id_mapping, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return {
        "migrated": migrated,
        "skipped": skipped,
        "errors": errors,
        "id_mapping": id_mapping,
        "mapping_file": str(mapping_file),
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="gobp.core.migrate_ids")
    parser.add_argument("--root", required=True, help="Project root path")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    root = Path(args.root)
    print(f"{'DRY RUN: ' if args.dry_run else ''}Migrating {root}")

    result = migrate_project(root, dry_run=args.dry_run)

    print(f"Migrated: {result['migrated']}")
    print(f"Skipped:  {result['skipped']} (already new format)")
    print(f"Errors:   {len(result['errors'])}")
    if result["errors"]:
        for e in result["errors"][:10]:
            print(f"  ERROR: {e}")

    if not args.dry_run and result.get("mapping_file"):
        print(f"ID mapping saved: {result['mapping_file']}")

    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())


