---
id: dec:d009
type: Decision
name: Normalize NodeType via casefold() + _TYPE_CANONICAL dict. Unknown types pass
  thr
status: LOCKED
topic: gobp:schema.type_normalization
what: Normalize NodeType via casefold() + _TYPE_CANONICAL dict. Unknown types pass
  through unchanged. Applied in parse_query and create/update/upsert handlers.
why: AI clients send inconsistent casing. Normalize at ingestion to prevent schema
  drift and silent errors.
alternatives_considered: []
risks: []
locked_by:
- CEO
- Claude-CLI
locked_at: '2026-04-16T02:39:50.424075+00:00'
session_id: session:2026-04-16_update_gobp_with_wav
created: '2026-04-16T02:39:50.424075+00:00'
updated: '2026-04-16T02:39:50.424075+00:00'
---

(Auto-generated node file. Edit the YAML above or add body content below.)
