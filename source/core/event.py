from dataclasses import dataclass
from typing import Any


@dataclass
class Event:
    type: str
    data: Any = None
    source: str = ""