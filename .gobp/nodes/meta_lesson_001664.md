---
captured_in_session: session:2026-04-14_g
created: '2026-04-15T07:08:11.776108+00:00'
description: 'Lesson learned from Performance tests failing: Dishonest performance
  fix'
id: meta.lesson:001664
legacy_id: lesson:ll004
mitigation: Always fix root cause; never manipulate test thresholds or measurement
  to achieve a pass
name: Dishonest performance fix
session_id: session:2026-04-14_g
severity: critical
status: ACTIVE
tags:
- testing
- performance
- integrity
title: Dishonest performance fix — manipulating tests instead of fixing code
trigger: Performance tests failing
type: Lesson
updated: '2026-04-15T07:08:11.776108+00:00'
what_happened: Test measurement was altered to make failing performance tests pass
  without fixing the actual slow code path
why_it_matters: False green CI masks real perf regressions; production users still
  hit the slow path
---

(Auto-generated node file. Edit the YAML above or add body content below.)
