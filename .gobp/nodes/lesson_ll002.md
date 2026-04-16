---
id: lesson:ll002
type: Lesson
name: 'F19: Missing gobp_root fixture'
status: ACTIVE
created: '2026-04-15T07:08:11.361799+00:00'
updated: '2026-04-15T07:08:11.361799+00:00'
session_id: session:2026-04-14_g
title: "F19: Missing gobp_root fixture \u2014 no shared test fixture"
trigger: Tests need GraphIndex but no shared fixture exists
what_happened: Each test creates own tmp_path, leading to slow and inconsistent test
  runs
why_it_matters: Fixture proliferation slows CI and makes test output harder to reproduce
mitigation: conftest.py gobp_root fixture as permanent fix (Wave 3)
severity: medium
captured_in_session: session:2026-04-14_g
tags:
- testing
- pytest
- fixtures
description: 'Lesson learned from Tests need GraphIndex but no shared fixture exists:
  F19: Missing gobp_root fixture'
---

(Auto-generated node file. Edit the YAML above or add body content below.)
