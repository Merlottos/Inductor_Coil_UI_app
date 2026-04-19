from __future__ import annotations

from typing import Any

import cv2
from PySide6.QtGui import QImage, QPixmap


class ViewRenderer:
    def __init__(self) -> None:
        self.filter_mode = "agnostic_nms"
        self.iou_threshold = 0.5

    def set_filter_mode(self, mode: str) -> None:
        self.filter_mode = mode

    def render_raw(self, frame: Any) -> QPixmap:
        return self._to_pixmap(frame)

    def render_seg(self, frame: Any, result: Any) -> QPixmap:
        filtered = self._filter_result(result)
        image = self._draw_seg(frame, filtered)
        return self._to_pixmap(image)

    def render_obb(self, frame: Any, result: Any) -> QPixmap:
        if result is None:
            return self._to_pixmap(frame)
        image = self._draw_obb(frame, result)
        return self._to_pixmap(image)

    def _draw_seg(self, frame: Any, result: Any) -> Any:
        if result is None:
            return frame
        if hasattr(result, "plot"):
            annotated = result.plot()
            return annotated
        if isinstance(result, dict):
            return self._draw_boxes(frame, result.get("boxes", []))
        return frame

    def _draw_obb(self, frame: Any, result: Any) -> Any:
        return frame

    def _filter_result(self, result: Any) -> Any:
        if result is None:
            return None
        if self.filter_mode == "raw":
            return result
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            return result
        xyxy = getattr(boxes, "xyxy", None)
        conf = getattr(boxes, "conf", None)
        if xyxy is None or conf is None:
            return result

        xyxy_list = self._to_list(xyxy)
        conf_list = self._to_list(conf)
        if not xyxy_list or not conf_list:
            return result

        if self.filter_mode == "top1_frame":
            best = max(range(len(conf_list)), key=lambda i: conf_list[i])
            return self._slice_result(result, [best])

        if self.filter_mode == "top1_region":
            keep = self._group_top1(xyxy_list, conf_list, self.iou_threshold)
            return self._slice_result(result, keep)

        if self.filter_mode == "agnostic_nms":
            keep = self._nms(xyxy_list, conf_list, self.iou_threshold)
            return self._slice_result(result, keep)

        return result

    def _slice_result(self, result: Any, indices: list[int]) -> Any:
        if hasattr(result, "__getitem__"):
            try:
                return result[indices]
            except Exception:
                return result
        return result

    def _to_list(self, data: Any) -> list:
        if hasattr(data, "tolist"):
            try:
                return data.tolist()
            except Exception:
                return list(data)
        return list(data)

    def _nms(self, boxes: list, scores: list, iou_thres: float) -> list[int]:
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        keep: list[int] = []
        while order:
            i = order.pop(0)
            keep.append(i)
            order = [j for j in order if self._iou(boxes[i], boxes[j]) <= iou_thres]
        return keep

    def _group_top1(self, boxes: list, scores: list, iou_thres: float) -> list[int]:
        remaining = set(range(len(boxes)))
        keep: list[int] = []
        while remaining:
            seed = next(iter(remaining))
            group = {seed}
            stack = [seed]
            while stack:
                idx = stack.pop()
                overlaps = [
                    j
                    for j in remaining
                    if j not in group and self._iou(boxes[idx], boxes[j]) > iou_thres
                ]
                for j in overlaps:
                    group.add(j)
                    stack.append(j)
            best = max(group, key=lambda i: scores[i])
            keep.append(best)
            remaining -= group
        return keep

    def _iou(self, a: list, b: list) -> float:
        ax1, ay1, ax2, ay2 = a[:4]
        bx1, by1, bx2, by2 = b[:4]
        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)
        if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
            return 0.0
        inter = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
        area_a = max(0.0, (ax2 - ax1)) * max(0.0, (ay2 - ay1))
        area_b = max(0.0, (bx2 - bx1)) * max(0.0, (by2 - by1))
        union = area_a + area_b - inter
        return 0.0 if union <= 0 else inter / union

    def _draw_boxes(self, frame: Any, boxes: list) -> Any:
        image = frame.copy()
        for box in boxes:
            if len(box) < 4:
                continue
            x1, y1, x2, y2 = [int(v) for v in box[:4]]
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 196, 255), 2)
        return image

    def _to_pixmap(self, frame: Any) -> QPixmap:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(image)
