# UI_app

工业流水线视觉检测 UI，支持 YOLOv11 分割 + OBB 推理，实时可视化与结果筛选。

## 运行

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 放置模型

- 分割模型放入 `models/`，例如 `models/seg.pt`
- OBB 模型（可选）放入 `models/`，例如 `models/obb.pt`

3. 启动

```bash
python main.py --source 0                     # 摄像头
python main.py --source video.mp4             # 视频文件
python main.py --seg-model models/best.pt     # 指定分割模型
python main.py --obb-model models/obb.pt      # 指定 OBB 模型
```

## 功能

| 功能 | 说明 |
|------|------|
| **实时 / 回看模式** | 工具栏切换，回看模式下可暂停/拖动 |
| **双语** | 中文 / English 下拉切换，全部界面文案跟随 |
| **视频 / 摄像头** | 打开视频文件或连接摄像头，自由切换 |
| **录制 & 截图** | 开始记录后存到 `data/`，支持单帧截图 |
| **自定义模型路径** | 默认在界面隐藏，可在源码开关中开启；开启后可选分割/OBB 模型文件并运行时热更换 |
| **筛选方式** | 下拉框选择：原始输出 / 跨类别 NMS / 区域内最高 / 全帧最高 |
| **类别映射（归并）** | 从模型自动检测类别名 → 生成 JSON 模板 → 编辑归并规则 → 启用映射，可视化中合并显示自定义类别名 |
| **识别类别统计** | 右侧实时显示当前帧识别到的类别及数量，字号大于其他选项，更醒目 |
| **双语类别名** | 中文模式下类别显示中文名，对照 `docs/中英文对照.txt`（如 `Broken_Wire` → 断线） |
| **合格判定** | 基于分割结果中是否全为 `Normal` 类别，实时显示合格/不合格 |

## 界面可见性开关

分割模型选择、OBB 模型选择、加载映射文件三项默认对用户隐藏。开关位于 `ui/main_window.py` 顶部：

```python
SHOW_SEG_MODEL_SELECTOR = False   # 分割模型选择（标签 / 路径 / 按钮）
SHOW_OBB_MODEL_SELECTOR = False   # OBB 模型选择（标签 / 路径 / 按钮）
SHOW_MAPPING_LOADER     = False   # 加载映射文件选项（标签 / 路径 / 按钮）
```

改为 `True` 即恢复显示；控件仍保留在代码中，默认加载 `configs/class_mapping.json` 的逻辑不受影响。

## 类别映射使用

1. 点击 **"从模型检测类别"** → 从当前分割模型权重读取类别名，生成 `configs/class_mapping.json`
2. 编辑 JSON，将需要归并的类别改成自定义名称，例如：
   ```json
   {
       "Cold_Solder": "Solder_Issue",
       "Solder_Void": "Solder_Issue",
       "Normal": "Normal"
   }
   ```
   - 未定义映射的类别保持原名不变
3. 点击 **"加载映射文件"** 选择编辑后的 JSON（该按钮默认隐藏，需在 `ui/main_window.py` 中开启 `SHOW_MAPPING_LOADER`）
4. 勾选 **"启用映射"**，结果视图即显示合并后的类别名
5. 取消勾选恢复原始类别名

> 默认会尝试加载 `configs/class_mapping.json`，启动即生效，无需在界面操作。

## 目录结构

```
UI_app/
  main.py                    # 入口
  ui/main_window.py          # 主窗口
  core/
    seg_engine.py            # 分割推理引擎
    obb_engine.py            # OBB 推理引擎（占位）
    video_worker.py          # 视频流线程
    view_render.py           # 渲染与筛选逻辑
    class_mapping.py         # 类别映射加载与应用
    i18n.py                  # 双语字典 + 类别中英文对照
    recorder.py              # 录像/截图
    review_player.py         # 回看播放
  configs/
    class_mapping.json       # 类别映射配置（自动生成，需用户编辑）
  docs/
    中英文对照.txt            # 分类中英文名称对照表（同步维护至 i18n.py）
  models/                    # 模型权重（不上传 git）
  data/                      # 录像输出（不上传 git）
```

## 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--source` | `""` | 视频路径或摄像头索引（如 `0`） |
| `--seg-model` | `models/seg.pt` | 分割模型路径（相对于 UI_app） |
| `--obb-model` | `models/obb.pt` | OBB 模型路径（相对于 UI_app，占位） |
