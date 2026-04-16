#!/usr/bin/env python3
"""Sync Wave graph: materialize Wave nodes from briefs, link briefs, link feats.

For every ``waves/wave_<slug>_brief.md``:
  - Ensure a ``Wave`` node ``wave:<slug>`` exists (``wave_<slug>.md``).
  - Ensure a ``Document`` node exists with ``source_path: waves/wave_<slug>_brief.md``
    (skip if any doc already points at that path — keeps ``doc:wave_14_brief_79fc28``).
  - Add ``wave:<slug>`` --references--> doc when missing.

Maps ``feat:*`` IDs to owning waves by prefix (w4_, wcore_, mcp_, …).

Idempotent: safe to re-run.

Run from repo root:
    D:/GoBP/venv/Scripts/python.exe scripts/link_wave_briefs_and_features.py
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
NODES_DIR = ROOT / ".gobp" / "nodes"
EDGES_FILE = ROOT / ".gobp" / "edges" / "semantic_edges.yaml"
WAVES_DIR = ROOT / "waves"

_ID_RE = re.compile(r"^id:\s*(\S+)\s*$", re.MULTILINE)
_SOURCE_RE = re.compile(r"^source_path:\s*(.+)\s*$", re.MULTILINE)
_WAVE_BRIEF_PATH = re.compile(r"^waves/wave_(.+)_brief\.md$", re.IGNORECASE)
_BRIEF_FILE_RE = re.compile(r"^wave_(.+)_brief\.md$", re.IGNORECASE)
_TITLE_RE = re.compile(r"^\*\*Title:\*\*\s*(.+)\s*$")
_STATUS_RE = re.compile(r"^\*\*Status:\*\*\s*(.+)\s*$", re.IGNORECASE)

_SESSION = "session:2026-04-16_create_wave_nodes_an"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return f"sha256:{h.hexdigest()}"


def _norm_path(s: str) -> str:
    return s.strip().strip("'\"").replace("\\", "/")


def iter_brief_files() -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    for p in sorted(WAVES_DIR.glob("wave_*_brief.md")):
        m = _BRIEF_FILE_RE.match(p.name)
        if m:
            out.append((m.group(1), p))
    return out


def parse_brief_meta(path: Path) -> tuple[str, str]:
    """Return (title_line, wave_status) from brief header."""
    head = path.read_text(encoding="utf-8", errors="replace")[:12000]
    title = f"Wave — {path.stem}"
    wstatus = "ACTIVE"
    for line in head.splitlines():
        tm = _TITLE_RE.match(line)
        if tm:
            title = tm.group(1).strip()
        sm = _STATUS_RE.match(line)
        if sm:
            raw = sm.group(1).strip().upper()
            if "COMPLETE" in raw or "DONE" in raw or "SHIPPED" in raw:
                wstatus = "COMPLETED"
            elif "DEPREC" in raw:
                wstatus = "DEPRECATED"
            elif "DRAFT" in raw:
                wstatus = "DRAFT"
            else:
                wstatus = "ACTIVE"
    return title, wstatus


def load_node_ids_and_docs() -> tuple[set[str], dict[str, str], set[str]]:
    """all_ids, wave_slug -> one doc id, set of source_paths on Document nodes."""
    all_ids: set[str] = set()
    doc_by_slug: dict[str, str] = {}
    source_paths: set[str] = set()
    for md in NODES_DIR.glob("*.md"):
        text = md.read_text(encoding="utf-8", errors="replace")
        m = _ID_RE.search(text)
        if not m:
            continue
        nid = m.group(1)
        all_ids.add(nid)
        if not nid.startswith("doc:"):
            continue
        sm = _SOURCE_RE.search(text)
        if not sm:
            continue
        raw_path = _norm_path(sm.group(1))
        source_paths.add(raw_path)
        pm = _WAVE_BRIEF_PATH.match(raw_path)
        if pm:
            slug = pm.group(1)
            # Prefer first; wave 14 has a single doc for path wave_14_brief.md
            doc_by_slug.setdefault(slug, nid)
    return all_ids, doc_by_slug, source_paths


def load_existing_edges() -> tuple[list[dict], set[tuple[str, str, str]]]:
    data = yaml.safe_load(EDGES_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit(f"Expected list in {EDGES_FILE}")
    keys: set[tuple[str, str, str]] = {
        (str(e["from"]), str(e["to"]), str(e["type"])) for e in data
    }
    return data, keys


def feat_to_wave(feat_id: str) -> str | None:
    """Map feat:<id> to wave:<slug> if pattern matches."""
    if not feat_id.startswith("feat:"):
        return None
    rest = feat_id.removeprefix("feat:")
    if rest.startswith("w10a_"):
        return "wave:10a"
    if rest.startswith("w10b_"):
        return "wave:10b"
    if rest.startswith("w10c_"):
        return "wave:10c"
    if rest.startswith("w11a_"):
        return "wave:11a"
    if rest.startswith("w11b_"):
        return "wave:11b"
    if rest.startswith("w16a01_"):
        return "wave:16a01"
    if rest.startswith("w4_"):
        return "wave:4"
    if rest.startswith("w14_"):
        return "wave:14"
    if rest.startswith("w15_"):
        return "wave:15"
    if rest.startswith("wcore_"):
        return "wave:core"
    if rest.startswith("mcp_") or rest.startswith("wave13_"):
        return "wave:13"
    return None


def ensure_doc_for_brief(
    slug: str,
    brief_path: Path,
    *,
    all_ids: set[str],
    source_paths: set[str],
) -> None:
    """Create Document node if no doc points at this brief path."""
    rel = f"waves/wave_{slug}_brief.md"
    if rel in source_paths:
        return
    doc_id = f"doc:wave_{slug}_brief"
    doc_file = NODES_DIR / f"doc_wave_{slug}_brief.md"
    if doc_id in all_ids or doc_file.exists():
        return
    now = _now_iso()
    chash = _sha256_file(brief_path)
    title, _ = parse_brief_meta(brief_path)
    body = f"""---
id: {doc_id}
type: Document
name: Wave {slug} Brief
status: ACTIVE
created: '{now}'
updated: '{now}'
session_id: {_SESSION}
source_path: {rel}
content_hash: {chash}
registered_at: '{now}'
last_verified: '{now}'
priority: high
sections: []
description: Graph pointer to canonical brief ({rel}).
tags:
  - wave
  - brief
spec_source: {rel}
---

(Brief body lives in repository file ``{rel}``.)
"""
    doc_file.write_text(body, encoding="utf-8")
    all_ids.add(doc_id)
    source_paths.add(rel)


def materialize_wave_node(
    slug: str,
    brief_path: Path,
    *,
    all_ids: set[str],
) -> None:
    """Create ``wave_<slug>.md`` if missing."""
    wave_id = f"wave:{slug}"
    wave_file = NODES_DIR / f"wave_{slug}.md"
    if wave_id in all_ids or wave_file.exists():
        return
    now = _now_iso()
    title, wstatus = parse_brief_meta(brief_path)
    rel = f"waves/wave_{slug}_brief.md"
    body = f"""---
id: {wave_id}
type: Wave
name: {title}
status: {wstatus}
created: '{now}'
updated: '{now}'
session_id: {_SESSION}
priority: high
description: Wave {slug} — scope and tasks in ``{rel}``.
tags:
  - wave
spec_source: {rel}
---

(Wave container node; link decisions, features, and tests here.)
"""
    wave_file.write_text(body, encoding="utf-8")
    all_ids.add(wave_id)


def main() -> None:
    all_ids, doc_by_slug, source_paths = load_node_ids_and_docs()

    for slug, brief_path in iter_brief_files():
        ensure_doc_for_brief(slug, brief_path, all_ids=all_ids, source_paths=source_paths)
        materialize_wave_node(slug, brief_path, all_ids=all_ids)

    all_ids, doc_by_slug, _ = load_node_ids_and_docs()
    edges, keys = load_existing_edges()
    new_edges: list[dict[str, str]] = []

    for slug, doc_id in sorted(doc_by_slug.items()):
        wave_id = f"wave:{slug}"
        if wave_id not in all_ids:
            continue
        t = (wave_id, doc_id, "references")
        if t in keys:
            continue
        new_edges.append({
            "from": wave_id,
            "to": doc_id,
            "type": "references",
            "reason": "canonical wave brief document",
        })
        keys.add(t)

    for md in sorted(NODES_DIR.glob("feat*.md")):
        text = md.read_text(encoding="utf-8", errors="replace")
        m = _ID_RE.search(text)
        if not m:
            continue
        fid = m.group(1)
        if not fid.startswith("feat:"):
            continue
        wid = feat_to_wave(fid)
        if not wid or wid not in all_ids:
            continue
        t = (fid, wid, "relates_to")
        if t in keys:
            continue
        new_edges.append({
            "from": fid,
            "to": wid,
            "type": "relates_to",
            "reason": "feature belongs to wave",
        })
        keys.add(t)

    created_waves = sorted({s for s, _ in iter_brief_files()})
    print(f"Wave briefs on disk: {len(created_waves)} slugs")

    if not new_edges:
        print("No new edges to add (already linked).")
        return

    edges.extend(new_edges)
    EDGES_FILE.write_text(
        yaml.dump(edges, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    print(f"Appended {len(new_edges)} edges to {EDGES_FILE}")


if __name__ == "__main__":
    main()
