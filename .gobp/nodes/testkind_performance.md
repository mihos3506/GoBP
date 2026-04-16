---
created: '2026-04-15T06:43:45.515314+00:00'
description: Measures responsiveness, speed, throughput, and stability under load.
extensible: true
group: non_functional
id: testkind:performance
name: Performance Test
scope: universal
seed_examples:
- test response < 200ms at 100 concurrent users
- test app startup < 2s
- test API throughput under load
template:
  scenario: Load profile description
  threshold: Acceptable latency/throughput target
  tool: Tool used (k6, Locust, etc.)
type: TestKind
updated: '2026-04-15T06:43:45.515314+00:00'
---
