"""
CameraProcessor — one instance per active camera.

Each processor runs as an asyncio Task and owns:
  • A cv2.VideoCapture for the RTSP stream (runs in a thread-pool executor)
  • A YOLO model (loaded once, shared across inference calls in the executor)
  • A LineCrossingDetector for the camera's configured counting line
  • A TrackerManager for cooldown / duplication prevention
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import cv2
import numpy as np

from ultralytics import YOLO

from worker.config import settings
from worker.database import (
    get_counting_line,
    save_system_log,
    save_vehicle_event,
    update_camera_status,
)
from worker.line_crossing import LineCrossingDetector
from worker.tracker_manager import TrackerManager

# ---------------------------------------------------------------------------
# COCO class IDs that map to vehicles we care about
# ---------------------------------------------------------------------------
VEHICLE_CLASSES: dict[int, str] = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}

# How often (in processed frames) to push a camera-online heartbeat to the DB.
_STATUS_UPDATE_EVERY_N_FRAMES = 100


class CameraProcessor:
    """Processes a single RTSP camera stream end-to-end."""

    def __init__(self, camera: dict) -> None:
        self.camera = camera
        self.camera_id: str = str(camera["id"])
        self.name: str = camera.get("name", self.camera_id)
        self.rtsp_url: str = camera["rtsp_url"]           # already decrypted
        self.fps: int = int(camera.get("processing_fps") or settings.DEFAULT_FPS)
        self.width: int = int(camera.get("processing_width") or 640)
        self.height: int = int(camera.get("processing_height") or 480)
        self.min_confidence: float = float(
            camera.get("min_confidence") or settings.DEFAULT_MIN_CONFIDENCE
        )

        self.running: bool = False
        self.cap: Optional[cv2.VideoCapture] = None
        self.model: Optional[YOLO] = None
        self.line_detector: Optional[LineCrossingDetector] = None
        self.active_classes: list[str] = ["car", "truck", "bus", "motorcycle"]
        self.tracker_manager: TrackerManager = TrackerManager(cooldown_seconds=30)

        self.logger = logging.getLogger(f"camera.{self.camera_id[:8]}")

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Load the YOLO model and configure the counting line."""
        loop = asyncio.get_running_loop()

        # Load model in a thread so we don't block the event loop.
        self.logger.info("Loading YOLO model '%s'", settings.YOLO_MODEL)
        try:
            self.model = await loop.run_in_executor(
                None, lambda: YOLO(settings.YOLO_MODEL)
            )
        except Exception as exc:
            self.logger.error("Failed to load YOLO model: %s", exc)
            await save_system_log(
                "ERROR",
                f"camera.{self.camera_id}",
                f"YOLO model load failed: {exc}",
                {"model": settings.YOLO_MODEL},
            )
            raise

        # Load counting line from DB.
        line = await get_counting_line(self.camera_id)
        if line is None:
            self.logger.warning(
                "No counting line configured for camera %s — events will NOT be recorded",
                self.name,
            )
            self.line_detector = None
        else:
            self.active_classes = line.get("active_classes") or self.active_classes
            # Convert relative (0–1) coordinates to absolute pixels.
            x1 = line["x1_relative"] * self.width
            y1 = line["y1_relative"] * self.height
            x2 = line["x2_relative"] * self.width
            y2 = line["y2_relative"] * self.height
            self.line_detector = LineCrossingDetector(
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
                direction=str(line["direction"]),
                frame_width=self.width,
                frame_height=self.height,
            )
            self.logger.info(
                "Counting line loaded: (%.0f,%.0f)→(%.0f,%.0f) dir=%s classes=%s",
                x1, y1, x2, y2,
                line["direction"],
                self.active_classes,
            )

    # ------------------------------------------------------------------
    # RTSP connection
    # ------------------------------------------------------------------

    def _connect(self) -> bool:
        """
        (Blocking) Open the RTSP stream via cv2.VideoCapture.

        Called inside run_in_executor so the event loop is never stalled.
        Returns True on success.
        """
        if self.cap is not None:
            self.cap.release()

        self.logger.info("Connecting to RTSP stream …")
        cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)

        # Reduce latency: use a 1-frame buffer and short open timeout.
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        # Some builds expose these timeout options.
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5_000)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5_000)

        if not cap.isOpened():
            cap.release()
            self.logger.warning("VideoCapture could not open stream")
            return False

        self.cap = cap
        self.logger.info("Connected to RTSP stream")
        return True

    def _read_frame(self) -> tuple[bool, Optional[np.ndarray]]:
        """(Blocking) Read exactly one frame from the capture."""
        if self.cap is None:
            return False, None
        ok, frame = self.cap.read()
        return ok, frame if ok else None

    def _run_inference(self, frame: np.ndarray):
        """
        (Blocking) Run YOLO tracking on a single frame.

        Returns the Ultralytics Results object (or None on error).
        """
        try:
            results = self.model.track(
                frame,
                tracker="bytetrack.yaml",
                persist=True,     # keep ByteTrack state across frames
                imgsz=self.width,
                verbose=False,
            )
            return results[0] if results else None
        except Exception as exc:  # noqa: BLE001
            self.logger.error("Inference error: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Main processing loop
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """
        Main async loop.  Runs until self.running is set to False.

        Frame-rate throttling strategy
        --------------------------------
        We read frames as fast as the source delivers them but only forward
        every N-th frame to YOLO.  N is computed from the camera's native FPS
        and the desired processing FPS, so we spend as little CPU as possible
        without introducing extra latency from sleeping.
        """
        self.running = True
        loop = asyncio.get_running_loop()

        frame_index = 0
        status_frame_counter = 0
        native_fps: float = 0.0   # updated after first successful connect

        # ── Connection loop ──────────────────────────────────────────────
        while self.running:
            connected = await loop.run_in_executor(None, self._connect)
            if not connected:
                self.logger.warning(
                    "Connection failed — retrying in %d s",
                    settings.RECONNECT_INTERVAL,
                )
                await update_camera_status(self.camera_id, False)
                await save_system_log(
                    "WARNING",
                    f"camera.{self.camera_id}",
                    f"Camera '{self.name}' connection failed",
                )
                await asyncio.sleep(settings.RECONNECT_INTERVAL)
                continue

            # Detect source FPS for skip-frame ratio.
            raw_fps = self.cap.get(cv2.CAP_PROP_FPS) if self.cap else 0
            native_fps = raw_fps if raw_fps and raw_fps > 0 else 25.0
            # How many source frames to skip between inferences.
            skip = max(1, round(native_fps / self.fps))

            await update_camera_status(self.camera_id, True)
            await save_system_log(
                "INFO",
                f"camera.{self.camera_id}",
                f"Camera '{self.name}' connected (native {native_fps:.1f} fps, "
                f"processing every {skip} frames)",
            )

            # ── Frame loop ───────────────────────────────────────────────
            while self.running:
                ok, frame = await loop.run_in_executor(None, self._read_frame)

                if not ok or frame is None:
                    self.logger.warning("Frame read failed — reconnecting")
                    await update_camera_status(self.camera_id, False)
                    break  # back to connection loop

                frame_index += 1
                status_frame_counter += 1

                # Heartbeat to DB every N processed frames.
                if status_frame_counter >= _STATUS_UPDATE_EVERY_N_FRAMES:
                    await update_camera_status(self.camera_id, True)
                    status_frame_counter = 0

                # Skip frames to stay at target processing FPS.
                if frame_index % skip != 0:
                    continue

                # Resize to the configured processing resolution.
                if frame.shape[1] != self.width or frame.shape[0] != self.height:
                    frame = cv2.resize(frame, (self.width, self.height))

                # Skip YOLO if no counting line is set up — nothing to do.
                if self.line_detector is None:
                    continue

                # ── YOLO inference (blocking → executor) ─────────────────
                result = await loop.run_in_executor(
                    None, self._run_inference, frame
                )
                if result is None:
                    continue

                await self._process_detections(result, frame)

        # ── Cleanup ──────────────────────────────────────────────────────
        if self.cap is not None:
            await loop.run_in_executor(None, self.cap.release)
            self.cap = None
        await update_camera_status(self.camera_id, False)
        self.logger.info("Camera processor stopped")

    # ------------------------------------------------------------------
    # Detection handling
    # ------------------------------------------------------------------

    async def _process_detections(self, result, frame: np.ndarray) -> None:
        """
        Iterate over all YOLO detections in a single result object, check for
        line crossings, and persist confirmed events.
        """
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return

        active_ids: set[int] = set()

        for box in boxes:
            # Skip detections that ByteTrack has not yet assigned an ID to.
            if box.id is None:
                continue

            tracker_id = int(box.id.item())
            cls_id = int(box.cls.item())
            conf = float(box.conf.item())

            # Filter by class and confidence.
            vehicle_type = VEHICLE_CLASSES.get(cls_id)
            if vehicle_type is None:
                continue
            if vehicle_type not in self.active_classes:
                continue
            if conf < self.min_confidence:
                continue

            # Compute bounding-box centre.
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0

            active_ids.add(tracker_id)
            self.tracker_manager.update_position(tracker_id, cx, cy)

            # Check line crossing.
            crossed, crossing_dir = self.line_detector.check_crossing(
                tracker_id, cx, cy
            )

            if crossed and self.tracker_manager.can_count(tracker_id):
                self.tracker_manager.mark_counted(tracker_id)
                self.logger.info(
                    "Vehicle %s (id=%d conf=%.2f) crossed line → %s",
                    vehicle_type,
                    tracker_id,
                    conf,
                    crossing_dir,
                )
                await self._save_event(
                    tracker_id=tracker_id,
                    vehicle_type=vehicle_type,
                    confidence=conf,
                    direction=crossing_dir,
                    bbox=(x1, y1, x2, y2),
                    frame=frame,
                )

        # Housekeeping — prune old tracker state.
        self.line_detector.cleanup_old_trackers(active_ids)
        self.tracker_manager.cleanup(active_ids)

    # ------------------------------------------------------------------
    # Event persistence
    # ------------------------------------------------------------------

    async def _save_event(
        self,
        tracker_id: int,
        vehicle_type: str,
        confidence: float,
        direction: str,
        bbox: tuple[float, float, float, float],
        frame: np.ndarray,
    ) -> None:
        """Optionally save a snapshot then persist the vehicle event to the DB."""
        event_id = str(uuid.uuid4())
        snapshot_path: Optional[str] = None

        if settings.SAVE_SNAPSHOTS:
            snapshot_path = await asyncio.get_running_loop().run_in_executor(
                None, self._save_snapshot, frame, event_id
            )

        x1, y1, x2, y2 = bbox
        event_data = {
            "id": event_id,   # pre-generate so snapshot can reference it
            "camera_id": self.camera_id,
            "event_time": datetime.now(tz=timezone.utc),
            "vehicle_type": vehicle_type,
            "confidence": confidence,
            "direction": direction,
            "tracker_id": tracker_id,
            "bbox_x1": x1,
            "bbox_y1": y1,
            "bbox_x2": x2,
            "bbox_y2": y2,
            "snapshot_path": snapshot_path,
        }
        await save_vehicle_event(event_data)

    def _save_snapshot(self, frame: np.ndarray, event_id: str) -> Optional[str]:
        """
        (Blocking) Write a JPEG snapshot to::

            {SNAPSHOTS_DIR}/{camera_id}/{YYYY-MM-DD}/{event_id}.jpg

        Returns the path *relative to SNAPSHOTS_DIR* (suitable for DB storage
        and serving via the backend's static-files route), or None on failure.
        """
        try:
            date_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
            rel_dir = os.path.join(self.camera_id, date_str)
            abs_dir = os.path.join(settings.SNAPSHOTS_DIR, rel_dir)
            os.makedirs(abs_dir, exist_ok=True)

            filename = f"{event_id}.jpg"
            abs_path = os.path.join(abs_dir, filename)
            cv2.imwrite(abs_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

            rel_path = os.path.join(rel_dir, filename)
            return rel_path
        except Exception as exc:  # noqa: BLE001
            self.logger.error("Snapshot save failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def stop(self) -> None:
        """Signal the processor to stop at the next iteration."""
        self.running = False
        loop = asyncio.get_running_loop()
        if self.cap is not None:
            await loop.run_in_executor(None, self.cap.release)
            self.cap = None
