# Findings & Discoveries

## Requirements
- 添加全面错误处理，系统不因任何故障而崩溃（14种故障场景全覆盖）
- 离线模式：硬件不可用时系统仍可启动，前端显示告警
- 混合重试：瞬时故障静默重试（≤2次连续），持续性故障通知用户
- 逐模块加固，不引入新抽象层

## Research Findings
- arm_controller.py 原 connect() 无重试，send_angles() SerialException 直接上抛
- vision_detector.py 原 __init__() 摄像头失败仅打印警告，无 camera_ok 状态标志
- llm_client.py 原 chat() 无显式超时区分，无重试机制
- coordinate_transform.py 原在导入时加载单应矩阵，文件缺失直接崩溃
- kinematics.py 已正确实现 solve_ik 返回 None（无需修改）
- web_server.py system_state 原无健康状态字段，execute_grab_task 异常处理不够分类化
- 前端原无健康告警显示机制

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 延迟加载 homography | 避免导入时崩溃，允许标定文件缺失时系统仍可启动 |
| camera_ok 标志在 detector 实例上 | VisionDetector 可独立判断自身状态 |
| health_errors 在 system_state 中管理 | 前端通过现有 state_update 事件自动获取，无需新 SocketIO 事件 |
| send_angles 保留 RuntimeError 上抛 | 调用方（web_server）已有 try/except 兜底 |
| parse_grab_command 始终返回 dict | 调用方不需要额外异常处理，错误信息通过 'error' 字段传播 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| parse_grab_command 返回 error dict 但 web_server 未传播具体错误消息 | 修改 != 'grab' 检查分支，优先使用 task.get('error') |
| 跨模块健康状态同步（arm_connected/camera_ok 在 arm/detector 对象上，不在 system_state） | web_server 作为中心协调层，在各关键路径同步状态到 system_state |

## Resources
- 设计文档：`docs/superpowers/specs/2026-06-14-error-handling-design.md`
- 改动文件：arm_controller.py, vision_detector.py, llm_client.py, coordinate_transform.py, web_server.py, templates/index.html
- 不改动：kinematics.py
