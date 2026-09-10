from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from jobpilot.storage.database import Database


@dataclass(frozen=True, slots=True)
class WorkerStatus:
    alive: bool
    paused: bool


class SampleLifecycleWorker:
    """Phase 1 only: exercises lifecycle persistence without external activity."""

    def __init__(self, database: Database, session_id: str, *, item_seconds: float = 0.4) -> None:
        self._database = database
        self._session_id = session_id
        self._item_seconds = max(0.05, item_seconds)
        self._run_gate = threading.Event()
        self._stop_event = threading.Event()
        self._cancel_current = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            self._run_gate.set()
            return
        self._run_gate.set()
        self._stop_event.clear()
        self._cancel_current.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name=f"jobpilot-phase1-sample-{self._session_id[:8]}",
            daemon=False,
        )
        self._thread.start()

    def pause(self) -> None:
        self._run_gate.clear()

    def resume(self) -> None:
        self._run_gate.set()

    def stop(self, timeout_seconds: float = 5.0) -> None:
        self._cancel_current.set()
        self._stop_event.set()
        self._run_gate.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout_seconds)
            if thread.is_alive():
                raise TimeoutError("sample lifecycle worker did not stop")
        self._database.requeue_owned_sample_work(self._session_id)

    def status(self) -> WorkerStatus:
        thread = self._thread
        return WorkerStatus(
            alive=bool(thread and thread.is_alive()),
            paused=not self._run_gate.is_set(),
        )

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            self._run_gate.wait()
            if self._stop_event.is_set():
                break
            item = self._database.claim_next_sample_work(self._session_id)
            if item is None:
                if self._stop_event.wait(0.1):
                    break
                continue

            deadline = time.monotonic() + self._item_seconds
            cancelled = False
            while time.monotonic() < deadline:
                if self._cancel_current.is_set() or self._stop_event.wait(0.02):
                    cancelled = True
                    break
            if cancelled:
                self._database.requeue_owned_sample_work(self._session_id)
                break
            self._database.complete_sample_work(item["id"], self._session_id)
