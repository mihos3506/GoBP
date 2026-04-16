---
created: '2026-04-15T06:43:45.515314+00:00'
description: Ensures usability for people with disabilities. Follows WCAG 2.1 AA.
extensible: true
group: non_functional
id: testkind:accessibility
name: Accessibility Test
scope: universal
seed_examples:
- test color contrast >= 4.5:1
- test screen reader compatibility
- test keyboard navigation
template:
  component: UI element being tested
  criterion: Specific requirement
  standard: WCAG criterion
  tool: axe-core, VoiceOver, etc.
type: TestKind
updated: '2026-04-15T06:43:45.515314+00:00'
---
