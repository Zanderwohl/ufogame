import sys
import argparse
import subprocess
import signal
import time

from common import get_logger
from server.main import main as server_main
from client.main import main as client_main


def main(argv=None):
    logger = get_logger('startup')

    parser = argparse.ArgumentParser(prog="ufogame", description="Run server or client")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-s", "--server", action="store_true", help="Run the server")
    group.add_argument("-c", "--client", action="store_true", help="Run the client")
    group.add_argument("-t", "--test", action="store_true", help="Run server + 4 panels on one machine")
    parser.add_argument("--player", type=int, default=None, help="Which player the client controls (1-9)")
    args = parser.parse_args(argv)

    if args.server:
        return server_main()
    elif args.client:
        player = args.player
        if player is None or player < 1 or player > 9:
            logger.error("--player must be an integer between 1 and 9")
            return 2
        return client_main(player)
    elif args.test:
        return _run_test_mode()
    else:
        logger.error("Must specify either --server or --client")
        return 0

def _run_test_mode() -> int:
    procs = []
    try:
        # Start server
        procs.append(subprocess.Popen([sys.executable, __file__, "-s"]))
        time.sleep(0.3)
        # Start 4 panels: players 1..4
        for player in range(1, 5):
            procs.append(subprocess.Popen([sys.executable, __file__, "-c", "--player", str(player)]))
            time.sleep(0.2)

        print("Test mode running: server + 4 panels. Press Ctrl-C to stop all.")
        # Wait until Ctrl-C
        stop = False
        def _sigint(sig, frame):
            nonlocal stop
            stop = True
        signal.signal(signal.SIGINT, _sigint)
        while not stop:
            time.sleep(0.3)
        return 0
    finally:
        for p in procs:
            if p.poll() is None:
                try:
                    p.terminate()
                except Exception:
                    pass
        # Give them a moment to exit, then kill if needed
        time.sleep(0.5)
        for p in procs:
            if p.poll() is None:
                try:
                    p.kill()
                except Exception:
                    pass
        return 0


if __name__ == "__main__":
    sys.exit(main())
