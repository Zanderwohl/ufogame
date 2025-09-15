
import time
import logging
import socket
from typing import Dict

from common.gamestate import GameStatePacket, GameState, ClientState, StartLevelPacket
from common.names import generate_names
from common.runner import run
from common.packets import TextPacket
from server.network import Client, ensure_server_ready, accept_new_clients, receive_packets, send_packet_to_player, \
    send_packet_to_all, PORT, all_clients_ready as net_all_clients_ready, set_client_ready, client_count, clients

COUNTDOWN_LENGTH = 3
_game_state: GameState = GameState.IDLE
_level = 0
_countdown: tuple[int, float] | None = None  # (value, last_sent_time)

def reset():
    global _game_state, _level, _countdown
    _game_state = GameState.IDLE
    _level = 0
    _countdown = None

def main():
    return run(
        logger_name="server",
        advertise_instance="ufogame-0",
        advertise_port=PORT,
        advertise_properties=None,
        run_frame=run_frame,
    )

def run_frame(logger: logging.Logger) -> bool:
    global _game_state, _countdown, _level
    try:
        ensure_server_ready(logger)
        new_client_ids = accept_new_clients(logger)
        for client_id in new_client_ids:
            # Send current state to newcomer, including countdown value if applicable
            if _game_state == GameState.LEVEL_COUNTDOWN and _countdown is not None:
                send_packet_to_player(client_id, GameStatePacket(state=_game_state, countdown=_countdown[0]))
            else:
                send_packet_to_player(client_id, GameStatePacket(state=_game_state))

        packets_by_player = receive_packets(logger)
        for pid, packets in packets_by_player.items():
            for p in packets:
                if isinstance(p, TextPacket):
                    logger.info(f"recv from {pid}: {p.text}")
                if isinstance(p, ClientState):
                    handle_client_state(logger, pid, p)

        if _game_state == GameState.IDLE and net_all_clients_ready():
            logger.info("All clients ready.")
            _game_state = GameState.LEVEL_COUNTDOWN
            _countdown = (COUNTDOWN_LENGTH + 1, 100.0)  # Distant past to force immediate countdown

        # Drive countdown timing and transition to IN_LEVEL
        if _game_state == GameState.LEVEL_COUNTDOWN and _countdown is not None:
            value, last_time = _countdown
            now = time.monotonic()
            if now - last_time >= 1.0:
                if value > 1:
                    value -= 1
                    _countdown = (value, now)
                    send_packet_to_all(GameStatePacket(state=GameState.LEVEL_COUNTDOWN, countdown=value))
                else:
                    _game_state = GameState.IN_LEVEL
                    _level += 1
                    _countdown = None
                    send_packet_to_all(GameStatePacket(state=GameState.IN_LEVEL))
                    # Start the level; provide doodad names

                    doodad_count = 0
                    for client in clients.values():
                        doodad_count += len(client.panel.capabilities)
                    doodad_names = generate_names(doodad_count)

                    n = 0
                    for pid, client in clients.items():
                        doodads = {}
                        for doodad in client.panel.capabilities:
                            doodads[doodad.id] = doodad_names[n]
                            n += 1
                        send_packet_to_player(pid, StartLevelPacket(doodad_names=doodads, level=_level))

        return True
    except Exception as e:
        logger.debug(f"Server frame error: {e}")
        return True


def handle_client_state(logger, pid, client_state):
    if client_state.ready:
        logger.info(f"Panel {pid} is ready")
        set_client_ready(pid, True)
    else:
        logger.info(f"Panel {pid} is not ready")
        set_client_ready(pid, False)
