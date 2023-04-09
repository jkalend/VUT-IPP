from dataclasses import dataclass
from typing import Any

@dataclass
class Variable:
    """Class for storing variable"""

    value: Any = None
    name: str = ""
    type: str = ""
