from enum import Enum

class DoodadKind(Enum):
    SingleButton = 0
    MultiButton = 1
    Slider = 2

class Doodad:
    def __init__(self, ident: str, player: int, kind: DoodadKind):
        self.id = ident
        self.player = player
        self.kind = kind
        self.name = ""

    def __str__(self):
        return "Doodad({}, {})".format(self.id, self.kind)

    def __repr__(self):
        match self.kind:
            case DoodadKind.SingleButton:
                return f"SingleButton({self.id})"
            case DoodadKind.MultiButton:
                return f"MultiButton({self.id})"
            case DoodadKind.Slider:
                return f"Slider({self.id})"
        return f"Doodad({self.id})"
