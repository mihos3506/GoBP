"""Wave J: implemented field + bug fixes."""

from pathlib import Path

import yaml


def test_default_implemented_false() -> None:
    from gobp.core.validator_v3 import coerce_implemented

    node = {"type": "Spec", "name": "x", "group": "Document > Spec"}
    assert coerce_implemented(node)["implemented"] is False


def test_implemented_true_preserved() -> None:
    from gobp.core.validator_v3 import coerce_implemented

    node = {"type": "Engine", "implemented": True, "code": "path.py"}
    assert coerce_implemented(node)["implemented"] is True


def test_implemented_true_no_code_warning() -> None:
    from gobp.core.validator_v3 import validate_implemented

    node = {"type": "Flow", "name": "x", "implemented": True, "code": ""}
    assert len(validate_implemented(node)) == 1


def test_implemented_true_with_code_no_warning() -> None:
    from gobp.core.validator_v3 import validate_implemented

    node = {"type": "Engine", "name": "x", "implemented": True, "code": "file.py"}
    assert len(validate_implemented(node)) == 0


def test_meta_nodes_skip_implemented() -> None:
    from gobp.core.validator_v3 import coerce_implemented

    for node_type in ["Session", "Wave", "Task", "Reflection"]:
        node = coerce_implemented({"type": node_type, "name": "x"})
        assert "implemented" not in node


def test_yaml_safe_description_colon() -> None:
    """description with ':' should round-trip via YAML safely."""
    from gobp.core.file_format import serialize_frontmatter

    desc = "Role: Dev - execute: task"
    node = {
        "type": "Spec",
        "id": "x",
        "name": "x",
        "group": "Document > Spec",
        "description": desc,
    }
    parsed = yaml.safe_load(serialize_frontmatter(node))
    assert parsed["description"] == desc


def test_yaml_safe_description_braces() -> None:
    """description with braces should round-trip via YAML safely."""
    from gobp.core.file_format import serialize_frontmatter

    desc = "Config: {key: value} format"
    node = {
        "type": "Spec",
        "id": "x",
        "name": "x",
        "group": "Document > Spec",
        "description": desc,
    }
    parsed = yaml.safe_load(serialize_frontmatter(node))
    assert parsed["description"] == desc


def test_load_from_disk_skips_broken_file(tmp_path: Path) -> None:
    """GraphIndex skips corrupted node files instead of crashing."""
    nodes_dir = tmp_path / ".gobp" / "nodes"
    nodes_dir.mkdir(parents=True)
    (nodes_dir / "valid.md").write_text(
        "---\n"
        "type: Spec\n"
        "id: spec.valid\n"
        "name: Valid\n"
        "group: Document > Spec\n"
        "description: Valid node\n"
        "---\n",
        encoding="utf-8",
    )
    (nodes_dir / "broken.md").write_text(
        "---\n"
        "type: Spec\n"
        "description: {broken: [oops}\n"
        "---\n",
        encoding="utf-8",
    )

    from gobp.core.graph import GraphIndex

    index = GraphIndex.load_from_disk(tmp_path)
    assert index.get_node("spec.valid") is not None
