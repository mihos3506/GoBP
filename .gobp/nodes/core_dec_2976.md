---
alternatives_considered: []
created: '2026-04-15T07:07:53.448146+00:00'
description: 'Locked decision for gobp:performance.index_design: GraphIndex uses dict-based
  type indexes (_nodes_by_type_idx) not O(n) scans'
id: core.dec:2976
legacy_id: dec:d002
locked_at: '2026-04-15T07:07:53.448146+00:00'
locked_by:
- CTO-Chat
- Claude-CLI-Audit
name: GraphIndex uses dict-based type indexes (_nodes_by_type_idx) not O(n) scans
risks: []
session_id: session:2026-04-14_g
status: LOCKED
topic: gobp:performance.index_design
type: Decision
updated: '2026-04-15T07:07:53.448146+00:00'
what: GraphIndex uses dict-based type indexes (_nodes_by_type_idx) not O(n) scans
why: 'Wave 9A: nodes_by_type() was O(n) scan, fixed to O(1) dict lookup'
---

(Auto-generated node file. Edit the YAML above or add body content below.)
