from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="UI app for YOLO inference")
    parser.add_argument(
        "--source",
        default="",
        help="video/image source, camera index or file path",
    )
    parser.add_argument(
        "--seg-model",
        default="models/seg.pt",
        help="seg model path under UI_app/models",
    )
    parser.add_argument(
        "--obb-model",
        default="models/obb.pt",
        help="obb model path under UI_app/models (placeholder)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app = QApplication(sys.argv)
    base_dir = Path(__file__).resolve().parent
    window = MainWindow(
        base_dir=base_dir,
        source=args.source,
        seg_model=args.seg_model,
        obb_model=args.obb_model,
    )
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
