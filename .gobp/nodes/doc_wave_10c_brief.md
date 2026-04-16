---
id: doc:wave_10c_brief
type: Document
name: Wave 10C Brief
status: ACTIVE
created: '2026-04-15T17:48:30.263216+00:00'
updated: '2026-04-15T17:48:30.263216+00:00'
session_id: session:2026-04-15_sequentially_import
source_path: waves/wave_10c_brief.md
content_hash: sha256:549f475151301f8107d6973064fd16f49cd0493bd9d337f66605c4abe69ac5d8
registered_at: '2026-04-15T17:48:30.263122+00:00'
last_verified: '2026-04-15T17:48:30.263122+00:00'
priority: high
sections:
- heading: WAVE 10C BRIEF — POSTGRESQL MIGRATION
  level: 1
- heading: CONTEXT
  level: 2
- heading: CURSOR EXECUTION RULES
  level: 2
- heading: R1 — Sequential execution
  level: 3
- heading: R2 — Discovery before creation
  level: 3
- heading: R3 — 1 task = 1 commit
  level: 3
- heading: R4 — Docs supreme authority
  level: 3
- heading: R5 — Document disagreement = STOP
  level: 3
- heading: R6 — 3 retries = STOP
  level: 3
- heading: R7 — No scope creep
  level: 3
- heading: R8 — Brief code authoritative
  level: 3
- heading: R9 — All 253 existing tests must pass after every task
  level: 3
- heading: PREREQUISITES
  level: 2
- heading: 'Expected: 253 tests passing'
  level: 1
- heading: Verify PostgreSQL connection
  level: 1
- heading: REQUIRED READING
  level: 2
- heading: TASKS
  level: 1
- heading: TASK 1 — Create gobp/core/db_config.py
  level: 2
- heading: TASK 2 — Rewrite gobp/core/db.py for PostgreSQL
  level: 2
- heading: TASK 3 — Update requirements.txt + .gitignore
  level: 2
---

(Auto-generated node file. Edit the YAML above or add body content below.)
