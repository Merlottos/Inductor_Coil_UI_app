from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Qt, Slot
from PySide6.QtGui import QAction, QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSlider,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from core.i18n import I18n
from core.obb_engine import OBBEngine
from core.recorder import Recorder
from core.review_player import ReviewPlayer
from core.seg_engine import SegEngine
from core.video_worker import VideoWorker
from core.view_render import ViewRenderer


class MainWindow(QMainWindow):
    def __init__(
        self, base_dir: Path, source: str, seg_model: str, obb_model: str
    ) -> None:
        super().__init__()
        self.base_dir = base_dir
        self.setWindowTitle("Inductor Coil Vision UI")
        self.setWindowIcon(QIcon())

        self.i18n = I18n()

        self.seg_engine = SegEngine(base_dir / seg_model)
        self.obb_engine = OBBEngine(base_dir / obb_model)
        self.renderer = ViewRenderer()
        self.recorder = Recorder(base_dir / "data")
        self.review_player = ReviewPlayer()

        self.source = source
        self.video_worker: VideoWorker | None = None

        self._build_ui()
        self._apply_style()

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._tick_review)
        self._refresh_timer.start(30)

        if self.source:
            self._start_worker(self.source)

    def _build_ui(self) -> None:
        central = QWidget()
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(8, 8, 8, 8)

        self.raw_view = QLabel(self.i18n.t("raw_view"))
        self.raw_view.setAlignment(Qt.AlignCenter)
        self.raw_view.setMinimumSize(480, 360)

        self.result_view = QLabel(self.i18n.t("result_view"))
        self.result_view.setAlignment(Qt.AlignCenter)
        self.result_view.setMinimumSize(480, 360)

        self.result_badge = QLabel("")
        self.result_badge.setAlignment(Qt.AlignCenter)
        self.result_badge.setObjectName("resultBadge")
        self._last_judge: bool | None = None

        view_split = QSplitter(Qt.Horizontal)
        view_split.addWidget(self.raw_view)
        view_split.addWidget(self.result_view)
        view_split.setSizes([1, 1])

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(10)

        self.lang_combo = QComboBox()
        self.lang_combo.addItem("中文", "zh")
        self.lang_combo.addItem("English", "en")
        self.lang_combo.currentIndexChanged.connect(self.on_lang_changed)

        self.btn_source = QPushButton(self.i18n.t("select_source"))
        self.btn_source.clicked.connect(self.on_select_source)

        self.camera_combo = QComboBox()
        for idx in range(0, 9):
            self.camera_combo.addItem(f"{self.i18n.t('camera')} {idx}", str(idx))

        self.btn_camera = QPushButton(self.i18n.t("connect_camera"))
        self.btn_camera.clicked.connect(self.on_connect_camera)

        self.btn_record = QPushButton(self.i18n.t("start_record"))
        self.btn_record.setCheckable(True)
        self.btn_record.clicked.connect(self.on_toggle_record)

        self.btn_snapshot = QPushButton(self.i18n.t("snapshot"))
        self.btn_snapshot.clicked.connect(self.on_snapshot)

        self.btn_load_review = QPushButton(self.i18n.t("load_review"))
        self.btn_load_review.clicked.connect(self.on_load_review)

        self.seg_model_label = QLabel(self.i18n.t("seg_model"))
        self.seg_model_path = QLineEdit()
        self.seg_model_path.setReadOnly(True)
        self.seg_model_path.setText(str(self.seg_engine.model_path.resolve()))
        self.btn_seg_model = QPushButton(self.i18n.t("select_seg_model"))
        self.btn_seg_model.clicked.connect(self.on_select_seg_model)

        self.obb_model_label = QLabel(self.i18n.t("obb_model"))
        self.obb_model_path = QLineEdit()
        self.obb_model_path.setReadOnly(True)
        self.obb_model_path.setText(str(self.obb_engine.model_path.resolve()))
        self.btn_obb_model = QPushButton(self.i18n.t("select_obb_model"))
        self.btn_obb_model.clicked.connect(self.on_select_obb_model)

        self.btn_play = QPushButton(self.i18n.t("play"))
        self.btn_play.setCheckable(True)
        self.btn_play.clicked.connect(self.on_toggle_play)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem(self.i18n.t("filter_raw"), "raw")
        self.filter_combo.addItem(self.i18n.t("filter_agnostic_nms"), "agnostic_nms")
        self.filter_combo.addItem(self.i18n.t("filter_top1_region"), "top1_region")
        self.filter_combo.addItem(self.i18n.t("filter_top1_frame"), "top1_frame")
        self.filter_combo.setCurrentIndex(0)
        self.filter_combo.currentIndexChanged.connect(self.on_filter_changed)

        self.review_slider = QSlider(Qt.Horizontal)
        self.review_slider.setMinimum(0)
        self.review_slider.setMaximum(0)
        self.review_slider.valueChanged.connect(self.on_review_seek)

        right_layout.addWidget(QLabel(self.i18n.t("language")))
        right_layout.addWidget(self.lang_combo)
        right_layout.addSpacing(6)
        right_layout.addWidget(self.btn_source)
        right_layout.addWidget(QLabel(self.i18n.t("camera_index")))
        right_layout.addWidget(self.camera_combo)
        right_layout.addWidget(self.btn_camera)
        right_layout.addWidget(self.btn_record)
        right_layout.addWidget(self.btn_snapshot)
        right_layout.addSpacing(12)
        right_layout.addWidget(self.seg_model_label)
        right_layout.addWidget(self.seg_model_path)
        right_layout.addWidget(self.btn_seg_model)
        right_layout.addWidget(self.obb_model_label)
        right_layout.addWidget(self.obb_model_path)
        right_layout.addWidget(self.btn_obb_model)
        right_layout.addSpacing(12)
        right_layout.addWidget(QLabel(self.i18n.t("review")))
        right_layout.addWidget(self.btn_load_review)
        right_layout.addWidget(self.btn_play)
        right_layout.addWidget(self.review_slider)
        right_layout.addSpacing(12)
        right_layout.addWidget(QLabel(self.i18n.t("filter_mode")))
        right_layout.addWidget(self.filter_combo)
        right_layout.addSpacing(12)
        right_layout.addWidget(self.result_badge)
        right_layout.addStretch(1)

        root_layout.addWidget(view_split, 4)
        root_layout.addWidget(right_panel, 1)
        self.setCentralWidget(central)

        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        action_live = QAction(self.i18n.t("live_mode"), self)
        action_review = QAction(self.i18n.t("review_mode"), self)
        action_live.triggered.connect(self.on_live_mode)
        action_review.triggered.connect(self.on_review_mode)
        toolbar.addAction(action_live)
        toolbar.addAction(action_review)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage(self.i18n.t("ready"))

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow { background: #0f1216; }
            QLabel { color: #dbe2ea; background: #13171c; border: 1px solid #20262e; }
            QPushButton { background: #1e2a35; color: #e6edf5; padding: 6px 10px; border-radius: 4px; }
            QPushButton:checked { background: #2b4458; }
            QComboBox { background: #1e2a35; color: #e6edf5; padding: 4px 8px; border-radius: 4px; }
            QToolBar { background: #0f1216; border-bottom: 1px solid #1d232b; }
            QStatusBar { background: #0f1216; color: #9fb2c3; }
            QSlider::groove:horizontal { height: 4px; background: #1c232a; }
            QSlider::handle:horizontal { width: 12px; background: #4b6b88; margin: -4px 0; }
            QLabel#resultBadge { background: #0f1216; border: none; font-size: 22px; padding: 10px; }
            """
        )

    @Slot()
    def on_select_source(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, self.i18n.t("select_video"))
        if file_path:
            self._start_worker(file_path)

    @Slot()
    def on_connect_camera(self) -> None:
        index = self.camera_combo.currentData()
        if index is not None:
            self._start_worker(index)

    @Slot()
    def on_toggle_record(self) -> None:
        if self.btn_record.isChecked():
            self.recorder.start()
            self.btn_record.setText(self.i18n.t("stop_record"))
        else:
            self.recorder.stop()
            self.btn_record.setText(self.i18n.t("start_record"))

    @Slot()
    def on_snapshot(self) -> None:
        if self.video_worker is None or self.video_worker.last_frame is None:
            return
        self.recorder.snapshot(
            self.video_worker.last_frame,
            self.video_worker.last_seg,
            self.video_worker.last_obb,
        )

    @Slot()
    def on_load_review(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, self.i18n.t("select_review_folder")
        )
        if folder:
            self.review_player.load(Path(folder))
            self.review_slider.setMaximum(max(0, self.review_player.count - 1))
            self.review_slider.setValue(0)
            self.status.showMessage(self.i18n.t("review_loaded"))

    @Slot()
    def on_select_seg_model(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.i18n.t("select_seg_model"),
            str(self.base_dir / "models"),
            f"{self.i18n.t('model_files')} (*.pt *.onnx *.engine *.tflite *.pth);;All Files (*)",
        )
        if file_path:
            try:
                self.seg_model_path.setText(file_path)
                self.seg_engine.set_model_path(Path(file_path))
                if self.video_worker is not None:
                    self.video_worker.reset_seg_engine(self.seg_engine)
                self.status.showMessage(self.i18n.t("model_loaded"))
            except Exception:
                self.status.showMessage(self.i18n.t("model_load_failed"))

    @Slot()
    def on_select_obb_model(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.i18n.t("select_obb_model"),
            str(self.base_dir / "models"),
            f"{self.i18n.t('model_files')} (*.pt *.onnx *.engine *.tflite *.pth);;All Files (*)",
        )
        if file_path:
            try:
                self.obb_model_path.setText(file_path)
                self.obb_engine.set_model_path(Path(file_path))
                if self.video_worker is not None:
                    self.video_worker.reset_obb_engine(self.obb_engine)
                self.status.showMessage(self.i18n.t("model_loaded"))
            except Exception:
                self.status.showMessage(self.i18n.t("model_load_failed"))

    @Slot()
    def on_toggle_play(self) -> None:
        if self.btn_play.isChecked():
            self.btn_play.setText(self.i18n.t("pause"))
        else:
            self.btn_play.setText(self.i18n.t("play"))

    @Slot(int)
    def on_review_seek(self, value: int) -> None:
        self.review_player.seek(value)

    @Slot()
    def on_live_mode(self) -> None:
        self.review_player.enable(False)
        self.status.showMessage(self.i18n.t("live_mode"))

    @Slot()
    def on_review_mode(self) -> None:
        self.review_player.enable(True)
        self.status.showMessage(self.i18n.t("review_mode"))

    @Slot()
    def on_filter_changed(self) -> None:
        mode = self.filter_combo.currentData()
        if mode:
            self.renderer.set_filter_mode(mode)

    @Slot()
    def on_lang_changed(self) -> None:
        self.i18n.set_lang(self.lang_combo.currentData())
        self.btn_source.setText(self.i18n.t("select_source"))
        self.btn_seg_model.setText(self.i18n.t("select_seg_model"))
        self.btn_obb_model.setText(self.i18n.t("select_obb_model"))
        self.btn_record.setText(
            self.i18n.t("start_record")
            if not self.btn_record.isChecked()
            else self.i18n.t("stop_record")
        )
        self.btn_snapshot.setText(self.i18n.t("snapshot"))
        self.btn_load_review.setText(self.i18n.t("load_review"))
        self.btn_play.setText(
            self.i18n.t("play")
            if not self.btn_play.isChecked()
            else self.i18n.t("pause")
        )
        self.btn_camera.setText(self.i18n.t("connect_camera"))
        self.camera_combo.clear()
        for idx in range(0, 9):
            self.camera_combo.addItem(f"{self.i18n.t('camera')} {idx}", str(idx))
        self.raw_view.setText(self.i18n.t("raw_view"))
        self.result_view.setText(self.i18n.t("result_view"))
        self.result_badge.setText(self._format_badge_text(self._last_judge))
        self.seg_model_label.setText(self.i18n.t("seg_model"))
        self.obb_model_label.setText(self.i18n.t("obb_model"))
        self.filter_combo.blockSignals(True)
        self.filter_combo.setItemText(0, self.i18n.t("filter_raw"))
        self.filter_combo.setItemText(1, self.i18n.t("filter_agnostic_nms"))
        self.filter_combo.setItemText(2, self.i18n.t("filter_top1_region"))
        self.filter_combo.setItemText(3, self.i18n.t("filter_top1_frame"))
        self.filter_combo.blockSignals(False)

    @Slot(object)
    def on_frame_ready(self, payload: dict) -> None:
        if self.review_player.enabled:
            return
        if self.video_worker is None:
            return
        frame = payload.get("frame")
        seg_result = payload.get("seg_result")
        obb_result = payload.get("obb_result")
        self.video_worker.cache_last(frame, seg_result, obb_result)
        raw_view = self.renderer.render_raw(frame)
        result_view = self.renderer.render_seg(frame, seg_result)
        self.raw_view.setPixmap(raw_view)
        self.result_view.setPixmap(result_view)
        self._update_judge(seg_result)
        self.recorder.write(frame, seg_result, obb_result)

    @Slot(str)
    def on_status_ready(self, message: str) -> None:
        self.status.showMessage(self.i18n.t(message))

    def _tick_review(self) -> None:
        if not self.review_player.enabled:
            return
        if self.btn_play.isChecked():
            self.review_player.step()
            self.review_slider.blockSignals(True)
            self.review_slider.setValue(self.review_player.index)
            self.review_slider.blockSignals(False)

        frame, seg_result = self.review_player.current()
        if frame is None:
            return
        raw_view = self.renderer.render_raw(frame)
        result_view = self.renderer.render_seg(frame, seg_result)
        self.raw_view.setPixmap(raw_view)
        self.result_view.setPixmap(result_view)
        self._update_judge(seg_result)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.video_worker is not None:
            self.video_worker.stop()
        self.recorder.stop()
        self.review_player.reset()
        event.accept()

    def _start_worker(self, source: str) -> None:
        if self.video_worker is not None:
            self.video_worker.stop()
        self.video_worker = VideoWorker(
            source=source,
            seg_engine=self.seg_engine,
            obb_engine=self.obb_engine,
        )
        self.video_worker.frame_ready.connect(self.on_frame_ready)
        self.video_worker.status_ready.connect(self.on_status_ready)
        self.video_worker.start()

    def _update_judge(self, seg_result: object) -> None:
        is_pass = self._is_all_normal(seg_result)
        self._last_judge = is_pass
        if is_pass is None:
            self.result_badge.setText("")
            self.result_badge.setStyleSheet("color: #9fb2c3;")
            return
        if is_pass:
            self.result_badge.setText(self._format_badge_text(True))
            self.result_badge.setStyleSheet("color: #2ecc71;")
        else:
            self.result_badge.setText(self._format_badge_text(False))
            self.result_badge.setStyleSheet("color: #e74c3c;")

    def _format_badge_text(self, is_pass: bool | None = None) -> str:
        if is_pass is None:
            return ""
        symbol = "√" if is_pass else "x"
        text = self.i18n.t("pass") if is_pass else self.i18n.t("fail")
        return f"{symbol} {text}"

    def _is_all_normal(self, seg_result: object) -> bool | None:
        if seg_result is None:
            return None
        names = getattr(seg_result, "names", None)
        boxes = getattr(seg_result, "boxes", None)
        if names is None or boxes is None:
            return None
        cls = getattr(boxes, "cls", None)
        if cls is None:
            return None
        indices = cls.tolist()
        if not indices:
            return None
        for idx in indices:
            name = ""
            if isinstance(names, dict):
                name = names.get(int(idx), "")
            elif isinstance(names, list) and int(idx) < len(names):
                name = names[int(idx)]
            if name.strip().lower() != "normal":
                return False
        return True
