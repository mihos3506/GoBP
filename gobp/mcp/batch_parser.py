"""Parse Wave 16A09 ``batch`` operation lines (multi-op block).

Each non-empty line is one operation. Supported prefixes (case-insensitive
prefix before the first colon):

- ``create:`` — ``Type: Name | Description``
- ``update:`` / ``replace:`` — ``<node_id> field=value ...``
- ``delete:`` — ``<node_id>``
- ``retype:`` — ``<node_id> new_type=Engine``
- ``merge:`` — ``keep=<id> absorb=<id>``
- ``edge+:`` / ``edge-:`` / ``edge~:`` / ``edge*:`` — ``From --type--> To`` (``edge*`` allows
  comma-separated targets; ``edge~`` supports `` to=newtype`` suffix).
"""

from __future__ import annotations

import re
from typing import Any

# From/to may contain ':' (e.g. doc:doc_01). Use explicit --edge_type--> delimiter;
# edge keyword is [a-zA-Z_]+ (schema-style slug), not \w (avoids odd Unicode edge cases).
_EDGE_ARROW = re.compile(r"^(.+?)\s*--([a-zA-Z_]+)-->\s*(.+)$", re.DOTALL)
_ASSIGN = re.compile(r"(\w+)=('([^']*)'|\"([^\"]*)\"|(\S+))")
_MERGE = re.compile(r"keep=(\S+)\s+absorb=(\S+)", re.I)
_NEW_TYPE = re.compile(r"new_type=(\S+)", re.I)
_EDGE_TILDE_TO = re.compile(r"\s+to=(\w+)\s*$", re.I)
_CREATE_PARAM = re.compile(r'(\w+)=(?:"([^"]*?)"|\'([^\']*?)\'|(\S+))')

# Known batch line prefixes (after stripping). Used to split ops without breaking quoted newlines.
_BATCH_OP_PREFIXES: tuple[str, ...] = (
    "create:",
    "update:",
    "replace:",
    "delete:",
    "retype:",
    "merge:",
    "edge+:",
    "edge-:",
    "edge~:",
    "edge*:",
    "quick:",
    "lock:",
)


def _parse_create_rhs(rhs: str) -> tuple[str, str, dict[str, str]]:
    """Parse the right-hand side of ``Type: …`` in a create line.

    Returns:
        ``(name, plain_description, named_params)``.
    """
    rhs = rhs.strip()
    if "|" not in rhs:
        return rhs, "", {}

    name_part, rest = rhs.split("|", 1)
    name = name_part.strip()
    rest = rest.strip()
    if not rest:
        return name, "", {}

    matches = list(_CREATE_PARAM.finditer(rest))
    named_params: dict[str, str] = {}
    for m in matches:
        key = m.group(1)
        value = m.group(2) or m.group(3) or m.group(4) or ""
        named_params[key] = value

    if matches:
        plain_desc = rest[: matches[0].start()].strip()
    else:
        plain_desc = rest.strip()

    return name, plain_desc, named_params


def _detect_unclosed_quote(text: str) -> str | None:
    """Return a quote character if ``text`` has an unclosed ``'`` or ``\"``, else ``None``."""
    in_quote: str | None = None
    for char in text:
        if char in ('"', "'") and in_quote is None:
            in_quote = char
        elif char == in_quote:
            in_quote = None
    return in_quote


def _split_ops(ops_text: str) -> list[str]:
    """Split batch text into op strings; newlines inside quoted values do not start a new op."""
    lines = ops_text.split("\n")
    current_op: list[str] = []
    ops: list[str] = []
    in_quote: str | None = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        lower = stripped.lower()
        is_known_op = any(lower.startswith(p) for p in _BATCH_OP_PREFIXES)
        colon_word = re.match(r"^([A-Za-z0-9_]+)\s*:", stripped)
        looks_like_prefixed_op = bool(colon_word) and not stripped.startswith("#")

        if in_quote is not None:
            if current_op:
                current_op.append(stripped)
                in_quote = _detect_unclosed_quote(" ".join(current_op))
            continue

        if is_known_op:
            if current_op:
                ops.append(" ".join(current_op))
            current_op = [stripped]
            in_quote = _detect_unclosed_quote(stripped)
            continue

        if looks_like_prefixed_op and not is_known_op:
            if current_op:
                ops.append(" ".join(current_op))
            current_op = [stripped]
            in_quote = _detect_unclosed_quote(stripped)
            continue

        if current_op:
            current_op.append(stripped)
            in_quote = _detect_unclosed_quote(" ".join(current_op))

    if current_op:
        ops.append(" ".join(current_op))

    return [op for op in ops if op.strip()]


def _parse_assignments(blob: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for m in _ASSIGN.finditer(blob):
        key = m.group(1)
        if m.group(3) is not None:
            out[key] = m.group(3)
        elif m.group(4) is not None:
            out[key] = m.group(4)
        else:
            out[key] = m.group(5)
    return out


def parse_batch_line(line: str) -> dict[str, Any]:
    """Parse a single batch op line into a normalized dict.

    Returns:
        Dict with at least ``kind`` and fields for that op, or
        ``{"kind": "error", "message": "...", "raw": line}``.
    """
    raw = line.strip()
    if not raw or raw.startswith("#"):
        return {"kind": "noop", "raw": raw}

    m = re.match(
        r"^(?P<prefix>edge\*|edge~|edge\+|edge-|create|update|replace|delete|retype|merge)\s*:\s*(?P<rest>.*)$",
        raw,
        re.I | re.DOTALL,
    )
    if not m:
        return {"kind": "error", "message": "unknown op prefix", "raw": raw}

    prefix = m.group("prefix").lower()
    rest = (m.group("rest") or "").strip()

    if prefix == "create":
        cm = re.match(r"^([A-Za-z0-9_]+)\s*:\s*(.+)$", rest)
        if not cm:
            return {"kind": "error", "message": "create: expected Type: Name | Desc", "raw": raw}
        node_type = cm.group(1)
        rhs = cm.group(2).strip()
        name, plain_desc, named_params = _parse_create_rhs(rhs)
        if not name:
            return {"kind": "error", "message": "create: empty name", "raw": raw}
        out: dict[str, Any] = {
            "kind": "create",
            "node_type": node_type,
            "name": name,
            "description": plain_desc,
            "raw": raw,
        }
        out.update(named_params)
        return out

    if prefix in ("update", "replace"):
        um = re.match(r"^(\S+)\s+(.+)$", rest)
        if not um:
            return {"kind": "error", "message": f"{prefix}: expected <id> field=value ...", "raw": raw}
        node_id = um.group(1)
        fields = _parse_assignments(um.group(2))
        if not fields:
            return {"kind": "error", "message": f"{prefix}: no field assignments", "raw": raw}
        return {
            "kind": prefix,
            "node_id": node_id,
            "fields": fields,
            "raw": raw,
        }

    if prefix == "delete":
        if not rest:
            return {"kind": "error", "message": "delete: missing id", "raw": raw}
        return {"kind": "delete", "node_id": rest.split()[0], "raw": raw}

    if prefix == "retype":
        parts = rest.split(None, 1)
        if len(parts) < 2:
            return {"kind": "error", "message": "retype: expected <id> new_type=X", "raw": raw}
        node_id = parts[0]
        nm = _NEW_TYPE.search(rest)
        if not nm:
            return {"kind": "error", "message": "retype: new_type= required", "raw": raw}
        return {"kind": "retype", "node_id": node_id, "new_type": nm.group(1), "raw": raw}

    if prefix == "merge":
        mm = _MERGE.search(rest.replace("\n", " "))
        if not mm:
            return {"kind": "error", "message": "merge: keep=id absorb=id", "raw": raw}
        return {"kind": "merge", "keep": mm.group(1), "absorb": mm.group(2), "raw": raw}

    if prefix in ("edge+", "edge-", "edge*", "edge~"):
        new_type_override: str | None = None
        body = rest
        if prefix == "edge~":
            tm = _EDGE_TILDE_TO.search(rest)
            if tm:
                new_type_override = tm.group(1)
                body = rest[: tm.start()].rstrip()
        em = _EDGE_ARROW.match(body.strip())
        if not em:
            return {"kind": "error", "message": f"{prefix}: expected From --type--> To", "raw": raw}
        from_name = em.group(1).strip()
        edge_type = em.group(2).strip()
        to_spec = em.group(3).strip()
        targets = [t.strip() for t in to_spec.split(",")] if prefix == "edge*" else [to_spec]
        if not targets or not all(targets):
            return {"kind": "error", "message": f"{prefix}: missing target(s)", "raw": raw}
        return {
            "kind": {
                "edge+": "edge_add",
                "edge-": "edge_remove",
                "edge*": "edge_replace_all",
                "edge~": "edge_ret_type",
            }[prefix],
            "from_name": from_name,
            "edge_type": edge_type,
            "targets": targets,
            "new_edge_type": new_type_override,
            "raw": raw,
        }

    return {"kind": "error", "message": f"unhandled prefix {prefix}", "raw": raw}


def parse_batch_ops(ops_text: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Parse a multi-line batch ops block.

    Returns:
        Tuple of (parsed_ops, errors) where each error is a human-readable string.
    """
    # Literal ``\\n`` / ``\n`` from MCP JSON often arrives as backslash+n; normalize first.
    text = ops_text.replace("\\\\n", "\n").replace("\\n", "\n")
    parsed: list[dict[str, Any]] = []
    errors: list[str] = []
    for op_line in _split_ops(text):
        item = parse_batch_line(op_line)
        if item.get("kind") == "noop":
            continue
        if item.get("kind") == "error":
            errors.append(f"{item.get('message')}: {item.get('raw', op_line)!r}")
            continue
        parsed.append(item)
    return parsed, errors


def parse_quick(raw: str) -> list[dict[str, Any]]:
    """Parse quick-capture lines: ``Name | category | wave | description``.

    Minimum: ``Name | description`` (two parts). Produces dicts compatible with
    :func:`parse_batch_line` output shape via :func:`quick_action` in write tools.
    """
    text = raw.replace("\\\\n", "\n").replace("\\n", "\n")
    ops: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if not parts or not parts[0]:
            continue
        op: dict[str, Any] = {
            "kind": "create",
            "node_type": "Node",
            "name": parts[0],
            "description": "",
            "raw": line,
        }
        if len(parts) == 2:
            op["description"] = parts[1]
        elif len(parts) == 3:
            op["category"] = parts[1]
            op["description"] = parts[2]
        elif len(parts) >= 4:
            op["category"] = parts[1]
            op["target_wave"] = parts[2]
            op["description"] = parts[3]
        ops.append(op)
    return ops


def parse_batch(raw: str) -> list[dict[str, Any]]:
    """Parse batch ops text; same newline rules as :func:`parse_batch_ops`.

    Unlike :func:`parse_batch_ops`, this fails the whole parse if **any** line
    is invalid — no silent partial results. Use :func:`parse_batch_ops` when
    you need per-line success and error lists.
    """
    ops, errors = parse_batch_ops(raw)
    if errors:
        detail = "; ".join(errors)
        raise ValueError(f"batch parse failed ({len(errors)} line(s)): {detail}")
    return ops
