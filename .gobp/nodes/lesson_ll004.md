---
id: lesson:ll004
type: Lesson
name: Dishonest performance fix
status: ACTIVE
created: '2026-04-15T07:08:11.776108+00:00'
updated: '2026-04-15T07:08:11.776108+00:00'
session_id: session:2026-04-14_g
title: "Dishonest performance fix \u2014 manipulating tests instead of fixing code"
trigger: Performance tests failing
what_happened: Test measurement was altered to make failing performance tests pass
  without fixing the actual slow code path
why_it_matters: False green CI masks real perf regressions; production users still
  hit the slow path
mitigation: Always fix root cause; never manipulate test thresholds or measurement
  to achieve a pass
severity: critical
captured_in_session: session:2026-04-14_g
tags:
- testing
- performance
- integrity
description: 'Lesson learned from Performance tests failing: Dishonest performance
  fix'
---

(Auto-generated node file. Edit the YAML above or add body content below.)
