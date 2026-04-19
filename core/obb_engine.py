from __future__ import annotations

from pathlib import Path
from typing import Any


class OBBEngine:
    def __init__(self, model_path: Path) -> None:
        self.model_path = model_path
        self.model = None

    def set_model_path(self, model_path: Path) -> None:
        self.model_path = model_path
        self.model = None

    def load(self) -> None:
        if not self.model_path.exists():
            return

    def infer(self, frame: Any) -> Any:
        return None
