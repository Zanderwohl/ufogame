from dataclasses import dataclass
from enum import Enum

from common.packets import Packet


class GameState(Enum):
    IDLE = 0
    RESET = 1


@dataclass
class GameStatePacket(Packet):
    packet: GameState
