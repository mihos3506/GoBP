---
alternatives_considered: []
created: '2026-04-16T02:39:50.424075+00:00'
id: core.dec:1712
legacy_id: dec:d009
locked_at: '2026-04-16T02:39:50.424075+00:00'
locked_by:
- CEO
- Claude-CLI
name: Normalize NodeType via casefold() + _TYPE_CANONICAL dict. Unknown types pass
  thr
risks: []
session_id: session:2026-04-16_update_gobp_with_wav
status: LOCKED
topic: gobp:schema.type_normalization
type: Decision
updated: '2026-04-16T02:39:50.424075+00:00'
what: Normalize NodeType via casefold() + _TYPE_CANONICAL dict. Unknown types pass
  through unchanged. Applied in parse_query and create/update/upsert handlers.
why: AI clients send inconsistent casing. Normalize at ingestion to prevent schema
  drift and silent errors.
---

(Auto-generated node file. Edit the YAML above or add body content below.)
