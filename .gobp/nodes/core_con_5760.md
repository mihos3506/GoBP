---
applies_to:
- TestKind
- TestCase
created: '2026-04-15T06:43:45.515314+00:00'
definition: 'GoBP organizes software tests into 3 levels: Level 1 (universal) — applies
  to all projects, pre-seeded on init; Level 2 (platform) — specific to Flutter, Deno,
  Web, etc., added by project; Level 3 (project) — custom kinds unique to this project.
  TestKind nodes define categories. TestCase nodes are individual test instances.'
description: 'GoBP organizes software tests into 3 levels: Level 1 (universal) — applies
  to all projects, pre-seeded on init; Level 2 (platform) — specific to Flutter, Deno,
  Web, etc., added by project; Level 3 (project) — custom kinds unique to this project.
  TestKind nodes define categories. TestCase nodes are individual test instances.'
extensible: true
id: core.con:5760
legacy_id: concept:test_taxonomy
name: Test Taxonomy
seed_values:
- functional
- non_functional
- security
- process
type: Concept
updated: '2026-04-15T06:43:45.515314+00:00'
usage_guide: 'To plan tests: (1) find(type=''TestKind'') to see available kinds. (2)
  Create TestCase nodes linked via of_kind edge to TestKind and via covers edge to
  the Feature/Node being tested. (3) Add platform kinds: node_upsert(type=''TestKind'',
  scope=''platform'', platform=''flutter''). (4) Check coverage: find(type=''TestCase'',
  covers=''feat:X'') to see all tests for a feature.'
---
