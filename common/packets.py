from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Any
import json


class Packet:  # Base class for future expansion
    pass


@dataclass
class TextPacket(Packet):
    text: str


def encode_packet(packet: Packet) -> bytes:
    # Local import to avoid circular import at module load time
    try:
        from common.gamestate import GameStatePacket  # type: ignore
    except Exception:
        GameStatePacket = None  # type: ignore

    if isinstance(packet, TextPacket):
        obj: dict[str, Any] = {"type": "text", "text": packet.text}
        return (json.dumps(obj) + "\n").encode("utf-8")
    if GameStatePacket is not None and isinstance(packet, GameStatePacket):
        state = getattr(packet, "packet", None)
        state_name = getattr(state, "name", str(state))
        obj = {"type": "game_state", "state": state_name}
        return (json.dumps(obj) + "\n").encode("utf-8")
    # Fallback to simple str with newline
    obj = {"type": "unknown", "repr": repr(packet)}
    return (json.dumps(obj) + "\n").encode("utf-8")


def decode_lines(buffer: bytes) -> Tuple[List[Packet], bytes]:
    try:
        text = buffer.decode("utf-8", errors="replace")
    except Exception:
        text = buffer.decode("utf-8", errors="ignore")
    lines = text.split("\n")
    if not lines:
        return [], buffer
    complete_lines = lines[:-1]
    remainder = lines[-1].encode("utf-8")

    try:
        from common.gamestate import GameStatePacket, GameState  # type: ignore
    except Exception:
        GameStatePacket = None  # type: ignore
        GameState = None  # type: ignore

    packets: List[Packet] = []
    for line in complete_lines:
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict) and "type" in obj:
                t = obj.get("type")
                if t == "text" and "text" in obj:
                    packets.append(TextPacket(str(obj.get("text"))))
                    continue
                if GameStatePacket is not None and t == "game_state" and "state" in obj:
                    state_name = str(obj.get("state"))
                    try:
                        state = getattr(GameState, state_name)
                    except Exception:
                        state = None
                    if state is not None:
                        packets.append(GameStatePacket(state))
                        continue
        except Exception:
            # Not JSON; fall through to text
            pass
        packets.append(TextPacket(line))
    return packets, remainder


