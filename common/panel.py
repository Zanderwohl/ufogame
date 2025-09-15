from typing import List, Any, Dict
from common.doodad import Doodad, DoodadKind


class Panel:
    def __init__(self, player: int):
        self.player: int = player
        self.capabilities: List[Doodad] = [
            Doodad("2312", player, DoodadKind.SingleButton),
            Doodad("2312", player, DoodadKind.MultiButton),
            Doodad("2312", player, DoodadKind.Slider),
        ]


def panel_to_json(panel: Panel) -> Dict[str, Any]:
    return {
        "player": panel.player,
        "capabilities": [
            {"id": d.id, "player": d.player, "kind": d.kind.name} for d in panel.capabilities
        ],
    }


def panel_from_json(obj: Dict[str, Any]) -> Panel:
    player_val = int(obj.get("player"))
    panel = Panel(player_val)
    caps_json = obj.get("capabilities")
    caps: List[Doodad] = []
    if isinstance(caps_json, list):
        for c in caps_json:
            try:
                kind_name = c.get("kind")
                kind = DoodadKind[kind_name] if isinstance(kind_name, str) else DoodadKind(int(kind_name))
                caps.append(Doodad(str(c.get("id")), int(c.get("player", player_val)), kind))
            except Exception:
                continue
    panel.capabilities = caps
    return panel
