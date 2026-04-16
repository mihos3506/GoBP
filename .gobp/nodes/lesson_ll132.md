---
id: lesson:ll132
type: Lesson
name: Use dry-run before high-impact write paths
status: ACTIVE
created: '2026-04-15T18:14:16.710184+00:00'
updated: '2026-04-15T18:14:16.710184+00:00'
session_id: session:2026-04-15_add_wave13_decisions
title: Use dry-run before high-impact write paths
trigger: When evolving MCP write protocol
what_happened: Write-path changes can alter behavior silently across create/update/upsert/session/lock
why_it_matters: Risk of data corruption or unexpected side effects
mitigation: Run dry_run flows and enforce guardrail response fields before rollout
severity: high
captured_in_session: session:2026-04-15_add_wave13_decisions
description: 'Lesson learned from When evolving MCP write protocol: Use dry-run before
  high-impact write paths'
---

(Auto-generated node file. Edit the YAML above or add body content below.)
