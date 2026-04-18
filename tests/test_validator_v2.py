"""Tests for gobp.core.validator_v2."""

from __future__ import annotations

from pathlib import Path

import pytest

from gobp.core.loader import package_schema_dir
from gobp.core.schema_loader import clear_schema_v2_cache, load_schema_v2
from gobp.core.validator_v2 import ValidatorV2, make_validator_v2


@pytest.fixture
def v2() -> ValidatorV2:
    clear_schema_v2_cache()
    return make_validator_v2(package_schema_dir())


def test_valid_entity_node(v2: ValidatorV2) -> None:
    node = {
        "id": "e1",
        "name": "Traveller",
        "type": "Entity",
        "group": "Dev > Domain > Entity",
        "description": {"info": "core entity", "code": ""},
    }
    assert v2.validate_node(node) == []


def test_missing_group_error(v2: ValidatorV2) -> None:
    node = {
        "id": "e1",
        "name": "X",
        "type": "Entity",
        "description": {"info": "i"},
    }
    errs = v2.validate_node(node)
    assert any("group" in e.lower() for e in errs)


def test_missing_description_info_error(v2: ValidatorV2) -> None:
    node = {
        "id": "e1",
        "name": "X",
        "type": "Entity",
        "group": "Dev > Domain > Entity",
        "description": {"info": "", "code": ""},
    }
    errs = v2.validate_node(node)
    assert any("description" in e.lower() for e in errs)


def test_unknown_type_error(v2: ValidatorV2) -> None:
    node = {
        "id": "e1",
        "name": "X",
        "type": "NotATypeEver123",
        "group": "g",
        "description": {"info": "i"},
    }
    errs = v2.validate_node(node)
    assert any("unknown" in e.lower() for e in errs)


def test_invariant_missing_rule_error(v2: ValidatorV2) -> None:
    node = {
        "id": "i1",
        "name": "Inv",
        "type": "Invariant",
        "group": "Constraint > Invariant",
        "description": {"info": "d"},
        "scope": "class",
        "enforcement": "hard",
        "violation_action": "reject",
    }
    errs = v2.validate_node(node)
    assert any("rule" in e.lower() for e in errs)


def test_errorcase_code_pattern_invalid(v2: ValidatorV2) -> None:
    node = {
        "id": "x",
        "name": "E",
        "type": "ErrorCase",
        "group": "Error > ErrorCase",
        "description": {"info": "i"},
        "code": "bad",
        "trigger": "t",
        "severity": "error",
        "handling": "h",
        "fix": "f",
    }
    errs = v2.validate_node(node)
    assert any("pattern" in e.lower() for e in errs)


def test_errorcase_code_pattern_valid(v2: ValidatorV2) -> None:
    node = {
        "id": "x",
        "name": "E",
        "type": "ErrorCase",
        "group": "Error > ErrorCase",
        "description": {"info": "i"},
        "code": "GPS_E_001",
        "trigger": "t",
        "severity": "error",
        "handling": "h",
        "fix": "f",
    }
    assert v2.validate_node(node) == []


def test_auto_fix_description_string(v2: ValidatorV2) -> None:
    fixed = v2.auto_fix(
        {"type": "Entity", "name": "N", "id": "id", "description": "plain text"}
    )
    assert fixed["description"] == {"info": "plain text", "code": ""}


def test_auto_fix_group_from_type(v2: ValidatorV2) -> None:
    fixed = v2.auto_fix({"type": "Entity", "name": "N", "id": "id"})
    assert "group" in fixed
    assert "Entity" in fixed.get("group", "")
    assert fixed.get("lifecycle") == "draft"


def test_valid_edge(v2: ValidatorV2) -> None:
    errs = v2.validate_edge(
        {"from": "a", "to": "b", "type": "relates_to"},
    )
    assert errs == []
