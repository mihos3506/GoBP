---
captured_in_session: session:2026-04-14_g
created: '2026-04-15T07:08:11.361799+00:00'
description: 'Lesson learned from Tests need GraphIndex but no shared fixture exists:
  F19: Missing gobp_root fixture'
id: missing_gobp_root_fixture.meta.93502464
legacy_id: meta.lesson:613056
mitigation: conftest.py gobp_root fixture as permanent fix (Wave 3)
name: 'F19: Missing gobp_root fixture'
session_id: session:2026-04-14_g
severity: medium
status: ACTIVE
tags:
- testing
- pytest
- fixtures
title: 'F19: Missing gobp_root fixture — no shared test fixture'
trigger: Tests need GraphIndex but no shared fixture exists
type: Lesson
updated: '2026-04-15T07:08:11.361799+00:00'
what_happened: Each test creates own tmp_path, leading to slow and inconsistent test
  runs
why_it_matters: Fixture proliferation slows CI and makes test output harder to reproduce
---

(Auto-generated node file. Edit the YAML above or add body content below.)
