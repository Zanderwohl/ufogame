import logging

import client.network
from client.network import attempt_connection, receive_packets, send_packet

from common.gamestate import GameStatePacket, GameState, ClientState, StartLevelPacket
from common.panel import Panel
from common.packets import TextPacket
from common.runner import run

_state = GameState.IDLE
_panel = None

def main(player: int | None):
    global _panel
    if player is None:
        print("No player specified")
        return 1
    _panel = Panel(player)
    client.network.PANEL = _panel
    return run(
        logger_name=f"client-{player}",
        advertise_instance=f"ufogame-{player}",
        advertise_port=8200 + player,
        advertise_properties={"player": str(player)},
        run_frame=run_frame,
    )

def run_frame(logger: logging.Logger) -> bool:
    global _state, _panel
    if client.network.SOCKET is None:
        if not attempt_connection(logger):
            return True

    packets = receive_packets(logger)
    for p in packets:
        if isinstance(p, TextPacket):
            logger.info(f"recv: {p.text}")
        if isinstance(p, GameStatePacket):
            _state = p.state
            countdown_info = f" {p.countdown}" if getattr(p, "countdown", 0) else ""
            logger.info(f"recv: {p.state}{countdown_info}")
            if p.state == GameState.RESET:
                pass # RESET self
            elif p.state == GameState.IDLE:
                send_packet(ClientState(ready=True))  # TODO: Wait for user to turn key.
            elif p.state == GameState.LEVEL_COUNTDOWN:
                # Potentially update UI with p.countdown
                pass
            elif p.state == GameState.IN_LEVEL:
                # Potentially update UI with p.level
                pass
        if isinstance(p, StartLevelPacket):
            logger.info(f"Starting level {p.level}, doodads: {p.doodad_names}")
    return True
