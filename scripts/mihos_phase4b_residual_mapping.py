"""Phase 4B residual semantic/schema mapping for MIHOS.

This script handles remaining known schema warnings conservatively:
- Session.name/priority -> handoff_notes
- Decision.name -> topic/what
- Flow.steps -> description
- Node.definition -> description, Node.phase -> tags
- Engine.note/query -> description/spec_source
- Concept.status -> tags
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex
from gobp.core.loader import load_schema, package_schema_dir
from gobp.core.mutator import update_node


def append_text(base: str, extra: str) -> str:
    base_clean = (base or "").strip()
    extra_clean = (extra or "").strip()
    if not extra_clean:
        return base_clean
    if extra_clean in base_clean:
        return base_clean
    if not base_clean:
        return extra_clean
    return f"{base_clean} {extra_clean}".strip()


def ensure_tag(node: dict[str, Any], tag: str) -> None:
    tags = node.get("tags")
    if not isinstance(tags, list):
        tags = []
    if tag not in tags:
        tags.append(tag)
    node["tags"] = tags


def normalize_steps(steps: Any) -> str:
    if isinstance(steps, list):
        return " -> ".join(str(s).strip() for s in steps if str(s).strip())
    if isinstance(steps, str):
        return steps.strip()
    if isinstance(steps, dict):
        parts = [f"{k}:{v}" for k, v in steps.items()]
        return " | ".join(parts).strip()
    return ""


def map_node(node: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    out = dict(node)
    changes: list[str] = []
    node_type = str(out.get("type", ""))

    if node_type == "Session":
        legacy_name = out.get("name")
        legacy_priority = out.get("priority")
        if isinstance(legacy_name, str) and legacy_name.strip():
            notes = str(out.get("handoff_notes", "") or "")
            out["handoff_notes"] = append_text(notes, f"[legacy_name] {legacy_name.strip()}")
            out.pop("name", None)
            changes.append("name->handoff_notes")
        if isinstance(legacy_priority, str) and legacy_priority.strip():
            notes = str(out.get("handoff_notes", "") or "")
            out["handoff_notes"] = append_text(notes, f"[legacy_priority] {legacy_priority.strip()}")
            out.pop("priority", None)
            changes.append("priority->handoff_notes")

    elif node_type == "Decision":
        legacy_name = out.get("name")
        if isinstance(legacy_name, str) and legacy_name.strip():
            if not str(out.get("topic", "")).strip():
                out["topic"] = legacy_name.strip()
                changes.append("name->topic")
            else:
                what = str(out.get("what", "") or "")
                out["what"] = append_text(what, f"[legacy_name] {legacy_name.strip()}")
                changes.append("name->what_append")
            out.pop("name", None)

    elif node_type == "Flow":
        legacy_steps = normalize_steps(out.get("steps"))
        if legacy_steps:
            desc = str(out.get("description", "") or "")
            out["description"] = append_text(desc, f"Steps: {legacy_steps}.")
            out.pop("steps", None)
            changes.append("steps->description")

    elif node_type == "Node":
        definition = out.get("definition")
        phase = out.get("phase")
        if isinstance(definition, str) and definition.strip():
            desc = str(out.get("description", "") or "")
            out["description"] = append_text(desc, f"Definition: {definition.strip()}.")
            out.pop("definition", None)
            changes.append("definition->description")
        if phase is not None and str(phase).strip():
            ensure_tag(out, f"phase:{str(phase).strip()}")
            out.pop("phase", None)
            changes.append("phase->tags")

    elif node_type == "Engine":
        note = out.get("note")
        query = out.get("query")
        if isinstance(note, str) and note.strip():
            desc = str(out.get("description", "") or "")
            out["description"] = append_text(desc, f"Note: {note.strip()}.")
            out.pop("note", None)
            changes.append("note->description")
        if isinstance(query, str) and query.strip():
            if not str(out.get("spec_source", "")).strip():
                out["spec_source"] = query.strip()
                changes.append("query->spec_source")
            else:
                desc = str(out.get("description", "") or "")
                out["description"] = append_text(desc, f"Query: {query.strip()}.")
                changes.append("query->description_append")
            out.pop("query", None)

    elif node_type == "Concept":
        status = out.get("status")
        if isinstance(status, str) and status.strip():
            ensure_tag(out, f"status:{status.strip().lower()}")
            out.pop("status", None)
            changes.append("status->tags")

    return out, changes


def plan(index: GraphIndex) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for node in index.all_nodes():
        mapped, changes = map_node(node)
        if changes:
            actions.append(
                {
                    "node_id": node.get("id"),
                    "type": node.get("type"),
                    "changes": changes,
                    "mapped_node": mapped,
                }
            )
    return actions


def apply(root: Path, nodes_schema: dict[str, Any], actions: list[dict[str, Any]]) -> dict[str, Any]:
    applied = 0
    errors: list[dict[str, Any]] = []
    for action in actions:
        try:
            update_node(root, action["mapped_node"], nodes_schema, actor="phase4b_residual_mapping")
            applied += 1
        except Exception as exc:
            errors.append({"node_id": action.get("node_id"), "changes": action.get("changes"), "error": str(exc)})
    return {"applied_count": applied, "error_count": len(errors), "errors": errors}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="D:/MIHOS-v1")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json-out", default=".gobp/history/mihos_phase4b_residual_mapping.json")
    args = parser.parse_args()

    root = Path(args.root)
    nodes_schema = load_schema(package_schema_dir() / "core_nodes.yaml")
    index = GraphIndex.load_from_disk(root)
    actions = plan(index)

    report: dict[str, Any] = {
        "project_root": str(root),
        "mode": "apply" if args.apply else "dry_run",
        "candidate_nodes": len(actions),
        "actions_preview": [
            {"node_id": a["node_id"], "type": a["type"], "changes": a["changes"]}
            for a in actions[:100]
        ],
    }

    if args.apply:
        report["apply_result"] = apply(root, nodes_schema, actions)

    out = Path(args.json_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nSaved report: {out}")

    if args.apply and report.get("apply_result", {}).get("error_count", 0) > 0:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
