from enum import Enum
from typing import Literal

from pydantic import BaseModel, field_validator, field_serializer
from common.packets import Packet


class GameState(Enum):
    IDLE = 0
    RESET = 1


class ClientState(Packet):
    type: Literal["client_state"] = "client_state"
    ready: bool  # Ready to start a game


class GameStatePacket(Packet):
    type: Literal["game_state"] = "game_state"
    state: GameState

    # Back-compat: access 'packet' like before
    @property
    def packet(self) -> GameState:
        return self.state

    @field_validator("state", mode="before")
    @classmethod
    def _parse_game_state(cls, v):
        if isinstance(v, GameState):
            return v
        if isinstance(v, str):
            try:
                return getattr(GameState, v)
            except Exception:
                return v
        return v

    @field_serializer("state")
    def _serialize_game_state(self, v: GameState, _info):
        return v.name


class StartLevelPacket(Packet):
    type: Literal["start_level"] = "start_level"
    doodad_names: dict[str, str]
