from threading import Event
import signal
import time
from common.connect import start_mdns_advertiser
from common.logger import get_logger


def main(player: int | None):
    if player is None:
        print("No player specified")
        return 1
    logger = get_logger(f"panel-{player}")
    logger.info(f"Panel starting for player={player}")

    # Start mDNS advertisement in background
    stop_event = start_mdns_advertiser(f"ufogame-{player}", 8200 + player, {"player": str(player)})

    # Block until Ctrl-C
    shutdown = Event()

    def _handle_sigint(signum, frame):
        shutdown.set()

    signal.signal(signal.SIGINT, _handle_sigint)
    logger.info("Panel running; press Ctrl-C to stop")
    try:
        while not shutdown.is_set():
            time.sleep(0.2)
    finally:
        logger.info("Panel shutting down")
        stop_event.set()
    return 0

    
