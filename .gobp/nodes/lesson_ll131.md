---
id: lesson:ll131
type: Lesson
name: Validate schema prefixes before create
status: ACTIVE
created: '2026-04-15T18:14:15.883911+00:00'
updated: '2026-04-15T18:14:15.883911+00:00'
session_id: session:2026-04-15_add_wave13_decisions
title: Validate schema prefixes before create
trigger: Before creating typed nodes with strict id patterns
what_happened: Auto node id generation for typed nodes can mismatch schema prefix
  requirements
why_it_matters: Failed writes waste interaction cycles and obscure intent
mitigation: Use explicit ids matching type prefixes for Entity/Feature/Repository/Flow/APIEndpoint/etc.
severity: critical
captured_in_session: session:2026-04-15_add_wave13_decisions
description: 'Lesson learned from Before creating typed nodes with strict id patterns:
  Validate schema prefixes before create'
---

(Auto-generated node file. Edit the YAML above or add body content below.)
