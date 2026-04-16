---
captured_in_session: session:2026-04-15_add_wave13_decisions
created: '2026-04-15T18:14:16.710184+00:00'
description: 'Lesson learned from When evolving MCP write protocol: Use dry-run before
  high-impact write paths'
id: use_dry_run_before_high_impact_write_pat.meta.76725248
legacy_id: meta.lesson:167488
mitigation: Run dry_run flows and enforce guardrail response fields before rollout
name: Use dry-run before high-impact write paths
session_id: session:2026-04-15_add_wave13_decisions
severity: high
status: ACTIVE
title: Use dry-run before high-impact write paths
trigger: When evolving MCP write protocol
type: Lesson
updated: '2026-04-15T18:14:16.710184+00:00'
what_happened: Write-path changes can alter behavior silently across create/update/upsert/session/lock
why_it_matters: Risk of data corruption or unexpected side effects
---

(Auto-generated node file. Edit the YAML above or add body content below.)
