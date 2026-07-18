"""In-memory ring buffer for diagnostics log viewer."""

from __future__ import annotations

import logging
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any


class RingLogHandler(logging.Handler):
    def __init__(self, capacity: int = 2000) -> None:
        super().__init__()
        self._capacity = capacity
        self._lock = threading.Lock()
        self._records: deque[dict[str, Any]] = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            entry = {
                "id": f"{record.created:.6f}-{record.thread}",
                "time": datetime.fromtimestamp(
                    record.created, tz=timezone.utc
                ).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": self.format(record) if self.formatter else record.getMessage(),
            }
            with self._lock:
                self._records.append(entry)
        except Exception:  # noqa: BLE001
            self.handleError(record)

    def list_entries(
        self,
        *,
        level: str | None = None,
        search: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        with self._lock:
            items = list(self._records)
        if level:
            level_u = level.upper()
            items = [i for i in items if i["level"] == level_u]
        if search:
            q = search.lower()
            items = [
                i
                for i in items
                if q in i["message"].lower() or q in i["logger"].lower()
            ]
        if limit > 0:
            items = items[-limit:]
        return items

    def clear(self) -> int:
        with self._lock:
            n = len(self._records)
            self._records.clear()
            return n

    def export_text(self) -> str:
        lines = [
            f"{e['time']} | {e['level']:<8} | {e['logger']} | {e['message']}"
            for e in self.list_entries(limit=0)
        ]
        return "\n".join(lines) + ("\n" if lines else "")


_HANDLER: RingLogHandler | None = None


def get_log_handler() -> RingLogHandler:
    global _HANDLER
    if _HANDLER is None:
        _HANDLER = RingLogHandler()
        _HANDLER.setFormatter(
            logging.Formatter("%(message)s")
        )
    return _HANDLER


def attach_log_handler() -> RingLogHandler:
    handler = get_log_handler()
    root = logging.getLogger()
    if handler not in root.handlers:
        root.addHandler(handler)
    return handler
