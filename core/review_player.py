from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cv2


class ReviewPlayer:
    def __init__(self) -> None:
        self.enabled = False
        self.index = 0
        self.items: list[dict[str, Any]] = []
        self.base_dir: Path | None = None

    @property
    def count(self) -> int:
        return len(self.items)

    def enable(self, flag: bool) -> None:
        self.enabled = flag

    def load(self, session_dir: Path) -> None:
        self.base_dir = session_dir
        results_path = session_dir / "results.jsonl"
        self.items = []
        if results_path.exists():
            with results_path.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        self.items.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        self.index = 0

    def seek(self, index: int) -> None:
        if not self.items:
            return
        self.index = max(0, min(index, len(self.items) - 1))

    def step(self) -> None:
        if not self.items:
            return
        self.index += 1
        if self.index >= len(self.items):
            self.index = 0

    def current(self) -> tuple[Any | None, Any | None]:
        if not self.items or self.base_dir is None:
            return None, None
        item = self.items[self.index]
        image_path = self.base_dir / "images" / item["image"]
        frame = cv2.imread(str(image_path))
        return frame, item.get("seg")

    def reset(self) -> None:
        self.items = []
        self.index = 0
        self.base_dir = None
