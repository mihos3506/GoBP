# ◈ GoBP — Documentation Index
**Version:** v3  
**Date:** 2026-04-19

---

## GoBP LÀ GÌ

GoBP (Graph of Brainstorm Project) là persistent AI memory layer cho software projects.  
1 MCP tool: `gobp(query="...")` — AI agents đọc/ghi project knowledge qua đây.

```
Không có GoBP:           Có GoBP:
  Claude tab → forgets     Claude → GoBP → nhớ
  Cursor → no context      Cursor → GoBP → nhớ
  CEO giải thích lại       CEO giải thích 1 lần
  ~20,000 tokens/session   ~1,500 tokens/session
```

---

## READING ORDER

| Mục đích | Đọc file này |
|---|---|
| Hiểu system shape | ARCHITECTURE.md |
| Biết node types + fields | SCHEMA.md |
| Gọi gobp() đúng cách | MCP_PROTOCOL.md |
| Làm task cụ thể | COOKBOOK.md |
| Biết rules của role mình | AGENT_RULES.md |
| Ghi history đúng cách | HISTORY_SPEC.md |

**AI agent mới bắt đầu:**
1. SCHEMA.md — biết 2 templates
2. MCP_PROTOCOL.md — biết syntax
3. COOKBOOK.md — copy recipe cần dùng

---

## QUICK START

### Install
```bash
git clone https://github.com/mihos3506/GoBP.git
cd GoBP
python -m venv venv && venv\Scripts\activate
pip install -e .
python -m gobp.cli init
```

### Connect MCP (Claude CLI)
```json
{
  "gobp": {
    "type": "stdio",
    "command": "D:/GoBP/venv/Scripts/python.exe",
    "args": ["-m", "gobp.mcp.server"],
    "env": {
      "GOBP_PROJECT_ROOT": "D:/your-project",
      "GOBP_DB_URL": "postgresql://user:pass@localhost/gobp_project"
    }
  }
}
```

### Verify
```
gobp(query="ping:")     → {ok: true, nodes: N}
gobp(query="overview:") → project state
```

---

## CURRENT STATE (2026-04-19)

```
Schema:       v3 — 2 templates, ~75 node types
Waves done:   A, B, C, D, E, F, G
Protocol:     single tool gobp(); writes use edit: (v3 PG + file backup)
PostgreSQL:   primary storage (clean, schema v3)
Tests:        764+ passing
Viewer:       3D graph + Dashboard
Multi-agent:  import lock + validate v3 + session watchdog + ping
```

---

## DOC SET

| File | Mục đích |
|---|---|
| SCHEMA.md | 2 templates, node taxonomy, edge format |
| ARCHITECTURE.md | Layers, PostgreSQL, tiers, algorithms |
| MCP_PROTOCOL.md | gobp() syntax + 5 optimizations |
| COOKBOOK.md | 20 recipes thực tế |
| AGENT_RULES.md | Rules + self-learning loop cho 3 roles |
| HISTORY_SPEC.md | Khi nào ghi history, format |

---

## DEPRECATED — ĐÃ XÓA (Wave B + Wave G)

Các files sau đã được xóa hoặc thay thế:

```
  GoBP_ARCHITECTURE.md   → superseded by ARCHITECTURE.md
  MCP_TOOLS.md           → superseded by MCP_PROTOCOL.md
  GoBP_AI_USER_GUIDE.md  → merged into MCP_PROTOCOL.md + COOKBOOK.md
  GOBP_SCHEMA_REDESIGN_v2_1.md → implemented in SCHEMA.md v3
  INPUT_MODEL.md         → merged into COOKBOOK.md
  IMPORT_MODEL.md        → merged into COOKBOOK.md
  IMPORT_CHECKLIST.md    → merged into COOKBOOK.md + AGENT_RULES.md
```

**Wave G (2026-04-19):** `gobp/core/validator_v2.py` → merged into `validator.py`;  
`gobp/core/mutator.py` → replaced by `fs_mutator.py`; MCP `update:` / `retype:` removed (use `edit:`);  
lifecycle/read_order no longer applied in write defaults (ValidatorV2 `auto_fix` only);  
live-path tests removed from `test_wave16a02.py`; viewer undefined `VISIBLE_*` fixed; orphaned `.gobp-query` CSS removed.

---

*◈ GoBP — Where knowledge persists.*
