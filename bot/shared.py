import threading
from collections import deque
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional

from .config import TIMEZONE


class LogBuffer:
    """Thread-safe rotating log buffer for UI consumption."""

    def __init__(self, maxlen: int = 500):
        self._buf: Deque[Dict[str, Any]] = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def add(self, level: str, message: str) -> None:
        with self._lock:
            self._buf.append(
                {
                    "ts": datetime.now(TIMEZONE).isoformat(),
                    "level": level,
                    "message": message,
                }
            )

    def latest(self, limit: int = 200) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._buf)[-limit:]


class SnapshotStore:
    """Holds the latest snapshots for API consumption."""

    def __init__(self):
        self._lock = threading.Lock()
        self.status: Dict[str, Any] = {}
        self.metrics: Dict[str, Any] = {}
        self.positions: List[Dict[str, Any]] = []
        self.candidates: List[Dict[str, Any]] = []

    def update(self, *, status=None, metrics=None, positions=None, candidates=None) -> None:
        with self._lock:
            if status is not None:
                self.status = status
            if metrics is not None:
                self.metrics = metrics
            if positions is not None:
                self.positions = positions
            if candidates is not None:
                self.candidates = candidates

    def get(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "status": self.status,
                "metrics": self.metrics,
                "positions": self.positions,
                "candidates": self.candidates,
            }


LOG_BUFFER = LogBuffer()
SNAPSHOTS = SnapshotStore()

