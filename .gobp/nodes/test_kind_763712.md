---
created: '2026-04-15T06:43:45.515314+00:00'
description: Tests across devices, OS versions, screen sizes, and configurations.
extensible: true
group: non_functional
id: test.kind:763712
legacy_id: testkind:compatibility
name: Compatibility Test
scope: universal
seed_examples:
- test on Android 10+
- test on iOS 15+
- test on small screen 320px width
template:
  given: Target device/OS/browser
  then: Works correctly on target
  when: Feature is used
type: TestKind
updated: '2026-04-15T06:43:45.515314+00:00'
---
