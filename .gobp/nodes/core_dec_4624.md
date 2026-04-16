---
alternatives_considered: []
created: '2026-04-16T02:39:53.730849+00:00'
id: core.dec:4624
legacy_id: dec:d012
locked_at: '2026-04-16T02:39:53.730849+00:00'
locked_by:
- CEO
- Claude-CLI
name: GOBP_READ_ONLY=true blocks create/update/upsert/lock/session/edge/import/commit/
risks: []
session_id: session:2026-04-16_update_gobp_with_wav
status: LOCKED
topic: gobp:access.read_only_mode
type: Decision
updated: '2026-04-16T02:39:53.730849+00:00'
what: GOBP_READ_ONLY=true blocks create/update/upsert/lock/session/edge/import/commit/batch.
  Returns ok:false with clear error + hint. Read actions unaffected.
why: Viewer/analyst AI agents must not write. CI/audit agents must not corrupt graph.
  Env var gives operator control without code changes.
---

(Auto-generated node file. Edit the YAML above or add body content below.)
