"""Tests for Wave 16A08: unidecode normalization + Session strict exclusion."""

from __future__ import annotations

import asyncio

from gobp.core.graph import GraphIndex
from gobp.core.init import init_project
from gobp.core.search import normalize_text, search_nodes
from gobp.mcp.dispatcher import dispatch


# ── unidecode normalization tests ─────────────────────────────────────────────


def test_unidecode_dang_nhap() -> None:
    assert normalize_text("đăng nhập") == "dang nhap"


def test_unidecode_mi_hot() -> None:
    assert normalize_text("Mi Hốt") == "mi hot"


def test_unidecode_ha_noi() -> None:
    assert normalize_text("Hà Nội") == "ha noi"


def test_unidecode_ban_co() -> None:
    assert normalize_text("Bàn Cờ") == "ban co"


def test_unidecode_ascii_unchanged() -> None:
    assert normalize_text("TrustGate") == "trustgate"
    assert normalize_text("MIHOS") == "mihos"


def test_normalize_dang_nhap_equivalence() -> None:
    """User typing 'dang nhap' finds 'đăng nhập' nodes."""
    assert normalize_text("đăng nhập") == normalize_text("dang nhap")


def test_normalize_mi_hot_equivalence() -> None:
    assert normalize_text("Mi Hốt") == normalize_text("mi hot")
    assert normalize_text("Mi Hốt").replace(" ", "") == normalize_text("mihot")


def test_normalize_ha_noi_equivalence() -> None:
    assert normalize_text("Hà Nội") == normalize_text("ha noi")


# ── Session strict exclusion tests ───────────────────────────────────────────


def test_find_session_keyword_excludes_sessions(tmp_path) -> None:
    """find: session (keyword) should NOT return Session nodes."""
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    asyncio.run(
        dispatch(
            "session:start actor='test' goal='session exclusion strict test'",
            index,
            tmp_path,
        )
    )

    index = GraphIndex.load_from_disk(tmp_path)
    r = asyncio.run(dispatch("find: session mode=summary", index, tmp_path))
    types = {m.get("type") for m in r.get("matches", [])}
    assert "Session" not in types, f"Session leaked into keyword search: {types}"


def test_find_session_type_filter_includes_sessions(tmp_path) -> None:
    """find:Session (type filter) SHOULD return Session nodes."""
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    asyncio.run(
        dispatch(
            "session:start actor='test' goal='explicit session type test'",
            index,
            tmp_path,
        )
    )

    index = GraphIndex.load_from_disk(tmp_path)
    r = asyncio.run(dispatch("find:Session mode=summary", index, tmp_path))
    types = {m.get("type") for m in r.get("matches", [])}
    assert "Session" in types, "Expected Session nodes with explicit type filter"


def test_find_include_sessions_param(tmp_path) -> None:
    """find: session include_sessions=true should include Session nodes."""
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    asyncio.run(
        dispatch(
            "session:start actor='test' goal='include sessions param test'",
            index,
            tmp_path,
        )
    )

    index = GraphIndex.load_from_disk(tmp_path)
    r = asyncio.run(dispatch("find: session include_sessions=true mode=summary", index, tmp_path))
    types = {m.get("type") for m in r.get("matches", [])}
    assert "Session" in types


# ── Integration: diacritics search finds nodes ───────────────────────────────


def test_search_dang_nhap_finds_node(tmp_path) -> None:
    """'dang nhap' should find node named 'Đăng Nhập'."""
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    sid = asyncio.run(dispatch("session:start actor='test' goal='dang nhap test'", index, tmp_path))[
        "session_id"
    ]
    index = GraphIndex.load_from_disk(tmp_path)
    asyncio.run(dispatch(f"create:Flow name='Đăng Nhập Flow' session_id={sid}", index, tmp_path))

    index = GraphIndex.load_from_disk(tmp_path)
    results = search_nodes(index, "dang nhap", exclude_types=[])
    names = [n.get("name", "") for _, n in results]
    assert any("Đăng Nhập" in n or "dang nhap" in normalize_text(n) for n in names), (
        f"Expected 'Đăng Nhập Flow' in results, got: {names}"
    )


def test_search_unicode_and_ascii_same_results(tmp_path) -> None:
    """find: đăng nhập and find: dang nhap return same results."""
    init_project(tmp_path)
    index = GraphIndex.load_from_disk(tmp_path)

    sid = asyncio.run(
        dispatch("session:start actor='test' goal='unicode ascii parity'", index, tmp_path)
    )["session_id"]
    index = GraphIndex.load_from_disk(tmp_path)
    asyncio.run(dispatch(f"create:Flow name='Đăng Nhập Flow' session_id={sid}", index, tmp_path))

    index = GraphIndex.load_from_disk(tmp_path)
    r1 = search_nodes(index, "dang nhap", exclude_types=[])
    r2 = search_nodes(index, "đăng nhập", exclude_types=[])

    ids1 = {n.get("id") for _, n in r1}
    ids2 = {n.get("id") for _, n in r2}
    assert ids1 == ids2, f"ASCII vs Unicode gave different results: {ids1} vs {ids2}"
