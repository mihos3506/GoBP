---
created: '2026-04-15T06:43:45.515314+00:00'
description: 'Tests API endpoint security per OWASP API Top 10: broken access control,
  excessive data exposure, rate limiting, injection, security misconfiguration.'
extensible: true
group: security
id: testkind:security_api
name: API Security Test
scope: universal
seed_examples:
- test endpoint requires valid JWT
- test rate limiting after 100 req/min
- test no excessive data exposure in response
- test CORS policy restricts origins
template:
  attack: Test attack or check description
  endpoint: API endpoint being tested
  expected: API handles safely
  owasp_category: OWASP API risk category
type: TestKind
updated: '2026-04-15T06:43:45.515314+00:00'
---
