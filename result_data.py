from dataclasses import dataclass
from typing import Any

@dataclass
class Result:
    error: bool
    message: str
    result: Any