from typing import List, Any


class Panel:
    def __init__(self, player: int):
        self.player: int = player
        self.capabilities: List[dict[str, Any]] = [
            {"foo": "bar", "baz": "qux"},
            {"a": "b", "c": "d"},
        ]
