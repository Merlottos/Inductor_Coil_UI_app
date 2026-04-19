from __future__ import annotations

from dataclasses import dataclass


@dataclass
class I18n:
    lang: str = "zh"

    def set_lang(self, lang: str) -> None:
        if lang in ("zh", "en"):
            self.lang = lang

    def t(self, key: str) -> str:
        return _TEXT.get(self.lang, {}).get(key, key)


_TEXT = {
    "zh": {
        "seg_view": "分割视图",
        "obb_view_placeholder": "OBB 视图（未加载）",
        "select_source": "选择视频/图片源",
        "start_record": "开始记录",
        "stop_record": "停止记录",
        "snapshot": "保存截图",
        "load_review": "加载回看",
        "play": "播放",
        "pause": "暂停",
        "review": "回看",
        "language": "语言",
        "select_video": "选择视频文件",
        "select_review_folder": "选择回看目录",
        "review_loaded": "回看加载完成",
        "live_mode": "实时模式",
        "review_mode": "回看模式",
        "ready": "就绪",
        "seg_model_missing": "分割模型未找到",
        "obb_model_missing": "OBB 模型未找到",
        "video_open_failed": "视频源打开失败",
        "camera": "摄像头",
        "connect_camera": "连接摄像头",
        "camera_index": "摄像头索引",
        "raw_view": "原图",
        "result_view": "结果",
        "pass": "合格",
        "fail": "不合格",
        "select_seg_model": "选择分割模型",
        "select_obb_model": "选择OBB模型",
        "model_files": "模型文件",
        "seg_model": "分割模型",
        "obb_model": "OBB模型",
        "model_loaded": "模型已加载",
        "model_load_failed": "模型加载失败",
        "filter_mode": "筛选方式",
        "filter_raw": "原始输出",
        "filter_agnostic_nms": "跨类别NMS",
        "filter_top1_region": "区域内最高",
        "filter_top1_frame": "全帧最高",
    },
    "en": {
        "seg_view": "Seg View",
        "obb_view_placeholder": "OBB View (Not Loaded)",
        "select_source": "Select Video/Image",
        "start_record": "Start Record",
        "stop_record": "Stop Record",
        "snapshot": "Snapshot",
        "load_review": "Load Review",
        "play": "Play",
        "pause": "Pause",
        "review": "Review",
        "language": "Language",
        "select_video": "Select Video File",
        "select_review_folder": "Select Review Folder",
        "review_loaded": "Review Loaded",
        "live_mode": "Live Mode",
        "review_mode": "Review Mode",
        "ready": "Ready",
        "seg_model_missing": "Seg model not found",
        "obb_model_missing": "OBB model not found",
        "video_open_failed": "Failed to open source",
        "camera": "Camera",
        "connect_camera": "Connect Camera",
        "camera_index": "Camera Index",
        "raw_view": "Raw",
        "result_view": "Result",
        "pass": "Pass",
        "fail": "Fail",
        "select_seg_model": "Select Seg Model",
        "select_obb_model": "Select OBB Model",
        "model_files": "Model Files",
        "seg_model": "Seg Model",
        "obb_model": "OBB Model",
        "model_loaded": "Model loaded",
        "model_load_failed": "Model load failed",
        "filter_mode": "Filter Mode",
        "filter_raw": "Raw Output",
        "filter_agnostic_nms": "Class-agnostic NMS",
        "filter_top1_region": "Top-1 per Region",
        "filter_top1_frame": "Top-1 per Frame",
    },
}
