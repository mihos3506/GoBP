---
id: doc:wave_16a07_brief_7cf5a0
type: Document
name: Wave 16A07 Brief
status: ACTIVE
created: '2026-04-17T08:25:49.239649+00:00'
updated: '2026-04-17T08:25:49.239649+00:00'
session_id: meta.session.2026-04-17.baf3579ba
source_path: waves/wave_16a07_brief.md
content_hash: sha256:d250b506be6c084dd14d36e56548396e4422b6a1e84d764e8ea07239638bccf1
registered_at: '2026-04-17T08:25:49.239555+00:00'
last_verified: '2026-04-17T08:25:49.239555+00:00'
priority: high
sections:
- heading: WAVE 16A07 BRIEF — SEARCH FIX + EDGE TYPES + SESSION NOISE + DUPLICATE
    DETECTION
  level: 1
- heading: CONTEXT
  level: 2
- heading: DESIGN
  level: 2
- heading: Search improvements
  level: 3
- heading: gobp/core/search.py — new module
  level: 1
- heading: Session noise — exclude from default search
  level: 3
- heading: 'find: keyword → excludes Session by default'
  level: 1
- heading: 'find: keyword include_sessions=true → includes Session'
  level: 1
- heading: find:Session keyword → includes Session (explicit type filter)
  level: 1
- heading: depends_on + tested_by edge types
  level: 3
- heading: 'gobp/schema/core_edges.yaml — add:'
  level: 1
- heading: Duplicate detection
  level: 3
- heading: 'When creating a node, warn if similar name exists:'
  level: 1
- heading: create:Engine name='TrustGate Engine'
  level: 1
- heading: '→ Warning: "Similar nodes found: trustgate.meta.53299456 (Node),'
  level: 1
- heading: trustgate.ops.84166144 (Engine)"
  level: 1
- heading: → Node still created, but warning returned
  level: 1
- heading: CURSOR EXECUTION RULES
  level: 2
- heading: PREREQUISITES
  level: 2
- heading: 'Expected: 486 tests passing'
  level: 1
---

(Auto-generated node file. Edit the YAML above or add body content below.)
