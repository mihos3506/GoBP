---
captured_in_session: session:2026-04-15_add_wave13_decisions
created: '2026-04-15T18:14:15.883911+00:00'
description: 'Lesson learned from Before creating typed nodes with strict id patterns:
  Validate schema prefixes before create'
id: meta.lesson:778880
legacy_id: lesson:ll131
mitigation: Use explicit ids matching type prefixes for Entity/Feature/Repository/Flow/APIEndpoint/etc.
name: Validate schema prefixes before create
session_id: session:2026-04-15_add_wave13_decisions
severity: critical
status: ACTIVE
title: Validate schema prefixes before create
trigger: Before creating typed nodes with strict id patterns
type: Lesson
updated: '2026-04-15T18:14:15.883911+00:00'
what_happened: Auto node id generation for typed nodes can mismatch schema prefix
  requirements
why_it_matters: Failed writes waste interaction cycles and obscure intent
---

(Auto-generated node file. Edit the YAML above or add body content below.)
