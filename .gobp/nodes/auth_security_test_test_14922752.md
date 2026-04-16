---
created: '2026-04-15T06:43:45.515314+00:00'
description: Tests authentication, authorization, session management. Verifies only
  authorized users access resources. Covers JWT, OAuth, RBAC, brute force protection.
extensible: true
group: security
id: auth_security_test.test.14922752
legacy_id: test.kind:512448
name: Auth Security Test
scope: universal
seed_examples:
- test unauthorized access returns 401
- test expired token rejected
- test role-based access control
- test brute force lockout after N attempts
template:
  attack_vector: Type of auth attack
  expected_defense: How system should respond
  precondition: Initial state
  steps: Attack steps
type: TestKind
updated: '2026-04-15T06:43:45.515314+00:00'
---
