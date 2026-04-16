---
captured_in_session: session:2026-04-14_g
created: '2026-04-15T07:08:11.156170+00:00'
description: 'Lesson learned from Cursor disagrees with Brief code: F17: Silent substitution'
id: meta.lesson:418752
legacy_id: lesson:ll001
mitigation: 'R8 rule: Brief code is authoritative, STOP and escalate when Cursor deviates'
name: 'F17: Silent substitution'
session_id: session:2026-04-14_g
severity: high
status: ACTIVE
tags:
- cursor
- brief-compliance
- audit
title: 'F17: Silent substitution — Cursor ignores Brief code'
trigger: Cursor disagrees with Brief code
type: Lesson
updated: '2026-04-15T07:08:11.156170+00:00'
what_happened: Cursor substitutes own implementation silently instead of following
  the Brief's authoritative code exactly
why_it_matters: Breaks audit parity; Brief code is the spec, silent divergence causes
  cascading failures downstream
---

(Auto-generated node file. Edit the YAML above or add body content below.)
