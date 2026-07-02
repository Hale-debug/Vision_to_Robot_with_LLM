# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 在此仓库中工作时提供指引。

## 项目概述

机械臂视觉抓取系统——自然语言指令 → LLM 解析 → HSV 颜色视觉检测 → 单应矩阵坐标变换 → 逆运动学 → 通过串口控制 Arduino 驱动的三自由度机械臂及夹爪。

## 运行项目

```bash
# 命令行模式（文本输入交互）
python main.py

# Web 界面模式（Flask + SocketIO，浏览器访问 http://localhost:5000）
python web_server.py

# 手动控制——终端直接输入舵机角度
python manual_control.py
```

## 工具脚本

```bash
# 相机标定流程（按顺序执行）：
python calibration/generate_world_points.py   # 1. 生成世界坐标网格点
python calibration/capture_calibration_image.py  # 2. 拍摄标定参考图
python calibration/click_points.py             # 3. 手动点击对应的像素点
python calibration/compute_homography.py       # 4. 计算并保存 homography.npy

# 颜色阈值拾取器——点击画面任意区域获取 HSV/BGR 取值范围
python HSV_detector.py

# 点击验证——鼠标点击图像，自动计算 IK 并发送舵机角度到机械臂
python verify_uv_xyz.py

# 重置所有标定文件
python reset_calibration.py

# 验证正/逆运动学往返精度
python test_kinematics.py
```

## 依赖

```
numpy opencv-python pyserial requests flask flask-socketio
```

## 架构

### 数据流

```
用户指令 → RobotTaskParser（通过 OpenAI 兼容 API 调用 LLM）→ {action, color, box_color}
                                                    ↓
VisionDetector（cv2 + HSV 掩膜）→ 像素坐标 (u,v)
                                                    ↓
coordinate_transform.pixel_to_world()（单应矩阵 H）→ 世界坐标 (x,y)
                                                    ↓
kinematics.solve_ik(x,y,z) → 舵机角度 (s1,s2,s3)
                                                    ↓
ArmController.send_angles() → 串口发送 "s1,s2,s3,grip\n" → Arduino
```

### 模块分层

- **`web_server.py`** — Flask + SocketIO Web 界面。通过 WebSocket 实时推送 base64 JPEG 帧作为摄像头画面，实时状态更新。每条指令在后台线程中运行 `execute_grab_task()`。内置了独立的抓取流程（未使用 `GrabInterface`），直接调用 `ArmController` + `solve_ik` + `pixel_to_world`。将摄像头作为全局 `VisionDetector` 实例管理，配有独立的推流线程。
- **`main.py`** — 命令行入口。组合调用 `RobotTaskParser` → `VisionDetector` → `pixel_to_world` → `GrabInterface.execute_grab()`。
- **`grab_interface.py` / `GrabInterface`** — 高层抓取接口，封装完整抓取流程：回零 → 张开夹爪 → 移动到抓取点（IK）→ 闭合夹爪 → 抬起 → 识别放置盒子（通过可调用对象 `place_pos`）→ 移动到盒子 → 松开 → 退回避让 → 回零。内部封装 `ArmController`。
- **`arm_controller.py` / `ArmController`** — 串口通信层。通过串口发送逗号分隔的角度字符串。跟踪当前舵机/夹爪状态。提供 `move_to_home()`、`open_gripper()`、`close_gripper()` 等便捷方法。
- **`kinematics.py`** — 三自由度平面机械臂正/逆运动学。臂体参数：基座高度 D1=81mm，连杆1=160mm，连杆2=190mm。`solve_ik(x,y,z)` 返回 `[s1,s2,s3]`，目标不可达时返回 `None`。`forward_kinematics(s1,s2,s3)` 返回 `(x,y,z)`。
- **`coordinate_transform.py`** — 在模块导入时加载 `calibration/homography.npy`（模块级变量）。`pixel_to_world(u,v)` 使用 3×3 单应矩阵进行坐标变换。
- **`vision_detector.py` / `VisionDetector`** — 两种检测方法，使用**不同的 HSV 阈值字典**：
  - `detect_object_by_color(color)` — 持续循环直到检测到目标；按面积 100–500 px² 过滤。支持颜色：green、orange、purple、pink、blue、yellow、red。
  - `detect_box_by_color(color)` — 单帧抓拍，进行形态学闭运算+开运算和孔洞填充；按 `config.py` 中的 `BOX_AREA_MIN`/`BOX_AREA_MAX` 过滤。支持颜色：red、blue、green（与物块检测使用不同的 HSV 阈值区间）。
- **`llm_client.py`** — `LLMClient`：通用的 OpenAI 兼容 `/chat/completions` 调用器。`RobotTaskParser`：发送结构化 system prompt + 用户指令，解析 JSON 响应，将中英文颜色别名映射为规范的英文颜色名称。返回 `{action, color, box_color, target}`。
- **`trajectory_planner.py`** — 直线插值工具（目前未接入抓取流程）。
- **`config.py`** — 所有可调参数：串口号/波特率、LLM 接口地址/密钥/模型、机械臂尺寸、夹爪角度、摄像头 ID、HSV 面积阈值、物块/盒子高度、像素毫米比。
- **`HSV_detector.py`** — 独立的颜色拾取工具。点击摄像头画面，获取小区域内的 HSV/BGR 平均值。用于调试 `VisionDetector` 中的 HSV 阈值。
- **`arduino/arduino.ino`** — Arduino 程序。4 路舵机（3 路机械臂 + 1 路夹爪）连接引脚 4/5/8/9。解析串口输入的 `"s1,s2,s3,s4\n"` 格式数据，施加每路舵机的安装偏移和限位保护，通过缓动函数实现角度平滑过渡。

## 重要细节

- **HSV 阈值因检测类型而异**：`color_ranges` 用于小物块检测；`box_color_ranges` 用于较大的盒子检测。同一颜色名称在不同字典中有不同的阈值（例如红色物块使用 `[155-195, 155-195, 0-255]`，而红色盒子使用两段环绕区间 `[0-10]` + `[160-180]`）。这是有意为之——在相同光照条件下，物块和盒子的外观不同。
- **夹爪角度是反的**：角度越大夹爪越闭合。`GRIP_CLOSE=80`，`GRIP_OPEN=50`。
- **IK 使用平面模型**：theta1（底座旋转）由 atan2(y,x) 计算；剩余两自由度在 r-z 平面内求解。所有角度单位均为度。
- **`coordinate_transform.py`** 在导入时通过模块级 `H = np.load(...)` 加载单应矩阵。如果 `calibration/homography.npy` 不存在，导入会直接失败。
- **`web_server.py` 第 15 行** 导入了 `VisionDetectorq`（拼写错误，应为 `VisionDetector`）——需确认是否实际可运行或需要修复。
- **`config.py` 中包含硬编码的默认值**，包括串口号（`COM7`）、摄像头 ID（`1`）和 API 凭据。这些参数因部署环境而异——用户直接修改 `config.py` 进行配置。
- **`Z_GRAB_OFFSET`**（`-25`）和 **`BLOCK_HEIGHT/2`** 会叠加到抓取 Z 坐标上，使夹爪对准物块中部而非底部。
