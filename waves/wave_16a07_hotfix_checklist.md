# Wave 16A07 Hotfix Checklist (Audit Parallel)

Use this while Claude CLI runs fail-stop audit.

## 1) When audit FAIL arrives
- Capture failed task number and exact failing check.
- Reproduce locally with the narrowest command first (single test or single action).
- Keep fix scope inside the failed task only.
- Re-run full suite after fix (`pytest tests/ -q --tb=no`).

## 2) Fast commands
- Full tests:
  - `D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no`
- Replay common search queries:
  - `D:/GoBP/venv/Scripts/python.exe scripts/wave16a07_search_replay.py --root D:/MIHOS-v1 --mode summary`
- Save replay report:
  - `D:/GoBP/venv/Scripts/python.exe scripts/wave16a07_search_replay.py --root D:/MIHOS-v1 --json .gobp/history/w16a07_search_replay.json`

## 3) Triage map
- **Search quality issues**
  - check `gobp/core/search.py`
  - check `gobp/mcp/tools/read.py`
  - check `gobp/mcp/dispatcher.py` for `find:<Type>` behavior
- **Edge type issues**
  - check `gobp/schema/core_edges.yaml`
  - check `gobp/mcp/parser.py` guide examples
- **Duplicate warning issues**
  - check `gobp/mcp/tools/write.py` (`node_upsert`)
  - verify warnings format and backward compatibility in tests
- **Performance issues**
  - profile `node_upsert` path and index reload points
  - avoid broad changes; optimize only hot paths used in failing test

## 4) Commit discipline reminder
- 1 task = 1 commit
- exact message from brief
- no unrelated files staged
