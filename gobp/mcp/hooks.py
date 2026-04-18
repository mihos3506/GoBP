"""MCP hook layer — pre/post action callbacks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Actions that participate in before_write validation (subset of server write actions).
WRITE_ACTIONS = frozenset(
    {
        "create",
        "upsert",
        "lock",
        "batch",
        "quick",
        "delete",
        "retype",
        "merge",
        "edge",
        "import",
    }
)


def before_write(action: str, params: dict[str, Any], index: Any) -> dict[str, Any] | None:
    """Pre-write validation hook.

    Returns None if OK, or ``{ok: False, error: str, suggestion: str}`` to block.
    """
    # 1. Schema check for create/upsert
    if action in ("create", "upsert"):
        node_type = params.get("type") or _extract_type_from_query(str(params.get("query", "")))

        if node_type and not _type_exists_in_schema(node_type, index):
            return {
                "ok": False,
                "error": f"Unknown node type: {node_type}",
                "suggestion": f"Valid types: {', '.join(_get_valid_types(index))}",
            }

        try:
            from gobp.core.validator_v2 import make_validator_v2

            schema_dir = _schema_dir_for_index(index)
            validator = make_validator_v2(schema_dir)
            node_data = _extract_node_data_for_v2(params)
            if node_data:
                fixed = validator.auto_fix(dict(node_data))
                errs = validator.validate_node(fixed)
                if errs:
                    return {
                        "ok": False,
                        "error": errs[0],
                        "all_errors": errs,
                        "suggestion": _suggest_fix_v2(errs[0], fixed),
                    }
        except Exception:
            pass  # Fallback to downstream validation

    # 2. Session required for writes
    session_id = params.get("session_id", "")
    if isinstance(session_id, str):
        session_ok = bool(session_id.strip())
    else:
        session_ok = bool(session_id)
    if action in ("create", "upsert", "lock", "delete") and not session_ok:
        return {
            "ok": False,
            "error": "session_id required for write operations",
            "suggestion": "gobp(query=\"session:start actor='...' goal='...'\") first",
        }

    return None


def on_error(action: str, error: str, params: dict[str, Any], index: Any) -> dict[str, Any]:
    """Enrich error with actionable suggestion.

    Called when an action fails. Returns enriched error response.
    """
    suggestion = _suggest_fix(action, error, params, index)

    result: dict[str, Any] = {"ok": False, "error": error}
    if suggestion:
        result["suggestion"] = suggestion
    return result


def _suggest_fix(action: str, error: str, params: dict[str, Any], index: Any) -> str:
    """Generate actionable fix suggestion from error."""
    from gobp.core.search import search_nodes

    err_l = error.lower()

    # Node not found → suggest similar
    if "not found" in err_l:
        name = str(params.get("name", "") or params.get("id", "") or "")
        if name and index:
            similar = search_nodes(index, name, exclude_types=["Session"], limit=3)
            if similar:
                names = [str(n.get("name", "")) for _, n in similar if n.get("name")]
                if names:
                    return f"Similar nodes: {', '.join(names)}"

    # Wrong type → suggest valid types
    if "unknown type" in err_l or "invalid type" in err_l:
        if index:
            types_list = _get_valid_types(index)
            if types_list:
                return f"Valid types: {', '.join(types_list)}"

    # Missing session
    if "session" in err_l:
        return "gobp(query=\"session:start actor='cursor' goal='...'\")"

    return ""


def _type_exists_in_schema(node_type: str, index: Any) -> bool:
    """Check if node type exists in schema."""
    try:
        schema = index._nodes_schema
        return node_type in schema.get("node_types", {})
    except Exception:
        return True  # Don't block if can't check


def _get_valid_types(index: Any) -> list[str]:
    """Get valid node types from schema."""
    try:
        schema = index._nodes_schema
        return sorted(schema.get("node_types", {}).keys())
    except Exception:
        return []


def _schema_dir_for_index(index: Any) -> Path:
    """Resolve ``gobp/schema`` for the project, else packaged schema."""
    from gobp.core.loader import package_schema_dir

    try:
        root = index._gobp_root
        if root:
            d = root / "gobp" / "schema"
            if d.exists():
                return d
    except Exception:
        pass
    return package_schema_dir()


def _extract_node_data_for_v2(params: dict[str, Any]) -> dict[str, Any] | None:
    """Build a minimal node dict for Validator v2 pre-check."""
    ntype = params.get("type")
    name = params.get("name")
    if not ntype or not name:
        return None
    fields = params.get("fields")
    if not isinstance(fields, dict):
        fields = {}
    out: dict[str, Any] = {**fields, "type": str(ntype), "name": str(name)}
    if params.get("id"):
        out["id"] = str(params["id"])
    return out


def _suggest_fix_v2(first_error: str, node_data: dict[str, Any]) -> str:
    """Short hint for common v2 validation failures."""
    err_l = first_error.lower()
    if "description" in err_l or "info" in err_l:
        return "Set fields.description or provide non-empty description.info for schema v2."
    if "group" in err_l:
        return "Ensure group is set; use template: to see v2 group breadcrumb for this type."
    return f"Check node fields against schema v2: {node_data.get('type', '')}"


def _extract_type_from_query(query: str) -> str:
    """Extract type from 'create:Type' format."""
    if ":" in query:
        parts = query.split(":", 1)
        if len(parts) > 1:
            return parts[1].split()[0].strip() if parts[1].strip() else ""
    return ""
