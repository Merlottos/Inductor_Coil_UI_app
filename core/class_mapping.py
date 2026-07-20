from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ClassMapping:
    def __init__(self) -> None:
        self.mapping: dict[str, str] = {}
        self.enabled: bool = False
        self.path: Path | None = None

    def load(self, path: Path) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            self.mapping = {str(k): str(v) for k, v in data.items()}
        else:
            self.mapping = {}
        self.path = path

    def clear(self) -> None:
        self.mapping = {}
        self.path = None

    def generate_template(self, names: dict[int, str], path: Path) -> None:
        mapping = {name: name for name in names.values()}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(mapping, f, indent=4, ensure_ascii=False)
        self.mapping = mapping
        self.path = path

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled

    def apply(self, result: Any) -> None:
        if not self.enabled or not self.mapping or result is None:
            return
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            return
        names = getattr(result, "names", None)
        if not names:
            return
        try:
            import torch
        except Exception:
            return

        merged_names_list: list[str] = []
        merged_name_to_idx: dict[str, int] = {}
        orig_idx_to_merged_idx: dict[int, int] = {}
        for idx, name in names.items():
            merged_name = self.mapping.get(name, name)
            if merged_name not in merged_name_to_idx:
                merged_name_to_idx[merged_name] = len(merged_names_list)
                merged_names_list.append(merged_name)
            orig_idx_to_merged_idx[int(idx)] = merged_name_to_idx[merged_name]

        data = getattr(boxes, "data", None)
        if data is None:
            return
        new_cls_list = [
            orig_idx_to_merged_idx.get(int(c), int(c)) for c in data[:, -1].tolist()
        ]
        with torch.inference_mode():
            data[:, -1] = torch.tensor(
                new_cls_list, device=data.device, dtype=data.dtype
            )
        result.names = {i: name for i, name in enumerate(merged_names_list)}
