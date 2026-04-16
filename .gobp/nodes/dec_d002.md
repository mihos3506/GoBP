---
id: dec:d002
type: Decision
name: GraphIndex uses dict-based type indexes (_nodes_by_type_idx) not O(n) scans
status: LOCKED
topic: gobp:performance.index_design
what: GraphIndex uses dict-based type indexes (_nodes_by_type_idx) not O(n) scans
why: 'Wave 9A: nodes_by_type() was O(n) scan, fixed to O(1) dict lookup'
alternatives_considered: []
risks: []
locked_by:
- CTO-Chat
- Claude-CLI-Audit
locked_at: '2026-04-15T07:07:53.448146+00:00'
session_id: session:2026-04-14_g
created: '2026-04-15T07:07:53.448146+00:00'
updated: '2026-04-15T07:07:53.448146+00:00'
description: 'Locked decision for gobp:performance.index_design: GraphIndex uses dict-based
  type indexes (_nodes_by_type_idx) not O(n) scans'
---

(Auto-generated node file. Edit the YAML above or add body content below.)
