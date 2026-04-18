# WAVE 17A02 BRIEF — VALIDATOR BRIDGE + CUTOVER + FULL SUITE

**Wave:** 17A02
**Title:** validator_v2, seed update, MCP bridge, cutover, full suite
**Author:** CTO Chat
**Date:** 2026-04-19
**For:** Cursor (sequential) + Claude CLI (audit)
**Status:** READY FOR EXECUTION
**Task count:** 6 tasks
**Estimated effort:** 4-6 hours

---

## REFERENCED GOBP NODES

| Node ID | Topic |
|---|---|
| `dec:d004` | GoBP update obligation |
| `dec:d006` | Brief reference nodes |
| `dec:d011` | Graph hygiene |

**CONTEXT từ Wave 17A01:**
```
✅ core_nodes_v2.yaml — 93 types, group, lifecycle, read_order
✅ core_edges_v2.yaml — reason field
✅ id_generator.py v2
✅ file_format.py v2
✅ schema_loader.py — SchemaV2, load_schema_v2()
✅ ErrorCase: context + keywords + error_messages + code pattern
✅ 25 tests wave17a01 passing

CHƯA LÀM (wave này):
  ❌ validator_v2.py
  ❌ seed_universal_nodes() update
  ❌ MCP tools dùng schema v2
  ❌ Cutover: core_nodes_v2 → core_nodes.yaml
  ❌ Full suite với schema v2
```

---

## CURSOR EXECUTION RULES

R1-R12 (.cursorrules v6).

**Testing:**
- Tasks 1-4: R9-B (module tests only)
- Task 5 (cutover): R9-B + verify không vỡ existing
- Task 6: R9-C full suite

**CRITICAL:**
- Backup core_nodes.yaml → core_nodes_v1.yaml TRƯỚC khi cutover
- Mỗi task test pass TRƯỚC khi sang task tiếp
- Nếu full suite vỡ → STOP, báo CEO

---

## PREREQUISITES

```powershell
cd D:\GoBP
git status
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

# Verify Wave 17A01 state
D:/GoBP/venv/Scripts/python.exe -m pytest tests/test_wave17a01.py -v --tb=short
# Expected: 25 passed

D:/GoBP/venv/Scripts/python.exe -m pytest tests/ -q --tb=no
# Expected: 591 fast suite passing
```

---

## REQUIRED READING

| # | File | Why |
|---|---|---|
| 1 | `gobp/schema/core_nodes_v2.yaml` | Schema v2 — source of truth |
| 2 | `gobp/core/validator.py` | Current validator v1 — hiểu trước khi bridge |
| 3 | `gobp/core/schema_loader.py` | SchemaV2 đã có |
| 4 | `gobp/core/init.py` | seed_universal_nodes() |
| 5 | `gobp/mcp/tools/write.py` | TYPE_DEFAULTS, validate flow |
| 6 | `gobp/mcp/hooks.py` | hooks dùng validator |

---

# TASKS

---

## TASK 1 — validator_v2.py

**Goal:** Validator hoàn chỉnh cho schema v2.

**File:** `gobp/core/validator_v2.py`

```python
"""GoBP Validator v2 — validates nodes against schema v2."""
from __future__ import annotations
import re
from typing import Any
from gobp.core.schema_loader import SchemaV2


class ValidatorV2:
    """Node validator for GoBP schema v2."""

    def __init__(self, schema: SchemaV2):
        self._schema = schema

    def validate_node(self, node: dict) -> list[str]:
        """Validate node. Returns list of error strings."""
        errors = []
        node_type = node.get('type', '')

        # 1. Base required fields
        for field in ['id', 'name', 'type', 'group']:
            if not node.get(field):
                errors.append(f"Missing required field: '{field}'")

        # 2. description.info required
        desc = node.get('description', {})
        if isinstance(desc, str):
            pass  # Will be auto-wrapped — OK
        elif isinstance(desc, dict):
            if not desc.get('info', '').strip():
                errors.append("description.info is required and cannot be empty")
        else:
            errors.append("description must be string or {info, code} dict")

        # 3. Unknown type check
        if node_type and not self._schema.is_valid_type(node_type):
            valid = sorted(self._schema.node_types.keys())
            errors.append(
                f"Unknown node type: '{node_type}'. "
                f"Valid types: {', '.join(valid[:10])}..."
            )
            return errors  # Can't validate further

        # 4. Type-specific required fields
        type_def = self._schema.node_types.get(node_type, {})
        type_required = type_def.get('required', {})

        for field, field_spec in type_required.items():
            value = node.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(
                    f"Type '{node_type}' requires field: '{field}'"
                )
                continue

            # Pattern validation
            if isinstance(field_spec, dict):
                pattern = field_spec.get('pattern')
                if pattern and isinstance(value, str):
                    if not re.match(pattern, value):
                        errors.append(
                            f"Field '{field}' value '{value}' "
                            f"does not match pattern: {pattern}"
                        )

                # Enum validation
                enum_values = field_spec.get('values', [])
                if enum_values and value not in enum_values:
                    errors.append(
                        f"Field '{field}' must be one of: "
                        f"{', '.join(str(v) for v in enum_values)}. "
                        f"Got: '{value}'"
                    )

        # 5. Enum validation for optional fields
        type_optional = type_def.get('optional', {})
        base_fields = self._schema._nodes.get('base', {})
        all_optional = {**base_fields, **type_optional}

        for field, field_spec in all_optional.items():
            value = node.get(field)
            if value is None:
                continue
            if not isinstance(field_spec, dict):
                continue
            enum_values = field_spec.get('values', [])
            if enum_values and value not in enum_values:
                errors.append(
                    f"Field '{field}' must be one of: "
                    f"{', '.join(str(v) for v in enum_values)}. "
                    f"Got: '{value}'"
                )

        return errors

    def validate_edge(self, edge: dict) -> list[str]:
        """Validate edge. Returns list of error strings."""
        errors = []
        for field in ['from', 'to', 'type']:
            if not edge.get(field):
                errors.append(f"Edge missing required field: '{field}'")

        edge_type = edge.get('type', '')
        if edge_type and not self._schema.is_valid_edge_type(edge_type):
            errors.append(f"Unknown edge type: '{edge_type}'")

        return errors

    def auto_fix(self, node: dict) -> dict:
        """Auto-fix common issues. Returns fixed node."""
        node = dict(node)

        # Auto-wrap description
        from gobp.core.file_format import auto_fill_description
        if 'description' in node:
            node['description'] = auto_fill_description(node['description'])
        else:
            node['description'] = {'info': '', 'code': ''}

        # Auto-fill group from type
        if not node.get('group') and node.get('type'):
            group = self._schema.get_group(node['type'])
            if group:
                node['group'] = group

        # Auto-fill lifecycle
        if not node.get('lifecycle'):
            node['lifecycle'] = 'draft'

        # Auto-fill read_order
        if not node.get('read_order') and node.get('type'):
            node['read_order'] = self._schema.get_default_read_order(
                node['type']
            )

        return node


def make_validator_v2(schema_dir) -> ValidatorV2:
    """Create ValidatorV2 from schema directory."""
    from gobp.core.schema_loader import load_schema_v2
    from pathlib import Path
    schema = load_schema_v2(Path(schema_dir))
    return ValidatorV2(schema)
```

**Tests:**
```python
# tests/test_validator_v2.py — 10 tests
# test_valid_entity_node
# test_missing_group_error
# test_missing_description_info_error
# test_unknown_type_error
# test_invariant_missing_rule_error
# test_errorcase_code_pattern_invalid
# test_errorcase_code_pattern_valid
# test_auto_fix_description_string
# test_auto_fix_group_from_type
# test_valid_edge
```

**Commit:**
```
Wave 17A02 Task 1: validator_v2.py — full schema v2 validation

- ValidatorV2: validates against core_nodes_v2.yaml
- Required fields, enum values, pattern matching
- auto_fix(): description wrap, group infer, lifecycle/read_order defaults
- 10 tests passing
```

---

## TASK 2 — Update seed_universal_nodes()

**Goal:** Seed dùng schema v2 group/lifecycle/read_order.

**File:** `gobp/core/init.py`

Tìm `seed_universal_nodes()` hoặc tương đương.
Update để seed nodes có đủ fields v2:

```python
# Mỗi seed node phải có:
{
    "id": generate_id(name, group),    # dùng id_generator v2
    "name": name,
    "type": type_name,
    "group": schema_v2.get_group(type_name),
    "lifecycle": "specified",
    "read_order": schema_v2.get_default_read_order(type_name),
    "description": {
        "info": description_text,
        "code": ""
    }
}
```

**Backward compat:**
- Seed nodes cũ vẫn load được (validator v1 vẫn chạy)
- Seed nodes mới dùng fields v2

**Commit:**
```
Wave 17A02 Task 2: seed_universal_nodes update for schema v2 fields

- group, lifecycle, read_order added to seed nodes
- description → {info, code} format
- id_generator v2 for new seed IDs
```

---

## TASK 3 — MCP tools bridge: template + hooks

**Goal:** MCP tools dùng schema v2 cho template + validation.

**File:** `gobp/mcp/tools/write.py`

Update `_type_defaults_v2()` để complete:
```python
def _apply_v2_defaults(node: dict, schema_v2) -> dict:
    """Apply schema v2 defaults to node."""
    if not node.get('group') and node.get('type'):
        node['group'] = schema_v2.get_group(node['type'])
    if not node.get('lifecycle'):
        node['lifecycle'] = 'draft'
    if not node.get('read_order') and node.get('type'):
        node['read_order'] = schema_v2.get_default_read_order(node['type'])
    # Auto-wrap description
    from gobp.core.file_format import auto_fill_description
    if 'description' in node:
        node['description'] = auto_fill_description(node['description'])
    return node
```

**File:** `gobp/mcp/hooks.py`

Update `before_write` để dùng validator_v2:
```python
from gobp.core.validator_v2 import make_validator_v2

def before_write(action, params, index):
    # ... existing logic ...

    # V2 validation if schema v2 available
    if action in ("create", "upsert"):
        try:
            schema_dir = _get_schema_dir(index)
            validator = make_validator_v2(schema_dir)
            node_data = _extract_node_data(params)
            errors = validator.validate_node(node_data)
            if errors:
                return {
                    "ok": False,
                    "error": errors[0],
                    "all_errors": errors,
                    "suggestion": _suggest_fix_v2(errors[0], node_data)
                }
        except Exception:
            pass  # Fallback to v1 validation
```

**File:** `gobp/mcp/tools/read.py` — template action

Update `template:` để hiển thị v2 fields:
```python
# Template response thêm:
{
    "group": schema_v2.get_group(node_type),
    "lifecycle": "draft",
    "read_order": schema_v2.get_default_read_order(node_type),
    "description": {
        "info": "...",
        "code": ""
    }
}
```

**Commit:**
```
Wave 17A02 Task 3: MCP bridge — template + hooks use schema v2

- _apply_v2_defaults(): group, lifecycle, read_order, description
- before_write: validator_v2 for schema v2 nodes
- template: shows v2 fields
```

---

## TASK 4 — Cutover: rename + load_schema() update

**Goal:** core_nodes_v2.yaml → production.

**Steps:**

```powershell
# Step 1: Backup v1
cd D:\GoBP\gobp\schema
Copy-Item core_nodes.yaml core_nodes_v1.yaml
Copy-Item core_edges.yaml core_edges_v1.yaml

# Step 2: Promote v2
Copy-Item core_nodes_v2.yaml core_nodes.yaml
Copy-Item core_edges_v2.yaml core_edges.yaml
```

**File:** `gobp/core/schema_loader.py`

Update `load_schema()` để load schema mới:
```python
def load_schema(project_root: Path) -> dict:
    """Load schema — now loads v2 format."""
    schema_dir = _find_schema_dir(project_root)
    # Load v2
    schema_v2 = load_schema_v2(schema_dir)
    # Return in format expected by existing code
    return _schema_v2_to_v1_format(schema_v2)

def _schema_v2_to_v1_format(schema_v2: SchemaV2) -> dict:
    """Convert SchemaV2 to v1-compatible dict format."""
    node_types = {}
    for type_name, type_def in schema_v2.node_types.items():
        node_types[type_name] = {
            "required": list(type_def.get("required", {}).keys()),
            "optional": list(type_def.get("optional", {}).keys()),
            "group": type_def.get("group", ""),
            "read_order": type_def.get("read_order", "reference"),
        }
    return {"node_types": node_types}
```

**Verify sau cutover:**
```powershell
D:/GoBP/venv/Scripts/python.exe -c "
from pathlib import Path
from gobp.core.schema_loader import load_schema_v2, package_schema_dir
schema = load_schema_v2(package_schema_dir())
print('Types:', len(schema.node_types))
print('Has AuthFlow:', schema.is_valid_type('AuthFlow'))
print('AuthFlow group:', schema.get_group('AuthFlow'))
"
# Expected:
# Types: 93+
# Has AuthFlow: True
# AuthFlow group: Dev > Infrastructure > Security > AuthFlow
```

**Commit:**
```
Wave 17A02 Task 4: cutover — core_nodes_v2 → production

- Backup: core_nodes_v1.yaml, core_edges_v1.yaml
- Promote: core_nodes_v2.yaml → core_nodes.yaml
- load_schema() returns v2-backed v1-compat format
- Existing code reads v2 data transparently
```

---

## TASK 5 — Fix tests for schema v2 + full suite

**Goal:** Tất cả tests pass với schema v2.

**Common issues sau cutover:**
```
1. Tests hardcode type names không còn trong v2
   → Update type names theo taxonomy mới

2. Tests check required fields v1
   → Update assertions cho fields v2

3. Tests check node structure
   → Add group, lifecycle, read_order assertions

4. Seed nodes changed
   → Update fixture nodes trong tests
```

**Process:**
```powershell
# Run full suite, capture failures
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ --override-ini="addopts=" -q --tb=short 2>&1 | head -100

# Fix failures một batch
# Re-run, tiếp tục fix
# Cho đến khi 0 failures
```

**Target:** 653+ tests passing.

**Commit:**
```
Wave 17A02 Task 5: fix tests for schema v2 compatibility

- Updated type names to v2 taxonomy
- Updated required field assertions
- Added group/lifecycle/read_order checks where needed
- All N tests passing
```

---

## TASK 6 — CHANGELOG + GoBP MCP + Full Suite verify

**CHANGELOG:**
```markdown
## [Wave 17A02] — Validator Bridge + Cutover — 2026-04-19

### Added
- gobp/core/validator_v2.py: ValidatorV2 for schema v2
  - Required fields, enum, pattern validation
  - auto_fix(): description wrap, group infer
- gobp/schema/core_nodes_v1.yaml: backup of v1 schema
- gobp/schema/core_edges_v1.yaml: backup of v1 edges

### Changed
- gobp/schema/core_nodes.yaml → promoted from v2
- gobp/schema/core_edges.yaml → promoted from v2
- load_schema(): returns v2-backed v1-compat format
- before_write hook: uses validator_v2
- template: shows v2 fields (group, lifecycle, read_order)
- seed_universal_nodes(): v2 fields

### Tests: 653+ passing
```

**Full suite:**
```powershell
$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"
D:/GoBP/venv/Scripts/python.exe -m pytest tests/ --override-ini="addopts=" -q --tb=no
# Expected: 653+ tests
```

**GoBP MCP:**
```
gobp(query="session:start actor='cursor' goal='Wave 17A02 complete — schema v2 cutover'")
gobp(query="session:end outcome='validator_v2 done, cutover complete, 653+ tests passing'")
```

**Commit:**
```
Wave 17A02 Task 6: CHANGELOG + full suite — 653+ tests, schema v2 live
```

---

# CEO DISPATCH

## Cursor
```
Read gobp/schema/core_nodes_v2.yaml TRƯỚC.
Read waves/wave_17a02_brief.md.
Read GoBP MCP: gobp(query="find:Decision mode=summary")

$env:GOBP_DB_URL = "postgresql://postgres:Hieu%408283%40@localhost/gobp"

Execute Tasks 1-6.
R9-B for Tasks 1-4, R9-C for Tasks 5-6.

CRITICAL RULES:
  Task 4 (cutover): BACKUP trước khi rename
  Task 5: fix tests 1 batch, re-run, repeat
  STOP nếu không fix được sau 3 retries — báo CEO

GoBP MCP sau mỗi task (dec:d004).
Lesson: suggest: trước khi tạo (dec:d011).
```

## Claude CLI
```
Audit Wave 17A02.
Verify:
  - validator_v2.py: ValidatorV2 correct
  - core_nodes.yaml = v2 schema (93+ types)
  - core_nodes_v1.yaml: backup exists
  - load_schema() works với v2
  - 653+ tests passing

GoBP MCP session capture. Không cần Lesson node.
```

## Push
```powershell
cd D:\GoBP
git add waves/wave_17a02_brief.md
git commit -m "Add Wave 17A02 Brief — validator bridge + cutover"
git push origin main
```

---

*Wave 17A02 Brief v1.0 — 2026-04-19*
*References: dec:d004, dec:d006, dec:d011*
*Part of: Wave 17A Series (7 waves)*
◈
