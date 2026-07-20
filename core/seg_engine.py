from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from ultralytics import YOLO
except Exception:  # pragma: no cover - optional dependency
    YOLO = None


class SegEngine:
    def __init__(self, model_path: Path) -> None:
        self.model_path = model_path
        self.model = None

    def set_model_path(self, model_path: Path) -> None:
        self.model_path = model_path
        self.model = None

    def load(self) -> None:
        if YOLO is None:
            raise RuntimeError("ultralytics not installed")
        if not self.model_path.exists():
            raise FileNotFoundError(str(self.model_path))
        self.model = YOLO(str(self.model_path))

    def infer(self, frame: Any) -> Any:
        if self.model is None:
            self.load()
        results = self.model.predict(frame, verbose=False)
        return results[0] if results else None

    def get_names(self) -> dict[int, str]:
        if self.model is None:
            self.load()
        names = getattr(self.model, "names", None)
        if isinstance(names, dict):
            return {int(k): str(v) for k, v in names.items()}
        if isinstance(names, list):
            return {i: str(n) for i, n in enumerate(names)}
        return {}
