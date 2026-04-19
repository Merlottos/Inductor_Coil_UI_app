from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2


class Recorder:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.session_dir: Path | None = None
        self.images_dir: Path | None = None
        self.results_path: Path | None = None
        self._index = 0
        self._enabled = False

    def start(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.base_dir / f"session_{stamp}"
        self.images_dir = self.session_dir / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.results_path = self.session_dir / "results.jsonl"
        self._index = 0
        self._enabled = True

    def stop(self) -> None:
        self._enabled = False

    def snapshot(self, frame: Any, seg_result: Any, obb_result: Any) -> None:
        if self.session_dir is None:
            self.start()
        self.write(frame, seg_result, obb_result)

    def write(self, frame: Any, seg_result: Any, obb_result: Any) -> None:
        if not self._enabled or self.images_dir is None or self.results_path is None:
            return
        image_name = f"frame_{self._index:06d}.jpg"
        image_path = self.images_dir / image_name
        cv2.imwrite(str(image_path), frame)
        record = {
            "image": image_name,
            "seg": self._serialize_result(seg_result),
            "obb": self._serialize_result(obb_result),
        }
        with self.results_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._index += 1

    def _serialize_result(self, result: Any) -> dict[str, Any] | None:
        if result is None:
            return None
        data = {
            "boxes": [],
            "masks": [],
        }
        try:
            if result.boxes is not None:
                data["boxes"] = result.boxes.xyxy.cpu().tolist()
        except Exception:
            pass
        try:
            if result.masks is not None:
                data["masks"] = [item.tolist() for item in result.masks.xy]
        except Exception:
            pass
        return data
