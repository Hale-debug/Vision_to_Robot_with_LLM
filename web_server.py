import base64
import json
import threading
import time
import traceback

import cv2
import numpy as np
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

from config import *
from arm_controller import ArmController
from kinematics import solve_ik, forward_kinematics
from vision_detector import VisionDetector
from coordinate_transform import pixel_to_world
from llm_client import RobotTaskParser

try:
    import serial.tools.list_ports
    HAS_SERIAL_TOOLS = True
except ImportError:
    HAS_SERIAL_TOOLS = False

app = Flask(__name__)
app.config['SECRET_KEY'] = 'robot-arm-control-secret'
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

arm = ArmController()
detector = None
camera_thread = None
camera_running = False
execution_running = False
execution_lock = threading.Lock()

system_state = {
    'connected': False,
    'servo_1': 90.0,
    'servo_2': 90.0,
    'servo_3': 90.0,
    'grip': GRIP_OPEN,
    'block_pixel_x': None,
    'block_pixel_y': None,
    'block_world_x': None,
    'block_world_y': None,
    'block_world_z': None,
    'box_pixel_x': None,
    'box_pixel_y': None,
    'box_world_x': None,
    'box_world_y': None,
    'box_world_z': None,
    'phase': 'idle',
    'phase_description': '等待指令',
    'message': '',
    'error': None,
    'command': '',
    'block_color': None,
    'box_color': None,
    # 健康状态
    'arm_connected': False,
    'camera_ok': False,
    'health_errors': [],
}


def reset_state():
    system_state['connected'] = arm.is_connected
    system_state['servo_1'] = arm.current_s1
    system_state['servo_2'] = arm.current_s2
    system_state['servo_3'] = arm.current_s3
    system_state['grip'] = arm.current_grip
    system_state['block_pixel_x'] = None
    system_state['block_pixel_y'] = None
    system_state['block_world_x'] = None
    system_state['block_world_y'] = None
    system_state['block_world_z'] = None
    system_state['box_pixel_x'] = None
    system_state['box_pixel_y'] = None
    system_state['box_world_x'] = None
    system_state['box_world_y'] = None
    system_state['box_world_z'] = None
    system_state['phase'] = 'idle'
    system_state['phase_description'] = '等待指令'
    system_state['message'] = ''
    system_state['error'] = None
    system_state['command'] = ''
    system_state['block_color'] = None
    system_state['box_color'] = None
    system_state['arm_connected'] = arm.is_connected
    system_state['camera_ok'] = detector is not None and detector.camera_ok


def add_health_error(source, level, message):
    """添加健康告警（自动去重：同 source 只保留最新）"""
    clear_health_errors(source)
    system_state['health_errors'].append({
        'source': source,
        'level': level,
        'message': message,
    })


def clear_health_errors(source=None):
    """清除健康告警。source=None 时清除全部"""
    if source is None:
        system_state['health_errors'] = []
    else:
        system_state['health_errors'] = [
            e for e in system_state['health_errors']
            if e['source'] != source
        ]


def emit_state():
    socketio.emit('state_update', system_state)


def enable_camera():
    global detector, camera_thread, camera_running
    if detector is None:
        from config import get_camera_id
        detector = VisionDetector(camera_id=get_camera_id())
    if camera_thread is None or not camera_thread.is_alive():
        camera_running = True
        camera_thread = threading.Thread(target=camera_stream_loop, daemon=True)
        camera_thread.start()


def camera_stream_loop():
    global camera_running, detector
    fail_count = 0
    while camera_running:
        if detector is None:
            time.sleep(0.1)
            continue
        try:
            ret, frame = detector.cap.read()
            if not ret:
                fail_count += 1
                # 连续失败超过 50 次（约 2.5 秒）才打印一次警告
                if fail_count == 50:
                    print('摄像头警告: 连续抓帧失败，请检查摄像头连接和 CAMERA_ID 配置')
                    detector.camera_ok = False
                    system_state['camera_ok'] = False
                elif fail_count > 100:
                    # 超过 100 次失败，尝试重新打开摄像头
                    print('摄像头错误: 尝试重新连接摄像头...')
                    if detector.reconnect_camera():
                        fail_count = 0
                        system_state['camera_ok'] = True
                        clear_health_errors('camera')
                        print('摄像头重连成功')
                    else:
                        fail_count = 0
                        add_health_error('camera', 'error', '摄像头重连失败——请检查连接')
                time.sleep(0.05)
                continue
            fail_count = 0
            if not detector.camera_ok:
                detector.camera_ok = True
                system_state['camera_ok'] = True
                clear_health_errors('camera')
            frame = cv2.resize(frame, (640, 480))
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            b64 = base64.b64encode(buffer).decode('utf-8')
            socketio.emit('camera_frame', {'image': b64})
            time.sleep(0.05)
        except Exception as e:
            print(f'摄像头流错误: {e}')
            detector.camera_ok = False
            system_state['camera_ok'] = False
            time.sleep(0.1)


def disable_camera():
    global camera_running, detector
    camera_running = False
    if detector is not None:
        detector.release()
        detector = None


def preflight_check():
    """任务执行前预检，返回 (通过, 原因)"""
    issues = []

    # 检查机械臂
    if not arm.is_connected:
        issues.append('机械臂未连接——请检查USB串口')
    # 注意：不阻止执行——允许仅做视觉测试

    # 检查摄像头
    if detector is None or not detector.camera_ok:
        issues.append('摄像头不可用——请检查CAMERA_ID配置')
        # 摄像头不可用 → 视觉检测必然失败，阻止执行

    # 检查单应矩阵
    try:
        from coordinate_transform import _ensure_homography
        if not _ensure_homography():
            issues.append('标定文件缺失——请先运行标定流程')
    except Exception:
        issues.append('坐标变换模块加载失败')

    if issues:
        return False, '; '.join(issues)
    return True, 'OK'


def execute_grab_task(command):
    global execution_running

    with execution_lock:
        if execution_running:
            system_state['error'] = '已有任务正在执行中'
            emit_state()
            return
        execution_running = True

    reset_state()
    system_state['command'] = command
    system_state['phase'] = 'parsing'
    system_state['phase_description'] = '正在解析指令...'
    emit_state()

    # 执行前预检（仅打印，不阻止——解析阶段不需要硬件）
    ok, reason = preflight_check()
    if not ok:
        print(f'预检警告: {reason}')

    task = None
    try:
        parser = RobotTaskParser()
        task = parser.parse_grab_command(command)
    except Exception as e:
        system_state['phase'] = 'error'
        system_state['phase_description'] = '指令解析失败'
        system_state['error'] = f'LLM解析失败: {e}'
        system_state['message'] = str(e)
        emit_state()
        with execution_lock:
            execution_running = False
        return

    if task.get('action') != 'grab':
        system_state['phase'] = 'error'
        system_state['phase_description'] = '不支持的指令'
        task_error = task.get('error', '')
        system_state['error'] = task_error or f"暂不支持该动作: {task.get('action')}"
        system_state['message'] = str(task)
        emit_state()
        with execution_lock:
            execution_running = False
        return

    color = task.get('color', 'unknown')
    box_color = task.get('box_color', 'unknown')
    system_state['block_color'] = color
    system_state['box_color'] = box_color

    if color == 'unknown':
        system_state['phase'] = 'error'
        system_state['phase_description'] = '未能识别物块颜色'
        system_state['error'] = '未能从指令中识别目标物块颜色'
        emit_state()
        with execution_lock:
            execution_running = False
        return

    if box_color == 'unknown':
        system_state['phase'] = 'error'
        system_state['phase_description'] = '未能识别盒子颜色'
        system_state['error'] = '未能从指令中识别目标盒子颜色'
        emit_state()
        with execution_lock:
            execution_running = False
        return

    enable_camera()
    time.sleep(0.5)

    if not arm.is_connected:
        if not arm.connect():
            system_state['phase'] = 'error'
            system_state['phase_description'] = '机械臂连接失败'
            system_state['error'] = '串口连接失败——请检查硬件连接'
            add_health_error('arm', 'error', '机械臂连接失败——请检查USB串口')
            emit_state()
            with execution_lock:
                execution_running = False
            return
        clear_health_errors('arm')

    system_state['connected'] = arm.is_connected
    system_state['arm_connected'] = arm.is_connected
    emit_state()

    # 复用摄像头流中已打开的 detector，避免重复打开同一设备导致冲突
    global detector
    det = detector

    try:
        system_state['phase'] = 'detecting_block'
        system_state['phase_description'] = f'正在识别{color}色物块...'
        emit_state()

        result = det.detect_object_by_color(color)
        if result is None:
            system_state['phase'] = 'error'
            system_state['phase_description'] = '未检测到物块'
            system_state['error'] = f'未检测到{color}色物块'
            emit_state()
            return

        px, py = result
        system_state['block_pixel_x'] = px
        system_state['block_pixel_y'] = py

        world_result = pixel_to_world(px, py)
        if world_result is None:
            system_state['phase'] = 'error'
            system_state['phase_description'] = '坐标变换失败'
            system_state['error'] = '标定文件缺失，无法进行坐标变换。请先运行标定流程'
            add_health_error('homography', 'error', '标定文件缺失——请先运行标定流程')
            emit_state()
            return

        x, y = world_result
        z = 20
        system_state['block_world_x'] = round(x, 1)
        system_state['block_world_y'] = round(y, 1)
        system_state['block_world_z'] = round(z, 1)

        system_state['phase'] = 'block_detected'
        system_state['phase_description'] = f'物块已识别: ({px}, {py})'
        emit_state()
        time.sleep(0.3)

        system_state['phase'] = 'homing'
        system_state['phase_description'] = '机械臂回零...'
        emit_state()
        arm.move_to_home()
        system_state['servo_1'] = arm.current_s1
        system_state['servo_2'] = arm.current_s2
        system_state['servo_3'] = arm.current_s3
        system_state['grip'] = arm.current_grip
        emit_state()
        time.sleep(2)

        system_state['phase'] = 'opening_gripper'
        system_state['phase_description'] = '张开夹爪...'
        emit_state()
        arm.open_gripper()
        system_state['grip'] = arm.current_grip
        emit_state()
        time.sleep(1)

        grab_x = x
        grab_y = y
        grab_z = z + Z_GRAB_OFFSET + BLOCK_HEIGHT / 2

        system_state['phase'] = 'moving_to_block'
        system_state['phase_description'] = f'移动到抓取点 ({grab_x:.1f}, {grab_y:.1f}, {grab_z:.1f})'
        emit_state()

        angles = solve_ik(grab_x, grab_y, grab_z)
        if angles is None:
            system_state['phase'] = 'error'
            system_state['phase_description'] = '目标不可达'
            system_state['error'] = '逆运动学求解失败，目标超出工作范围'
            emit_state()
            return

        s1, s2, s3 = angles
        arm.send_angles(s1, s2, s3, arm.current_grip)
        system_state['servo_1'] = s1
        system_state['servo_2'] = s2
        system_state['servo_3'] = s3
        emit_state()
        time.sleep(2.5)

        system_state['phase'] = 'closing_gripper'
        system_state['phase_description'] = '闭合夹爪，抓取物块...'
        emit_state()
        arm.close_gripper()
        system_state['grip'] = arm.current_grip
        emit_state()
        time.sleep(3)

        system_state['phase'] = 'lifting_block'
        system_state['phase_description'] = '抬起物块...'
        emit_state()
        lift_z = grab_z + 60
        lift_angles = solve_ik(grab_x, grab_y, lift_z)
        if lift_angles:
            s1, s2, s3 = lift_angles
            arm.send_angles(s1, s2, s3, arm.current_grip)
            system_state['servo_1'] = s1
            system_state['servo_2'] = s2
            system_state['servo_3'] = s3
            emit_state()
        time.sleep(2)

        system_state['phase'] = 'detecting_box'
        system_state['phase_description'] = f'正在识别{box_color}色盒子...'
        emit_state()

        box_result = det.detect_box_by_color(box_color)
        if box_result is None:
            system_state['phase'] = 'error'
            system_state['phase_description'] = '未检测到盒子'
            system_state['error'] = f'未检测到{box_color}色盒子'
            emit_state()
            return

        box_px, box_py = box_result
        system_state['box_pixel_x'] = box_px
        system_state['box_pixel_y'] = box_py

        box_world_result = pixel_to_world(box_px, box_py)
        if box_world_result is None:
            system_state['phase'] = 'error'
            system_state['phase_description'] = '坐标变换失败'
            system_state['error'] = '标定文件缺失，无法进行坐标变换'
            add_health_error('homography', 'error', '标定文件缺失——请先运行标定流程')
            emit_state()
            return

        box_x, box_y = box_world_result
        box_z = BOX_HEIGHT
        system_state['box_world_x'] = round(box_x, 1)
        system_state['box_world_y'] = round(box_y, 1)
        system_state['box_world_z'] = round(box_z, 1)

        system_state['phase'] = 'box_detected'
        system_state['phase_description'] = f'盒子已识别: ({box_px}, {box_py})'
        emit_state()
        time.sleep(0.3)

        place_z = box_z + 20

        system_state['phase'] = 'moving_to_box'
        system_state['phase_description'] = f'移动到放置点 ({box_x:.1f}, {box_y:.1f}, {place_z:.1f})'
        emit_state()

        place_angles = solve_ik(box_x, box_y, place_z)
        if place_angles is None:
            system_state['phase'] = 'error'
            system_state['phase_description'] = '放置位置不可达'
            system_state['error'] = '逆运动学求解失败，放置位置超出工作范围'
            emit_state()
            return

        s1, s2, s3 = place_angles
        arm.send_angles(s1, s2, s3, arm.current_grip)
        system_state['servo_1'] = s1
        system_state['servo_2'] = s2
        system_state['servo_3'] = s3
        emit_state()
        time.sleep(2.5)

        system_state['phase'] = 'releasing_block'
        system_state['phase_description'] = '松开夹爪，放置物块...'
        emit_state()
        arm.open_gripper()
        system_state['grip'] = arm.current_grip
        emit_state()
        time.sleep(1.5)

        system_state['phase'] = 'lifting_arm'
        system_state['phase_description'] = '抬起机械臂...'
        emit_state()
        retract_z = place_z + 60
        retract_angles = solve_ik(box_x, box_y, retract_z)
        if retract_angles:
            s1, s2, s3 = retract_angles
            arm.send_angles(s1, s2, s3, arm.current_grip)
            system_state['servo_1'] = s1
            system_state['servo_2'] = s2
            system_state['servo_3'] = s3
            emit_state()
        time.sleep(2)

        system_state['phase'] = 'homing_final'
        system_state['phase_description'] = '回零...'
        emit_state()
        arm.move_to_home()
        system_state['servo_1'] = arm.current_s1
        system_state['servo_2'] = arm.current_s2
        system_state['servo_3'] = arm.current_s3
        system_state['grip'] = arm.current_grip
        emit_state()
        time.sleep(2)

        system_state['phase'] = 'completed'
        system_state['phase_description'] = '任务完成'
        system_state['message'] = f'成功将{color}色物块放入{box_color}色盒子'
        system_state['error'] = None
        emit_state()

    except Exception as e:
        system_state['phase'] = 'error'
        system_state['phase_description'] = '执行出错'
        system_state['error'] = str(e)
        system_state['message'] = traceback.format_exc()
        system_state['arm_connected'] = arm.is_connected
        system_state['connected'] = arm.is_connected
        if not arm.is_connected:
            add_health_error('arm', 'error', '机械臂连接中断')
        emit_state()

    finally:
        # 注意：不释放 det，因为它复用的是全局摄像头流实例
        with execution_lock:
            execution_running = False


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('connect')
def handle_connect():
    reset_state()
    system_state['connected'] = arm.is_connected
    system_state['arm_connected'] = arm.is_connected
    if not system_state['connected']:
        try:
            system_state['connected'] = arm.connect()
            system_state['arm_connected'] = arm.is_connected
        except Exception:
            system_state['connected'] = False
            system_state['arm_connected'] = False
    system_state['servo_1'] = arm.current_s1
    system_state['servo_2'] = arm.current_s2
    system_state['servo_3'] = arm.current_s3
    system_state['grip'] = arm.current_grip

    # 检查硬件状态，生成初始健康告警
    if not system_state['arm_connected']:
        add_health_error('arm', 'warning', '机械臂未连接——请检查USB串口')

    enable_camera()
    # 同步摄像头状态
    global detector
    if detector is not None:
        system_state['camera_ok'] = detector.camera_ok
    if not system_state['camera_ok']:
        add_health_error('camera', 'warning', '摄像头未连接——请检查CAMERA_ID配置')

    emit_state()


@socketio.on('disconnect')
def handle_disconnect():
    global execution_running
    with execution_lock:
        execution_running = False
    disable_camera()


@socketio.on('execute_command')
def handle_execute_command(data):
    command = data.get('command', '').strip()
    if not command:
        emit('command_error', {'error': '请输入指令'})
        return

    thread = threading.Thread(target=execute_grab_task, args=(command,), daemon=True)
    thread.start()


@socketio.on('stop_execution')
def handle_stop():
    global execution_running
    with execution_lock:
        execution_running = False
    system_state['phase'] = 'stopped'
    system_state['phase_description'] = '已停止'
    system_state['error'] = '用户手动停止'
    emit_state()


@socketio.on('manual_move_home')
def handle_move_home():
    try:
        if not arm.is_connected:
            arm.connect()
        arm.move_to_home()
        system_state['servo_1'] = arm.current_s1
        system_state['servo_2'] = arm.current_s2
        system_state['servo_3'] = arm.current_s3
        system_state['grip'] = arm.current_grip
        system_state['connected'] = arm.is_connected
        system_state['arm_connected'] = arm.is_connected
        if arm.is_connected:
            clear_health_errors('arm')
        emit_state()
    except Exception as e:
        system_state['arm_connected'] = arm.is_connected
        system_state['connected'] = arm.is_connected
        add_health_error('arm', 'error', f'回零失败: {e}')
        emit('command_error', {'error': f'回零失败: {e}'})


@socketio.on('list_serial_ports')
def handle_list_serial_ports():
    """返回可用串口列表"""
    ports = []
    if HAS_SERIAL_TOOLS:
        try:
            for port in serial.tools.list_ports.comports():
                ports.append({
                    'device': port.device,
                    'description': port.description,
                    'hwid': port.hwid,
                })
        except Exception as e:
            print(f'枚举串口出错: {e}')
    # 也包含当前配置的端口（即使未被检测到）
    from config import get_serial_port
    current = get_serial_port()
    if current and not any(p['device'] == current for p in ports):
        ports.insert(0, {'device': current, 'description': '当前配置', 'hwid': ''})
    emit('serial_ports_list', {'ports': ports})


@socketio.on('get_settings')
def handle_get_settings():
    """返回当前生效的配置"""
    from config import get_effective_config
    emit('current_settings', get_effective_config())


@socketio.on('save_settings')
def handle_save_settings(data):
    """保存用户配置到 user_config.json（串口和摄像头需要重启后生效）"""
    try:
        allowed_keys = ['serial_port', 'camera_id', 'llm_api_base', 'llm_model']
        config_to_save = {}
        for key in allowed_keys:
            if key in data and data[key] is not None and data[key] != '':
                config_to_save[key] = data[key]

        with open('user_config.json', 'w', encoding='utf-8') as f:
            json.dump(config_to_save, f, indent=2, ensure_ascii=False)

        # 清除配置缓存，使下次 get_* 调用重新读取文件
        import config as cfg
        cfg._user_config = None

        print(f'用户配置已保存: {config_to_save}')
        emit('settings_saved', {'success': True, 'config': config_to_save})
    except Exception as e:
        print(f'保存配置失败: {e}')
        emit('settings_saved', {'success': False, 'error': str(e)})


def main():
    print('========================================')
    print('  机械臂控制 Web 服务器启动中...')
    print('========================================')

    # 读取生效配置
    from config import get_serial_port, get_camera_id, get_llm_api_base, get_llm_model
    effective_port = get_serial_port()
    effective_camera = get_camera_id()
    effective_api = get_llm_api_base()
    effective_model = get_llm_model()
    print(f'[配置] 串口={effective_port}, 摄像头ID={effective_camera}')
    print(f'[配置] LLM API={effective_api}, Model={effective_model}')
    print(f'[配置] API密钥: {"已设置" if LLM_API_KEY else "未设置 -- 请在环境变量中设置 LLM_API_KEY"}')

    # 启动时检测硬件（不崩溃）
    print('[硬件检测]')
    if arm.connect(port=effective_port):
        print(f'  [OK] 机械臂串口连接成功 ({effective_port})')
        system_state['arm_connected'] = True
        system_state['connected'] = True
    else:
        print(f'  [X] 机械臂未连接 ({effective_port}) -- 进入离线模式')
        system_state['arm_connected'] = False
        system_state['connected'] = False
        add_health_error('arm', 'warning', f'机械臂未连接——{effective_port}')

    global detector
    try:
        detector = VisionDetector(camera_id=effective_camera)
        if detector.camera_ok:
            print('  [OK] 摄像头可用')
            system_state['camera_ok'] = True
        else:
            print('  [X] 摄像头不可用——进入离线模式')
            system_state['camera_ok'] = False
            add_health_error('camera', 'warning', '摄像头未连接——请检查CAMERA_ID配置')
    except Exception as e:
        print(f'  [X] 摄像头初始化失败: {e}')
        detector = None
        system_state['camera_ok'] = False
        add_health_error('camera', 'warning', '摄像头初始化失败')

    # 检查标定文件
    try:
        from coordinate_transform import _ensure_homography
        if _ensure_homography():
            print('  [OK] 标定文件已加载')
        else:
            print('  [X] 标定文件缺失')
            add_health_error('homography', 'error', '标定文件缺失——请先运行标定流程')
    except Exception as e:
        print(f'  [X] 坐标变换模块加载异常: {e}')

    if system_state.get('health_errors'):
        warnings = [e['message'] for e in system_state['health_errors']]
        print(f'\n[警告] 共 {len(warnings)} 项告警，系统将以离线模式运行：')
        for w in warnings:
            print(f'  - {w}')
    else:
        print('\n[就绪] 所有硬件正常')

    print('\n  访问地址: http://localhost:5000')
    print('========================================')
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    main()
