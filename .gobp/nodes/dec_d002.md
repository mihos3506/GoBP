---
id: dec:d002
type: Decision
name: 'Import protocol: template trước → liệt kê toàn bộ nodes+edges → CEO review
  plan '
status: LOCKED
topic: import.protocol
what: 'Import protocol: template trước → liệt kê toàn bộ nodes+edges → CEO review
  plan → batch nhập. AI PHẢI đọc toàn bộ doc trước khi nhập. KHÔNG tạo nodes rồi tính
  sau edges. Node mới trong graph có data PHẢI relate tới node đã có.'
why: AI hay lướt qua chỉ tạo nodes bỏ qua edges. 130/211 Invariants không có enforces
  edge = orphan vô giá trị. Rule trước khi nhập ngăn tạo rác.
alternatives_considered: []
risks: []
locked_by:
- CEO
- Claude-CLI
locked_at: '2026-04-18T08:09:08.752658+00:00'
session_id: meta.session.2026-04-18.fe8edaae3
created: '2026-04-18T08:09:08.752658+00:00'
updated: '2026-04-18T08:09:08.752658+00:00'
---

(Auto-generated node file. Edit the YAML above or add body content below.)
