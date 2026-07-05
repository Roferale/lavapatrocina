"""
Line-crossing detector based on the signed cross-product of two 2-D vectors.

Geometry refresher
------------------
Given a directed line from P1=(x1,y1) to P2=(x2,y2), the line vector is
    L = (dx, dy) = (x2-x1, y2-y1)

For any point Q=(px, py), the perpendicular vector from P1 to Q is
    V = (px-x1, py-y1)

The 2-D cross product (z-component of the 3-D cross product) is
    cross = dx*(py-y1) - dy*(px-x1)

    cross > 0  →  Q is on the LEFT  side of the directed line  (side = +1)
    cross < 0  →  Q is on the RIGHT side of the directed line  (side = -1)
    cross = 0  →  Q is exactly ON the line

Entry / exit convention
-----------------------
"entry"  →  vehicle crosses from the positive side (+1) to the negative side (-1)
             i.e. the sign of cross changes from + to –
"exit"   →  vehicle crosses from the negative side (-1) to the positive side (+1)
             i.e. the sign of cross changes from – to +
"both"   →  any crossing is recorded; the direction is derived from the sign change
"""

from __future__ import annotations


class LineCrossingDetector:
    """Stateful, per-tracker-ID crossing detector for a single virtual line."""

    def __init__(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        direction: str,
        frame_width: int,
        frame_height: int,
    ) -> None:
        """
        Parameters
        ----------
        x1, y1, x2, y2   Absolute pixel coordinates of the line endpoints.
        direction         ``"entry"``, ``"exit"``, or ``"both"``.
        frame_width,
        frame_height      Dimensions of the processed frame (kept for reference /
                          future normalisation; not strictly required here).
        """
        # Store the directed line in absolute pixel coordinates.
        self.x1 = float(x1)
        self.y1 = float(y1)
        self.x2 = float(x2)
        self.y2 = float(y2)
        self.dx = self.x2 - self.x1   # line direction vector  (horizontal component)
        self.dy = self.y2 - self.y1   # line direction vector  (vertical component)
        self.direction = direction.lower()  # "entry" | "exit" | "both"
        self.frame_width = frame_width
        self.frame_height = frame_height

        # Map tracker_id → last known side (+1 or -1).
        # A side of 0 means the tracker has never been assigned a side yet.
        self._prev_side: dict[int, int] = {}

    # ------------------------------------------------------------------
    # Core geometry
    # ------------------------------------------------------------------

    def get_side(self, px: float, py: float) -> int:
        """
        Return +1 if (px, py) is on the left side of the directed line,
        -1 if on the right side, and 0 if exactly on the line.

        Uses the z-component of the cross product:
            cross = dx*(py - y1) - dy*(px - x1)
        """
        cross = self.dx * (py - self.y1) - self.dy * (px - self.x1)
        if cross > 0:
            return 1
        if cross < 0:
            return -1
        return 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_crossing(
        self, tracker_id: int, cx: float, cy: float
    ) -> tuple[bool, str]:
        """
        Determine whether tracker ``tracker_id`` has crossed the line since the
        last call.

        Parameters
        ----------
        tracker_id   Unique integer ID assigned by ByteTrack.
        cx, cy       Centre coordinates of the bounding box in absolute pixels.

        Returns
        -------
        (crossed, direction)
            crossed     True only on the frame where the side changes.
            direction   ``"entry"`` or ``"exit"``; meaningless when crossed=False.
        """
        current_side = self.get_side(cx, cy)

        # Points exactly on the line are ambiguous — skip them to avoid spurious
        # detections when a vehicle stops right on the line.
        if current_side == 0:
            return False, ""

        prev_side = self._prev_side.get(tracker_id, 0)
        self._prev_side[tracker_id] = current_side

        # First observation — no previous side yet, cannot determine crossing.
        if prev_side == 0:
            return False, ""

        # No side change → no crossing.
        if prev_side == current_side:
            return False, ""

        # ── A crossing happened ──────────────────────────────────────────────
        # Determine the crossing direction from the sign change:
        #   +1 → -1  means the vehicle moved from left to right of the directed
        #             line, which we call "entry" (approaching the counter).
        #   -1 → +1  means the vehicle moved from right to left → "exit".
        if prev_side == 1:
            crossing_direction = "entry"
        else:
            crossing_direction = "exit"

        # Apply the configured filter.
        if self.direction == "both":
            return True, crossing_direction
        if self.direction == crossing_direction:
            return True, crossing_direction

        # Crossing happened but in the wrong direction for the current config.
        return False, ""

    def remove_tracker(self, tracker_id: int) -> None:
        """Discard all state for the given tracker ID."""
        self._prev_side.pop(tracker_id, None)

    def cleanup_old_trackers(self, active_ids: set[int]) -> None:
        """Remove state for all tracker IDs that are no longer active."""
        stale = [tid for tid in self._prev_side if tid not in active_ids]
        for tid in stale:
            del self._prev_side[tid]
