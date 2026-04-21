# ◈ GoBP MCP PROTOCOL v2
**Status:** AUTHORITATIVE — v2 only  
**Date:** 2026-04-19  
**Supersedes:** MCP_TOOLS.md  
**Read after:** SCHEMA.md, ARCHITECTURE.md  
**Audience:** Mọi AI agent cần gọi gobp()

---

## SAU KHI ĐỌC FILE NÀY, AI BIẾT

1. Syntax chính xác của mọi gobp() action
2. Khi nào dùng action nào — và action nào NHANH HƠN
3. Token cost ước tính per action
4. 5 optimizations: context:, since=, mode=compact, import_atomic:, session:resume

---

## SINGLE TOOL

```
gobp(query="<action> <params>")
```

---

## SESSION START

```
Bước 1 — New session:
  gobp(query="overview:")
  gobp(query="session:start actor='{role}' goal='{goal}'")

Bước 1 — Resume session:
  gobp(query="session:resume id='{prev_session_id}'")
  → Nhận: pending handoff + graph changes since prev session
  → Token savings: ~70% session startup cost

role: cursor | claude_cli | cto_chat | ceo
```

---

## READ ACTIONS

### overview:
```
gobp(query="overview:")
gobp(query="overview: full_interface=true")

→ Project stats, node counts, active sessions
→ Token: ~800 (slim)
→ Rule: 1 LẦN đầu session
```

### context: ← KHUYẾN NGHỊ CHO CURSOR
```
gobp(query="context: task='{task description}'")

→ Server tự làm: FTS search → BFS expand → bundle context
→ Trả về: Flow + Engine + Table + Invariant + ErrorCase liên quan
→ 1 request thay vì 3-5 requests
→ Token: ~400-600
```

### find:
```
gobp(query="find: {keyword}")
gobp(query="find: {keyword} mode=summary")
gobp(query="find: {keyword} mode=brief")
gobp(query="find: {keyword} mode=compact")
gobp(query="find: {keyword} group='{group_path}'")
gobp(query="find: {keyword} page_size=50")
gobp(query="find: {keyword} cursor='{last_id}' page_size=50")

Modes:
  compact:  id + name + group (~10 tokens/node)
  summary:  + desc_l1 (~15 tokens/node)
  brief:    + desc_l2 + top edges (~40 tokens/node)

KHÔNG dùng blank find:
```

### get:
```
gobp(query="get: {node_id} mode=brief")
gobp(query="get: {node_id} mode=full")

→ brief: ~40 tokens | full: ~200+ tokens
```

### get_batch: ← TIÊU CHUẨN
```
gobp(query="get_batch: ids='{id1},{id2},{id3}' mode=brief")
gobp(query="get_batch: ids='{id1},{id2}' since='{updated_at}'")

→ since=: unchanged node = 5 tokens thay vì 40
→ Max: 10 nodes per batch
→ Rule: LUÔN dùng thay vì nhiều get: riêng lẻ
```

### explore:
```
gobp(query="explore: {keyword}")
gobp(query="explore: {node_id}")

→ Best-match node + edges + related trong 1 call
→ Token: ~200-400
```

### suggest:
```
gobp(query="suggest: {name}")

→ Check duplicate trước khi create
→ Rule: LUÔN chạy trước create:
```

### related:
```
gobp(query="related: {node_id} mode=summary")
gobp(query="related: {node_id} direction='outgoing'")
```

### signature:
```
gobp(query="signature: {node_id}")
→ name + group + desc_l1 (~20 tokens)
```

### recent:
```
gobp(query="recent: {n}")
→ N sessions gần nhất (~200 tokens)
```

### template:
```
gobp(query="template: {NodeType}")
→ Fields cho NodeType từ schema
→ Rule: Chạy trước lần đầu create NodeType mới
```

### tests:
```
gobp(query="tests: {node_id}")
gobp(query="tests: {node_id} status='FAILING'")
```

### stats:
```
gobp(query="stats:")
gobp(query="stats: reset")
```

### ping:
```
gobp(query="ping:")
→ ~20 tokens
```

### version:
```
gobp(query="version:")
```

---

## WRITE ACTIONS

**Tất cả write actions cần session_id.**

**Bắt buộc dùng Session trên graph (chặn session_id opaque do AI bịa):** đặt `GOBP_GRAPH_SESSION_ONLY=true` trong môi trường MCP — khi đó mọi write phải dùng đúng `session_id` từ `session:start` (hoặc `GOBP_SESSION_ID` trỏ tới cùng id đó); không còn chấp nhận chuỗi tự đặt / `audit:…` tự sinh khi thiếu id.

### NGUYÊN LÝ CỐT LÕI

```
Mọi thay đổi trong GoBP đều quy về 2 primitives:
  CREATE  — thêm node/edge mới
  DELETE  — xóa node/edge

edit: node = DELETE node cũ + CREATE node mới
             với content cũ + giá trị mới thay thế

Đây là graph primitive đúng nghĩa:
  Node không "mutate" — nó được thay thế
  Khi type/group thay đổi: ID mới được tạo
  Edges được rewire về node mới
```

### session:start / session:end / session:resume
```
gobp(query="session:start actor='{role}' goal='{goal}'")
→ Returns: {session_id: "meta.session.YYYY-MM-DD.xxx"}

gobp(query="session:resume id='{prev_sid}'")
→ Returns: {session_id, pending_handoff, changes_since_last_session}
→ Token savings: ~700 tokens

gobp(query="session:end outcome='{outcome}' handoff='{pending}'")
→ Rule: LUÔN end session khi xong
```

### batch: ← CÁCH WRITE CHÍNH
```
gobp(query="batch session_id='{sid}' ops='
  create: {Type}: {Name} | {description}
  create: {Type}: {Name} | {description} field="value"
  edit:   id="{node_id}" description="{new}"
  edit:   id="{node_id}" type="{NewType}"
  edge+:  {from_id} -- {to_id} reason="{reason}"
  edge-:  {from_id} -- {to_id}
  delete: id="{node_id}"
'")

Quy tắc:
  □ Nodes trước, edges sau
  □ Parent nodes trước child nodes
  □ Mixed types OK trong 1 batch
  □ Auto-chunk nếu > 50 ops
  □ Edge type do hệ thống infer
  □ Nếu op fail → chỉ retry failed op
```

### create:
```
gobp(query="create:{NodeType} name='{name}' session_id='{sid}'")
gobp(query="create:{NodeType} name='{name}' session_id='{sid}' dry_run=true")

→ id auto-generated nếu không truyền
→ Prefer batch: cho nhiều nodes
```

### edit: ← THAY THẾ update: VÀ retype:
```
gobp(query="edit: id='{node_id}' description='{new}' session_id='{sid}'")
gobp(query="edit: id='{node_id}' type='{NewType}' session_id='{sid}'")
gobp(query="edit: id='{node_id}' name='{new}' type='{NewType}' session_id='{sid}'")
gobp(query="edit: id='{node_id}' add_edge='{to_id}' reason='{reason}' session_id='{sid}'")
gobp(query="edit: id='{node_id}' remove_edge='{to_id}' session_id='{sid}'")
gobp(query="edit: id='{node_id}' expected_updated_at='{ts}' session_id='{sid}'")

Bản chất: DELETE node cũ + CREATE node mới
  Nếu chỉ đổi description/code/history:
    → Tạo version mới, ID giữ nguyên

  Nếu đổi type hoặc group:
    → ID mới (từ type/group mới)
    → Delete node cũ
    → Edges được rewire về node mới
    → Lịch sử history[] được kế thừa

  Nếu add_edge/remove_edge:
    → Thêm hoặc xóa edge liên quan node này

  expected_updated_at: optimistic lock
    → Nếu node đã bị ai khác sửa → conflict_warning trong response
    → Không block write, agent tự quyết
```

### upsert:
```
gobp(query="upsert:{NodeType} dedupe_key='name' name='{name}' session_id='{sid}'")

→ Create nếu chưa có, edit nếu đã có
→ Idempotent import
```

### delete:
```
gobp(query="delete: {node_id} session_id='{sid}'")

→ Soft delete → archive
→ History log ghi lại
```

### import_atomic: ← IDEMPOTENT IMPORT
```
gobp(query="import_atomic: session_id='{sid}' ops='
  ensure: {Name} | {description}
  ensure: {Name} | {description}
  edge+: {from} -- {to} reason='{reason}'
'")

ensure: = create nếu chưa có, skip nếu đã có
→ Response: {created: N, existed: M, edges: K}
→ An toàn để chạy nhiều lần
```

---

## MAINTENANCE ACTIONS

### validate:
```
gobp(query="validate: metadata")
gobp(query="validate: all")
→ Chạy trước session:end
```

### dedupe:
```
gobp(query="dedupe: edges")
→ Sau batch lớn
```

### recompute:
```
gobp(query="recompute: priorities dry_run=true")
gobp(query="recompute: priorities session_id='{sid}'")
```

### refresh:
```
gobp(query="refresh:")
→ Force reload GraphIndex
```

### import:
```
gobp(query="import: {path/to/doc.md} session_id='{sid}'")
gobp(query="commit: imp:{proposal_id}")
```

---

## TOKEN GUIDE

```
Action                        Tokens    Notes
──────────────────────────────────────────────────────
overview:                     ~800      1x/session
session:resume                ~300      thay overview+recent
context: task='...'           ~400-600  full task context
find: compact 20 nodes        ~200
find: summary 20 nodes        ~300
find: brief 20 nodes          ~800
get: brief                    ~40
get: full                     ~200+
get_batch: 5 brief            ~200
get_batch: 10 brief           ~400
get_batch: since= unchanged   ~25
explore:                      ~300
suggest:                      ~300
related: summary              ~200
template:                     ~200
batch: response               ~100
import_atomic: response       ~50
session:start/end             ~50
validate: metadata            ~200
ping:                         ~20

SESSION BUDGET:
  New session:    ~2,000 tokens
  Resume session: ~600 tokens
  Task context:   ~400-600 tokens
```

---

## ANTI-PATTERNS

```
✗ Nhiều get: riêng lẻ → dùng get_batch:
✗ overview: nhiều lần → dùng session:resume
✗ find: blank query → vô ích
✗ create không suggest: trước → duplicate risk
✗ Write không session_id → không trace được
✗ Không session:end → IN_PROGRESS mãi
✗ get: full khi brief đủ → lãng phí
✗ Import nhiều lần → dùng import_atomic:
✗ Khai báo edge type → hệ thống tự infer
✗ Không gửi expected_updated_at → conflict im lặng
```

---

## QUICK REFERENCE

```
Mục đích                          Action
────────────────────────────────────────────────────────
Bắt đầu session mới               overview: + session:start
Tiếp tục session cũ               session:resume id='...'
Lấy context cho 1 task            context: task='...'
Tìm node                          find: {keyword} mode=compact
Lấy nhiều nodes                   get_batch: ids='a,b,c'
Lấy nodes đã changed              get_batch: ids='a,b,c' since='{ts}'
Overview 1 concept                explore: {keyword}
Check duplicate                   suggest: {name}
Tạo nodes + edges                 batch: ops='...'
Sửa node/edge/type/group          edit: id='x' ...
Import idempotent                 import_atomic: ops='...'
Kết thúc session                  session:end outcome='...'
Kiểm tra graph                    validate: metadata
Health check                      ping:
```

---

*GoBP MCP PROTOCOL v2 — 2026-04-19*  
*Supersedes: MCP_TOOLS.md*  
*edit: = delete + create — graph primitive đúng nghĩa*  
◈
