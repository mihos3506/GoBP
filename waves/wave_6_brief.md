# WAVE 6 BRIEF — ADVANCED FEATURES: LESSONS EXTRACT + MIGRATE + PRUNE

**Wave:** 6
**Title:** lessons_extract (MCP tool) + migrate + prune
**Author:** CTO Chat (Claude Sonnet 4.6)
**Date:** 2026-04-15
**For:** Cursor (sequential execution) + Claude CLI (sequential audit)
**Status:** READY FOR EXECUTION
**Task count:** 10 atomic tasks
**Estimated effort:** 3-4 hours

---

## CONTEXT

Wave 5 shipped GoBP v1 with all 13 MCP tools functional. GoBP is now feature-complete for basic usage.

**Wave 6 adds 3 maintenance/intelligence capabilities:**

1. **`lessons_extract`** — MCP tool (tool #14). Scans session history + existing nodes → proposes new Lesson nodes from patterns. Primary value: AI agents on other projects can call this to extract learnable patterns from a GoBP-tracked project. This is the cross-project intelligence layer.

2. **`migrate`** — Python function (not MCP tool yet). Upgrades `.gobp/` folder when schema version bumps. Called by `node_upsert` and `validate` automatically when schema mismatch detected.

3. **`prune`** — Python function (not MCP tool yet). Archives stale nodes (WITHDRAWN status + zero active edges). Writes archive file, removes from active graph. Keeps graph clean for long-running projects.

**Why `migrate` and `prune` are not MCP tools in Wave 6:**
Both are maintenance operations. Adding them as MCP tools would require careful auth/safety design (AI calling `prune` on accident = data loss risk). Wave 6 ships them as internal Python functions callable from CLI in Wave 7. Wave 7 can expose them as MCP tools if CEO decides.

**In scope:**
- `lessons_extract` MCP tool (registered in server, full input/output spec)
- `gobp/core/lessons.py` — extraction logic
- `gobp/core/migrate.py` — schema migration logic
- `gobp/core/prune.py` — stale node archival
- Tests for all 3 modules
- Register `lessons_extract` in MCP server (tool count: 13 → 14)
- Update `README.md` tool count

**NOT in scope:**
- CLI commands for migrate/prune (Wave 7)
- MCP tools for migrate/prune (defer, safety concern)
- Automatic lesson application to other projects (manual export only)
- LLM-powered lesson inference (pattern-based only, no AI call inside GoBP)

---

## CURSOR EXECUTION RULES (READ FIRST — NON-NEGOTIABLE)

### R1 — Sequential execution
Execute Task 1 → Task 2 → ... → Task 10 in order. Do NOT skip, reorder, or parallelize. Do NOT stop between tasks unless a blocker rule triggers.

### R2 — Discovery before creation
Before creating ANY file, use explorer subagent to check if it already exists. If found, read it first, then decide whether to modify or replace.

### R3 — 1 task = 1 commit
After each task's tests pass → commit immediately. Message must match the exact commit message in the Brief. Do not batch multiple tasks into one commit.

### R4 — MCP_TOOLS.md is supreme authority
If ANY code in this Brief conflicts with `docs/MCP_TOOLS.md` (tool signatures, input/output schemas, field names, error format):
- `docs/MCP_TOOLS.md` WINS
- STOP immediately
- Report the exact conflict: "Brief says X, MCP_TOOLS.md §N.N says Y"
- Wait for CTO resolution. Do NOT substitute your own interpretation.

### R5 — Document disagreement = STOP and suggest
If you believe a foundational doc (`docs/SCHEMA.md`, `docs/ARCHITECTURE.md`, `docs/MCP_TOOLS.md`) contains an error or inconsistency:
- STOP
- Do NOT silently work around it
- Report: "I believe docs/X.md §N may have an issue: [your observation]. Recommend CTO review before I proceed."
- Wait for instruction.

### R6 — 3 retries = STOP and report
If a test fails and you cannot fix it after 3 attempts:
- STOP
- Do NOT continue to the next task
- File a stop report (see format below)
- Wait for CEO to relay to CTO Chat

### R7 — No scope creep
Implement EXACTLY the functions/classes/tools specified. No extra methods, no convenience wrappers, no "symmetric" additions. Private `_` helpers are OK. Public API must match Brief exactly.

### R8 — Brief code blocks are authoritative
If you disagree with a code block in this Brief, STOP and escalate. Do not substitute your own implementation silently. This rule exists because of Wave 3 Task 7 (F17 failure mode).

---

## STOP REPORT FORMAT

Use this exact format when any blocker rule triggers:

```
STOP — Wave 6 Task <N>

Rule triggered: R<N> — <rule name>

Completed so far: Tasks 1–<N-1> (committed)
Current task: Task <N> — <title>

What I was doing: <description>
What went wrong: <exact error or conflict>
What I tried: <list of attempts if R6>
Why I cannot proceed: <reason>

Conflict details (if R4 or R5):
  Brief says: <quote>
  Doc says: <quote from docs/X.md §N.N>

Current git state:
  Staged: <list>
  Unstaged: <list>

What I need from CEO/CTO: <specific question>
```

---

## AUTHORITATIVE SOURCE

**`docs/SCHEMA.md` §2.6 (Lesson node) is source of truth for Lesson schema.**
**`docs/MCP_TOOLS.md` is source of truth for ALL tool signatures, input/output, error format.**

Cross-reference map:
- `docs/SCHEMA.md §2.6` → Task 1 (Lesson node fields in lessons.py)
- `docs/MCP_TOOLS.md §11` (tool registration pattern) → Task 5
- `docs/ARCHITECTURE.md` (file-first, atomic writes) → Tasks 2, 3
- `gobp/mcp/tools/write.py` (tool handler pattern) → Task 4
- `gobp/mcp/server.py` (dispatch pattern) → Task 5

Cursor MUST re-read the mapped doc section BEFORE implementing each task.
If Brief conflicts with docs → **docs win, Cursor STOPS and escalates (R4).**

---

## SCOPE DISCIPLINE RULE

Implement EXACTLY what this Brief specifies. No additional MCP tools, no CLI wrappers, no "while I'm at it" extras.

Brief code blocks are authoritative. If you think there is a better approach, STOP and escalate (R8). Do not substitute.

Private `_` helpers inside modules are OK.

---

## PREREQUISITES

Before Task 1:

```powershell
cd D:\GoBP
git status              # clean working tree
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v
# Expected: 137 tests passing (all Wave 0-5)

D:/GoBP/venv/Scripts/python.exe -c "
import asyncio
from gobp.mcp.server import list_tools
tools = asyncio.run(list_tools())
print(f'Tools: {len(tools)}')
"
# Expected: Tools: 13
```

If any check fails, STOP and escalate before proceeding.

---

## REQUIRED READING — WAVE START (before Task 1)

Cursor MUST read ALL of these before writing any code:

| # | File | Why |
|---|---|---|
| 1 | `.cursorrules` | Execution rules, stop conditions, commit format |
| 2 | `docs/SCHEMA.md` | Full schema — especially §2.6 Lesson node |
| 3 | `docs/MCP_TOOLS.md` | All tool specs — §11 registration pattern |
| 4 | `docs/ARCHITECTURE.md` | File-first design, atomic writes, folder structure |
| 5 | `gobp/mcp/server.py` | How tools are registered and dispatched |
| 6 | `gobp/mcp/tools/write.py` | Pattern for tool handler implementation |
| 7 | `gobp/core/graph.py` | GraphIndex API used in lessons/prune |
| 8 | `gobp/core/history.py` | append_event API used in prune |

**Per-task reading** (re-read before each task):

| Task | Must re-read before starting |
|---|---|
| Task 1 (lessons.py) | `docs/SCHEMA.md §2.6`, `gobp/core/graph.py` |
| Task 2 (migrate.py) | `docs/ARCHITECTURE.md` |
| Task 3 (prune.py) | `docs/ARCHITECTURE.md`, `gobp/core/history.py` |
| Task 4 (advanced.py) | `docs/MCP_TOOLS.md §11`, `gobp/mcp/tools/write.py` |
| Task 5 (server.py) | `gobp/mcp/server.py` current state, `docs/MCP_TOOLS.md §11` |
| Tasks 6–9 (tests) | The module being tested |
| Task 10 (README) | `README.md` current state |

---

# TASKS

---

## TASK 1 — Create gobp/core/lessons.py skeleton

**Goal:** Create the lessons module with skeleton functions (stubs only, no logic yet).

**File to create:** `gobp/core/lessons.py`

**Content:**

```python
"""GoBP lessons extraction.

Scans session history and existing nodes to identify patterns
that can be captured as Lesson nodes.

Extraction is pattern-based (no LLM calls). Patterns recognized:
- P1: Session ended INTERRUPTED or FAILED → candidate "failure mode" lesson
- P2: Same topic appears in 3+ sessions without a Decision → candidate
  "recurring uncertainty" lesson
- P3: Decision superseded within 7 days → candidate "premature decision" lesson
- P4: Node with 0 edges after 30 days (created, never connected) → candidate
  "orphan work" lesson

lessons_extract MCP tool calls _scan_patterns() → returns raw candidates →
caller (AI) reviews → calls node_upsert to create confirmed Lessons.

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
    candidates: list[dict[str, Any]] = []

    candidates.extend(_scan_p1_failed_sessions(index, gobp_root))
    candidates.extend(_scan_p2_recurring_uncertainty(index))
    candidates.extend(_scan_p3_premature_decisions(index))
    candidates.extend(_scan_p4_orphan_nodes(index))

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
    index: GraphIndex,
    gobp_root: Path,
) -> list[dict[str, Any]]:
    """P1: Sessions that ended INTERRUPTED or FAILED."""
    candidates = []
    sessions = [n for n in index.all_nodes() if n.get("type") == "Session"]

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
    index: GraphIndex,
) -> list[dict[str, Any]]:
    """P2: Topics appearing in 3+ Idea nodes without a locking Decision."""
    from collections import Counter

    # Count topics across Idea nodes
    idea_topics: list[str] = []
    for n in index.all_nodes():
        if n.get("type") != "Idea":
            continue
        subject = n.get("subject", "")
        if subject:
            idea_topics.append(subject)

    topic_counts = Counter(idea_topics)

    # Get topics that have a locked Decision
    decided_topics: set[str] = set()
    for n in index.all_nodes():
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
                    n.get("id", "") for n in index.all_nodes()
                    if n.get("type") == "Idea" and n.get("subject") == topic
                ][:5],
                "suggested_tags": ["decision-debt", topic.replace(":", "-")],
            })

    return candidates


def _scan_p3_premature_decisions(
    index: GraphIndex,
) -> list[dict[str, Any]]:
    """P3: Decisions superseded within 7 days of being locked."""
    from datetime import datetime, timezone

    candidates = []
    for n in index.all_nodes():
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
    index: GraphIndex,
) -> list[dict[str, Any]]:
    """P4: Non-Session nodes with 0 edges after creation."""
    from datetime import datetime, timezone

    # Build set of all node IDs that appear in any edge
    connected_ids: set[str] = set()
    for edge in index.all_edges():
        connected_ids.add(edge.get("from", ""))
        connected_ids.add(edge.get("to", ""))

    candidates = []
    for n in index.all_nodes():
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
```

**Acceptance criteria:**
- File created at `gobp/core/lessons.py`
- 1 public function: `extract_candidates`
- 4 private scanner functions: `_scan_p1`, `_scan_p2`, `_scan_p3`, `_scan_p4`
- All type hints present
- Module docstring explains the 4 patterns

**Commit message:**
```
Wave 6 Task 1: create gobp/core/lessons.py

- extract_candidates(index, root, max) → list of lesson candidates
- 4 pattern scanners: P1 failed sessions, P2 recurring uncertainty,
  P3 premature decisions, P4 orphan nodes
- No LLM calls, no node creation — proposals only
- All type hints, full docstrings
```

---

## TASK 2 — Create gobp/core/migrate.py

**Goal:** Schema migration logic for `.gobp/` folder upgrades.

**File to create:** `gobp/core/migrate.py`

**Content:**

```python
"""GoBP schema migration.

Handles upgrades when gobp schema version bumps.
Migration is conservative: never deletes fields, only adds missing ones
with safe defaults.

Version format: integer (1, 2, 3, ...).
Current version: 1 (set by Wave 0).

Callers:
- validate tool calls check_version() and warns if mismatch
- node_upsert calls _ensure_node_compatible() before writing

Migration is idempotent: running twice produces same result.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

CURRENT_SCHEMA_VERSION = 1


def check_version(gobp_root: Path) -> dict[str, Any]:
    """Check if .gobp/ schema version matches current version.

    Args:
        gobp_root: Project root containing .gobp/ folder.

    Returns:
        Dict with:
        - ok: bool
        - current_version: int (version on disk)
        - expected_version: int (this code's version)
        - needs_migration: bool
        - message: str
    """
    config_path = gobp_root / ".gobp" / "config.yaml"

    if not config_path.exists():
        return {
            "ok": False,
            "current_version": 0,
            "expected_version": CURRENT_SCHEMA_VERSION,
            "needs_migration": True,
            "message": "No config.yaml found. Run gobp init.",
        }

    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        return {
            "ok": False,
            "current_version": 0,
            "expected_version": CURRENT_SCHEMA_VERSION,
            "needs_migration": False,
            "message": f"config.yaml parse error: {e}",
        }

    on_disk = config.get("schema_version", 1)

    if on_disk == CURRENT_SCHEMA_VERSION:
        return {
            "ok": True,
            "current_version": on_disk,
            "expected_version": CURRENT_SCHEMA_VERSION,
            "needs_migration": False,
            "message": "Schema version up to date.",
        }

    return {
        "ok": False,
        "current_version": on_disk,
        "expected_version": CURRENT_SCHEMA_VERSION,
        "needs_migration": on_disk < CURRENT_SCHEMA_VERSION,
        "message": (
            f"Schema mismatch: disk={on_disk}, code={CURRENT_SCHEMA_VERSION}. "
            "Run gobp migrate to upgrade."
        ),
    }


def run_migration(gobp_root: Path) -> dict[str, Any]:
    """Run all pending migrations on .gobp/ folder.

    Idempotent. Safe to run multiple times.

    Args:
        gobp_root: Project root containing .gobp/ folder.

    Returns:
        Dict with:
        - ok: bool
        - steps_run: list[str]
        - message: str
    """
    version_check = check_version(gobp_root)

    if not version_check["needs_migration"]:
        return {
            "ok": True,
            "steps_run": [],
            "message": "No migration needed.",
        }

    on_disk = version_check["current_version"]
    steps_run: list[str] = []

    # Migration chain: run each step in order
    migration_steps = {
        # Example: migrate from v0 to v1
        # ("v0_to_v1", _migrate_v0_to_v1),
    }

    for step_name, step_fn in migration_steps.items():
        try:
            step_fn(gobp_root)
            steps_run.append(step_name)
        except Exception as e:
            return {
                "ok": False,
                "steps_run": steps_run,
                "message": f"Migration failed at step '{step_name}': {e}",
            }

    # Update config version after all steps pass
    _update_config_version(gobp_root, CURRENT_SCHEMA_VERSION)
    steps_run.append(f"updated_config_to_v{CURRENT_SCHEMA_VERSION}")

    return {
        "ok": True,
        "steps_run": steps_run,
        "message": f"Migration complete. Schema now at v{CURRENT_SCHEMA_VERSION}.",
    }


def _update_config_version(gobp_root: Path, version: int) -> None:
    """Update schema_version in config.yaml."""
    config_path = gobp_root / ".gobp" / "config.yaml"

    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}

    config["schema_version"] = version

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
```

**Acceptance criteria:**
- File created at `gobp/core/migrate.py`
- 2 public functions: `check_version`, `run_migration`
- `CURRENT_SCHEMA_VERSION = 1` constant
- No actual migration steps yet (v1 is baseline, migration chain is empty)
- Idempotent: running twice is safe

**Commit message:**
```
Wave 6 Task 2: create gobp/core/migrate.py

- check_version(root) → version status dict
- run_migration(root) → idempotent migration runner
- CURRENT_SCHEMA_VERSION = 1 (baseline, empty migration chain)
- Foundation for future schema bumps
```

---

## TASK 3 — Create gobp/core/prune.py

**Goal:** Archive stale nodes (WITHDRAWN + zero active edges).

**File to create:** `gobp/core/prune.py`

**Content:**

```python
"""GoBP prune — archive stale nodes.

A node is prunable if:
1. Its status field is "WITHDRAWN"
2. It has zero active edges (edges where neither endpoint is ACTIVE/LOCKED)

Prune does NOT delete. It moves nodes to .gobp/archive/YYYY-MM-DD/
and removes their edges from the active graph.

Prune is conservative: when in doubt, do NOT prune.
If a node has ANY edge (even to another WITHDRAWN node), skip it.

This keeps the graph clean for long-running projects without
risking data loss.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex
from gobp.core.history import append_event


def dry_run(index: GraphIndex) -> list[dict[str, Any]]:
    """Identify prunable nodes without making any changes.

    Args:
        index: Current GraphIndex.

    Returns:
        List of dicts: {id, type, name, reason}
    """
    return _find_prunable(index)


def run_prune(
    index: GraphIndex,
    gobp_root: Path,
    actor: str = "prune",
) -> dict[str, Any]:
    """Archive prunable nodes and their edges.

    Args:
        index: Current GraphIndex (used for discovery only).
        gobp_root: Project root containing .gobp/ folder.
        actor: Who initiated the prune (for history log).

    Returns:
        Dict with:
        - ok: bool
        - pruned_nodes: list[str] (IDs archived)
        - pruned_edges: list[str] (edge filenames archived)
        - archive_path: str
        - message: str
    """
    candidates = _find_prunable(index)

    if not candidates:
        return {
            "ok": True,
            "pruned_nodes": [],
            "pruned_edges": [],
            "archive_path": "",
            "message": "Nothing to prune.",
        }

    # Create archive folder
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    archive_dir = gobp_root / ".gobp" / "archive" / date_str
    archive_dir.mkdir(parents=True, exist_ok=True)

    nodes_dir = gobp_root / ".gobp" / "nodes"
    edges_dir = gobp_root / ".gobp" / "edges"

    pruned_nodes: list[str] = []
    pruned_edges: list[str] = []

    candidate_ids = {c["id"] for c in candidates}

    # Archive node files
    for candidate in candidates:
        node_id = candidate["id"]
        # Node file: nodes/{node_id_slug}.md (replace : with -)
        node_slug = node_id.replace(":", "-")
        node_file = nodes_dir / f"{node_slug}.md"

        if node_file.exists():
            dest = archive_dir / node_file.name
            shutil.move(str(node_file), str(dest))
            pruned_nodes.append(node_id)

    # Archive edge files that reference pruned nodes
    if edges_dir.exists():
        for edge_file in edges_dir.glob("*.yaml"):
            try:
                import yaml
                with open(edge_file, encoding="utf-8") as f:
                    edge = yaml.safe_load(f) or {}
                from_id = edge.get("from", "")
                to_id = edge.get("to", "")
                if from_id in candidate_ids or to_id in candidate_ids:
                    dest = archive_dir / edge_file.name
                    shutil.move(str(edge_file), str(dest))
                    pruned_edges.append(edge_file.name)
            except Exception:
                # Skip unreadable edge files — don't block prune
                continue

    # Log to history
    append_event(
        gobp_root=gobp_root,
        event_type="graph.prune",
        payload={
            "pruned_nodes": pruned_nodes,
            "pruned_edges": pruned_edges,
            "archive_path": str(archive_dir),
        },
        actor=actor,
    )

    return {
        "ok": True,
        "pruned_nodes": pruned_nodes,
        "pruned_edges": pruned_edges,
        "archive_path": str(archive_dir),
        "message": (
            f"Pruned {len(pruned_nodes)} nodes, {len(pruned_edges)} edges "
            f"→ {archive_dir}"
        ),
    }


def _find_prunable(index: GraphIndex) -> list[dict[str, Any]]:
    """Find nodes that qualify for pruning."""
    # Build set of all node IDs referenced in any edge
    connected_ids: set[str] = set()
    for edge in index.all_edges():
        connected_ids.add(edge.get("from", ""))
        connected_ids.add(edge.get("to", ""))

    candidates = []
    for n in index.all_nodes():
        if n.get("status") != "WITHDRAWN":
            continue
        node_id = n.get("id", "")
        if node_id in connected_ids:
            continue  # Has edges, skip
        candidates.append({
            "id": node_id,
            "type": n.get("type", ""),
            "name": n.get("name", ""),
            "reason": "WITHDRAWN status + zero edges",
        })

    return candidates
```

**Acceptance criteria:**
- File created at `gobp/core/prune.py`
- 2 public functions: `dry_run`, `run_prune`
- Archive destination: `.gobp/archive/YYYY-MM-DD/`
- Uses `shutil.move` (not delete)
- Logs to history via `append_event`
- If nothing to prune → returns ok with empty lists

**Commit message:**
```
Wave 6 Task 3: create gobp/core/prune.py

- dry_run(index) → list of prunable node candidates
- run_prune(index, root, actor) → archive WITHDRAWN+unconnected nodes
- Archives to .gobp/archive/YYYY-MM-DD/ using shutil.move
- Logs prune event to history
- Conservative: any edge = skip
```

---

## TASK 4 — Implement lessons_extract tool in tools/advanced.py

**Goal:** Create new tool module with `lessons_extract` implementation.

**File to create:** `gobp/mcp/tools/advanced.py`

**Content:**

```python
"""GoBP MCP advanced tools.

Wave 6 additions:
- lessons_extract: scan graph + history for lesson candidates
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gobp.core.graph import GraphIndex
from gobp.core.lessons import extract_candidates


async def lessons_extract(
    index: GraphIndex,
    project_root: Path,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Scan graph + session history for lesson candidates.

    Identifies patterns that indicate learnable lessons.
    Does NOT create nodes. Returns proposals for AI/human review.

    Input:
        max_candidates: int (default 20, max 50)
        patterns: list[str] (default all: ["P1","P2","P3","P4"])

    Output:
        ok: bool
        candidates: list[dict] — each candidate has:
            pattern, title, trigger, what_happened,
            why_it_matters, mitigation, severity,
            evidence, suggested_tags
        count: int
        note: str — reminder that these are proposals, not created nodes
    """
    max_candidates = min(int(args.get("max_candidates", 20)), 50)
    requested_patterns = args.get("patterns", ["P1", "P2", "P3", "P4"])

    if not isinstance(requested_patterns, list):
        return {"ok": False, "error": "patterns must be a list of strings"}

    valid_patterns = {"P1", "P2", "P3", "P4"}
    for p in requested_patterns:
        if p not in valid_patterns:
            return {
                "ok": False,
                "error": f"Invalid pattern '{p}'. Valid: {sorted(valid_patterns)}",
            }

    all_candidates = extract_candidates(
        index=index,
        gobp_root=project_root,
        max_candidates=max_candidates,
    )

    # Filter by requested patterns
    filtered = [c for c in all_candidates if c.get("pattern") in requested_patterns]

    return {
        "ok": True,
        "candidates": filtered,
        "count": len(filtered),
        "note": (
            "These are proposals only. To create a Lesson node, "
            "review each candidate and call node_upsert with type='Lesson'."
        ),
    }
```

**Acceptance criteria:**
- File created at `gobp/mcp/tools/advanced.py`
- 1 async function: `lessons_extract`
- Validates `patterns` input
- Caps `max_candidates` at 50
- Returns `note` reminding caller these are proposals only
- Does not create nodes

**Commit message:**
```
Wave 6 Task 4: create gobp/mcp/tools/advanced.py

- lessons_extract async tool handler
- Validates patterns param (P1/P2/P3/P4)
- Caps max_candidates at 50
- Returns proposals with note — no auto node creation
```

---

## TASK 5 — Register lessons_extract in MCP server

**Goal:** Add `lessons_extract` to `gobp/mcp/server.py` — tool list and dispatch.

**File to modify:** `gobp/mcp/server.py`

**Re-read `gobp/mcp/server.py` in full before editing.**

**Two changes needed:**

**Change 1 — Add import at top of file (after existing tool imports):**
```python
from gobp.mcp.tools import advanced as tools_advanced
```

**Change 2 — Add to `list_tools()` return list:**
```python
types.Tool(
    name="lessons_extract",
    description=(
        "Scan project graph and session history for lesson candidates. "
        "Identifies 4 patterns: failed sessions (P1), recurring uncertainty (P2), "
        "premature decisions (P3), orphan nodes (P4). "
        "Returns proposals only — does not create Lesson nodes. "
        "Use node_upsert to create confirmed lessons."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "max_candidates": {
                "type": "integer",
                "default": 20,
                "description": "Max candidates to return (hard cap: 50)",
            },
            "patterns": {
                "type": "array",
                "items": {"type": "string", "enum": ["P1", "P2", "P3", "P4"]},
                "default": ["P1", "P2", "P3", "P4"],
                "description": "Which patterns to scan (default: all)",
            },
        },
        "required": [],
    },
),
```

**Change 3 — Add to `call_tool()` dispatch dict:**
```python
"lessons_extract": tools_advanced.lessons_extract,
```

**Acceptance criteria:**
- `lessons_extract` appears in `list_tools()` output
- `call_tool("lessons_extract", {})` routes to `tools_advanced.lessons_extract`
- No other tools modified
- Tool count increases from 13 to 14

**Commit message:**
```
Wave 6 Task 5: register lessons_extract in MCP server

- gobp/mcp/server.py: import tools_advanced
- list_tools: add lessons_extract (tool #14)
- call_tool dispatch: route to tools_advanced.lessons_extract
- Tool count: 13 → 14
```

---

## TASK 6 — Write lessons module tests

**Goal:** Test `extract_candidates` and all 4 pattern scanners.

**File to create:** `tests/test_lessons.py`

**Content:**

```python
"""Tests for gobp.core.lessons module."""

from pathlib import Path
from datetime import datetime, timezone, timedelta

import pytest
import yaml

from gobp.core.graph import GraphIndex
from gobp.core.lessons import extract_candidates


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_gobp_root(tmp_path: Path) -> Path:
    """Create minimal .gobp/ structure."""
    (tmp_path / ".gobp" / "nodes").mkdir(parents=True)
    (tmp_path / ".gobp" / "edges").mkdir(parents=True)
    (tmp_path / ".gobp" / "history").mkdir(parents=True)
    return tmp_path


def _write_node(gobp_root: Path, node: dict) -> None:
    """Write a node to .gobp/nodes/."""
    node_id = node["id"].replace(":", "-")
    node_path = gobp_root / ".gobp" / "nodes" / f"{node_id}.md"
    frontmatter = yaml.dump(node, allow_unicode=True, default_flow_style=False)
    node_path.write_text(f"---\n{frontmatter}---\n", encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _days_ago_iso(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


# ---------------------------------------------------------------------------
# Tests: empty graph
# ---------------------------------------------------------------------------

def test_extract_candidates_empty_graph(tmp_path: Path):
    """Empty graph returns empty candidates."""
    root = _make_gobp_root(tmp_path)
    index = GraphIndex.load_from_disk(root)
    candidates = extract_candidates(index, root)
    assert candidates == []


# ---------------------------------------------------------------------------
# Tests: P1 — failed sessions
# ---------------------------------------------------------------------------

def test_p1_detects_interrupted_session(tmp_path: Path):
    """P1 fires for INTERRUPTED session."""
    root = _make_gobp_root(tmp_path)
    _write_node(root, {
        "id": "session:s001",
        "type": "Session",
        "actor": "test",
        "started_at": _days_ago_iso(2),
        "goal": "Build something complex",
        "status": "INTERRUPTED",
        "outcome": "ran out of context",
        "pending": ["task A"],
        "created": _days_ago_iso(2),
        "updated": _days_ago_iso(1),
    })
    index = GraphIndex.load_from_disk(root)
    candidates = extract_candidates(index, root)

    p1 = [c for c in candidates if c["pattern"] == "P1"]
    assert len(p1) >= 1
    assert "session:s001" in p1[0]["evidence"]
    assert p1[0]["severity"] == "medium"


def test_p1_detects_failed_session_as_high_severity(tmp_path: Path):
    """P1 FAILED session → severity=high."""
    root = _make_gobp_root(tmp_path)
    _write_node(root, {
        "id": "session:s002",
        "type": "Session",
        "actor": "test",
        "started_at": _days_ago_iso(3),
        "goal": "Ship wave",
        "status": "FAILED",
        "outcome": "tests broke",
        "pending": [],
        "created": _days_ago_iso(3),
        "updated": _days_ago_iso(2),
    })
    index = GraphIndex.load_from_disk(root)
    candidates = extract_candidates(index, root)

    p1 = [c for c in candidates if c["pattern"] == "P1"]
    assert any(c["severity"] == "high" for c in p1)


def test_p1_skips_completed_sessions(tmp_path: Path):
    """P1 does not flag COMPLETED sessions."""
    root = _make_gobp_root(tmp_path)
    _write_node(root, {
        "id": "session:s003",
        "type": "Session",
        "actor": "test",
        "started_at": _now_iso(),
        "goal": "Write docs",
        "status": "COMPLETED",
        "outcome": "done",
        "created": _now_iso(),
        "updated": _now_iso(),
    })
    index = GraphIndex.load_from_disk(root)
    candidates = extract_candidates(index, root)
    p1 = [c for c in candidates if c["pattern"] == "P1"]
    assert p1 == []


# ---------------------------------------------------------------------------
# Tests: P2 — recurring uncertainty
# ---------------------------------------------------------------------------

def test_p2_detects_undecided_topic(tmp_path: Path):
    """P2 fires when 3+ Ideas share a topic with no Decision."""
    root = _make_gobp_root(tmp_path)
    for i in range(3):
        _write_node(root, {
            "id": f"idea:i00{i}",
            "type": "Idea",
            "name": f"idea {i}",
            "subject": "auth:login",
            "raw_quote": "some thought",
            "interpretation": "login idea",
            "maturity": "ROUGH",
            "confidence": "low",
            "created": _now_iso(),
            "updated": _now_iso(),
        })
    index = GraphIndex.load_from_disk(root)
    candidates = extract_candidates(index, root)
    p2 = [c for c in candidates if c["pattern"] == "P2"]
    assert len(p2) >= 1
    assert "auth:login" in p2[0]["title"]


def test_p2_skips_topic_with_locked_decision(tmp_path: Path):
    """P2 does not flag a topic if a locked Decision exists."""
    root = _make_gobp_root(tmp_path)
    for i in range(3):
        _write_node(root, {
            "id": f"idea:i01{i}",
            "type": "Idea",
            "name": f"idea {i}",
            "subject": "storage:backend",
            "raw_quote": "thought",
            "interpretation": "storage idea",
            "maturity": "ROUGH",
            "confidence": "low",
            "created": _now_iso(),
            "updated": _now_iso(),
        })
    _write_node(root, {
        "id": "dec:d001",
        "type": "Decision",
        "name": "Use file storage",
        "topic": "storage:backend",
        "what": "Use YAML files",
        "why": "Simple",
        "status": "LOCKED",
        "locked_at": _now_iso(),
        "locked_by": ["CEO"],
        "created": _now_iso(),
        "updated": _now_iso(),
    })
    index = GraphIndex.load_from_disk(root)
    candidates = extract_candidates(index, root)
    p2 = [c for c in candidates if c["pattern"] == "P2" and "storage:backend" in c.get("title", "")]
    assert p2 == []


# ---------------------------------------------------------------------------
# Tests: P3 — premature decisions
# ---------------------------------------------------------------------------

def test_p3_detects_decision_superseded_within_7_days(tmp_path: Path):
    """P3 fires when Decision is superseded within 7 days."""
    root = _make_gobp_root(tmp_path)
    locked_at = _days_ago_iso(5)
    updated = _days_ago_iso(3)
    _write_node(root, {
        "id": "dec:d010",
        "type": "Decision",
        "name": "Old decision",
        "topic": "ui:theme",
        "what": "Use dark mode",
        "why": "Trend",
        "status": "SUPERSEDED",
        "locked_at": locked_at,
        "locked_by": ["CEO"],
        "created": locked_at,
        "updated": updated,
    })
    index = GraphIndex.load_from_disk(root)
    candidates = extract_candidates(index, root)
    p3 = [c for c in candidates if c["pattern"] == "P3"]
    assert len(p3) >= 1
    assert "dec:d010" in p3[0]["evidence"]


def test_p3_skips_decision_superseded_after_7_days(tmp_path: Path):
    """P3 skips Decision superseded after 7+ days (normal lifecycle)."""
    root = _make_gobp_root(tmp_path)
    locked_at = _days_ago_iso(30)
    updated = _days_ago_iso(15)
    _write_node(root, {
        "id": "dec:d011",
        "type": "Decision",
        "name": "Old decision 2",
        "topic": "api:version",
        "what": "Use REST",
        "why": "Standard",
        "status": "SUPERSEDED",
        "locked_at": locked_at,
        "locked_by": ["CEO"],
        "created": locked_at,
        "updated": updated,
    })
    index = GraphIndex.load_from_disk(root)
    candidates = extract_candidates(index, root)
    p3 = [c for c in candidates if c["pattern"] == "P3" and "dec:d011" in c.get("evidence", [])]
    assert p3 == []


# ---------------------------------------------------------------------------
# Tests: P4 — orphan nodes
# ---------------------------------------------------------------------------

def test_p4_detects_old_orphan_node(tmp_path: Path):
    """P4 fires for non-Session node older than 30 days with no edges."""
    root = _make_gobp_root(tmp_path)
    _write_node(root, {
        "id": "node:orphan001",
        "type": "Node",
        "name": "Forgotten feature",
        "status": "ACTIVE",
        "created": _days_ago_iso(45),
        "updated": _days_ago_iso(45),
    })
    index = GraphIndex.load_from_disk(root)
    candidates = extract_candidates(index, root)
    p4 = [c for c in candidates if c["pattern"] == "P4"]
    assert len(p4) >= 1
    assert "node:orphan001" in p4[0]["evidence"]


def test_p4_skips_recent_orphan(tmp_path: Path):
    """P4 skips orphan nodes created less than 30 days ago."""
    root = _make_gobp_root(tmp_path)
    _write_node(root, {
        "id": "node:recent001",
        "type": "Node",
        "name": "New feature",
        "status": "ACTIVE",
        "created": _days_ago_iso(5),
        "updated": _days_ago_iso(5),
    })
    index = GraphIndex.load_from_disk(root)
    candidates = extract_candidates(index, root)
    p4 = [c for c in candidates if c["pattern"] == "P4" and "node:recent001" in c.get("evidence", [])]
    assert p4 == []


# ---------------------------------------------------------------------------
# Tests: max_candidates cap
# ---------------------------------------------------------------------------

def test_max_candidates_cap(tmp_path: Path):
    """extract_candidates respects max_candidates cap."""
    root = _make_gobp_root(tmp_path)
    # Create 10 interrupted sessions to get 10 P1 candidates
    for i in range(10):
        _write_node(root, {
            "id": f"session:s{i:03d}",
            "type": "Session",
            "actor": "test",
            "started_at": _days_ago_iso(i + 1),
            "goal": f"Goal {i}",
            "status": "INTERRUPTED",
            "outcome": "interrupted",
            "pending": [],
            "created": _days_ago_iso(i + 1),
            "updated": _days_ago_iso(i),
        })
    index = GraphIndex.load_from_disk(root)
    candidates = extract_candidates(index, root, max_candidates=3)
    assert len(candidates) <= 3
```

**Acceptance criteria:**
- File `tests/test_lessons.py` created
- 12 test functions
- All tests pass
- Covers: empty graph, P1 (3 tests), P2 (2 tests), P3 (2 tests), P4 (2 tests), max_candidates cap (1 test)

**Commit message:**
```
Wave 6 Task 6: write lessons module tests

- tests/test_lessons.py: 12 tests
- Covers all 4 patterns + empty graph + max_candidates
- Uses tmp_path + helper _write_node for isolation
- All tests pass
```

---

## TASK 7 — Write migrate module tests

**Goal:** Test `check_version` and `run_migration`.

**File to create:** `tests/test_migrate.py`

**Content:**

```python
"""Tests for gobp.core.migrate module."""

from pathlib import Path

import pytest
import yaml

from gobp.core.migrate import (
    CURRENT_SCHEMA_VERSION,
    check_version,
    run_migration,
)


def _make_gobp_with_version(tmp_path: Path, version: int) -> Path:
    gobp_dir = tmp_path / ".gobp"
    gobp_dir.mkdir()
    config = {"schema_version": version, "project_name": "test"}
    (gobp_dir / "config.yaml").write_text(
        yaml.dump(config, allow_unicode=True), encoding="utf-8"
    )
    return tmp_path


def test_check_version_current(tmp_path: Path):
    """check_version returns ok=True when version matches."""
    root = _make_gobp_with_version(tmp_path, CURRENT_SCHEMA_VERSION)
    result = check_version(root)
    assert result["ok"] is True
    assert result["needs_migration"] is False


def test_check_version_missing_config(tmp_path: Path):
    """check_version returns ok=False when no config.yaml."""
    (tmp_path / ".gobp").mkdir()
    result = check_version(tmp_path)
    assert result["ok"] is False
    assert result["needs_migration"] is True


def test_check_version_old_version(tmp_path: Path):
    """check_version detects outdated schema."""
    root = _make_gobp_with_version(tmp_path, 0)
    result = check_version(root)
    assert result["ok"] is False
    assert result["current_version"] == 0
    assert result["needs_migration"] is True


def test_run_migration_no_op_when_current(tmp_path: Path):
    """run_migration is no-op when version is current."""
    root = _make_gobp_with_version(tmp_path, CURRENT_SCHEMA_VERSION)
    result = run_migration(root)
    assert result["ok"] is True
    assert result["steps_run"] == []
    assert "No migration needed" in result["message"]


def test_run_migration_idempotent(tmp_path: Path):
    """run_migration can be called twice safely."""
    root = _make_gobp_with_version(tmp_path, CURRENT_SCHEMA_VERSION)
    run_migration(root)
    result = run_migration(root)
    assert result["ok"] is True


def test_check_version_returns_expected_version(tmp_path: Path):
    """check_version always reports CURRENT_SCHEMA_VERSION as expected."""
    root = _make_gobp_with_version(tmp_path, 99)
    result = check_version(root)
    assert result["expected_version"] == CURRENT_SCHEMA_VERSION
```

**Acceptance criteria:**
- File `tests/test_migrate.py` created
- 6 test functions
- All tests pass

**Commit message:**
```
Wave 6 Task 7: write migrate module tests

- tests/test_migrate.py: 6 tests
- Covers: current version, missing config, old version,
  no-op migration, idempotent run, expected version field
```

---

## TASK 8 — Write prune module tests

**Goal:** Test `dry_run` and `run_prune`.

**File to create:** `tests/test_prune.py`

**Content:**

```python
"""Tests for gobp.core.prune module."""

from pathlib import Path
from datetime import datetime, timezone, timedelta

import pytest
import yaml

from gobp.core.graph import GraphIndex
from gobp.core.prune import dry_run, run_prune


def _make_root(tmp_path: Path) -> Path:
    (tmp_path / ".gobp" / "nodes").mkdir(parents=True)
    (tmp_path / ".gobp" / "edges").mkdir(parents=True)
    (tmp_path / ".gobp" / "history").mkdir(parents=True)
    return tmp_path


def _write_node(root: Path, node: dict) -> None:
    node_id = node["id"].replace(":", "-")
    path = root / ".gobp" / "nodes" / f"{node_id}.md"
    fm = yaml.dump(node, allow_unicode=True, default_flow_style=False)
    path.write_text(f"---\n{fm}---\n", encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def test_dry_run_empty_graph(tmp_path: Path):
    """dry_run returns empty list on empty graph."""
    root = _make_root(tmp_path)
    index = GraphIndex.load_from_disk(root)
    result = dry_run(index)
    assert result == []


def test_dry_run_finds_withdrawn_node(tmp_path: Path):
    """dry_run identifies WITHDRAWN node with no edges."""
    root = _make_root(tmp_path)
    _write_node(root, {
        "id": "node:old001",
        "type": "Node",
        "name": "Old feature",
        "status": "WITHDRAWN",
        "created": _now(),
        "updated": _now(),
    })
    index = GraphIndex.load_from_disk(root)
    candidates = dry_run(index)
    assert len(candidates) == 1
    assert candidates[0]["id"] == "node:old001"


def test_dry_run_skips_active_node(tmp_path: Path):
    """dry_run skips ACTIVE nodes even with no edges."""
    root = _make_root(tmp_path)
    _write_node(root, {
        "id": "node:active001",
        "type": "Node",
        "name": "Active feature",
        "status": "ACTIVE",
        "created": _now(),
        "updated": _now(),
    })
    index = GraphIndex.load_from_disk(root)
    candidates = dry_run(index)
    assert candidates == []


def test_run_prune_nothing_to_prune(tmp_path: Path):
    """run_prune returns ok with empty lists when nothing prunable."""
    root = _make_root(tmp_path)
    index = GraphIndex.load_from_disk(root)
    result = run_prune(index, root)
    assert result["ok"] is True
    assert result["pruned_nodes"] == []
    assert result["pruned_edges"] == []
    assert "Nothing to prune" in result["message"]


def test_run_prune_archives_node_file(tmp_path: Path):
    """run_prune moves node file to archive directory."""
    root = _make_root(tmp_path)
    _write_node(root, {
        "id": "node:stale001",
        "type": "Node",
        "name": "Stale",
        "status": "WITHDRAWN",
        "created": _now(),
        "updated": _now(),
    })
    index = GraphIndex.load_from_disk(root)
    result = run_prune(index, root)

    assert result["ok"] is True
    assert "node:stale001" in result["pruned_nodes"]
    # Original file should be gone
    node_file = root / ".gobp" / "nodes" / "node-stale001.md"
    assert not node_file.exists()
    # Archive directory should exist
    assert result["archive_path"] != ""
    archive_dir = Path(result["archive_path"])
    assert archive_dir.exists()


def test_run_prune_logs_history_event(tmp_path: Path):
    """run_prune appends to history log."""
    root = _make_root(tmp_path)
    _write_node(root, {
        "id": "node:stale002",
        "type": "Node",
        "name": "Stale 2",
        "status": "WITHDRAWN",
        "created": _now(),
        "updated": _now(),
    })
    index = GraphIndex.load_from_disk(root)
    run_prune(index, root, actor="test-prune")

    from gobp.core.history import read_events
    events = read_events(root)
    prune_events = [e for e in events if e.get("event_type") == "graph.prune"]
    assert len(prune_events) >= 1
    assert prune_events[0]["actor"] == "test-prune"
```

**Acceptance criteria:**
- File `tests/test_prune.py` created
- 6 test functions
- All tests pass

**Commit message:**
```
Wave 6 Task 8: write prune module tests

- tests/test_prune.py: 6 tests
- Covers: empty graph, withdrawn detection, active skip,
  nothing-to-prune, archive file move, history log
```

---

## TASK 9 — Write lessons_extract MCP tool tests

**Goal:** Test the `lessons_extract` tool handler in isolation.

**File to create:** `tests/test_tool_lessons_extract.py`

**Content:**

```python
"""Tests for gobp.mcp.tools.advanced.lessons_extract tool."""

import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta

import pytest
import yaml

from gobp.core.graph import GraphIndex
from gobp.mcp.tools.advanced import lessons_extract


def _make_root(tmp_path: Path) -> Path:
    (tmp_path / ".gobp" / "nodes").mkdir(parents=True)
    (tmp_path / ".gobp" / "edges").mkdir(parents=True)
    (tmp_path / ".gobp" / "history").mkdir(parents=True)
    return tmp_path


def _write_node(root: Path, node: dict) -> None:
    node_id = node["id"].replace(":", "-")
    path = root / ".gobp" / "nodes" / f"{node_id}.md"
    fm = yaml.dump(node, allow_unicode=True, default_flow_style=False)
    path.write_text(f"---\n{fm}---\n", encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_lessons_extract_empty_graph(tmp_path: Path):
    """lessons_extract returns ok with empty candidates on empty graph."""
    root = _make_root(tmp_path)
    index = GraphIndex.load_from_disk(root)
    result = _run(lessons_extract(index, root, {}))
    assert result["ok"] is True
    assert result["candidates"] == []
    assert result["count"] == 0
    assert "note" in result


def test_lessons_extract_invalid_pattern(tmp_path: Path):
    """lessons_extract returns error for invalid pattern."""
    root = _make_root(tmp_path)
    index = GraphIndex.load_from_disk(root)
    result = _run(lessons_extract(index, root, {"patterns": ["P99"]}))
    assert result["ok"] is False
    assert "Invalid pattern" in result["error"]


def test_lessons_extract_default_args(tmp_path: Path):
    """lessons_extract works with no args (all defaults)."""
    root = _make_root(tmp_path)
    index = GraphIndex.load_from_disk(root)
    result = _run(lessons_extract(index, root, {}))
    assert result["ok"] is True


def test_lessons_extract_pattern_filter(tmp_path: Path):
    """lessons_extract only returns candidates for requested patterns."""
    root = _make_root(tmp_path)
    _write_node(root, {
        "id": "session:s001",
        "type": "Session",
        "actor": "test",
        "started_at": _now(),
        "goal": "test",
        "status": "INTERRUPTED",
        "outcome": "interrupted",
        "pending": [],
        "created": _now(),
        "updated": _now(),
    })
    index = GraphIndex.load_from_disk(root)

    # Only request P2, P3, P4 — should not return P1 candidates
    result = _run(lessons_extract(index, root, {"patterns": ["P2", "P3", "P4"]}))
    assert result["ok"] is True
    for c in result["candidates"]:
        assert c["pattern"] != "P1"


def test_lessons_extract_max_candidates_respected(tmp_path: Path):
    """lessons_extract respects max_candidates parameter."""
    root = _make_root(tmp_path)
    for i in range(10):
        _write_node(root, {
            "id": f"session:s{i:03d}",
            "type": "Session",
            "actor": "test",
            "started_at": _now(),
            "goal": f"goal {i}",
            "status": "INTERRUPTED",
            "outcome": "interrupted",
            "pending": [],
            "created": _now(),
            "updated": _now(),
        })
    index = GraphIndex.load_from_disk(root)
    result = _run(lessons_extract(index, root, {"max_candidates": 3}))
    assert result["ok"] is True
    assert len(result["candidates"]) <= 3


def test_lessons_extract_note_always_present(tmp_path: Path):
    """lessons_extract always includes note reminding about proposals."""
    root = _make_root(tmp_path)
    index = GraphIndex.load_from_disk(root)
    result = _run(lessons_extract(index, root, {}))
    assert "note" in result
    assert "node_upsert" in result["note"]
```

**Acceptance criteria:**
- File `tests/test_tool_lessons_extract.py` created
- 6 test functions
- All tests pass

**Commit message:**
```
Wave 6 Task 9: write lessons_extract tool tests

- tests/test_tool_lessons_extract.py: 6 tests
- Covers: empty graph, invalid pattern, default args,
  pattern filter, max_candidates cap, note always present
```

---

## TASK 10 — Update tool count in README + run full test suite

**Goal:** Update README tool count (13 → 14) and verify all tests pass.

**File to modify:** `README.md`

**Change:** Find the line that references "13 MCP tools" and update to "14 MCP tools". Also add `lessons_extract` to the tool list in the "What Works After Wave 5" section.

**Cursor: search for "13 MCP tools" and "13 tools" in README.md and update all occurrences to 14.**

**Then run full test suite:**

```powershell
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v
# Expected: 137 (existing) + 12 + 6 + 6 + 6 = 167 tests passing

D:/GoBP/venv/Scripts/python.exe -c "
import asyncio
from gobp.mcp.server import list_tools
tools = asyncio.run(list_tools())
print(f'Tools: {len(tools)}')
print([t.name for t in tools])
"
# Expected: Tools: 14, lessons_extract in list
```

**Commit message:**
```
Wave 6 Task 10: update README tool count 13→14

- README.md: 13 MCP tools → 14 MCP tools
- Add lessons_extract to tool list
- All 167 tests passing
- MCP server registers 14 tools
```

---

# POST-WAVE VERIFICATION

After all 10 tasks:

```powershell
# All tests pass
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v
# Expected: 167 tests passing

# 14 tools registered
D:/GoBP/venv/Scripts/python.exe -c "
import asyncio
from gobp.mcp.server import list_tools
tools = asyncio.run(list_tools())
print(f'Tools: {len(tools)}')
assert len(tools) == 14
print('OK')
"

# New modules importable
D:/GoBP/venv/Scripts/python.exe -c "
from gobp.core.lessons import extract_candidates
from gobp.core.migrate import check_version, run_migration
from gobp.core.prune import dry_run, run_prune
from gobp.mcp.tools.advanced import lessons_extract
print('All imports OK')
"

# Git log
git log --oneline | Select-Object -First 10
# Expected: 10 Wave 6 commits
```

---

# ESCALATION TRIGGERS

Stop and escalate (use STOP REPORT FORMAT) if:
- Existing 137 tests break after any task (R6)
- Any Brief code conflicts with `docs/MCP_TOOLS.md` (R4)
- Any foundational doc appears to have an error (R5)
- `shutil.move` fails on Windows — report exact error
- `GraphIndex.load_from_disk` API differs from what Brief assumes — report diff
- Same test fails after 3 fix attempts (R6)

---

# CEO DISPATCH INSTRUCTIONS

## STEP 1 — Upload Brief to repo

```powershell
cd D:\GoBP
copy <download_path>\wave_6_brief.md waves\wave_6_brief.md
git add waves\wave_6_brief.md
git commit -m "Add Wave 6 Brief"
```

## STEP 2 — Dispatch Cursor (paste exactly as-is)

```
Read each of these files in full before writing any code:
1. .cursorrules
2. docs/SCHEMA.md
3. docs/MCP_TOOLS.md
4. docs/ARCHITECTURE.md
5. gobp/mcp/server.py
6. gobp/mcp/tools/write.py
7. gobp/core/graph.py
8. gobp/core/history.py
9. waves/wave_6_brief.md

Then execute ALL 10 tasks in waves/wave_6_brief.md sequentially.
Rules:
- Do NOT stop between tasks unless a blocker rule triggers (R1–R8 in Brief)
- Use explorer subagent before creating any new file
- Re-read the per-task docs listed in REQUIRED READING before each task
- If Brief code conflicts with docs/MCP_TOOLS.md → docs win, STOP and report (R4)
- If you believe a doc has an error → STOP and report your suggestion (R5)
- If a test fails 3 times → STOP and report (R6)
- 1 task = 1 commit, message must match Brief exactly
- Report full wave summary only after Task 10 is committed
```

Sau đó **không làm gì thêm** — chờ Cursor báo xong toàn bộ wave.

## STEP 3 — Verify before audit

```powershell
cd D:\GoBP
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -v
# Expected: 167 tests passing

git log --oneline | Select-Object -First 12
# Expected: 10 Wave 6 commits + 1 Brief commit + previous
```

## STEP 4 — Dispatch Claude CLI (audit)

Mở terminal mới tại `D:\GoBP\`, chạy:

```powershell
cd D:\GoBP
claude
```

Paste vào Claude CLI:

```
Read CLAUDE.md in full.
Then audit Wave 6. Brief is at waves/wave_6_brief.md.
Audit all 10 tasks sequentially. Stop on first failure — do not continue past failure.
Use FAIL REPORT FORMAT from CLAUDE.md when stopping.
After all tasks pass, output WAVE 6 AUDIT COMPLETE report.
```

Chờ Claude CLI báo `WAVE 6 AUDIT COMPLETE`. Nếu có FAIL report → relay nguyên văn sang CTO Chat (tab này).

## STEP 5 — Push to GitHub

Chỉ sau khi Claude CLI báo audit complete:

```powershell
cd D:\GoBP
git push origin main
```

---

# WHAT COMES NEXT

After Wave 6 pushed:
- **Wave 7** — Documentation polish (install guide, CONTRIBUTING.md, docstring audit, CHANGELOG)
- **Wave 8** — MIHOS integration test (import 31 MIHOS docs, stress test 14 tools, extract lessons, benchmark)

---

*Wave 6 Brief v0.2*
*Author: CTO Chat (Claude Sonnet 4.6)*
*Date: 2026-04-15*

◈
