#!/usr/bin/env python3
"""Link Wave nodes to brief Documents and Feature nodes to owning Waves.

Idempotent: skips edges that already exist (same from, to, type).

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
_WAVE_BRIEF_PATH = re.compile(r"^waves/wave_(.+)_brief\.md$")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return f"sha256:{h.hexdigest()}"


def load_node_ids_and_docs() -> tuple[set[str], dict[str, str]]:
    """Return (all_node_ids, wave_slug -> doc_id) for brief docs."""
    all_ids: set[str] = set()
    doc_by_slug: dict[str, str] = {}
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
        raw_path = sm.group(1).strip().strip("'\"")
        pm = _WAVE_BRIEF_PATH.match(raw_path.replace("\\", "/"))
        if pm:
            doc_by_slug[pm.group(1)] = nid
    return all_ids, doc_by_slug


def load_existing_edges() -> tuple[list[dict], set[tuple[str, str, str]]]:
    data = yaml.safe_load(EDGES_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit(f"Expected list in {EDGES_FILE}")
    keys: set[tuple[str, str, str]] = set()
    for e in data:
        keys.add((str(e["from"]), str(e["to"]), str(e["type"])))
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


def ensure_doc_and_wave_for_brief(
    *,
    slug: str,
    brief_filename: str,
    wave_name: str,
    all_ids: set[str],
) -> None:
    """Create Document + Wave nodes for a brief on disk if missing."""
    brief_path = WAVES_DIR / brief_filename
    if not brief_path.is_file():
        return
    doc_id = f"doc:wave_{slug}_brief"
    wave_id = f"wave:{slug}"
    now = _now_iso()
    session = "session:2026-04-16_create_wave_nodes_an"
    chash = _sha256_file(brief_path)

    doc_path = NODES_DIR / f"doc_wave_{slug}_brief.md"
    if doc_id not in all_ids and not doc_path.exists():
        body = f"""---
id: {doc_id}
type: Document
name: Wave {slug.upper()} Brief
status: ACTIVE
created: '{now}'
updated: '{now}'
session_id: {session}
source_path: waves/{brief_filename}
content_hash: {chash}
registered_at: '{now}'
last_verified: '{now}'
priority: high
sections: []
description: Canonical brief for Wave {slug} (linked from graph).
tags:
  - wave
  - brief
spec_source: waves/{brief_filename}
---

(Brief body lives in ``{brief_filename}``; this node is the graph pointer.)
"""
        doc_path.write_text(body, encoding="utf-8")
        all_ids.add(doc_id)

    wave_file = NODES_DIR / f"wave_{slug}.md"
    if wave_id not in all_ids and not wave_file.exists():
        wbody = f"""---
id: {wave_id}
type: Wave
name: {wave_name}
status: ACTIVE
created: '{now}'
updated: '{now}'
session_id: {session}
priority: high
description: Wave {slug} execution container; brief at ``waves/{brief_filename}``.
---

(Auto-generated wave node — link tasks and decisions here.)
"""
        wave_file.write_text(wbody, encoding="utf-8")
        all_ids.add(wave_id)


def main() -> None:
    all_ids, doc_by_slug = load_node_ids_and_docs()
    edges, keys = load_existing_edges()
    new_edges: list[dict[str, str]] = []

    # Optional: materialize Wave 15 + 16A01 brief nodes if missing
    ensure_doc_and_wave_for_brief(
        slug="15",
        brief_filename="wave_15_brief.md",
        wave_name="Wave 15 Parser Import Edge Dedupe",
        all_ids=all_ids,
    )
    ensure_doc_and_wave_for_brief(
        slug="16a01",
        brief_filename="wave_16a01_brief.md",
        wave_name="Wave 16A01 Response Tiers Metadata Linter Priority",
        all_ids=all_ids,
    )

    # Reload ids if we created files
    all_ids, doc_by_slug = load_node_ids_and_docs()

    # wave -> doc references
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

    # feat -> wave relates_to
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
