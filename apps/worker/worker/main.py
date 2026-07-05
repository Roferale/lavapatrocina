"""
WorkerOrchestrator — top-level entry point for the worker container.

Responsibilities
----------------
* Read active cameras from PostgreSQL every 60 seconds.
* Start a CameraProcessor task for each newly active camera.
* Stop / restart tasks for cameras that become inactive or crash.
* Write a JSON status file to WORKER_STATUS_FILE.
* Handle SIGTERM / SIGINT for clean shutdown.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import traceback
from datetime import datetime, timezone

from worker.camera_processor import CameraProcessor
from worker.config import settings
from worker.database import get_active_cameras, save_system_log

logger = logging.getLogger("orchestrator")

# How often the orchestrator reconciles cameras against the DB.
_RECONCILE_INTERVAL_SECONDS = 60


class WorkerOrchestrator:
    def __init__(self) -> None:
        # camera_id (str) → CameraProcessor
        self.processors: dict[str, CameraProcessor] = {}
        # camera_id (str) → asyncio.Task
        self.tasks: dict[str, asyncio.Task] = {}
        self.running: bool = False

    # ------------------------------------------------------------------
    # Public lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the orchestrator.  Runs until stop_all() is called."""
        self.running = True
        self._write_status("starting")

        await save_system_log("INFO", "orchestrator", "Worker starting")
        logger.info("Worker orchestrator starting")

        try:
            await self._main_loop()
        finally:
            await self.stop_all()

    async def stop_all(self) -> None:
        """Gracefully stop every camera processor and write a final status."""
        logger.info("Stopping all camera processors …")
        self.running = False

        # Signal all processors to stop.
        stop_coros = [p.stop() for p in self.processors.values()]
        if stop_coros:
            await asyncio.gather(*stop_coros, return_exceptions=True)

        # Wait for all tasks to finish (up to 10 s each).
        for cam_id, task in list(self.tasks.items()):
            if not task.done():
                try:
                    await asyncio.wait_for(task, timeout=10.0)
                except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
                    task.cancel()

        self.processors.clear()
        self.tasks.clear()

        self._write_status("stopped")
        await save_system_log("INFO", "orchestrator", "Worker stopped")
        logger.info("Worker stopped")

    # ------------------------------------------------------------------
    # Main reconciliation loop
    # ------------------------------------------------------------------

    async def _main_loop(self) -> None:
        """
        Every _RECONCILE_INTERVAL_SECONDS:
          1. Reload active cameras from the DB.
          2. Start processors for new cameras.
          3. Stop processors for cameras that are no longer active.
          4. Restart crashed tasks.
        """
        while self.running:
            try:
                await self._reconcile()
            except Exception as exc:  # noqa: BLE001
                logger.error("Reconcile error: %s\n%s", exc, traceback.format_exc())
                await save_system_log(
                    "ERROR",
                    "orchestrator",
                    f"Reconcile error: {exc}",
                    {"traceback": traceback.format_exc()},
                )

            self._write_status("running")

            # Sleep in small increments so SIGINT is handled promptly.
            for _ in range(_RECONCILE_INTERVAL_SECONDS):
                if not self.running:
                    break
                await asyncio.sleep(1)

    async def _reconcile(self) -> None:
        """Diff active cameras vs running processors and start/stop as needed."""
        active_cameras = await get_active_cameras()
        active_ids = {str(cam["id"]) for cam in active_cameras}
        running_ids = set(self.processors.keys())

        # ── Stop processors for cameras no longer active ─────────────────
        removed = running_ids - active_ids
        for cam_id in removed:
            logger.info("Camera %s removed — stopping processor", cam_id)
            await self._stop_camera(cam_id)

        # ── Restart crashed tasks ─────────────────────────────────────────
        for cam_id, task in list(self.tasks.items()):
            if task.done() and cam_id in active_ids:
                exc = task.exception() if not task.cancelled() else None
                logger.warning(
                    "Task for camera %s exited unexpectedly (exc=%s) — restarting",
                    cam_id,
                    exc,
                )
                await save_system_log(
                    "WARNING",
                    f"camera.{cam_id}",
                    f"Camera processor crashed, restarting: {exc}",
                )
                # Find the camera dict so we can recreate the processor.
                cam_dict = next(
                    (c for c in active_cameras if str(c["id"]) == cam_id), None
                )
                if cam_dict:
                    await self._stop_camera(cam_id)
                    await self._start_camera(cam_dict)

        # ── Start processors for new cameras ─────────────────────────────
        new_cameras = [c for c in active_cameras if str(c["id"]) not in self.tasks]
        for cam in new_cameras:
            logger.info("Starting processor for camera %s (%s)", cam["id"], cam["name"])
            try:
                await self._start_camera(cam)
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to start camera %s: %s", cam["id"], exc)
                await save_system_log(
                    "ERROR",
                    f"camera.{cam['id']}",
                    f"Failed to start camera processor: {exc}",
                    {"traceback": traceback.format_exc()},
                )

    # ------------------------------------------------------------------
    # Per-camera start / stop helpers
    # ------------------------------------------------------------------

    async def _start_camera(self, camera: dict) -> None:
        """Initialise and launch a CameraProcessor task."""
        cam_id = str(camera["id"])

        processor = CameraProcessor(camera)
        await processor.initialize()  # loads YOLO, fetches counting line

        task = asyncio.create_task(
            processor.run(),
            name=f"camera-{cam_id[:8]}",
        )

        self.processors[cam_id] = processor
        self.tasks[cam_id] = task

        logger.info("Camera %s (%s) processor started", cam_id, camera["name"])

    async def _stop_camera(self, cam_id: str) -> None:
        """Stop a single camera processor and clean up."""
        processor = self.processors.pop(cam_id, None)
        task = self.tasks.pop(cam_id, None)

        if processor:
            await processor.stop()

        if task and not task.done():
            try:
                await asyncio.wait_for(task, timeout=10.0)
            except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
                task.cancel()

    # ------------------------------------------------------------------
    # Status file
    # ------------------------------------------------------------------

    def _write_status(self, status: str) -> None:
        """
        Atomically write worker status to WORKER_STATUS_FILE.

        Any error here is logged but never raised — the status file is
        best-effort telemetry, not critical path.
        """
        data = {
            "status": status,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "cameras": [
                {
                    "id": cam_id,
                    "name": p.name,
                    "running": not self.tasks[cam_id].done()
                    if cam_id in self.tasks
                    else False,
                }
                for cam_id, p in self.processors.items()
            ],
            "camera_count": len(self.processors),
        }
        tmp_path = settings.WORKER_STATUS_FILE + ".tmp"
        try:
            # Write to a temp file first, then rename for atomic replacement.
            with open(tmp_path, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, settings.WORKER_STATUS_FILE)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not write status file: %s", exc)
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
        format="%(asctime)s %(name)-20s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    orchestrator = WorkerOrchestrator()

    loop = asyncio.get_running_loop()

    def _request_shutdown() -> None:
        logger.info("Shutdown signal received")
        asyncio.create_task(orchestrator.stop_all())

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _request_shutdown)
        except NotImplementedError:
            # Windows does not support add_signal_handler.
            pass

    await orchestrator.start()


if __name__ == "__main__":
    asyncio.run(main())
