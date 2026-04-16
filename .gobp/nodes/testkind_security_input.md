---
created: '2026-04-15T06:43:45.515314+00:00'
description: Tests input validation and injection resistance. SQL injection, XSS,
  fuzzing. Verifies system rejects malicious inputs safely.
extensible: true
group: security
id: testkind:security_input
name: Input Security Test
scope: universal
seed_examples:
- test SQL injection in login field
- test XSS in text input
- test fuzz API with random data
- test oversized input rejected
template:
  expected: System rejects safely
  field: Input field being tested
  input_type: Type of malicious input
  payload: Attack payload
type: TestKind
updated: '2026-04-15T06:43:45.515314+00:00'
---
