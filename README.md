# UI_app

工业流水线视觉 UI（Seg + OBB 同屏，占位接口）。

## 运行

1. 安装依赖（示例）

```bash
pip install -U PySide6 opencv-python ultralytics
```

或使用：

```bash
pip install -r UI_app/requirements.txt
```

2. 放置模型

- Seg 模型放在 `UI_app/models/seg.pt`
- OBB 模型放在 `UI_app/models/obb.pt`（可先留空）

3. 启动

```bash
python UI_app/main.py --source 0
```

## 说明

- 默认双语支持：中文/English。
- OBB 目前为占位接口，后续补上 `UI_app/core/obb_engine.py` 即可。
