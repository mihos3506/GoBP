---
id: lesson:ll001
type: Lesson
name: 'F17: Silent substitution'
status: ACTIVE
created: '2026-04-15T07:08:11.156170+00:00'
updated: '2026-04-15T07:08:11.156170+00:00'
session_id: session:2026-04-14_g
title: "F17: Silent substitution \u2014 Cursor ignores Brief code"
trigger: Cursor disagrees with Brief code
what_happened: Cursor substitutes own implementation silently instead of following
  the Brief's authoritative code exactly
why_it_matters: Breaks audit parity; Brief code is the spec, silent divergence causes
  cascading failures downstream
mitigation: 'R8 rule: Brief code is authoritative, STOP and escalate when Cursor deviates'
severity: high
captured_in_session: session:2026-04-14_g
tags:
- cursor
- brief-compliance
- audit
description: 'Lesson learned from Cursor disagrees with Brief code: F17: Silent substitution'
---

(Auto-generated node file. Edit the YAML above or add body content below.)
