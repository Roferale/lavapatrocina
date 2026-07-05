"""
Anti-duplication tracking manager.

Prevents the same physical vehicle from being counted multiple times while it
is near the counting line.  A cooldown window (default 30 s) suppresses
re-counting of the same ByteTrack ID.  Position history is stored for optional
future use (trajectory-based heuristics, UI playback, etc.).
"""

from __future__ import annotations

import time
from collections import deque


class TrackerManager:
    """Per-camera manager for active ByteTrack IDs."""

    # Maximum position samples kept per tracker ID.
    _MAX_HISTORY = 30

    def __init__(self, cooldown_seconds: int = 30) -> None:
        self.cooldown = cooldown_seconds
        # tracker_id → unix timestamp of last counting event
        self.counted_ids: dict[int, float] = {}
        # tracker_id → deque of (cx, cy, timestamp) tuples
        self.id_history: dict[int, deque[tuple[float, float, float]]] = {}

    # ------------------------------------------------------------------
    # Cooldown logic
    # ------------------------------------------------------------------

    def can_count(self, tracker_id: int) -> bool:
        """
        Return True when this tracker has *not* been counted within the
        cooldown window.  New (never-seen) trackers always return True.
        """
        last = self.counted_ids.get(tracker_id)
        if last is None:
            return True
        return (time.monotonic() - last) >= self.cooldown

    def mark_counted(self, tracker_id: int) -> None:
        """Record the current monotonic time as the last count for this ID."""
        self.counted_ids[tracker_id] = time.monotonic()

    # ------------------------------------------------------------------
    # Position history
    # ------------------------------------------------------------------

    def update_position(self, tracker_id: int, cx: float, cy: float) -> None:
        """Append the current position (with timestamp) to the history ring."""
        if tracker_id not in self.id_history:
            self.id_history[tracker_id] = deque(maxlen=self._MAX_HISTORY)
        self.id_history[tracker_id].append((cx, cy, time.monotonic()))

    def get_history(
        self, tracker_id: int
    ) -> list[tuple[float, float, float]]:
        """Return a copy of the position history for the given tracker."""
        buf = self.id_history.get(tracker_id)
        return list(buf) if buf else []

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup(self, active_ids: set[int]) -> None:
        """
        Remove position history for trackers that are no longer active.
        Entries in ``counted_ids`` are only removed once the cooldown has
        expired — this prevents a vehicle that briefly leaves the frame from
        being double-counted on re-entry while still within the window.
        """
        now = time.monotonic()

        # Drop position history for gone trackers immediately.
        stale_history = [tid for tid in self.id_history if tid not in active_ids]
        for tid in stale_history:
            del self.id_history[tid]

        # Drop counted_ids entries only after cooldown has fully expired.
        stale_counts = [
            tid
            for tid, ts in self.counted_ids.items()
            if tid not in active_ids and (now - ts) >= self.cooldown
        ]
        for tid in stale_counts:
            del self.counted_ids[tid]
