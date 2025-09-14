
from threading import Event
import signal
import time
from common.logger import get_logger
from common.connect import start_mdns_advertiser


def main():
    logger = get_logger("server")
    logger.info("Game server starting")

    # Start mDNS advertisement in background
    stop_event = start_mdns_advertiser("ufogame-0", 8200)

    # Block until Ctrl-C
    shutdown = Event()

    def _handle_sigint(signum, frame):
        shutdown.set()

    signal.signal(signal.SIGINT, _handle_sigint)
    logger.info("Game server running; press Ctrl-C to stop")
    try:
        while not shutdown.is_set():
            time.sleep(0.2)
    finally:
        logger.info("Game server shutting down")
        stop_event.set()

    
