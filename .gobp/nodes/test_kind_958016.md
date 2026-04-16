---
created: '2026-04-15T06:43:45.515314+00:00'
description: Verifies consumer and provider agree on API shape, fields, and types.
  Prevents integration breaks.
extensible: true
group: functional
id: test.kind:958016
legacy_id: testkind:contract
name: Contract Test
scope: universal
seed_examples:
- test API response has required fields
- test field types match contract
- test error response format
template:
  given: Consumer expectation defined
  then: Response matches consumer contract
  when: Provider response received
type: TestKind
updated: '2026-04-15T06:43:45.515314+00:00'
---
