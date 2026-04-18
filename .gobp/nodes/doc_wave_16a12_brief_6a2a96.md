---
id: doc:wave_16a12_brief_6a2a96
type: Document
name: Wave 16A12 Brief
status: ACTIVE
created: '2026-04-18T02:52:39.473735+00:00'
updated: '2026-04-18T02:52:39.473735+00:00'
session_id: meta.session.2026-04-18.fc882e70c
source_path: waves/wave_16a12_brief.md
content_hash: sha256:53f5b0e48c83c10ae84f629e5593ff15a055e0ef8316ea0b2b611d494d2e83a4
registered_at: '2026-04-18T02:52:39.473639+00:00'
last_verified: '2026-04-18T02:52:39.473639+00:00'
priority: high
sections:
- heading: WAVE 16A12 BRIEF — SERVER CACHE
  level: 1
- heading: CONTEXT
  level: 2
- heading: DESIGN
  level: 2
- heading: Server-level cache
  level: 3
- heading: gobp/mcp/server.py
  level: 1
- heading: Read path — use cache
  level: 3
- heading: 'Current (every call reloads):'
  level: 1
- heading: 'After (use cache):'
  level: 1
- heading: Write path — update cache after write
  level: 3
- heading: 'Read-only actions: use cache directly'
  level: 1
- heading: 'Write actions: after write, update cache'
  level: 1
- heading: Batch write — update cache with working_index
  level: 3
- heading: 'In batch_action after single-save:'
  level: 1
- heading: Update server cache with the working_index (already has all new data)
  level: 1
- heading: This avoids reload from disk after batch
  level: 1
- heading: Cache invalidation strategy
  level: 3
- heading: 'refresh: action'
  level: 3
- heading: CURSOR EXECUTION RULES
  level: 2
- heading: PREREQUISITES
  level: 2
- heading: 'Expected: 581 tests'
  level: 1
---

(Auto-generated node file. Edit the YAML above or add body content below.)
