---
created: '2026-04-15T06:43:45.515314+00:00'
description: 'Tests communication layer security: TLS/HTTPS enforcement, no cleartext
  HTTP, certificate pinning, MITM protection. Critical for mobile apps.'
extensible: true
group: security
id: testkind:security_network
name: Network Security Test
scope: universal
seed_examples:
- test all traffic uses HTTPS not HTTP
- test TLS 1.2+ enforced
- test certificate pinning prevents MITM
- test no sensitive data in URL params or headers
template:
  check: Security property to verify
  expected: Encrypted, certificate valid, no cleartext
  protocol: Network protocol being tested
  tool: Proxy/scanner (Burp Suite, ZAP, Wireshark)
type: TestKind
updated: '2026-04-15T06:43:45.515314+00:00'
---
