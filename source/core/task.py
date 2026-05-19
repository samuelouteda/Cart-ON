from dataclasses import dataclass
from typing import Any


@dataclass
class Task:
    """
    Ordenes enviadas desde el Planificador hacia los modulos.
    """
    type: str
    data: Any = None

    def __init__(self, type, data = None):
        self.type = type
        self.data = data