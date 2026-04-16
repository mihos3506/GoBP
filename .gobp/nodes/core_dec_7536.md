---
alternatives_considered: []
created: '2026-04-16T05:05:14.360757+00:00'
id: core.dec:7536
legacy_id: dec:d015
locked_at: '2026-04-16T05:05:14.360757+00:00'
locked_by:
- CEO
- Claude-CLI
name: priority_score = incoming_edges + outgoing_edges + TIER_WEIGHTS[node_type].
  TIER
risks: []
session_id: session:2026-04-16_capture_wave_16a01_k
status: LOCKED
topic: gobp:mcp.numeric_priority
type: Decision
updated: '2026-04-16T05:05:14.360757+00:00'
what: 'priority_score = incoming_edges + outgoing_edges + TIER_WEIGHTS[node_type].
  TIER_WEIGHTS: Invariant=20, Decision=15, Engine/Flow/Entity=10, Feature/Screen/APIEndpoint=5,
  Document/TestCase/Lesson=2, Node/Idea/Concept=3, TestKind=1, Session/Wave/Repository=0.
  Thresholds: 0-4=low, 5-9=medium, 10-19=high, 20+=critical.'
why: 'Manual priority assignment was subjective and drifted. Numeric formula from
  graph topology gives consistent, auto-recomputable signal. recompute: priorities
  updates all nodes in batch.'
---

(Auto-generated node file. Edit the YAML above or add body content below.)
