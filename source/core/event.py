from dataclasses import dataclass
from typing import Any


@dataclass
class Event:
    """
    Informacion enviada desde los modulos al PLanificador.
    """
    type: str
    data: Any = None
    origin: str = ""

    def __init__(self, origin, type, data=None):
        self.origin = origin
        self.type = type
        self.data = data