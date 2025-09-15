from enum import Enum
from typing import Literal

from common.packets import Packet


class GameState(str, Enum):
    IDLE = "IDLE"
    RESET = "RESET"
    LEVEL_COUNTDOWN = "LEVEL_COUNTDOWN"
    IN_LEVEL = "IN_LEVEL"

class ClientState(Packet):
    type: Literal["client_state"] = "client_state"
    ready: bool  # Ready to start a game


class GameStatePacket(Packet):
    type: Literal["game_state"] = "game_state"
    state: GameState
    countdown: int = 0


class StartLevelPacket(Packet):
    type: Literal["start_level"] = "start_level"
    doodad_names: dict[str, str]
    level: int | None = None
