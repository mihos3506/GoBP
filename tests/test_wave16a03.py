"""Tests for Wave 16A03: new slug.group.number ID format."""

from __future__ import annotations

import asyncio
from pathlib import Path

from gobp.core.graph import GraphIndex
from gobp.core.id_config import (
    VALID_TESTKINDS,
    generate_external_id,
    make_id_slug,
    parse_external_id,
)
from gobp.core.init import init_project
from gobp.mcp.dispatcher import dispatch


def test_slug_flow_prefix_f2() -> None:
    assert make_id_slug("F2: Verify Gate") == "verify_gate"


def test_slug_flow_prefix_f10() -> None:
    assert make_id_slug("F10: Homecoming") == "homecoming"


def test_slug_plain_name() -> None:
    assert make_id_slug("TrustGate Engine") == "trustgate_engine"


def test_slug_traveller() -> None:
    assert make_id_slug("Traveller Identity") == "traveller_identity"


def test_slug_doc_prefix() -> None:
    assert "core_user_flows" in make_id_slug("DOC-07 Core User Flows")


def test_slug_wave_prefix() -> None:
    assert "new_ids" in make_id_slug("WAVE 16A03 — New IDs")


def test_slug_empty() -> None:
    assert make_id_slug("") == ""


def test_slug_max_40_chars() -> None:
    result = make_id_slug("This Is A Very Long Name That Exceeds Forty Characters Easily Here")
    assert len(result) <= 40


def test_slug_special_chars() -> None:
    assert make_id_slug("Use OTP (Email) for Auth!") == "use_otp_email_for_auth"


def test_flow_id_format() -> None:
    eid = generate_external_id("Flow", "Verify Gate")
    assert eid.startswith("verify_gate.ops.")
    parts = eid.split(".")
    assert len(parts) == 3
    assert len(parts[2]) == 8


def test_decision_id_format() -> None:
    eid = generate_external_id("Decision", "Use OTP for Auth")
    assert eid.startswith("use_otp_for_auth.core.")


def test_entity_id_format() -> None:
    eid = generate_external_id("Entity", "Traveller Identity")
    assert eid.startswith("traveller_identity.domain.")


def test_testcase_id_with_kind() -> None:
    eid = generate_external_id("TestCase", "Auth OTP Valid", "unit")
    assert "auth_otp_valid.test.unit." in eid
    parts = eid.split(".")
    assert len(parts) == 4
    assert parts[2] == "unit"
    assert len(parts[3]) == 8


def test_testcase_invalid_kind_defaults_to_unit() -> None:
    eid = generate_external_id("TestCase", "My Test", "invalid_kind")
    assert ".test.unit." in eid


def test_session_id_format() -> None:
    eid = generate_external_id("Session")
    assert eid.startswith("meta.session.")
    assert len(eid.split(".")) == 4


def test_id_without_name_uses_prefix() -> None:
    eid = generate_external_id("Flow")
    assert eid.startswith("flow.ops.")


def test_valid_testkinds_complete() -> None:
    assert "unit" in VALID_TESTKINDS
    assert "e2e" in VALID_TESTKINDS
    assert "performance" in VALID_TESTKINDS
    assert "security" in VALID_TESTKINDS
    assert len(VALID_TESTKINDS) >= 10


def test_parse_standard_new_format() -> None:
    p = parse_external_id("verify_gate.ops.00000002")
    assert p["slug"] == "verify_gate"
    assert p["group"] == "ops"
    assert p["number"] == "00000002"
    assert p["testkind"] == ""
    assert p["format"] == "new"


def test_parse_testcase_format() -> None:
    p = parse_external_id("auth_otp_valid.test.unit.00000001")
    assert p["slug"] == "auth_otp_valid"
    assert p["group"] == "test"
    assert p["testkind"] == "unit"
    assert p["number"] == "00000001"


def test_parse_session_format() -> None:
    p = parse_external_id("meta.session.2026-04-16.a3f7c2abc")
    assert p["group"] == "meta"


def test_parse_legacy_colon_format() -> None:
    p = parse_external_id("flow:verify_gate")
    assert p["format"] == "legacy"
    assert p["slug"] == "verify_gate"


def test_create_flow_gets_slug_id(gobp_root: Path) -> None:
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch("session:start actor='test' goal='slug test'", index, gobp_root))
    sid = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    r = asyncio.run(
        dispatch(
            f"create:Flow name='Verify Gate' priority='critical' session_id='{sid}'",
            index,
            gobp_root,
        )
    )
    assert r["ok"] is True, r
    node_id = r.get("node_id", "")
    assert "verify_gate" in node_id
    assert ".ops." in node_id


def test_create_testcase_gets_kind_in_id(gobp_root: Path) -> None:
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch("session:start actor='test' goal='testcase slug'", index, gobp_root))
    sid = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    flow = asyncio.run(
        dispatch(
            f"create:Flow name='Auth Flow' session_id='{sid}'",
            index,
            gobp_root,
        )
    )
    assert flow["ok"] is True
    index = GraphIndex.load_from_disk(gobp_root)

    existing_kinds = index.nodes_by_type("TestKind")
    if not existing_kinds:
        return
    kind_id = existing_kinds[0]["id"]

    r = asyncio.run(
        dispatch(
            f"create:TestCase name='Auth OTP Valid' kind_id='{kind_id}' testkind='unit' covers='{flow['node_id']}' status='DRAFT' priority='medium' session_id='{sid}'",
            index,
            gobp_root,
        )
    )
    assert r["ok"] is True, r
    node_id = r.get("node_id", "")
    assert ".test.unit." in node_id


def test_find_by_slug_in_id(gobp_root: Path) -> None:
    init_project(gobp_root, force=True)
    index = GraphIndex.load_from_disk(gobp_root)

    sess = asyncio.run(dispatch("session:start actor='test' goal='find slug'", index, gobp_root))
    sid = sess["session_id"]
    index = GraphIndex.load_from_disk(gobp_root)

    asyncio.run(dispatch(f"create:Flow name='Verify Gate' session_id='{sid}'", index, gobp_root))
    index = GraphIndex.load_from_disk(gobp_root)

    r = asyncio.run(dispatch("find: verify_gate", index, gobp_root))
    assert r["ok"] is True
    ids = [m["id"] for m in r["matches"]]
    assert any("verify_gate" in nid for nid in ids)
