"""Logging setup for the API process."""

import logging
import sys


def configure_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        stream=sys.stdout,
        force=True,
    )
    # Attach ring buffer for Diagnostics → Log viewer (additive)
    try:
        from app.services.log_buffer import attach_log_handler

        attach_log_handler()
    except Exception:  # noqa: BLE001
        pass
