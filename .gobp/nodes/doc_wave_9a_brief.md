---
id: doc:wave_9a_brief
type: Document
name: "WAVE 9A BRIEF \u2014 SQLITE PERSISTENT INDEX + LRU CACHE"
source_path: waves/wave_9a_brief.md
content_hash: sha256:716693dbdd875521cd0121fee5dc6c475a020b5ce9767edafd28ed4da5d9b911
registered_at: '2026-04-15T07:05:19.012292+00:00'
last_verified: '2026-04-15T07:05:19.012292+00:00'
created: '2026-04-15T07:05:19.012292+00:00'
updated: '2026-04-15T07:05:19.012292+00:00'
sections:
- level: 1
  title: "WAVE 9A BRIEF \u2014 SQLITE PERSISTENT INDEX + LRU CACHE"
- level: 2
  title: CONTEXT
- level: 2
  title: "CURSOR EXECUTION RULES (READ FIRST \u2014 NON-NEGOTIABLE)"
- level: 3
  title: "R1 \u2014 Sequential execution"
- level: 3
  title: "R2 \u2014 Discovery before creation"
- level: 3
  title: "R3 \u2014 1 task = 1 commit"
- level: 3
  title: "R4 \u2014 Docs are supreme authority"
- level: 3
  title: "R5 \u2014 Document disagreement = STOP"
- level: 3
  title: "R6 \u2014 3 retries = STOP"
- level: 3
  title: "R7 \u2014 No scope creep"
- level: 3
  title: "R8 \u2014 Brief code blocks are authoritative"
- level: 3
  title: "R9 \u2014 Backward compatibility is mandatory"
- level: 2
  title: STOP REPORT FORMAT
- level: 2
  title: AUTHORITATIVE SOURCE
- level: 2
  title: PREREQUISITES
- level: 1
  title: 'Expected: 200 tests passing'
- level: 1
  title: 'Baseline: gobp_overview ~460ms, others ~60ms'
- level: 2
  title: "REQUIRED READING \u2014 WAVE START"
- level: 1
  title: TASKS
- level: 2
  title: "TASK 1 \u2014 Create gobp/core/db.py (SQLite index manager)"
- level: 2
  title: "TASK 2 \u2014 Create gobp/core/cache.py (LRU cache with TTL)"
- level: 1
  title: Module-level singleton for MCP server use
- level: 2
  title: "TASK 3 \u2014 Modify gobp/core/graph.py to use SQLite index"
- level: 2
  title: "TASK 4 \u2014 Add write-through SQLite update in mutator.py"
- level: 2
  title: "TASK 5 \u2014 Modify gobp/mcp/server.py to use SQLite + cache for gobp_overview"
- level: 2
  title: "TASK 6 \u2014 Add --reindex flag to gobp validate CLI command"
- level: 2
  title: "TASK 7 \u2014 Update .gitignore for index.db"
- level: 1
  title: GoBP derived files
- level: 2
  title: "TASK 8 \u2014 Write tests for db.py and cache.py"
- level: 1
  title: "\u2500\u2500 Cache tests \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\
    \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\
    \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\
    \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\
    \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\
    \u2500\u2500\u2500"
- level: 1
  title: "\u2500\u2500 SQLite db tests \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\
    \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\
    \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\
    \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\
    \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500"
- level: 1
  title: 'Expected: ~19 tests passing'
- level: 2
  title: "TASK 9 \u2014 Performance verification + CHANGELOG update"
- level: 1
  title: 'Expected: 219+ tests passing (200 + ~19 new)'
- level: 2
  title: "[Wave 9A] \u2014 SQLite Persistent Index + LRU Cache \u2014 2026-04-15"
- level: 3
  title: Added
- level: 3
  title: Changed
- level: 3
  title: Performance improvement vs Wave H baseline
- level: 3
  title: 'Total after wave: 14 MCP tools, 219+ tests passing'
- level: 1
  title: POST-WAVE VERIFICATION
- level: 1
  title: All tests pass
- level: 1
  title: 'Expected: 219+ tests'
- level: 1
  title: Performance within targets
- level: 1
  title: 'Expected: all < max latency targets'
- level: 1
  title: SQLite index created on init
- level: 1
  title: 'Expected: True'
- level: 1
  title: Reindex works
- level: 1
  title: 'Expected: prints rebuild message + validation result'
- level: 1
  title: Git log
- level: 1
  title: 'Expected: 9 Wave 9A commits'
- level: 1
  title: CEO DISPATCH INSTRUCTIONS
- level: 2
  title: "1. Copy Brief v\xE0o repo"
- level: 1
  title: Save wave_9a_brief.md to D:\GoBP\waves\wave_9a_brief.md
- level: 2
  title: 2. Dispatch Cursor
- level: 2
  title: 3. Audit Claude CLI
- level: 2
  title: 4. Push
- level: 1
  title: WHAT COMES NEXT
tags:
- wave
- brief
- wave-9a
status: ACTIVE
description: Imported document from waves/wave_9a_brief.md with 57 indexed sections.
spec_source: waves/wave_9a_brief.md
---

(Auto-generated node file. Edit the YAML above or add body content below.)
