from __future__ import annotations

from typing import List, Tuple, Any, Literal, Dict, Type, Optional
import json
from pydantic import BaseModel


# Registry of all Packet subclasses by their discriminating 'type' field
_PACKET_REGISTRY: Dict[str, Type["Packet"]] = {}
_REGISTRY_BUILT: bool = False


class Packet(BaseModel):  # Base class for future expansion
    # Auto-register subclasses that define a Literal 'type' field with a default
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        try:
            field = getattr(cls, "model_fields", {}).get("type")
            type_name: Optional[str] = getattr(field, "default", None)
            if isinstance(type_name, str) and type_name:
                _PACKET_REGISTRY[type_name] = cls  # type: ignore[assignment]
        except Exception:
            # Best-effort registration only
            pass


def _register_from_class(cls: Type["Packet"]) -> None:
    try:
        field = getattr(cls, "model_fields", {}).get("type")
        type_name: Optional[str] = getattr(field, "default", None)
        if isinstance(type_name, str) and type_name:
            _PACKET_REGISTRY.setdefault(type_name, cls)  # type: ignore[assignment]
    except Exception:
        pass


def _walk_subclasses(base: Type["Packet"]) -> List[Type["Packet"]]:
    result: List[Type["Packet"]] = []
    for sub in base.__subclasses__():
        result.append(sub)
        result.extend(_walk_subclasses(sub))
    return result


def _ensure_registry_populated() -> None:
    global _REGISTRY_BUILT
    if _REGISTRY_BUILT:
        return
    # Build registry from all imported subclasses
    for cls in [Packet, * _walk_subclasses(Packet)]:
        if cls is Packet:
            continue
        _register_from_class(cls)
    _REGISTRY_BUILT = True


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
    _ensure_registry_populated()
    try:
        text = buffer.decode("utf-8", errors="replace")
    except Exception:
        text = buffer.decode("utf-8", errors="ignore")
    lines = text.split("\n")
    if not lines:
        return [], buffer
    complete_lines = lines[:-1]
    remainder = lines[-1].encode("utf-8")

    packets: List[Packet] = []
    for line in complete_lines:
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict) and "type" in obj:
                t = obj.get("type")
                model_cls = _PACKET_REGISTRY.get(str(t))
                if model_cls is not None:
                    try:
                        packets.append(model_cls.model_validate(obj))
                        continue
                    except Exception:
                        # If validation fails, fall back to text below
                        pass
        except Exception:
            # Not JSON; fall through to text
            pass
        packets.append(TextPacket(text=line))
    return packets, remainder


