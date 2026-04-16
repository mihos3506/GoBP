---
alternatives_considered: []
created: '2026-04-16T05:05:22.356185+00:00'
id: mode_summary_brief_full_standard_for_fin.core.05851136
legacy_id: core.dec:9056
locked_at: '2026-04-16T05:05:22.356185+00:00'
locked_by:
- CEO
- Claude-CLI
name: 'mode=summary|brief|full|standard for find/get/related/get_batch. summary: id/typ'
risks: []
session_id: session:2026-04-16_capture_wave_16a01_k
status: LOCKED
topic: gobp:mcp.response_mode_system
type: Decision
updated: '2026-04-16T05:05:22.356185+00:00'
what: 'mode=summary|brief|full|standard for find/get/related/get_batch. summary: id/type/name/status/priority/edge_count/estimated_tokens/hint
  (~50 tokens). brief: summary + 5 key fields + outgoing_edges (~150 tokens). full:
  all fields + edges (current behavior). get_batch: fetches up to 50 nodes in one
  call.'
why: AI was loading full 500-token nodes when only needing name+type. Mode system
  lets AI choose payload size. estimated_tokens hint lets AI decide before fetching.
  get_batch reduces sequential roundtrips for multi-node detail.
---

(Auto-generated node file. Edit the YAML above or add body content below.)
