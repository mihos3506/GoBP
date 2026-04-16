"""GoBP lessons extraction.

Scans session history and existing nodes to identify patterns
that can be captured as Lesson nodes.

Extraction is pattern-based (no LLM calls). Patterns recognized:
- P1: Session ended INTERRUPTED or FAILED -> candidate "failure mode" lesson
- P2: Same topic appears in 3+ sessions without a Decision -> candidate
  "recurring uncertainty" lesson
- P3: Decision superseded within 7 days -> candidate "premature decision" lesson
- P4: Node with 0 edges after 30 days (created, never connected) -> candidate
  "orphan work" lesson

lessons_extract MCP tool calls _scan_patterns() -> returns raw candidates ->
caller (AI) reviews -> calls node_upsert to create confirmed Lessons.

GoBP does NOT auto-create Lesson nodes. Extraction produces proposals only.
Human (or AI with human present) confirms before node_upsert.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex
from gobp.core.history import read_events


def extract_candidates(
    index: GraphIndex,
    gobp_root: Path,
    max_candidates: int = 20,
) -> list[dict[str, Any]]:
    """Scan graph + history for lesson candidates.

    Does not create nodes. Returns a list of candidate dicts
    for AI/human review.

    Args:
        index: Current GraphIndex (loaded from disk).
        gobp_root: Project root containing .gobp/ folder.
        max_candidates: Max candidates to return. Default 20.

    Returns:
        List of candidate dicts, each with:
        - pattern: str (P1/P2/P3/P4)
        - title: str (suggested lesson title)
        - trigger: str (when it applies)
        - what_happened: str
        - why_it_matters: str
        - mitigation: str
        - severity: str (low/medium/high/critical)
        - evidence: list[str] (node IDs or session IDs that triggered this)
        - suggested_tags: list[str]
    """
    nodes = index.all_nodes()
    edges = index.all_edges()
    candidates: list[dict[str, Any]] = []

    candidates.extend(_scan_p1_failed_sessions(nodes, gobp_root))
    candidates.extend(_scan_p2_recurring_uncertainty(nodes))
    candidates.extend(_scan_p3_premature_decisions(nodes))
    candidates.extend(_scan_p4_orphan_nodes(nodes, edges))

    # Deduplicate by title, cap at max_candidates
    seen_titles: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for c in candidates:
        if c["title"] not in seen_titles:
            seen_titles.add(c["title"])
            deduped.append(c)
        if len(deduped) >= max_candidates:
            break

    return deduped


def _scan_p1_failed_sessions(
    nodes: list[dict[str, Any]],
    gobp_root: Path,
) -> list[dict[str, Any]]:
    """P1: Sessions that ended INTERRUPTED or FAILED."""
    candidates = []
    sessions = [n for n in nodes if n.get("type") == "Session"]

    for s in sessions:
        status = s.get("status", "")
        if status not in ("INTERRUPTED", "FAILED"):
            continue
        goal = s.get("goal", "unknown goal")
        outcome = s.get("outcome", "no outcome recorded")
        pending = s.get("pending", [])
        candidates.append({
            "pattern": "P1",
            "title": f"Session interruption pattern: {goal[:60]}",
            "trigger": "Starting a session with similar scope or goal",
            "what_happened": (
                f"Session '{s.get('id')}' ended with status {status}. "
                f"Goal was: {goal}. Outcome: {outcome}. "
                f"Pending: {pending}"
            ),
            "why_it_matters": (
                "Interrupted sessions lose context and create orphan work. "
                "Understanding why interruptions happen helps prevent them."
            ),
            "mitigation": (
                "Break large goals into smaller sessions. "
                "Always set handoff_notes before ending."
            ),
            "severity": "medium" if status == "INTERRUPTED" else "high",
            "evidence": [s.get("id", "")],
            "suggested_tags": ["session-management", "interruption"],
        })

    return candidates


def _scan_p2_recurring_uncertainty(
    nodes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """P2: Topics appearing in 3+ Idea nodes without a locking Decision."""
    from collections import Counter

    # Count topics across Idea nodes
    idea_topics: list[str] = []
    for n in nodes:
        if n.get("type") != "Idea":
            continue
        subject = n.get("subject", "")
        if subject:
            idea_topics.append(subject)

    topic_counts = Counter(idea_topics)

    # Get topics that have a locked Decision
    decided_topics: set[str] = set()
    for n in nodes:
        if n.get("type") == "Decision" and n.get("status") == "LOCKED":
            t = n.get("topic", "")
            if t:
                decided_topics.add(t)

    candidates = []
    for topic, count in topic_counts.items():
        if count >= 3 and topic not in decided_topics:
            candidates.append({
                "pattern": "P2",
                "title": f"Recurring uncertainty on topic: {topic}",
                "trigger": f"When topic '{topic}' comes up again without resolution",
                "what_happened": (
                    f"Topic '{topic}' appeared in {count} Idea nodes "
                    f"but never produced a locked Decision."
                ),
                "why_it_matters": (
                    "Unresolved recurring topics drain cognitive resources "
                    "and delay execution."
                ),
                "mitigation": (
                    f"Force a decision on '{topic}' even if imperfect. "
                    "Use decision_lock with explicit alternatives_considered."
                ),
                "severity": "high" if count >= 5 else "medium",
                "evidence": [
                    n.get("id", "") for n in nodes
                    if n.get("type") == "Idea" and n.get("subject") == topic
                ][:5],
                "suggested_tags": ["decision-debt", topic.replace(":", "-")],
            })

    return candidates


def _scan_p3_premature_decisions(
    nodes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """P3: Decisions superseded within 7 days of being locked."""
    from datetime import datetime, timezone

    candidates = []
    for n in nodes:
        if n.get("type") != "Decision":
            continue
        if n.get("status") != "SUPERSEDED":
            continue

        locked_at_raw = n.get("locked_at", "")
        updated_raw = n.get("updated", "")
        if not locked_at_raw or not updated_raw:
            continue

        try:
            locked_at = datetime.fromisoformat(locked_at_raw)
            updated = datetime.fromisoformat(updated_raw)
            # Make both offset-aware for comparison
            if locked_at.tzinfo is None:
                locked_at = locked_at.replace(tzinfo=timezone.utc)
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)

            days_alive = (updated - locked_at).days
        except (ValueError, TypeError):
            continue

        if days_alive <= 7:
            candidates.append({
                "pattern": "P3",
                "title": f"Premature decision on: {n.get('topic', 'unknown')}",
                "trigger": (
                    f"When locking a decision on topic '{n.get('topic', '')}' "
                    "without sufficient exploration"
                ),
                "what_happened": (
                    f"Decision '{n.get('id')}' on topic '{n.get('topic')}' "
                    f"was locked then superseded within {days_alive} day(s). "
                    f"Original: {n.get('what', '')[:80]}"
                ),
                "why_it_matters": (
                    "Premature decisions signal insufficient exploration "
                    "of alternatives before locking."
                ),
                "mitigation": (
                    "Require at least 2 alternatives_considered before locking. "
                    "Wait 24h on high-severity decisions."
                ),
                "severity": "medium",
                "evidence": [n.get("id", "")],
                "suggested_tags": ["decision-quality", "premature-lock"],
            })

    return candidates


def _scan_p4_orphan_nodes(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """P4: Non-Session nodes with 0 edges after creation."""
    from datetime import datetime, timezone

    # Build set of all node IDs that appear in any edge
    connected_ids: set[str] = set()
    for edge in edges:
        connected_ids.add(edge.get("from", ""))
        connected_ids.add(edge.get("to", ""))

    candidates = []
    for n in nodes:
        node_type = n.get("type", "")
        # Skip Session nodes (they start orphaned by design)
        if node_type in ("Session",):
            continue

        node_id = n.get("id", "")
        if node_id in connected_ids:
            continue

        # Check age: only flag if > 30 days old
        created_raw = n.get("created", "")
        try:
            created = datetime.fromisoformat(created_raw)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            age_days = (datetime.now(timezone.utc) - created).days
        except (ValueError, TypeError):
            age_days = 0

        if age_days >= 30:
            candidates.append({
                "pattern": "P4",
                "title": f"Orphan {node_type} node: {n.get('name', node_id)[:60]}",
                "trigger": "When cleaning up the graph or reviewing stale work",
                "what_happened": (
                    f"Node '{node_id}' ({node_type}) has existed for {age_days} days "
                    f"with 0 edges. It was created but never connected to anything."
                ),
                "why_it_matters": (
                    "Orphan nodes pollute the graph and indicate work that was "
                    "started but never integrated."
                ),
                "mitigation": (
                    "Either connect the node to relevant context or "
                    "mark it WITHDRAWN and run prune."
                ),
                "severity": "low",
                "evidence": [node_id],
                "suggested_tags": ["graph-hygiene", "orphan", node_type.lower()],
            })

    return candidates
