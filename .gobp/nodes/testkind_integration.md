---
created: '2026-04-15T06:43:45.515314+00:00'
description: Tests multiple modules or services working together. Includes DB, API,
  or service interactions.
extensible: true
group: functional
id: testkind:integration
name: Integration Test
scope: universal
seed_examples:
- test service A calls service B correctly
- test DB read after write
- test API returns correct response shape
template:
  given: Real dependencies available
  then: Integrated behavior matches spec
  when: Components interact
type: TestKind
updated: '2026-04-15T06:43:45.515314+00:00'
---
