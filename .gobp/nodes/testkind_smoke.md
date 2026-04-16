---
created: '2026-04-15T06:43:45.515314+00:00'
description: Basic sanity check after deploy. Verifies critical paths before full
  testing.
extensible: true
group: process
id: testkind:smoke
name: Smoke Test
scope: universal
seed_examples:
- app launches without crash
- login endpoint responds 200
- home screen loads
template:
  check: Minimum viable check
  feature: Critical feature
  pass_condition: What passing looks like
type: TestKind
updated: '2026-04-15T06:43:45.515314+00:00'
---
