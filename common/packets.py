from __future__ import annotations

from typing import List, Tuple, Any, Literal
import json
from pydantic import BaseModel


class Packet(BaseModel):  # Base class for future expansion
    pass


class TextPacket(Packet):
    type: Literal["text"] = "text"
    text: str


def encode_packet(packet: Packet) -> bytes:
    try:
        if isinstance(packet, Packet):
            return (packet.model_dump_json() + "\n").encode("utf-8")
    except Exception:
        pass
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
        from common.gamestate import GameStatePacket, ClientState  # type: ignore
    except Exception:
        GameStatePacket = None  # type: ignore
        ClientState = None  # type: ignore

    packets: List[Packet] = []
    for line in complete_lines:
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict) and "type" in obj:
                t = obj.get("type")
                if t == "text" and "text" in obj:
                    packets.append(TextPacket.model_validate(obj))
                    continue
                if GameStatePacket is not None and t == "game_state" and "state" in obj:
                    packets.append(GameStatePacket.model_validate(obj))
                    continue
                if ClientState is not None and t == "client_state" and "ready" in obj:
                    packets.append(ClientState.model_validate(obj))
                    continue
        except Exception:
            # Not JSON; fall through to text
            pass
        packets.append(TextPacket(text=line))
    return packets, remainder


