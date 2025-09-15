from threading import Event
import signal
import time
from typing import Callable, Optional, Dict
import logging

from .logger import get_logger
from .connect import start_mdns_advertiser


def run(
    logger_name: str,
    advertise_instance: Optional[str],
    advertise_port: Optional[int],
    advertise_properties: Optional[Dict[str, str]],
    run_frame: Callable[[logging.Logger], bool],
) -> int:
    logger = get_logger(logger_name)
    logger.info("Starting")

    stop_event: Optional[Event] = None
    if advertise_instance and advertise_port:
        stop_event = start_mdns_advertiser(advertise_instance, advertise_port, advertise_properties or {})

    shutdown = Event()

    def _handle_sigint(signum, frame):
        shutdown.set()

    signal.signal(signal.SIGINT, _handle_sigint)
    logger.info("Running; press Ctrl-C to stop")

    try:
        while not shutdown.is_set():
            start = time.monotonic()
            should_continue = run_frame(logger)
            if not should_continue:
                break
            elapsed = time.monotonic() - start
            min_frame_seconds = 0.05
            remaining = min_frame_seconds - elapsed
            if remaining > 0:
                time.sleep(remaining)
        return 0
    finally:
        logger.info("Shutting down")
        if stop_event is not None:
            stop_event.set()


