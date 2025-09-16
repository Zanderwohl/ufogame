#!/usr/bin/env python3

import sys
import argparse
import subprocess
import signal
import time
from pathlib import Path
import tomllib

from common import get_logger
from server.main import main as server_main
from client.main import main as client_main


def main(argv=None):
    logger = get_logger('startup')

    parser = argparse.ArgumentParser(prog="ufogame", description="Run server or client")
    # CLI flags are optional if config.toml provides a role
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("-s", "--server", action="store_true", help="Run the server")
    group.add_argument("-c", "--client", action="store_true", help="Run the client")
    group.add_argument("-t", "--test", action="store_true", help="Run server + 4 panels on one machine")
    parser.add_argument("--player", type=int, default=None, help="Which player the client controls (1-9)")
    args = parser.parse_args(argv)

    # Load top-level config.toml if present
    config: dict = {}
    config_path = Path(__file__).parent / "config.toml"
    if config_path.exists():
        try:
            with config_path.open("rb") as f:
                config = tomllib.load(f)
        except Exception as e:
            logger.debug(f"Failed to read config.toml: {e}")

    # Determine role: CLI flags take precedence; otherwise use config["role"]
    role = None
    if args.server:
        role = "server"
    elif args.client:
        role = "client"
    elif args.test:
        role = "test"
    else:
        raw_role = config.get("role") if config else None
        if isinstance(raw_role, str):
            role = raw_role.strip().lower()

    if role == "server":
        return server_main()
    elif role == "client":
        # Player from CLI if provided; otherwise from config
        player_value = args.player if args.player is not None else (config.get("player") if config else None)
        try:
            player = int(player_value) if player_value is not None else None
        except (TypeError, ValueError):
            player = None
        if player is None or player < 1 or player > 9:
            logger.error("player must be an integer between 1 and 9 (via --player or config.toml)")
            return 2
        return client_main(player)
    elif role == "test":
        return _run_test_mode()
    else:
        if config_path.exists():
            logger.error("config.toml must set role to 'server', 'client', or 'test'")
        else:
            logger.error("Must specify --server/--client/--test or provide config.toml with role")
        return 2

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
