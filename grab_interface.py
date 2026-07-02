import time

from config import *

from arm_controller import ArmController
from kinematics import solve_ik


class GrabInterface:

    def __init__(self):

        self.arm = ArmController()

    # 连接
    def connect(self):

        return self.arm.connect()

    # 断开
    def disconnect(self):

        self.arm.disconnect()

    # XYZ运动
    def move_xyz(
        self,
        x,
        y,
        z,
        grip=None,
        wait=True,
        wait_time=2.0
    ):

        # IK
        angles = solve_ik(
            x,
            y,
            z
        )

        if angles is None:

            print("目标不可达")

            return None

        s1, s2, s3 = angles

        # grip默认保持当前状态
        if grip is None:

            grip = self.arm.current_grip

        # 发送角度
        self.arm.send_angles(
            s1,
            s2,
            s3,
            grip
        )

        # 等待舵机到位
        if wait:

            time.sleep(wait_time)

        return [s1, s2, s3, grip]

    # 执行抓取
    def execute_grab(
        self,
        x,
        y,
        z,
        place_pos
    ):

        print()
        print("================================")
        print("开始抓取")
        print("================================")

        # 回零
        print("回零")

        self.arm.move_to_home()

        time.sleep(2)

        # 张开夹爪
        print("张开夹爪")

        self.arm.open_gripper()

        time.sleep(1)

        # 抓取高度补偿
        # 加上物块高度的一半，让夹爪夹在物块中部
        grab_x = x
        grab_y = y
        grab_z = z + Z_GRAB_OFFSET + BLOCK_HEIGHT / 2

        print()
        print("抓取目标坐标:")
        print(
            f"X={grab_x:.2f}, "
            f"Y={grab_y:.2f}, "
            f"Z={grab_z:.2f}"
        )

        # 一步到位移动到抓取点
        print("移动到抓取点")

        self.move_xyz(
            grab_x,
            grab_y,
            grab_z,
            wait=True,
            wait_time=2.5
        )

        # 闭合夹爪
        print("闭合夹爪")

        self.arm.close_gripper()

        print("等待夹爪完成抓取...")
        time.sleep(3.0)

        # 抬起
        print("抬起目标")

        lift_z = grab_z + 60

        self.move_xyz(
            grab_x,
            grab_y,
            lift_z,
            wait=True,
            wait_time=2.0
        )

        # 放置位置
        if callable(place_pos):

            print("识别放置目标")

            place_pos = place_pos()

            if place_pos is None:

                print("未获取到放置目标坐标")

                return False

        px, py, pz = place_pos

        place_z = pz + 20

        print()
        print("放置目标坐标:")
        print(
            f"X={px:.2f}, "
            f"Y={py:.2f}, "
            f"Z={place_z:.2f}"
        )

        # 一步到位移动到放置点
        print("移动到放置点")

        self.move_xyz(
            px,
            py,
            place_z,
            wait=True,
            wait_time=2.5
        )

        # 松开夹爪
        print("松开夹爪")

        self.arm.open_gripper()

        time.sleep(1.5)

        # 抬起
        print("抬起机械臂")

        self.move_xyz(
            px,
            py,
            place_z + 60,
            wait=True,
            wait_time=2.0
        )

        # 回零
        print("回零")

        self.arm.move_to_home()

        time.sleep(2)

        print()
        print("================================")
        print("抓取完成")
        print("================================")

        return True
