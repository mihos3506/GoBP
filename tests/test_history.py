"""Tests for gobp.core.history module."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from gobp.core.history import append_event, read_events


def test_append_event_creates_folder(tmp_path: Path):
    """append_event creates .gobp/history/ folder if missing."""
    event = append_event(
        gobp_root=tmp_path,
        event_type="test.event",
        payload={"foo": "bar"},
        actor="test",
    )

    history_dir = tmp_path / ".gobp" / "history"
    assert history_dir.exists()
    assert history_dir.is_dir()


def test_append_event_returns_event_dict(tmp_path: Path):
    """append_event returns the event it wrote."""
    event = append_event(
        gobp_root=tmp_path,
        event_type="test.event",
        payload={"key": "value"},
        actor="tester",
    )

    assert event["event_type"] == "test.event"
    assert event["actor"] == "tester"
    assert event["payload"] == {"key": "value"}
    assert "timestamp" in event


def test_append_event_writes_jsonl_line(tmp_path: Path):
    """Event is written as single JSON line."""
    append_event(tmp_path, "a.b", {"x": 1}, "actor1")

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = tmp_path / ".gobp" / "history" / f"{date_str}.jsonl"
    assert log_file.exists()

    content = log_file.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    assert len(lines) == 1

    parsed = json.loads(lines[0])
    assert parsed["event_type"] == "a.b"
    assert parsed["payload"]["x"] == 1


def test_append_multiple_events_all_logged(tmp_path: Path):
    """Multiple events append to same daily file."""
    append_event(tmp_path, "evt.1", {"n": 1}, "a")
    append_event(tmp_path, "evt.2", {"n": 2}, "a")
    append_event(tmp_path, "evt.3", {"n": 3}, "a")

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = tmp_path / ".gobp" / "history" / f"{date_str}.jsonl"
    lines = log_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 3


def test_append_event_default_actor(tmp_path: Path):
    """Default actor is 'unknown'."""
    event = append_event(tmp_path, "e", {})
    assert event["actor"] == "unknown"


def test_append_event_non_serializable_raises(tmp_path: Path):
    """Non-JSON-serializable payload raises ValueError."""

    class NotSerializable:
        pass

    with pytest.raises(ValueError, match="not JSON-serializable"):
        append_event(tmp_path, "bad", {"obj": NotSerializable()})


def test_read_events_empty_if_no_log(tmp_path: Path):
    """read_events returns [] if no log file exists."""
    events = read_events(tmp_path)
    assert events == []


def test_read_events_returns_all_events(tmp_path: Path):
    """read_events returns all events from today's log."""
    append_event(tmp_path, "e1", {"x": 1}, "a")
    append_event(tmp_path, "e2", {"x": 2}, "b")
    append_event(tmp_path, "e3", {"x": 3}, "c")

    events = read_events(tmp_path)
    assert len(events) == 3
    assert events[0]["event_type"] == "e1"
    assert events[1]["event_type"] == "e2"
    assert events[2]["event_type"] == "e3"


def test_read_events_specific_date(tmp_path: Path):
    """read_events(date_str) reads a specific day's log."""
    # Create a fake log for a past date
    history_dir = tmp_path / ".gobp" / "history"
    history_dir.mkdir(parents=True)
    past_log = history_dir / "2025-01-01.jsonl"
    past_log.write_text(
        '{"event_type":"old","payload":{},"actor":"a","timestamp":"2025-01-01T00:00:00+00:00"}\n'
    )

    events = read_events(tmp_path, date_str="2025-01-01")
    assert len(events) == 1
    assert events[0]["event_type"] == "old"


def test_read_events_corrupted_log_raises(tmp_path: Path):
    """Corrupted JSON in log raises ValueError."""
    history_dir = tmp_path / ".gobp" / "history"
    history_dir.mkdir(parents=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = history_dir / f"{date_str}.jsonl"
    log_file.write_text("not valid json\n")

    with pytest.raises(ValueError, match="Corrupted history log"):
        read_events(tmp_path)
