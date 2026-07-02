# Vision_to_Robot_with_LLM

机械臂视觉抓取系统：基于视觉识别和大语言模型的三自由度机械臂抓取与放置方案。

## 项目概述

本项目实现了从自然语言指令到机械臂控制的完整流程，涵盖：
- 自然语言任务解析
- HSV 颜色视觉识别
- 像素坐标到世界坐标的单应变换
- 逆运动学与轨迹规划
- Arduino 舵机控制

系统目标是让机械臂通过“抓取某种颜色物块”这类中文指令执行抓取任务。

## 关键功能

- **自然语言任务解析**：使用 LLM 解析用户输入，提取目标颜色和动作
- **颜色视觉检测**：基于 HSV 阈值进行目标物体和放置盒识别
- **坐标变换**：通过相机标定和单应矩阵，将像素坐标转为机械臂坐标
- **运动学求解**：支持平面三自由度机械臂的正逆运动学
- **串口控制**：通过 Arduino 发送舵机角度命令，实现机械臂末端动作

## 项目结构

```
├── arm_controller.py          # 舵机串口控制
├── calibration/               # 相机标定相关脚本与数据
├── config.py                  # 全局参数配置
├── coordinate_transform.py    # 像素到世界坐标变换
├── grab_interface.py          # 抓取流程封装
├── kinematics.py              # 正逆运动学计算
├── llm_client.py              # 大语言模型客户端与解析器
├── main.py                    # 运行主程序入口
├── manual_control.py          # 手动控制测试脚本
├── test_kinematics.py         # 运动学测试脚本
├── trajectory_planner.py      # 轨迹生成
├── verify_uv_xyz.py           # 坐标变换验证脚本
├── vision_detector.py         # 视觉检测模块
├── web_server.py              # Flask + SocketIO Web 界面
└── arduino/arduino.ino         # Arduino 舵机控制程序
```

## 硬件要求

- 三自由度机械臂（3 个舵机 + 1 个夹爪舵机）
- Arduino 开发板
- USB 摄像头
- 串口线

## 机械臂参数

- 基座高度：81 mm
- 连杆 1 长度：160 mm
- 连杆 2 长度：190 mm
- 末端偏移：16 mm

## 软件依赖

```bash
pip install numpy opencv-python pyserial requests flask flask-socketio
```

## 配置说明

在 `config.py` 中修改以下参数：

### 串口配置

```python
SERIAL_PORT = 'COM7'
SERIAL_BAUDRATE = 9600
```

### LLM 配置

```python
LLM_API_BASE = 'https://chat.sjtu.edu.cn/api/v1'
LLM_API_KEY = ''
LLM_MODEL = 'gpt-4o-mini'
```

### 摄像头配置

```python
CAMERA_ID = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
```

### 夹爪配置

```python
GRIP_CLOSE = 80
GRIP_OPEN = 50
```

## 使用步骤

### 1. 相机标定

```bash
cd calibration
python generate_world_points.py
python capture_calibration_image.py
python click_points.py
python compute_homography.py
```

### 2. 运行主程序

```bash
cd ..
python main.py
```

程序会提示输入指令，例如：

```text
抓取绿色物块
```

### 3. 手动控制（可选）

```bash
python manual_control.py
```

## 常见脚本说明

- `test_kinematics.py`：测试运动学求解准确性
- `verify_uv_xyz.py`：验证像素到世界坐标变换
- `reset_calibration.py`：重置标定文件
- `HSV_detector.py`：HSV 颜色调试工具

## 注意事项

- 先完成相机标定再运行抓取流程
- 调整 HSV 阈值以适应当前光照环境
- 确保 Arduino 的串口号与系统实际一致
- 运行前检查摄像头是否可用

## 贡献说明

欢迎补充更多颜色识别、任务解析或机械臂扩展功能。
