---
created: '2026-04-15T06:43:45.515314+00:00'
description: Tests data encryption at rest and in transit. Verifies sensitive data
  (tokens, PII, GPS, photos, payment info) is encrypted in storage and transmission.
extensible: true
group: security
id: test.kind:706752
legacy_id: testkind:security_encryption
name: Encryption Test
scope: universal
seed_examples:
- test auth token encrypted in local storage
- test PII not stored plaintext
- test GPS coords encrypted before transmitting
- test encryption key not hardcoded in source
template:
  check: How to verify encryption is applied
  data_type: Type of sensitive data
  encryption_standard: AES-256 / TLS 1.3 / etc.
  storage_or_transit: at_rest | in_transit
type: TestKind
updated: '2026-04-15T06:43:45.515314+00:00'
---
