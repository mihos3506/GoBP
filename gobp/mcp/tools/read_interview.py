"""GoBP interview read tools.

Node template declarations and guided relationship interviews.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex

# Required and optional edges per NodeType (AI declaration guide)
_NODE_EDGE_REQUIREMENTS: dict[str, dict[str, list[dict[str, str]]]] = {
    "Flow": {
        "required_edges": [
            {
                "type": "implements",
                "target": "Protocol or Node",
                "description": "Protocol nÃ y Flow thá»±c hiá»‡n",
            },
            {
                "type": "references",
                "target": "Document",
                "description": "DOC source cá»§a Flow",
            },
        ],
        "optional_edges": [
            {
                "type": "depends_on",
                "target": "Entity or Node",
                "description": "Dependencies",
            },
            {
                "type": "tested_by",
                "target": "TestCase",
                "description": "Test coverage",
            },
        ],
    },
    "Engine": {
        "required_edges": [
            {
                "type": "implements",
                "target": "Flow or Node",
                "description": "Flow Engine nÃ y phá»¥c vá»¥",
            },
        ],
        "optional_edges": [
            {
                "type": "depends_on",
                "target": "Entity",
                "description": "Entity Engine cáº§n",
            },
            {
                "type": "references",
                "target": "Document",
                "description": "Spec document",
            },
        ],
    },
    "Entity": {
        "required_edges": [
            {
                "type": "references",
                "target": "Document",
                "description": "DOC Ä‘á»‹nh nghÄ©a Entity",
            },
        ],
        "optional_edges": [
            {
                "type": "relates_to",
                "target": "Entity",
                "description": "Entities liÃªn quan",
            },
        ],
    },
    "Feature": {
        "required_edges": [
            {
                "type": "implements",
                "target": "Flow or Node",
                "description": "Flow Feature nÃ y thuá»™c vá»",
            },
        ],
        "optional_edges": [
            {
                "type": "references",
                "target": "Document",
                "description": "Spec source",
            },
            {
                "type": "depends_on",
                "target": "Entity or Feature",
                "description": "Dependencies",
            },
            {
                "type": "tested_by",
                "target": "TestCase",
                "description": "Test coverage",
            },
        ],
    },
    "Decision": {
        "required_edges": [],
        "optional_edges": [
            {
                "type": "references",
                "target": "Document",
                "description": "Source document",
            },
            {
                "type": "supersedes",
                "target": "Decision",
                "description": "Decision cÅ© bá»‹ thay tháº¿",
            },
        ],
    },
    "Document": {
        "required_edges": [],
        "optional_edges": [
            {
                "type": "references",
                "target": "Document",
                "description": "Docs liÃªn quan",
            },
        ],
    },
    "TestCase": {
        "required_edges": [
            {
                "type": "covers",
                "target": "Node or Flow or Feature",
                "description": "Node nÃ y test covers",
            },
            {
                "type": "of_kind",
                "target": "TestKind",
                "description": "Loáº¡i test",
            },
        ],
        "optional_edges": [],
    },
}


def node_template(
    index: GraphIndex,
    project_root: Path,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Return declaration template for a NodeType.

    Shows required + optional edges AI should declare when creating this type.

    Args:
        query: NodeType name (e.g. "Flow", "Engine", "Entity")

    Returns:
        ok, node_type, required_edges[], optional_edges[], example_queries[]
    """
    del index, project_root  # Signature parity with other read tools.
    node_type = str(args.get("query", args.get("node_type", ""))).strip()
    if not node_type:
        return {
            "ok": True,
            "templates": {k: dict(v) for k, v in _NODE_EDGE_REQUIREMENTS.items()},
            "hint": "gobp(query='template: Flow') to see Flow-specific template",
        }

    reqs = _NODE_EDGE_REQUIREMENTS.get(node_type, {})
    required = list(reqs.get("required_edges", []))
    optional = list(reqs.get("optional_edges", []))

    examples = [
        f"gobp(query=\"create:{node_type} name='My {node_type}' priority='high' session_id='x'\")",
    ]
    for edge in required:
        et = edge["type"]
        examples.append(
            f"gobp(query=\"edge: {node_type.lower()}:my_id --{et}--> target:id\")"
            f"  # {edge['description']}"
        )

    return {
        "ok": True,
        "node_type": node_type,
        "required_edges": required,
        "optional_edges": optional,
        "required_count": len(required),
        "optional_count": len(optional),
        "example_queries": examples,
        "hint": (
            f"After creating {node_type} node, declare {len(required)} required edge(s). "
            "Use interview: to be guided through all relationships."
        )
        if required
        else f"No required edges for {node_type}.",
    }


def node_interview(
    index: GraphIndex,
    project_root: Path,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Generate interview questions for declaring a node's relationships.

    AI uses this after creating a node to discover all relationships.
    Returns structured questions â€” AI answers each, then creates edges.

    Args:
        node_id: str â€” node to interview about
        answered: list[str] (optional) â€” edge types already declared

    Returns:
        ok, node_id, node_name, questions[], next_question, completion_pct
    """
    del project_root
    node_id = str(args.get("node_id") or args.get("query", "")).strip()
    if not node_id:
        return {"ok": False, "error": "node_id required"}

    node = index.get_node(node_id)
    if not node:
        return {"ok": False, "error": f"Node not found: {node_id}"}

    node_type = str(node.get("type", "Node"))
    reqs = _NODE_EDGE_REQUIREMENTS.get(node_type, {})
    required_edges = list(reqs.get("required_edges", []))
    optional_edges = list(reqs.get("optional_edges", []))

    existing_edge_types = {e.get("type") for e in index.get_edges_from(node_id) if e.get("type")}
    answered_raw = args.get("answered", [])
    if isinstance(answered_raw, str):
        answered_list = [a.strip() for a in answered_raw.split(",") if a.strip()]
    else:
        answered_list = [str(a).strip() for a in answered_raw if str(a).strip()]
    answered: set[str] = set(answered_list) | existing_edge_types

    questions: list[dict[str, Any]] = []

    for edge in required_edges:
        if edge["type"] not in answered:
            et = edge["type"]
            questions.append({
                "edge_type": et,
                "required": True,
                "question": (
                    f"[REQUIRED] {node.get('name', node_id)} {et} which {edge['target']}?"
                ),
                "description": edge["description"],
                "example": f"gobp(query=\"edge: {node_id} --{et}--> target:id\")",
            })

    for edge in optional_edges:
        if edge["type"] not in answered:
            et = edge["type"]
            questions.append({
                "edge_type": et,
                "required": False,
                "question": (
                    f"[OPTIONAL] Does {node.get('name', node_id)} {et} any {edge['target']}?"
                ),
                "description": edge["description"],
                "example": f"gobp(query=\"edge: {node_id} --{et}--> target:id\")",
            })

    if not questions or all(q["required"] is False for q in questions):
        questions.append({
            "edge_type": "_catch_all",
            "required": False,
            "question": f"Are there any other nodes that relate to {node.get('name', node_id)}?",
            "description": "Catch-all: any relationship not covered above",
            "example": f"gobp(query=\"edge: {node_id} --relates_to--> other:id\")",
        })

    total = len(required_edges) + len(optional_edges) + 1
    answered_count = len(answered)
    completion_pct = min(100, round(answered_count / total * 100)) if total else 100

    next_q = questions[0] if questions else None

    return {
        "ok": True,
        "node_id": node_id,
        "node_name": node.get("name", ""),
        "node_type": node_type,
        "questions": questions,
        "next_question": next_q,
        "answered_edge_types": sorted(answered),
        "completion_pct": completion_pct,
        "done": len(questions) == 0 or (
            len(questions) == 1 and questions[0]["edge_type"] == "_catch_all"
        ),
        "hint": (
            "Answer each question by creating edges, then call interview: again to continue."
            if questions
            else f"All relationships declared for {node.get('name', node_id)}."
        ),
    }


