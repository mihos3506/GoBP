---
created: '2026-04-15T06:43:45.515314+00:00'
description: Verifies new changes do not break existing functionality. Run after every
  change.
extensible: true
group: functional
id: regression_test.test.44282880
legacy_id: test.kind:929536
name: Regression Test
scope: universal
seed_examples:
- re-run all unit tests after refactor
- verify login still works after auth change
template:
  given: Feature was working before change
  then: Feature still works as before
  when: Change is deployed
type: TestKind
updated: '2026-04-15T06:43:45.515314+00:00'
---
