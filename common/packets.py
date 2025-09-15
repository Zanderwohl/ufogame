from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


class Packet:  # Base class for future expansion
    pass


@dataclass
class TextPacket(Packet):
    text: str


def encode_packet(packet: Packet) -> bytes:
    if isinstance(packet, TextPacket):
        return (packet.text + "\n").encode("utf-8")
    raise ValueError(f"Unknown packet type: {type(packet)}")


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
    packets: List[Packet] = [TextPacket(line) for line in complete_lines if line]
    return packets, remainder


