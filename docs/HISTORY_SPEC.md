# ◈ GoBP HISTORY SPEC v1
**Status:** AUTHORITATIVE  
**Date:** 2026-04-19  
**Audience:** Cursor, CTO Chat — khi thêm history vào bất kỳ node nào

---

## MỤC TIÊU

```
1. Xem sự phát triển của node qua thời gian
   → Node này đã thay đổi gì, tại sao, do ai, khi nào

2. AI đọc để hiểu context
   → Không hỏi lại CEO những gì đã quyết định trước đó
```

---

## TEMPLATE

```yaml
history[]:   # append-only — KHÔNG sửa, KHÔNG xóa entry cũ
  - description: |
      [Ai] [khi nào/wave nào]: [thay đổi gì] vì [tại sao].
      Ví dụ:
      "Cursor Wave 12B: Thêm idempotency key support vì mobile client
      retry on timeout mà không check request gốc đã success chưa."
```

**Chỉ có 1 field duy nhất: `description`**  
Chứa tất cả: ai thay đổi, khi nào, thay đổi gì, tại sao.  
Không có fields riêng cho date/actor/wave — ít token hơn, AI đọc hiểu ngay.

---

## KHI NÀO GHI

```
GHI KHI:
  ✓ Business logic thay đổi
  ✓ Bug phát hiện + fix
  ✓ Requirement thay đổi
  ✓ Decision bị revisit
  ✓ Security vulnerability fix
  ✓ Performance tuning sau incident

KHÔNG GHI KHI:
  ✗ Typo fix trong description
  ✗ Code formatting
  ✗ Thêm field optional không thay đổi behavior
  ✗ Re-import với data giống nhau
```

---

## APPEND-ONLY RULE

```
KHÔNG BAO GIỜ:
  ✗ Sửa entry cũ
  ✗ Xóa entry
  ✗ Reorder entries

Nếu entry cũ sai → thêm entry mới correction:
  "CTO Chat 2026-04-20: Correction — threshold là 50m,
  không phải 40m như entry trước. Typo trong Brief."
```

---

## QUALITY CHECK

```
Entry đạt chuẩn khi AI đọc xong biết ngay:
  □ Ai thay đổi (actor + wave/date)
  □ Thay đổi gì (cụ thể, không phải "updated")
  □ Tại sao (root cause, không phải triệu chứng)

Ví dụ BAD:
  "Updated payment logic" — không biết gì cả

Ví dụ GOOD:
  "Cursor Wave 14A: Đổi timeout từ 5s → 10s vì Stripe webhook
  response time trung bình là 7s — 5s gây false timeout errors."
```

---

*GoBP HISTORY SPEC v1 — 2026-04-19*  
*Append-only. 1 field. Plain text tự giải thích.*  
◈
