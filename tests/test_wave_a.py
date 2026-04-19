"""Tests for GoBP Wave A — Database Foundation."""

from __future__ import annotations

from gobp.core.file_format_v3 import (
    deserialize_edges,
    deserialize_node,
    serialize_edges,
    serialize_node,
)
from gobp.core.id_generator import generate_id, generate_session_id
from gobp.core.pyramid import extract_pyramid, pyramid_from_node
from gobp.core.validator_v3 import ValidatorV3, validator_v3


# ── Pyramid tests ─────────────────────────────────────────────────────────────


def test_pyramid_simple() -> None:
    l1, l2 = extract_pyramid(
        "PaymentService handles transactions. Validates balance. SLA: p99 < 300ms."
    )
    assert l1 == "PaymentService handles transactions."
    assert "Validates balance" in l2


def test_pyramid_empty() -> None:
    assert extract_pyramid("") == ("", "")
    assert extract_pyramid("   ") == ("", "")


def test_pyramid_single_sentence() -> None:
    l1, l2 = extract_pyramid("Single sentence only.")
    assert l1 == "Single sentence only."
    assert l2 == "Single sentence only."


def test_pyramid_long_first_sentence() -> None:
    long = "A" * 150 + "."
    l1, l2 = extract_pyramid(long)
    assert len(l1) <= 100


def test_pyramid_from_node_plain() -> None:
    node = {"description": "First sentence. Second sentence."}
    l1, l2 = pyramid_from_node(node)
    assert l1 == "First sentence."


def test_pyramid_from_node_v2_dict() -> None:
    node = {"description": {"info": "First sentence. Second.", "code": ""}}
    l1, l2 = pyramid_from_node(node)
    assert l1 == "First sentence."


def test_pyramid_l2_max_300() -> None:
    text = ". ".join(["Sentence " + str(i) for i in range(20)]) + "."
    _, l2 = extract_pyramid(text)
    assert len(l2) <= 300


# ── ID Generator tests ────────────────────────────────────────────────────────


def test_generate_id_format() -> None:
    id_ = generate_id("PaymentService", "Dev > Infrastructure > Engine")
    parts = id_.split(".")
    assert parts[0] == "dev"
    assert "paymentservice" in id_
    assert len(parts[-1]) == 8  # 8hex suffix


def test_generate_id_deterministic() -> None:
    id1 = generate_id("PaymentService", "Dev > Infrastructure > Engine")
    id2 = generate_id("PaymentService", "Dev > Infrastructure > Engine")
    assert id1 == id2


def test_generate_id_different_names() -> None:
    id1 = generate_id("ServiceA", "Dev > Infrastructure > Engine")
    id2 = generate_id("ServiceB", "Dev > Infrastructure > Engine")
    assert id1 != id2


def test_generate_id_special_chars() -> None:
    id_ = generate_id("My Service (v2)", "Dev > Infrastructure")
    assert id_  # không có lỗi, trả về string


def test_generate_session_id_format() -> None:
    sid = generate_session_id("2026-04-19")
    assert sid.startswith("meta.session.2026-04-19.")
    assert len(sid.split(".")[-1]) == 8


# ── Validator v3 tests ────────────────────────────────────────────────────────


def test_validator_valid_base_node() -> None:
    v = ValidatorV3()
    errors = v.validate(
        {
            "name": "PaymentService",
            "group": "Dev > Infrastructure > Engine",
            "description": "Handles payments.",
        }
    )
    assert errors == []


def test_validator_missing_name() -> None:
    v = ValidatorV3()
    errors = v.validate({"group": "Dev > Engine", "description": "text"})
    assert any("name" in e for e in errors)


def test_validator_missing_group() -> None:
    v = ValidatorV3()
    errors = v.validate({"name": "X", "description": "text"})
    assert any("group" in e for e in errors)


def test_validator_missing_description() -> None:
    v = ValidatorV3()
    errors = v.validate({"name": "X", "group": "Y"})
    assert any("description" in e for e in errors)


def test_validator_empty_description() -> None:
    v = ValidatorV3()
    errors = v.validate({"name": "X", "group": "Y", "description": ""})
    assert any("description" in e for e in errors)


def test_validator_errorcase_valid() -> None:
    v = ValidatorV3()
    errors = v.validate(
        {
            "name": "Payment Timeout",
            "group": "Error > Payment",
            "description": "Timeout error.",
            "type": "ErrorCase",
            "severity": "error",
        }
    )
    assert errors == []


def test_validator_errorcase_invalid_severity() -> None:
    v = ValidatorV3()
    errors = v.validate(
        {
            "name": "X",
            "group": "Y",
            "description": "Z",
            "type": "ErrorCase",
            "severity": "CRITICAL",
        }
    )
    assert any("severity" in e for e in errors)


def test_validator_errorcase_missing_severity() -> None:
    v = ValidatorV3()
    errors = v.validate(
        {
            "name": "X",
            "group": "Y",
            "description": "Z",
            "type": "ErrorCase",
        }
    )
    assert any("severity" in e for e in errors)


def test_validator_auto_fix_infer_group() -> None:
    v = ValidatorV3()
    fixed = v.auto_fix({"name": "X", "type": "Engine", "description": "Y"})
    assert fixed["group"] == "Dev > Infrastructure > Engine"


def test_validator_auto_fix_v2_description() -> None:
    v = ValidatorV3()
    fixed = v.auto_fix(
        {
            "name": "X",
            "group": "Y",
            "description": {"info": "plain text", "code": "snippet"},
        }
    )
    assert fixed["description"] == "plain text"
    assert fixed["code"] == "snippet"


def test_validator_history_valid() -> None:
    v = ValidatorV3()
    errors = v.validate(
        {
            "name": "X",
            "group": "Y",
            "description": "Z",
            "history": [{"description": "change log"}],
        }
    )
    assert errors == []


def test_validator_history_invalid_entry() -> None:
    v = ValidatorV3()
    errors = v.validate(
        {
            "name": "X",
            "group": "Y",
            "description": "Z",
            "history": [{"description": ""}],
        }
    )
    assert any("history" in e for e in errors)


def test_validator_v3_module_singleton() -> None:
    assert validator_v3.is_valid({"name": "n", "group": "g", "description": "d"})


# ── File format v3 tests ──────────────────────────────────────────────────────


def test_serialize_deserialize_roundtrip() -> None:
    node = {
        "id": "dev.engine.payment.a1b2c3d4",
        "name": "PaymentService",
        "group": "Dev > Infrastructure > Engine",
        "description": "Handles payments.",
        "code": "def pay(): pass",
    }
    serialized = serialize_node(node)
    recovered = deserialize_node(serialized)
    assert recovered["name"] == "PaymentService"
    assert recovered["description"] == "Handles payments."


def test_serialize_no_type_field() -> None:
    node = {
        "id": "x",
        "name": "Y",
        "group": "Z",
        "description": "desc",
        "type": "Engine",
    }
    serialized = serialize_node(node)
    # type field không được serialize (trừ ErrorCase severity)
    assert "type: Engine" not in serialized


def test_serialize_errorcase_severity() -> None:
    node = {
        "id": "x",
        "name": "Y",
        "group": "Error > Payment",
        "description": "desc",
        "type": "ErrorCase",
        "severity": "error",
    }
    serialized = serialize_node(node)
    assert "severity: error" in serialized


def test_serialize_edges_roundtrip() -> None:
    edges = [
        {"from_id": "a", "to_id": "b", "reason": "because"},
        {"from_id": "c", "to_id": "d", "reason": "another reason"},
    ]
    serialized = serialize_edges(edges)
    recovered = deserialize_edges(serialized)
    assert len(recovered) == 2
    assert recovered[0]["reason"] == "because"


def test_serialize_edges_no_type() -> None:
    edges = [{"from_id": "a", "to_id": "b", "reason": "r", "type": "depends_on"}]
    serialized = serialize_edges(edges)
    assert "type: depends_on" not in serialized


def test_deserialize_empty_edges() -> None:
    assert deserialize_edges("") == []
    assert deserialize_edges("   ") == []


def test_deserialize_invalid_yaml() -> None:
    assert deserialize_node("not yaml") == {}
