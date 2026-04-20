# GoBP EDGE POLICY v1

- Date: 2026-04-20
- Schema version: `1.0`
- Status: `DRAFT`
- Author: `CTO Chat`
- Next step: `CEO review -> Wave I implement vào GoBP schema + dispatcher`

## Scope

Policy nay quy dinh:
- 5 role groups.
- 5 core edge types.
- Ma tran hop le `from_group -> to_group`.
- Traverse policy de chon doc gi truoc.
- Validator rules muc canh bao/loi.

`reason_mode`:
- `template`: dung template mac dinh, khong can nhap tay.
- `required_short`: bat buoc 1 cau reason ngan.
- `none`: khong ap dung.

## Role Groups

### Knowledge
- Includes: `Document`, `Spec`, `Idea`, `Lesson`, `LessonRule`, `LessonDev`, `LessonQA`, `LessonCTO`
- Description: Tai lieu + dac ta + bai hoc (nguon tri thuc)

### Code
- Includes: `Flow`, `Feature`, `Engine`, `UseCase`, `Command`, `Entity`, `ValueObject`, `Aggregate`, `Repository`, `APIContract`, `APIEndpoint`, `Module`, `Class`, `Function`, `Interface`, `ErrorCase`, `ErrorDomain`
- Description: Code domain + infrastructure + error (hien thuc)
- Note: `ErrorCase`/`ErrorDomain` nam trong Code, van giu field `error_severity`

### Constraint
- Includes: `Invariant`, `BusinessRule`, `Precondition`, `Postcondition`, `Policy`
- Description: Rang buoc bat bien, luat khong duoc vi pham

### Test
- Includes: `TestSuite`, `TestKind`, `TestCase`
- Description: Kiem chung bao phu Code va Constraint

### Meta
- Includes: `Session`, `Wave`, `Task`, `Reflection`
- Description: Provenance, khong dung de traverse ky thuat

## Core Edge Types

| Edge | Meaning | Traverse priority | Default reason template |
|---|---|---|---|
| `depends_on` | `from` can `to` de dung vung/hoat dong dung | high | `{from} cần {to} để hoạt động đúng.` |
| `implements` | `from` hien thuc dac ta/contract cua `to` | high | `{from} hiện thực đặc tả {to}.` |
| `enforces` | Constraint ap rang buoc len Code hoac Test | medium | `{from} ràng buộc {to}.` |
| `covers` | Test bao phu Code / Constraint / Knowledge | low | `{from} kiểm chứng {to}.` |
| `discovered_in` | Node duoc tao trong session nao (provenance) | skip | `null` |

Note: `discovered_in` khong dung de quyet dinh doc sau, chi phuc vu audit trail.

## Matrix 5x5

### From `Knowledge`

| To group | Edge | Reason mode | Note |
|---|---|---|---|
| Knowledge | `depends_on` | `template` | Spec A phu thuoc Spec B lam nen tang |
| Code | `implements` | `template` | Code hien thuc Knowledge; chieu nguoc co the dung alias `specified_in` |
| Constraint | `depends_on` | `template` |  |
| Test | `covers` | `template` | Hiem: Knowledge duoc test truc tiep |
| Meta | `discovered_in` | `none` |  |

### From `Code`

| To group | Edge | Reason mode | Note |
|---|---|---|---|
| Knowledge | `implements` | `template` |  |
| Code | `depends_on` | `template` |  |
| Constraint | `enforces` | `required_short` | Can neu ro vi pham se dan den dieu gi |
| Test | `covers` | `template` |  |
| Meta | `discovered_in` | `none` |  |

### From `Constraint`

| To group | Edge | Reason mode | Note |
|---|---|---|---|
| Knowledge | `depends_on` | `template` | Constraint duoc dac ta trong Knowledge nao |
| Code | `enforces` | `required_short` | Bat buoc 1 cau ngan: "Neu vi pham -> X" |
| Constraint | `null` | `none` |  |
| Test | `null` | `none` |  |
| Meta | `discovered_in` | `none` |  |

### From `Test`

| To group | Edge | Reason mode | Note |
|---|---|---|---|
| Knowledge | `covers` | `template` |  |
| Code | `covers` | `template` |  |
| Constraint | `enforces` | `template` | Test enforce Constraint (kiem chung bat bien) |
| Test | `depends_on` | `template` | Vi du: TestSuite -> TestCase |
| Meta | `discovered_in` | `none` |  |

### From `Meta`

| To group | Edge | Reason mode | Note |
|---|---|---|---|
| Knowledge | `depends_on` | `template` | Session/Wave tham chieu doc lam boi canh |
| Code | `null` | `none` |  |
| Constraint | `null` | `none` |  |
| Test | `null` | `none` |  |
| Meta | `discovered_in` | `none` |  |

## Traverse Policy (BFS)

### Tier 1 expand
- Edges: `depends_on`, `implements`
- Read depth: `desc_l2` cua node dich
- Rule: luon mo rong (truc hieu cot loi)

### Tier 2 expand
- Edges: `enforces`, `covers`
- Read depth: `desc_l1` cua node dich
- Rule: mo rong neu con budget token

### Skip
- Edges: `discovered_in`
- Read depth: `none`
- Rule: khong traverse, chi phuc vu audit

### Full document
- Trigger: `get: node_id mode=full` hoac load tu `source_path`
- Rule: graph la map + `desc_l1/l2`; full doc la buoc rieng

## Validator Rules

- Warning: `enforces` tu `Constraint -> Code` phai co reason.
- Warning: `implements` phai co `to` thuoc group `Knowledge`.
- Error: `discovered_in` phai co `to` thuoc group `Meta`.
- Error: `depends_on` khong duoc tao vong lap (`A -> B -> A`).

## Error Node Fields

- `error_severity`: `fatal | error | warning | info`
- Note: giu kha nang loc loi ma khong can tach `Error` thanh group rieng.
