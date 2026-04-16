"""Snowflake ID generator for GoBP.

Generates 64-bit integers that are:
- Globally unique (without central coordination)
- Time-sortable (newer IDs are larger)
- Fast (4096 IDs per millisecond per machine)

Bit layout (Twitter Snowflake):
  1  bit  — sign (always 0)
  41 bits — milliseconds since EPOCH
  10 bits — machine ID (0-1023)
  12 bits — sequence per millisecond (0-4095)

Epoch: 2024-01-01 00:00:00 UTC
"""

from __future__ import annotations

import os
import threading
import time
from typing import ClassVar

# Epoch: 2024-01-01 00:00:00 UTC in milliseconds
_EPOCH_MS: int = 1704067200000

# Bit shifts
_MACHINE_ID_BITS = 10
_SEQUENCE_BITS = 12
_MACHINE_ID_SHIFT = _SEQUENCE_BITS
_TIMESTAMP_SHIFT = _SEQUENCE_BITS + _MACHINE_ID_BITS

# Masks
_MAX_MACHINE_ID = (1 << _MACHINE_ID_BITS) - 1   # 1023
_MAX_SEQUENCE = (1 << _SEQUENCE_BITS) - 1         # 4095


class SnowflakeGenerator:
    """Thread-safe Snowflake ID generator."""

    _instance: ClassVar["SnowflakeGenerator | None"] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self, machine_id: int = 0) -> None:
        if machine_id < 0 or machine_id > _MAX_MACHINE_ID:
            raise ValueError(f"machine_id must be 0-{_MAX_MACHINE_ID}, got {machine_id}")
        self.machine_id = machine_id & _MAX_MACHINE_ID
        self._sequence = 0
        self._last_ms = -1
        self._gen_lock = threading.Lock()

    @classmethod
    def default(cls) -> "SnowflakeGenerator":
        """Get default singleton generator."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    # Machine ID from env or random
                    machine_id = int(os.environ.get("GOBP_MACHINE_ID", "0")) % 1024
                    cls._instance = cls(machine_id=machine_id)
        return cls._instance

    def next_id(self) -> int:
        """Generate next unique Snowflake ID."""
        with self._gen_lock:
            ms = self._current_ms()

            if ms < self._last_ms:
                # Clock went backwards — wait
                time.sleep((self._last_ms - ms) / 1000)
                ms = self._current_ms()

            if ms == self._last_ms:
                self._sequence = (self._sequence + 1) & _MAX_SEQUENCE
                if self._sequence == 0:
                    # Sequence exhausted — wait for next ms
                    while ms <= self._last_ms:
                        ms = self._current_ms()
            else:
                self._sequence = 0

            self._last_ms = ms

            return (
                ((ms - _EPOCH_MS) << _TIMESTAMP_SHIFT) |
                (self.machine_id << _MACHINE_ID_SHIFT) |
                self._sequence
            )

    def _current_ms(self) -> int:
        return int(time.time() * 1000)


# Module-level convenience function
def generate_snowflake() -> int:
    """Generate a Snowflake ID using default generator."""
    return SnowflakeGenerator.default().next_id()


def snowflake_to_timestamp(snowflake_id: int) -> float:
    """Extract creation timestamp from Snowflake ID."""
    ms = (snowflake_id >> _TIMESTAMP_SHIFT) + _EPOCH_MS
    return ms / 1000


def snowflake_to_datetime(snowflake_id: int):
    """Extract creation datetime from Snowflake ID."""
    from datetime import datetime, timezone

    ts = snowflake_to_timestamp(snowflake_id)
    return datetime.fromtimestamp(ts, tz=timezone.utc)
