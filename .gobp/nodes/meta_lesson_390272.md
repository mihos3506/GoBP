---
captured_in_session: session:2026-04-15_add_wave13_decisions
created: '2026-04-15T18:14:15.049122+00:00'
description: 'Lesson learned from When loading many project artifacts into GoBP: Prefer
  sequential MCP imports'
id: meta.lesson:390272
legacy_id: lesson:ll130
mitigation: Use sequential import with per-item status logging and retry failures
  separately
name: Prefer sequential MCP imports
session_id: session:2026-04-15_add_wave13_decisions
severity: high
status: ACTIVE
title: Prefer sequential MCP imports
trigger: When loading many project artifacts into GoBP
type: Lesson
updated: '2026-04-15T18:14:15.049122+00:00'
what_happened: Parallel ingestion caused unstable feedback and user confusion
why_it_matters: Maintains deterministic progress and traceability for founder visibility
---

(Auto-generated node file. Edit the YAML above or add body content below.)
