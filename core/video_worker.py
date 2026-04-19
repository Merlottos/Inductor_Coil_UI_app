from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
from PySide6.QtCore import QThread, Signal

from core.obb_engine import OBBEngine
from core.seg_engine import SegEngine


class VideoWorker(QThread):
    frame_ready = Signal(object)
    status_ready = Signal(str)

    def __init__(
        self, source: str, seg_engine: SegEngine, obb_engine: OBBEngine
    ) -> None:
        super().__init__()
        self.source = source
        self.seg_engine = seg_engine
        self.obb_engine = obb_engine
        self._running = True
        self._capture: cv2.VideoCapture | None = None
        self.last_frame = None
        self.last_seg = None
        self.last_obb = None

    def set_source(self, source: str) -> None:
        self.source = source
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def stop(self) -> None:
        self._running = False
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def reset_seg_engine(self, seg_engine: SegEngine) -> None:
        self.seg_engine = seg_engine

    def reset_obb_engine(self, obb_engine: OBBEngine) -> None:
        self.obb_engine = obb_engine

    def _open(self) -> cv2.VideoCapture | None:
        if self.source.isdigit():
            cap = cv2.VideoCapture(int(self.source))
        else:
            cap = cv2.VideoCapture(str(Path(self.source)))
        if not cap.isOpened():
            return None
        return cap

    def run(self) -> None:
        self._capture = self._open()
        if self._capture is None:
            self.status_ready.emit("video_open_failed")
            return
        while self._running:
            ok, frame = self._capture.read()
            if not ok:
                self._capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            seg_result = self._safe_infer(self.seg_engine, frame)
            obb_result = self._safe_infer(self.obb_engine, frame)
            payload = {
                "frame": frame,
                "seg_result": seg_result,
                "obb_result": obb_result,
            }
            self.frame_ready.emit(payload)

    def _safe_infer(self, engine: Any, frame: Any) -> Any:
        try:
            return engine.infer(frame)
        except Exception:
            return None

    def cache_last(self, frame: Any, seg_result: Any, obb_result: Any) -> None:
        self.last_frame = frame
        self.last_seg = seg_result
        self.last_obb = obb_result
