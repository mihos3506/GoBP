"""Phase 4 controlled mapping for remaining schema warnings (MIHOS).

Mappings:
- TestKind.priority/status -> tags (priority:*, status:*)
- Invariant.topic -> rule (or appended to description)
- Flow.steps -> description append
- TestCase.expected_result/description -> then/scenario
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex
from gobp.core.loader import load_schema, package_schema_dir
from gobp.core.fs_mutator import update_node


def ensure_tag(node: dict[str, Any], tag: str) -> None:
    tags = node.get("tags")
    if not isinstance(tags, list):
        tags = []
    if tag not in tags:
        tags.append(tag)
    node["tags"] = tags


def map_node(node: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    out = dict(node)
    changes: list[str] = []
    ntype = str(node.get("type", ""))

    if ntype == "TestKind":
        pr = out.get("priority")
        st = out.get("status")
        if isinstance(pr, str) and pr.strip():
            ensure_tag(out, f"priority:{pr.strip().lower()}")
            out.pop("priority", None)
            changes.append("priority->tags")
        if isinstance(st, str) and st.strip():
            ensure_tag(out, f"status:{st.strip().lower()}")
            out.pop("status", None)
            changes.append("status->tags")

    elif ntype == "Invariant":
        topic = out.get("topic")
        if isinstance(topic, str) and topic.strip():
            if not out.get("rule"):
                out["rule"] = topic.strip()
                changes.append("topic->rule")
            else:
                desc = str(out.get("description", "") or "")
                extra = f" Topic: {topic.strip()}."
                if extra.strip() not in desc:
                    out["description"] = (desc + extra).strip()
                    changes.append("topic->description_append")
            out.pop("topic", None)

    elif ntype == "Flow":
        steps = out.get("steps")
        if isinstance(steps, list) and steps:
            steps_txt = " -> ".join(str(s) for s in steps[:10])
            desc = str(out.get("description", "") or "")
            append = f" Steps: {steps_txt}."
            if append.strip() not in desc:
                out["description"] = (desc + append).strip()
                changes.append("steps->description")
            out.pop("steps", None)

    elif ntype == "TestCase":
        expected = out.get("expected_result")
        descr = out.get("description")
        if isinstance(expected, str) and expected.strip():
            if not out.get("then"):
                out["then"] = expected.strip()
                changes.append("expected_result->then")
            else:
                scenario = str(out.get("scenario", "") or "")
                extra = f" Expected: {expected.strip()}."
                if extra.strip() not in scenario:
                    out["scenario"] = (scenario + extra).strip()
                    changes.append("expected_result->scenario_append")
            out.pop("expected_result", None)
        if isinstance(descr, str) and descr.strip():
            if not out.get("scenario"):
                out["scenario"] = descr.strip()
                changes.append("description->scenario")
            else:
                scenario = str(out.get("scenario", "") or "")
                if descr.strip() not in scenario:
                    out["scenario"] = (scenario + f" {descr.strip()}").strip()
                    changes.append("description->scenario_append")
            out.pop("description", None)

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
            update_node(root, action["mapped_node"], nodes_schema, actor="phase4_controlled_mapping")
            applied += 1
        except Exception as exc:
            errors.append(
                {"node_id": action.get("node_id"), "changes": action.get("changes"), "error": str(exc)}
            )
    return {"applied_count": applied, "error_count": len(errors), "errors": errors}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="D:/MIHOS-v1")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json-out", default=".gobp/history/mihos_phase4_controlled_mapping.json")
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
