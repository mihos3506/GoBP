---
id: doc:wave_16a08_brief_65b376
type: Document
name: Wave 16A08 Brief
status: ACTIVE
created: '2026-04-17T09:25:07.761770+00:00'
updated: '2026-04-17T09:25:07.761770+00:00'
session_id: meta.session.2026-04-17.fe6be993a
source_path: waves/wave_16a08_brief.md
content_hash: sha256:adcb31f9a08488b2913a96e0ce35356c5ee9c36f4504d76efa4ddb9d4b84f69b
registered_at: '2026-04-17T09:25:07.761691+00:00'
last_verified: '2026-04-17T09:25:07.761691+00:00'
priority: high
sections:
- heading: WAVE 16A08 BRIEF — PROPER TEXT NORMALIZATION
  level: 1
- heading: CONTEXT
  level: 2
- heading: DESIGN
  level: 2
- heading: normalize_text() update
  level: 3
- heading: 'Before (Wave 16A07):'
  level: 1
- heading: 'After (Wave 16A08):'
  level: 1
- heading: Session exclusion — strict default
  level: 3
- heading: 'find: session → excludes Session (keyword matches text, not type)'
  level: 1
- heading: find:Session  → includes Session (explicit type filter)
  level: 1
- heading: 'find: session include_sessions=true → includes Session'
  level: 1
- heading: 'Rule: Session excluded unless:'
  level: 1
- heading: 1. type_filter == "Session" (explicit)
  level: 1
- heading: 2. include_sessions=true (explicit opt-in)
  level: 1
- heading: CURSOR EXECUTION RULES
  level: 2
- heading: PREREQUISITES
  level: 2
- heading: 'Expected: 507 tests passing'
  level: 1
- heading: Install unidecode
  level: 1
- heading: REQUIRED READING
  level: 2
- heading: TASKS
  level: 1
- heading: TASK 1 — Update normalize_text() with unidecode
  level: 2
---

(Auto-generated node file. Edit the YAML above or add body content below.)
