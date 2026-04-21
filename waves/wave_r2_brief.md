# Wave R2 — Cache & async documentation

**Status:** COMPLETE (2026-04-20)  
**Goal:** Document cache invalidation semantics and async-vs-sync I/O policy for MCP; **no behavior change** in production code (docstrings + architecture only).

## Context

`GoBPCache` (LRU + per-entry TTL) and async `dispatch()` calling sync I/O were not fully specified in foundational docs. Wave R2 closes that gap so audits and onboarding match implementation.

## Tasks (4)

| # | Deliverable |
|---|-------------|
| 1 | `docs/ARCHITECTURE.md` **§9.4** — `GoBPCache`: in-process scope, LRU/TTL defaults (`max_size=500`, `default_ttl` per entry), `invalidate_all` after writes, multi-process limits. |
| 2 | `docs/ARCHITECTURE.md` **§16** — Async I/O strategy: sync file/PG in async MCP handler acceptable for current model; Option A default; when to consider `to_thread` or async drivers; `.cursorrules` constraints. |
| 3 | `gobp/core/cache.py` — class docstring + `invalidate_all` docstring reference §9.4. |
| 4 | `CHANGELOG.md` — Wave R2 entry. |

## Implementation note

Tasks 1 and 2 were applied in **one** documentation commit (same file). §9.4 text matches **actual** `GoBPCache` (TTL + LRU), not a hypothetical “no TTL / 1000 entries” draft.

## Tests

- `pytest tests/ -q --tb=no` — full fast suite after Task 4 (no code-path changes expected).

## Commits (reference)

- `docs: document cache invalidation + async I/O — Wave R2 Tasks 1–2`
- `docs(cache): reference invalidation policy in docstrings — Wave R2 Task 3`
- `docs: add Wave R2 to CHANGELOG — Wave R2 Task 4`

## Cross-references

- Cache policy: `docs/ARCHITECTURE.md` §9.4  
- Async policy: `docs/ARCHITECTURE.md` §16  
- Code: `gobp/core/cache.py`, `gobp/mcp/dispatcher.py`
