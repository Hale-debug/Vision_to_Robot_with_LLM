import time
import serial

from config import *


class ArmController:

    def __init__(self):

        self.ser = None

        self.is_connected = False

        # 当前状态记录
        self.current_s1 = 90
        self.current_s2 = 90
        self.current_s3 = 90
        self.current_grip = GRIP_OPEN

    # 连接串口（最多重试3次，间隔递增）
    def connect(self, port=None):

        target_port = port or SERIAL_PORT
        last_error = None
        for attempt in range(3):
            try:
                self.ser = serial.Serial(
                    target_port,
                    SERIAL_BAUDRATE,
                    timeout=SERIAL_TIMEOUT
                )

                time.sleep(2)

                self.is_connected = True

                print("机械臂串口连接成功")

                return True

            except Exception as e:
                last_error = e
                if attempt < 2:
                    wait = [1, 2][attempt]
                    print(f"连接失败 (尝试 {attempt+1}/3): {e}，{wait}秒后重试...")
                    time.sleep(wait)

        print(f"连接失败 (3次重试已用尽): {last_error}")
        self.is_connected = False
        return False

    # 关闭串口
    def disconnect(self):

        if self.ser and self.ser.is_open:

            self.ser.close()

        self.is_connected = False

        print("串口已关闭")

    # 检查连接状态（尝试一次无操作验证）
    def check_connection(self):

        if not self.is_connected or self.ser is None:
            self.is_connected = False
            return False

        try:
            if not self.ser.is_open:
                self.is_connected = False
                return False
            return True
        except (serial.SerialException, OSError):
            self.is_connected = False
            return False

    # 发送角度
    def send_angles(
        self,
        s1,
        s2,
        s3,
        grip
    ):

        if not self.check_connection():
            # 尝试重连一次
            print("机械臂未连接，尝试重新连接...")
            if not self.connect():
                self.is_connected = False
                raise RuntimeError(
                    "机械臂未连接——串口重连失败"
                )

        # 限幅保护
        s1 = max(0, min(180, s1))
        s2 = max(0, min(180, s2))
        s3 = max(0, min(180, s3))
        grip = max(0, min(180, grip))

        # 保存当前状态
        self.current_s1 = s1
        self.current_s2 = s2
        self.current_s3 = s3
        self.current_grip = grip

        # 串口命令
        cmd = (
            f"{s1:.2f},"
            f"{s2:.2f},"
            f"{s3:.2f},"
            f"{grip:.2f}\n"
        )

        try:
            self.ser.write(
                cmd.encode()
            )

            print(
                f"发送角度: "
                f"{cmd.strip()}"
            )

        except (serial.SerialException, OSError) as e:
            self.is_connected = False
            # 尝试重连一次
            print(f"串口写入失败: {e}，尝试重连...")
            if self.connect():
                try:
                    self.ser.write(cmd.encode())
                    print(f"重连成功，已补发: {cmd.strip()}")
                    return
                except (serial.SerialException, OSError) as e2:
                    print(f"重连后写入仍失败: {e2}")
            raise RuntimeError(
                f"串口通信失败: {e}"
            )

    # 回零
    def move_to_home(self):

        self.send_angles(
            90,
            90,
            90,
            GRIP_OPEN
        )

    # 张开夹爪
    def open_gripper(self):

        self.send_angles(
            self.current_s1,
            self.current_s2,
            self.current_s3,
            GRIP_OPEN
        )

    # 闭合夹爪
    def close_gripper(self):

        self.send_angles(
            self.current_s1,
            self.current_s2,
            self.current_s3,
            GRIP_CLOSE
        )