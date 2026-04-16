---
created: '2026-04-15T06:43:45.515314+00:00'
description: Tests a single function, method, or class in isolation. Fast, no external
  dependencies.
extensible: true
group: functional
id: testkind:unit
name: Unit Test
scope: universal
seed_examples:
- test happy path
- test null/empty input
- test boundary values
- test error handling
template:
  given: Known input state
  then: Expected output or state change
  when: Function called with specific input
type: TestKind
updated: '2026-04-15T06:43:45.515314+00:00'
---
