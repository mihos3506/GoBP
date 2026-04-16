---
id: doc:workflow
type: Document
name: Workflow
status: ACTIVE
created: '2026-04-15T17:48:26.688250+00:00'
updated: '2026-04-15T17:48:26.688250+00:00'
session_id: session:2026-04-15_sequentially_import
source_path: waves/WORKFLOW.md
content_hash: sha256:74306f7573957e52f108a32d66305ebf0a0ac3535232ee2155509ebebb2e3db8
registered_at: '2026-04-15T17:48:26.688189+00:00'
last_verified: '2026-04-15T17:48:26.688189+00:00'
priority: medium
sections:
- heading: "WORKFLOW \u2014 GoBP Build Pipeline"
  level: 1
- heading: OVERVIEW
  level: 2
- heading: ACTORS
  level: 2
- heading: "CTO Chat (Claude Desktop) \u2014 Designer"
  level: 3
- heading: "Claude CLI \u2014 Orchestrator + Tier 3 Auditor"
  level: 3
- heading: "Cursor \u2014 Tier 1 Builder"
  level: 3
- heading: "Qodo \u2014 Tier 2 Tester"
  level: 3
- heading: "CEO \u2014 Escalation contact"
  level: 3
- heading: TASK GRANULARITY (CRITICAL RULE)
  level: 2
- heading: PIPELINE EXECUTION (per task)
  level: 2
- heading: "Step 1 \u2014 Read task"
  level: 3
- heading: "Step 2 \u2014 Dispatch to Cursor (Tier 1)"
  level: 3
- heading: "Step 3 \u2014 Test (Tier 2)"
  level: 3
- heading: "Step 4 \u2014 Audit (Tier 3)"
  level: 3
- heading: "Step 5 \u2014 Commit task"
  level: 3
- heading: "Step 6 \u2014 Escalate (only if blocked)"
  level: 3
- heading: RETRY POLICY
  level: 2
- heading: "Cursor failure \u2014 retry up to 3 times"
  level: 3
- heading: "Qodo failure \u2014 retry up to 2 times"
  level: 3
- heading: "Test failure \u2014 retry up to 3 times"
  level: 3
description: Imported document from waves/WORKFLOW.md with 20 indexed sections.
tags:
- document
spec_source: waves/WORKFLOW.md
---

(Auto-generated node file. Edit the YAML above or add body content below.)
