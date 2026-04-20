"""Wave I: Edge Policy tests."""

from gobp.core.validator_v3 import auto_reason, validate_edge_type


def test_valid_edge_knowledge_to_code() -> None:
    r = validate_edge_type("Spec", "Flow", "implements")
    assert r["ok"] is True
    assert r.get("warning") is None


def test_wrong_edge_type_warning() -> None:
    r = validate_edge_type("Spec", "Flow", "covers")
    assert r["ok"] is True
    assert "warning" in r and r["warning"]


def test_auto_reason_depends_on() -> None:
    r = auto_reason("Flow A", "Engine B", "depends_on")
    assert "Flow A" in r and "Engine B" in r


def test_auto_reason_implements() -> None:
    r = auto_reason("PaymentEngine", "Payment Spec", "implements")
    assert "hien thuc dac ta" in r


def test_auto_reason_empty_for_discovered_in() -> None:
    r = auto_reason("NodeX", "Session Y", "discovered_in")
    assert r == ""


def test_enforces_needs_reason_from_constraint() -> None:
    r = validate_edge_type("Invariant", "Flow", "enforces")
    assert r.get("needs_reason") is True


def test_unknown_node_type_skip() -> None:
    r = validate_edge_type("UnknownType", "Flow", "depends_on")
    assert r["ok"] is True
    assert r.get("warning") is None


def test_discovered_in_must_go_to_meta() -> None:
    r = validate_edge_type("Spec", "Flow", "discovered_in")
    assert r.get("warning")


def test_valid_test_covers_code() -> None:
    r = validate_edge_type("TestCase", "Engine", "covers")
    assert r["ok"] is True
    assert not r.get("warning")
