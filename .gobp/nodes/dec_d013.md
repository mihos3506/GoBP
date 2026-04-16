---
id: dec:d013
type: Decision
name: 'version: action returns protocol_version=2.0, schema_version=2.1, changelog,
  dep'
status: LOCKED
topic: gobp:mcp.protocol_version
what: 'version: action returns protocol_version=2.0, schema_version=2.1, changelog,
  deprecated_actions. All responses include _protocol field.'
why: AI clients need to detect protocol version to handle breaking changes. Implicit
  versioning caused silent routing errors.
alternatives_considered: []
risks: []
locked_by:
- CEO
- Claude-CLI
locked_at: '2026-04-16T02:39:55.502849+00:00'
session_id: session:2026-04-16_update_gobp_with_wav
created: '2026-04-16T02:39:55.502849+00:00'
updated: '2026-04-16T02:39:55.502849+00:00'
---

(Auto-generated node file. Edit the YAML above or add body content below.)
