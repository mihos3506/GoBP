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
Schema:     v3 — 2 templates, ~75 node types
Protocol:   v2 — single tool gobp(), 30+ actions
PostgreSQL: primary storage
Tests:      705+ (Wave A adds 35+, Wave B adds 12+)
Viewer:     3D graph (Page 1) + Dashboard (Page 2)
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

## DEPRECATED — ĐÃ XÓA (Wave B)

Các files sau đã được xóa khỏi repo:

```
  GoBP_ARCHITECTURE.md   → superseded by ARCHITECTURE.md
  MCP_TOOLS.md           → superseded by MCP_PROTOCOL.md
  GoBP_AI_USER_GUIDE.md  → merged into MCP_PROTOCOL.md + COOKBOOK.md
  GOBP_SCHEMA_REDESIGN_v2_1.md → implemented in SCHEMA.md v3
  INPUT_MODEL.md         → merged into COOKBOOK.md
  IMPORT_MODEL.md        → merged into COOKBOOK.md
  IMPORT_CHECKLIST.md    → merged into COOKBOOK.md + AGENT_RULES.md
```

---

*◈ GoBP — Where knowledge persists.*
