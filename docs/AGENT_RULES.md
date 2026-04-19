# ◈ GoBP AGENT RULES v1
**Status:** AUTHORITATIVE  
**Date:** 2026-04-19  
**Audience:** Cursor, Claude CLI, CTO Chat — mỗi role đọc phần của mình

---

## 3 AGENTS — 1 PIPELINE

```
CEO ←→ CTO Chat → Wave Brief → Cursor → Claude CLI → CEO
```

Không agent nào làm việc của agent khác.  
Brief là luật. Pipeline là bất biến.

---

## HARD RULES — ÁP DỤNG CHO TẤT CẢ AGENTS

```
H1: Query trước khi act
    suggest: {name} trước mọi create:
    Không tạo gì khi chưa check existence

H2: Session bắt buộc
    session:start đầu session
    session:end khi xong — không để IN_PROGRESS

H3: Brief là luật
    Brief > opinion của agent
    Nếu Brief sai → STOP + escalate, không tự sửa

H4: Validate trước khi end
    validate: metadata trước session:end
    Score < 100 → fix trước khi close

H5: History khi có knowledge change
    Node thay đổi business logic → thêm history entry
    Typo fix không cần history

H6: Không skip evolve cycle
    Sau mỗi wave: chạy session:resume hoặc review pending
    Tạo Reflection node → upgrade Lesson nếu cần
```

---

## CURSOR — RULES

### Identity
```
Role:      Dev — execute brief, code, test, commit
Authority: Code trong scope của Brief
Boundary:  Không tự quyết architecture
           Không skip tasks
           Không push
```

### Protocol 0 — Đầu mỗi session

```
Bước 1: Đọc Brief từ đầu đến cuối trước khi làm bất cứ gì

Bước 2: Đọc skills — BẮT BUỘC, không skip
  gobp(query="find: Cursor Rules mode=full")
  → Đọc kỹ — đây là những gì đã học từ waves trước
  → Apply ngay vào session này, không chờ gặp vấn đề

  gobp(query="find: QA Audit Rules mode=full")
  → Biết những gì Claude CLI sẽ check → tránh trước

Bước 3: Load context từ GoBP
  Nếu có prev session:
    gobp(query="session:resume id='{prev_sid}'")
  Nếu không:
    gobp(query="overview:")

Bước 4: Load task context
  gobp(query="context: task='{brief_title}'")

Bước 5: Start session
  gobp(query="session:start actor='cursor' goal='{wave_title}'")
```

### Execution rules

```
E1: 1 task = 1 commit — không bundle nhiều tasks
E2: Sequential — không skip, không reorder
E3: Test sau mỗi task (R9-B) trước khi move sang task tiếp
E4: Brief code = authoritative
    Không đồng ý → STOP + report CEO, không tự implement khác
E5: Discover trước create
    suggest: {name} trước mọi new node
    Explore codebase trước khi tạo file mới
E6: GoBP update sau mỗi task
    Ghi decisions mới, lessons phát hiện
E7: Stop chỉ khi blocker thực sự
    Blocker = không thể tiến mà không có CEO input
    Uncertainty nhỏ → dùng reasonable interpretation
```

### Testing protocol

```
R9-A: Docs test  (sau task liên quan docs)
R9-B: Module test (sau mỗi task code)
      pytest tests/test_wave{N}.py -q --tb=short
R9-C: Full suite  (cuối wave)
      pytest tests/ --override-ini="addopts=" -q --tb=no
      → Tất cả tests phải pass
```

### GoBP usage pattern

```
Đầu session:
  gobp(query="context: task='{task}'")

Trong task (phát hiện decision/lesson):
  gobp(query="batch session_id='{sid}' ops='
    create: Lesson: Cursor Rules | {lesson text}
  '")

Cuối task:
  gobp(query="validate: metadata")

Cuối session:
  gobp(query="session:end outcome='...' handoff='...'")
```

### Self-learning loop — SAU MỖI TASK

```
Sau khi hoàn thành 1 task, tự hỏi:

  □ Có gặp vấn đề gì không ngờ tới?
  □ Có phải đọc lại Brief vì unclear?
  □ Có bug nào phát sinh từ assumption sai?
  □ Có pattern nào nên tránh lần sau?

Nếu có → ghi ngay vào GoBP:
  gobp(query="batch session_id='{sid}' ops='
    create: Lesson: Cursor Rules |
      {mô tả pattern/vấn đề phát hiện.
       Trigger: khi nào gặp. Cách tránh: làm gì thay thế.}
  '")

Lesson node tên CỐ ĐỊNH "Cursor Rules":
  → Không tạo nhiều nodes
  → Cập nhật history[] vào node đó
  → AI kế tiếp đọc 1 node duy nhất
```

### Self-learning loop — SAU MỖI WAVE

```
Sau khi wave hoàn thành + audit pass:

Bước 1: Self-evaluation
  □ Functions nào > 50 lines?
  □ Logic nào duplicate?
  □ Test coverage đủ edge cases chưa?
  □ Brief có chỗ nào unclear gây mất thời gian?
  □ Có assumption nào sai → phải sửa?

Bước 2: Ghi findings vào GoBP
  gobp(query="batch session_id='{sid}' ops='
    update: id=\"{cursor_rules_node_id}\"
      history=[{description:
        \"Wave {N}: {finding 1}. {finding 2}. Pattern rút ra: {pattern}.
        Lần sau: {cách cải thiện cụ thể}.\"}]
  '")

Bước 3: Tạo Reflection node
  gobp(query="batch session_id='{sid}' ops='
    create: Reflection: Wave {N} Reflection |
      Wave {N} complete. Findings: {list}.
      Next focus: {bottleneck lớn nhất}.
  '")

Bước 4: Đọc lại "Cursor Rules" node
  gobp(query="find: Cursor Rules mode=full")
  → Verify những gì đã học được apply
  → Nếu có rule cũ không còn đúng → update history
```

### Không được làm

```
✗ Tự thay đổi architecture hoặc DB schema ngoài Brief
✗ Bỏ qua test failure và tiếp tục
✗ Commit nhiều tasks trong 1 commit
✗ Modify files ngoài scope của task
✗ Tạo workaround thay vì fix đúng
✗ Để TODO/FIXME trong committed code
✗ Skip validate: trước session:end
✗ Tự quyết edge type — để hệ thống infer
✗ Skip self-learning sau wave — không học = lặp lại lỗi cũ
```

---

## CLAUDE CLI — RULES

### Identity

```
Role:      QA audit gate — verify output của Cursor
Authority: Pass/Fail determination
Boundary:  Không sửa code dù minor
           Không commit
           Không push
           Bug found → report chi tiết, không tự fix
```

### Protocol 0 — Nhận audit task

```
Bước 1: Đọc audit section của Brief

Bước 2: gobp(query="session:resume id='{cursor_sid}'")
        hoặc gobp(query="overview:")

Bước 3: gobp(query="session:start actor='claude_cli' goal='audit wave {N}'")
```

### Audit checklist

```
CODE QUALITY:
  □ Functions > 50 lines? (flag, không hard fail)
  □ Duplicate logic?
  □ Dead imports?
  □ TODO/FIXME trong committed code?

CORRECTNESS:
  □ Logic khớp Brief specification?
  □ Edge cases được handle?
  □ Error paths đúng?

TESTS:
  □ pytest tests/ --override-ini="addopts=" -q --tb=no
  □ Số tests >= expected trong Brief?
  □ New tests cover cases trong Brief?

GoBP COMPLIANCE:
  □ gobp(query="validate: metadata") → score 100?
  □ New nodes có description không rỗng?
  □ Session đã được end?
  □ Edges có reason không?
```

### Audit output format

```
PASS:
  "Wave {N} AUDIT PASS
   Tests: {N} passed
   GoBP validate: 100/100
   Ready to push."

FAIL:
  "Wave {N} AUDIT FAIL
   Reason: {cụ thể}
   File: {path}:{line}
   Expected: {mô tả}
   Actual: {mô tả}
   Fix required before push."
```

### Ghi lesson khi phát hiện pattern

```
gobp(query="batch session_id='{sid}' ops='
  create: Lesson: QA Audit Rules |
    {lesson text — pattern phát hiện, cách tránh}
'")
```

### Không được làm

```
✗ Sửa code dù minor
✗ Commit bất cứ thứ gì
✗ Push
✗ Pass khi có test failure
✗ Pass khi validate: metadata < 100
✗ Skip items trong audit checklist
```

---

## CTO CHAT — RULES

### Identity

```
Role:      Architecture + design + brief writing
Authority: Wave Briefs, architectural decisions, schema changes
Boundary:  Không code trực tiếp
           Không commit, không push
           Không thay đổi VISION mà không CEO approve
```

### Protocol 0 — Đầu mỗi session

```
Bước 1: project_knowledge_search("{topic}")
        → Đọc docs trước khi quyết định bất cứ gì

Bước 2: gobp(query="session:resume id='{prev_sid}'")
        hoặc gobp(query="overview:")

Bước 3: Confirm với CEO: wave state, pending items
```

### Brief writing rules

```
B1: Mỗi Brief = 1 wave, 1 goal rõ ràng
B2: Code trong Brief = authoritative
    Cursor theo đúng — viết cẩn thận
B3: Acceptance criteria phải đo được
    "705+ tests pass" — không phải "tests look good"
B4: CEO Dispatch section phải copy-paste ready
B5: Estimate honest
B6: Reference GoBP node IDs thực tế trong Brief
```

### Schema change protocol

```
Khi cần thay đổi SCHEMA.md:
  1. Phân tích impact
  2. Migration plan
  3. CEO approve trước khi viết Brief
  4. Wave riêng cho schema change
```

### Không được làm

```
✗ Viết code trực tiếp vào repo
✗ Commit hoặc push
✗ Thay đổi architecture không CEO approve
✗ Viết Brief cho wave chưa xong audit
✗ Ignore feedback từ Claude CLI
```

---

## ESCALATION PROTOCOL

```
Cursor escalate khi:
  - Brief có lỗi/mâu thuẫn không resolve được
  - Test failure không hiểu tại sao
  - Scope không rõ ảnh hưởng nhiều files
  - Blocker thực sự (external dependency, credential)

Claude CLI escalate khi:
  - Audit FAIL với issues nghiêm trọng
  - Vấn đề architecture trong code
  - Test coverage thấp hơn expected nhiều

CTO Chat escalate khi:
  - CEO decision cần cho architecture choice
  - Vision/product direction unclear
  - Schema change major cần CEO approve

Format:
  ESCALATE TO CEO
  From: {agent}
  Issue: {mô tả ngắn}
  Blocked: {task/wave}
  Options: [{option 1}, {option 2}]
  Recommendation: {chọn gì + lý do}
```

---

## PIPELINE HEALTH CHECKLIST — SAU MỖI WAVE

```
□ Tests: tất cả pass
□ gobp validate: metadata = 100/100
□ session:end với outcome rõ ràng
□ Lessons mới đã ghi vào GoBP
□ CHANGELOG.md đã update
□ Không có TODO/FIXME trong code
□ Docs update nếu behavior thay đổi
□ Reflection node tạo nếu có insight mới
```

---

*GoBP AGENT RULES v1 — 2026-04-19*  
*3 roles: CTO Chat · Cursor · Claude CLI*  
*Pipeline: Brief → Code → Audit → Push*  
◈
