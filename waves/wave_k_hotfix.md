# WAVE K HOTFIX — Import/Query Runtime Stabilization

**Wave:** K-Hotfix  
**Date:** 2026-04-21  
**Status:** COMPLETED  
**Scope:** GoBP MCP runtime + viewer stability fixes discovered during MIHOS import operations.

---

## Why this hotfix exists

Trong lúc nhập liệu MIHOS, có nhiều lỗi vận hành lặp lại:

- `find` theo type trả sai/lẫn loại do PG mirror path.
- `get_batch` báo thiếu node dù file graph có node.
- `edit` báo `Node not found` với id/prefix hoặc path file legacy.
- `edge:` fail trên project không có `gobp/schema` local.
- Viewer bị nén mạnh theo chiều sâu, khó điều hướng.

Wave K hotfix gom các bản vá runtime để AI/ops không phải workaround thủ công mỗi lần.

---

## Applied fixes (shipped)

1. **Find type filter path**
   - `find` có `type=`/`type_filter=` đi qua file index để giữ exact type.

2. **Batch read mirror fallback**
   - `get_batch` fallback file index khi PG mirror thiếu id.
   - Trả metadata: `source: hybrid_pg_file`, `mirror_fallback_count`.

3. **Edge schema fallback**
   - `edge:` fallback sang package schema nếu project root thiếu `gobp/schema/core_edges.yaml`.

4. **Edit node resolution hardening**
   - `edit` chấp nhận tốt hơn các dạng id (kể cả `node:` prefix).
   - Mutator fallback scan `.gobp/nodes` theo `id` khi path canonical không tồn tại.

5. **Viewer de-compression + controls**
   - Tăng tách layout X/Y/Z.
   - Thêm slider điều chỉnh X/Y/Z và reset nhanh.

6. **Import guide updates**
   - Bổ sung các pitfall/fix mới trong `docs/IMPORT_GUIDE.md` để tránh lặp lỗi.

---

## Operational rule clarified

- Audit `session_id` **không đồng nghĩa** bắt buộc có node `Meta > Session`.
- `session:start` là tùy chọn, chỉ dùng khi cần graph session lifecycle.

---

## Commits in this hotfix window

- `2b7348f` — get_batch fallback + viewer de-compress
- `56d60bb` — find type-filter + edge schema fallback
- `c4c6882` — edit node resolution hardening
- `7ea7a95` — IMPORT_GUIDE operational pitfalls

---

*Wave K Hotfix — runtime stabilization for MIHOS import flow*  
◈
