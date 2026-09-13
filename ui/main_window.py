from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Qt, Slot
from PySide6.QtGui import QAction, QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSlider,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from core.class_mapping import ClassMapping
from core.i18n import I18n
from core.obb_engine import OBBEngine
from core.recorder import Recorder
from core.review_player import ReviewPlayer
from core.seg_engine import SegEngine
from core.video_worker import VideoWorker
from core.view_render import ViewRenderer


# ── 界面可见性开关（在此处调整是否显示以下控件）────────────────────────────
# True = 显示该选项；False = 在界面上隐藏（控件仍在代码中可用，可随时改回）
SHOW_SEG_MODEL_SELECTOR = False   # 分割模型选择（标签 / 路径 / 按钮）
SHOW_OBB_MODEL_SELECTOR = False   # OBB 模型选择（标签 / 路径 / 按钮）
SHOW_MAPPING_LOADER = False       # 加载映射文件选项（标签 / 路径 / 按钮）


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
        self.class_mapping = ClassMapping()
        self.renderer.set_class_mapping(self.class_mapping)
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
        self.raw_view.setMinimumSize(320, 240)

        self.result_view = QLabel(self.i18n.t("result_view"))
        self.result_view.setAlignment(Qt.AlignCenter)
        self.result_view.setMinimumSize(400, 240)

        self.obb_view = QLabel(self.i18n.t("obb_view"))
        self.obb_view.setAlignment(Qt.AlignCenter)
        self.obb_view.setMinimumSize(400, 240)

        self.result_badge = QLabel("")
        self.result_badge.setAlignment(Qt.AlignCenter)
        self.result_badge.setObjectName("resultBadge")
        self._last_judge: str = ""

        self.class_stats_title = QLabel(self.i18n.t("detected_classes"))
        self.class_stats_title.setObjectName("classStatsTitle")
        self.class_stats_label = QLabel(self.i18n.t("no_detection"))
        self.class_stats_label.setObjectName("classStats")
        self.class_stats_label.setWordWrap(True)
        self.class_stats_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._last_seg_result: object = None
        self._last_obb_result: object = None

        result_split = QSplitter(Qt.Vertical)
        result_split.addWidget(self.result_view)
        result_split.addWidget(self.obb_view)
        result_split.setSizes([1, 1])

        view_split = QSplitter(Qt.Horizontal)
        view_split.addWidget(self.raw_view)
        view_split.addWidget(result_split)
        view_split.setSizes([1, 2])

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

        self.mapping_label = QLabel(self.i18n.t("class_mapping"))
        self.btn_load_mapping = QPushButton(self.i18n.t("load_class_mapping"))
        self.btn_load_mapping.clicked.connect(self.on_load_mapping)
        self.chk_mapping_enable = QCheckBox(self.i18n.t("mapping_enable"))
        self.chk_mapping_enable.toggled.connect(self.on_toggle_mapping)
        self.mapping_path = QLineEdit()
        self.mapping_path.setReadOnly(True)
        default_mapping = self.base_dir / "configs" / "class_mapping.json"
        if default_mapping.exists():
            self.mapping_path.setText(str(default_mapping))
            try:
                self.class_mapping.load(default_mapping)
            except Exception:
                pass

        self.btn_detect_classes = QPushButton(self.i18n.t("detect_class_names"))
        self.btn_detect_classes.clicked.connect(self.on_detect_classes)

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
        if SHOW_SEG_MODEL_SELECTOR:
            right_layout.addWidget(self.seg_model_label)
            right_layout.addWidget(self.seg_model_path)
            right_layout.addWidget(self.btn_seg_model)
        if SHOW_OBB_MODEL_SELECTOR:
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
        if SHOW_MAPPING_LOADER:
            right_layout.addWidget(self.mapping_label)
            right_layout.addWidget(self.mapping_path)
            right_layout.addWidget(self.btn_load_mapping)
        right_layout.addWidget(self.btn_detect_classes)
        right_layout.addWidget(self.chk_mapping_enable)
        right_layout.addSpacing(12)
        right_layout.addWidget(self.class_stats_title)
        right_layout.addWidget(self.class_stats_label)
        right_layout.addSpacing(12)
        right_layout.addWidget(self.result_badge)
        right_layout.addStretch(1)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(right_panel)
        scroll_area.setMinimumWidth(260)
        scroll_area.setMaximumWidth(360)

        root_layout.addWidget(view_split, 4)
        root_layout.addWidget(scroll_area, 1)
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
            QCheckBox { color: #dbe2ea; background: #13171c; }
            QLineEdit { background: #1e2a35; color: #e6edf5; padding: 4px 6px; border-radius: 4px; }
            QToolBar { background: #0f1216; border-bottom: 1px solid #1d232b; }
            QStatusBar { background: #0f1216; color: #9fb2c3; }
            QSlider::groove:horizontal { height: 4px; background: #1c232a; }
            QSlider::handle:horizontal { width: 12px; background: #4b6b88; margin: -4px 0; }
            QLabel#classStatsTitle { background: #13171c; border: none; color: #9fb2c3; font-size: 14px; padding: 2px; }
            QLabel#classStats { background: #13171c; border: 1px solid #20262e; border-radius: 4px; color: #7fd1ff; font-size: 17px; font-weight: 600; padding: 8px; }
            QLabel#resultBadge { background: #0f1216; border: none; font-size: 22px; padding: 10px; }
            QScrollArea { background: #0f1216; border: none; }
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
    def on_load_mapping(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.i18n.t("select_mapping_file"),
            str(self.base_dir / "configs"),
            f"{self.i18n.t('mapping_files')} (*.json);;All Files (*)",
        )
        if file_path:
            try:
                self.class_mapping.load(Path(file_path))
                self.mapping_path.setText(file_path)
                self.status.showMessage(self.i18n.t("mapping_loaded"))
            except Exception:
                self.status.showMessage(self.i18n.t("mapping_load_failed"))

    @Slot(bool)
    def on_toggle_mapping(self, checked: bool) -> None:
        self.class_mapping.set_enabled(checked)

    @Slot()
    def on_detect_classes(self) -> None:
        try:
            names = self.seg_engine.get_names()
            if not names:
                self.status.showMessage(self.i18n.t("seg_model_missing"))
                return
            out_path = self.base_dir / "configs" / "class_mapping.json"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            self.class_mapping.generate_template(names, out_path)
            self.mapping_path.setText(str(out_path))
            class_list = ", ".join(names.values())
            self.status.showMessage(
                f"{self.i18n.t('class_names_detected')}: {class_list}"
            )
        except Exception:
            self.status.showMessage(self.i18n.t("mapping_load_failed"))

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
        self.obb_view.setText(self.i18n.t("obb_view"))
        self.result_badge.setText(self._format_badge_text(self._last_judge))
        self.seg_model_label.setText(self.i18n.t("seg_model"))
        self.obb_model_label.setText(self.i18n.t("obb_model"))
        self.filter_combo.blockSignals(True)
        self.filter_combo.setItemText(0, self.i18n.t("filter_raw"))
        self.filter_combo.setItemText(1, self.i18n.t("filter_agnostic_nms"))
        self.filter_combo.setItemText(2, self.i18n.t("filter_top1_region"))
        self.filter_combo.setItemText(3, self.i18n.t("filter_top1_frame"))
        self.filter_combo.blockSignals(False)
        self.mapping_label.setText(self.i18n.t("class_mapping"))
        self.btn_load_mapping.setText(self.i18n.t("load_class_mapping"))
        self.btn_detect_classes.setText(self.i18n.t("detect_class_names"))
        self.chk_mapping_enable.setText(self.i18n.t("mapping_enable"))
        self.class_stats_title.setText(self.i18n.t("detected_classes"))
        self._update_class_stats(self._last_seg_result, self._last_obb_result)

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
        obb_view = self.renderer.render_obb(frame, obb_result)
        self.raw_view.setPixmap(raw_view)
        self.result_view.setPixmap(result_view)
        self.obb_view.setPixmap(obb_view)
        self._update_judge(seg_result, obb_result)
        self._update_class_stats(seg_result, obb_result)
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

        frame, seg_result, obb_result = self.review_player.current()
        if frame is None:
            return
        raw_view = self.renderer.render_raw(frame)
        result_view = self.renderer.render_seg(frame, seg_result)
        obb_view = self.renderer.render_obb(frame, None)
        self.raw_view.setPixmap(raw_view)
        self.result_view.setPixmap(result_view)
        self.obb_view.setPixmap(obb_view)
        self._update_judge(seg_result, obb_result)
        self._update_class_stats(seg_result, obb_result)

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

    def _update_judge(self, seg_result: object, obb_result: object) -> None:
        seg_ok, seg_norm, seg_total, seg_non = self._inspect_result(seg_result)
        obb_ok, obb_norm, obb_total, obb_non = self._inspect_result(obb_result)

        # both models detected nothing → no badge
        if not seg_ok and not obb_ok:
            self._last_judge = ""
            self.result_badge.setText("")
            self.result_badge.setStyleSheet("color: #9fb2c3;")
            return

        # one model blind → fail
        if not seg_ok or not obb_ok:
            self._last_judge = "fail"
            self.result_badge.setText(self._format_badge_text("fail"))
            self.result_badge.setStyleSheet("color: #e74c3c;")
            return

        # both models see something → evaluate
        seg_perfect = not seg_non and seg_norm == 4
        obb_perfect = not obb_non and obb_norm == 2

        if seg_perfect and obb_perfect:
            self._last_judge = "pass"
            self.result_badge.setText(self._format_badge_text("pass"))
            self.result_badge.setStyleSheet("color: #2ecc71;")
        elif not seg_non and not obb_non:
            self._last_judge = "manual_check"
            self.result_badge.setText(self._format_badge_text("manual_check"))
            self.result_badge.setStyleSheet("color: #f0c040;")
        else:
            self._last_judge = "fail"
            self.result_badge.setText(self._format_badge_text("fail"))
            self.result_badge.setStyleSheet("color: #e74c3c;")

    def _format_badge_text(self, kind: str) -> str:
        if not kind:
            return ""
        if kind == "pass":
            return f"√ {self.i18n.t('pass')}"
        if kind == "manual_check":
            return f"! {self.i18n.t('manual_check')}"
        return f"x {self.i18n.t('fail')}"

    def _inspect_result(self, result: object) -> tuple[bool, int, int, bool]:
        if result is None:
            return False, 0, 0, False
        names = getattr(result, "names", None)
        detections = getattr(result, "boxes", None) or getattr(result, "obb", None)
        if names is None or detections is None:
            return False, 0, 0, False
        cls = getattr(detections, "cls", None)
        if cls is None:
            return False, 0, 0, False
        indices = cls.tolist()
        if not indices:
            return False, 0, 0, False
        total = len(indices)
        normal_count = 0
        for idx in indices:
            name = ""
            if isinstance(names, dict):
                name = names.get(int(idx), "")
            elif isinstance(names, list) and int(idx) < len(names):
                name = names[int(idx)]
            if name.strip().lower() == "normal":
                normal_count += 1
        has_non_normal = normal_count < total
        return True, normal_count, total, has_non_normal

    def _update_class_stats(self, seg_result: object, obb_result: object) -> None:
        self._last_seg_result = seg_result
        self._last_obb_result = obb_result
        counts: dict[str, int] = {}
        for result in (seg_result, obb_result):
            for name, count in self._collect_class_counts(result).items():
                counts[name] = counts.get(name, 0) + count
        if not counts:
            self.class_stats_label.setText(self.i18n.t("no_detection"))
            return
        self.class_stats_label.setText(
            "\n".join(f"{name}: {count}" for name, count in counts.items())
        )

    def _collect_class_counts(self, result: object) -> dict[str, int]:
        if result is None:
            return {}
        names = getattr(result, "names", None)
        detections = getattr(result, "boxes", None) or getattr(result, "obb", None)
        if names is None or detections is None:
            return {}
        cls = getattr(detections, "cls", None)
        if cls is None:
            return {}
        counts: dict[str, int] = {}
        for idx in cls.tolist():
            name = self._resolve_class_name(names, int(idx))
            counts[name] = counts.get(name, 0) + 1
        return counts

    def _resolve_class_name(self, names: object, idx: int) -> str:
        name = str(idx)
        if isinstance(names, dict):
            name = str(names.get(idx, idx))
        elif isinstance(names, list) and idx < len(names):
            name = str(names[idx])
        if self.class_mapping.enabled:
            name = self.class_mapping.mapping.get(name, name)
        return self.i18n.t_class(name)
