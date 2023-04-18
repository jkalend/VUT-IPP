# IPP 2023 project 2
# Author: Jan Kalenda
# Login: xkalen07

from dataclasses import dataclass
from typing import Any

@dataclass
class Variable:
    """Class for storing variable"""

    value: Any = None
    name: str = ""
    type: str = ""
