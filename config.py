import json
import os

# ── 环境变量（优先级最高）──
SERIAL_PORT = os.getenv('SERIAL_PORT', 'COM7')
SERIAL_BAUDRATE = int(os.getenv('SERIAL_BAUDRATE', '9600'))
SERIAL_TIMEOUT = float(os.getenv('SERIAL_TIMEOUT', '1.0'))

# 摄像头参数
CAMERA_ID = int(os.getenv('CAMERA_ID', '1'))

# LLM API 配置 —— API 密钥仅从环境变量读取
LLM_API_BASE = os.getenv('LLM_API_BASE', 'https://api.openai.com/v1')
LLM_API_KEY = os.getenv('LLM_API_KEY', '')
LLM_MODEL = os.getenv('LLM_MODEL', 'gpt-4o-mini')
LLM_TIMEOUT = float(os.getenv('LLM_TIMEOUT', '30'))

# ── 用户配置文件（覆盖环境变量默认值，但 API 密钥除外）──
_user_config = None


def _load_user_config():
    """加载 user_config.json，失败时返回空 dict"""
    global _user_config
    if _user_config is not None:
        return _user_config
    try:
        with open('user_config.json', 'r', encoding='utf-8') as f:
            _user_config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        _user_config = {}
    return _user_config


def get_effective_config():
    """
    返回当前生效的配置（环境变量 + user_config.json 合并）。
    API 密钥不在返回值中，仅从环境变量读取。
    用于前端的 get_settings 接口。
    """
    uc = _load_user_config()
    return {
        'serial_port': uc.get('serial_port', SERIAL_PORT),
        'camera_id': uc.get('camera_id', CAMERA_ID),
        'llm_api_base': uc.get('llm_api_base', LLM_API_BASE),
        'llm_model': uc.get('llm_model', LLM_MODEL),
        # API 密钥不返回，仅返回是否已设置
        'llm_key_configured': bool(LLM_API_KEY),
    }


def get_serial_port():
    """返回当前生效的串口"""
    uc = _load_user_config()
    return uc.get('serial_port', SERIAL_PORT)


def get_camera_id():
    """返回当前生效的摄像头 ID"""
    uc = _load_user_config()
    return int(uc.get('camera_id', CAMERA_ID))


def get_llm_api_base():
    """返回当前生效的 LLM API 地址"""
    uc = _load_user_config()
    return uc.get('llm_api_base', LLM_API_BASE)


def get_llm_model():
    """返回当前生效的 LLM 模型名"""
    uc = _load_user_config()
    return uc.get('llm_model', LLM_MODEL)

# 机械臂参数（mm）
BASE_HEIGHT = 16.0
LINK_1 = 160.0
LINK_2 = 190.0
LINK_3 = 81.0
Z_GRAB_OFFSET = -25

# 夹爪角度 切记：夹爪角度越大，夹爪越闭合
GRIP_CLOSE = 80
GRIP_OPEN = 50

# 舵机限制
SERVO_MIN = 0
SERVO_MAX = 180

FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# 工作平面实际尺寸（mm）
WORKSPACE_WIDTH = 300
WORKSPACE_HEIGHT = 300

# 图像中心
CX = FRAME_WIDTH / 2
CY = FRAME_HEIGHT / 2

# 像素转毫米比例
PIXEL_TO_MM = 0.5

# 物块参数
BLOCK_HEIGHT = 30  # 物块高度（mm），用于调整夹取位置到物块中部

# 盒子参数
BOX_HEIGHT = 80  # 盒子高度（mm）
BOX_AREA_MIN = 800  # 盒子检测最小面积
BOX_AREA_MAX = 20000  # 盒子检测最大面积

# 放置位置
PLACE_X = 200
PLACE_Y = 200
PLACE_Z = 100
