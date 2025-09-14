import sys
import argparse
import subprocess
import signal
import time
from game.main import main as game_main
from panel.main import main as panel_main


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ufogame", description="Run game or panel")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-g", "--game", action="store_true", help="Run the game")
    group.add_argument("-p", "--panel", action="store_true", help="Run the panel")
    group.add_argument("-t", "--test", action="store_true", help="Run server + 4 panels on one machine")
    parser.add_argument("--player", type=int, default=None, help="Which player the panel controls (1-9)")
    args = parser.parse_args(argv)

    if args.game:
        game_main()
    elif args.panel:
        player = args.player
        if player is None or player < 1 or player > 9:
            print("--player must be an integer between 1 and 9")
            return 2
        panel_main(player)
    elif args.test:
        return _run_test_mode()

def _run_test_mode() -> int:
    procs = []
    try:
        # Start server
        procs.append(subprocess.Popen([sys.executable, __file__, "-g"]))
        time.sleep(0.3)
        # Start 4 panels: players 1..4
        for player in range(1, 5):
            procs.append(subprocess.Popen([sys.executable, __file__, "-p", "--player", str(player)]))
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
