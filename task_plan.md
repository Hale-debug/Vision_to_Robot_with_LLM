# Task Plan: 错误处理与异常保护

## Goal
为机械臂视觉抓取系统添加全面的错误处理和异常保护，实现优雅降级、自动恢复和清晰的用户通知。覆盖 14 种故障场景。

## Current Phase
Phase 7 — 完成

## Phases

### Phase 1: arm_controller.py 串口通信层加固
- [x] connect() 3次重试（间隔1s/2s/3s）
- [x] send_angles() 捕获 SerialException，自动重连1次
- [x] 新增 check_connection() 方法
- **Status:** complete

### Phase 2: vision_detector.py 摄像头视觉层加固
- [x] __init__() 设置 camera_ok 标志，初始化失败不崩溃
- [x] detect_object_by_color() 新增 timeout 参数（默认10s）
- [x] detect_box_by_color() 新增 camera_ok 检查
- [x] 新增 reconnect_camera() 方法（3次重试）
- [x] 新增 check_camera() 方法
- **Status:** complete

### Phase 3: llm_client.py LLM通信层加固
- [x] LLMClient.chat() 区分连接超时(10s)/读取超时
- [x] 网络错误重试2次（指数退避1s/3s）
- [x] HTTP 4xx不重试，5xx/网络错误重试
- [x] RobotTaskParser._safe_parse_json() 安全JSON解析
- [x] JSON修复尝试（markdown代码块、尾部逗号、单引号）
- [x] parse_grab_command() 始终返回 dict，不再上抛异常
- **Status:** complete

### Phase 4: coordinate_transform.py 坐标变换层加固
- [x] 改为延迟加载（模块级 H=None）
- [x] _ensure_homography() 加载函数
- [x] pixel_to_world() 返回 Optional[Tuple]
- **Status:** complete

### Phase 5: web_server.py Web服务层加固
- [x] system_state 新增 arm_connected, camera_ok, health_errors
- [x] 新增 add_health_error() / clear_health_errors()
- [x] 新增 preflight_check() 执行前预检
- [x] execute_grab_task() 集成预检、pixel_to_world None处理、健康状态同步
- [x] handle_connect() 初始硬件检测和健康告警生成
- [x] handle_move_home() 增强错误处理和健康状态同步
- [x] camera_stream_loop() 同步 camera_ok 到 system_state
- [x] main() 启动时硬件检测（不崩溃），打印告警汇总
- **Status:** complete

### Phase 6: templates/index.html 前端通知层
- [x] 新增 health-alerts 区域（executionView 顶部）
- [x] 新增状态指示器（header 中，支持 ok/warning/error/offline）
- [x] 离线模式横幅（commandView 顶部）
- [x] CSS 告警样式 + 状态点动画
- [x] JS renderHealthAlerts() + updateStatusDot()
- [x] updatePhase() 不再覆盖状态点，由 updateStatusDot 统一管理
- **Status:** complete

### Phase 7: 验证与代码审查
- [x] 全文件代码审查，确认模块间接口一致
- [x] 修复 parse_grab_command 错误消息传播链
- [ ] 实际硬件测试（需连接机械臂+摄像头）
- **Status:** complete (代码审查) / pending (硬件测试)

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 逐模块加固，不引入新抽象层 | 每个模块故障模式不同，统一抽象会增加复杂度 |
| 混合重试：瞬时静默，持续通知 | 避免噪声，但不隐藏真正的问题 |
| 离线模式启动 | 系统和前端始终可用，只是显示硬件告警 |
| 全故障场景覆盖 | 用户选择 F（全部场景） |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| parse_grab_command 返回 error dict 但 web_server 未传播错误消息 | 1 | 修改 web_server 中 != 'grab' 检查，优先使用 task['error'] |

## Files Modified
| File | Changes |
|------|---------|
| arm_controller.py | connect() 3次重试, send_angles() SerialException处理+自动重连, check_connection() |
| vision_detector.py | camera_ok标志, timeout参数, reconnect_camera(), check_camera(), release()安全化 |
| llm_client.py | chat() 超时区分+重试+退避, _safe_parse_json(), parse_grab_command()始终返回dict |
| coordinate_transform.py | 延迟加载, _ensure_homography(), pixel_to_world返回Optional |
| web_server.py | health状态模型, add/clear_health_error, preflight_check, 启动硬件检测, 全链路健康同步 |
| templates/index.html | health-alerts区域, 状态指示器, 离线横幅, CSS+JS |

## Notes
- 设计文档：`docs/superpowers/specs/2026-06-14-error-handling-design.md`
- kinematics.py 无需改动（已正确处理不可达目标）
