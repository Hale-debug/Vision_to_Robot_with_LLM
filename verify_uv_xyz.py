import cv2
import numpy as np
import serial
import time

from config import BLOCK_HEIGHT
from coordinate_transform import pixel_to_world
from kinematics import solve_ik

# 串口配置
SERIAL_PORT = "COM7"

BAUDRATE = 9600

# 摄像头
CAMERA_ID = 1

# 固定抓取高度
# 使用物块高度的一半，让夹爪夹在物块中部
Z_HEIGHT = 10 + BLOCK_HEIGHT / 2

# 打开串口
try:

    ser = serial.Serial(
        SERIAL_PORT,
        BAUDRATE,
        timeout=1
    )

    time.sleep(2)

    print("机械臂串口连接成功")

except Exception as e:

    print("串口连接失败")
    print(e)

    exit()

# 打开摄像头
cap = cv2.VideoCapture(CAMERA_ID)

if not cap.isOpened():

    print("摄像头打开失败")
    exit()

# 鼠标回调
def mouse_callback(
    event,
    x,
    y,
    flags,
    param
):

    if event == cv2.EVENT_LBUTTONDOWN:

        print()
        print("================================")
        print("点击位置")
        print(f"u,v = ({x}, {y})")

        # 坐标变换
        world_x, world_y = pixel_to_world(
            x,
            y
        )

        world_z = Z_HEIGHT

        print()
        print("机械臂坐标:")
        print(
            f"({world_x:.2f}, "
            f"{world_y:.2f}, "
            f"{world_z:.2f})"
        )


        # IK
        angles = solve_ik(
            world_x,
            world_y,
            world_z
        )

        if angles is None:

            print()
            print("目标不可达")
            return

        s1,s2,s3 = angles

        print()
        print("舵机角度:")
        print(
            round(s1,2),
            round(s2,2),
            round(s3,2)
        )

        # 发送串口
        cmd = (
            f"{s1:.1f},"
            f"{s2:.1f},"
            f"{s3:.1f},"
            f"75\n"
        )

        ser.write(
            cmd.encode()
        )

        print()
        print("已发送机械臂")

# 创建窗口
cv2.namedWindow("Verify UV XYZ")

cv2.setMouseCallback(
    "Verify UV XYZ",
    mouse_callback
)

print()
print("================================")
print("鼠标点击图像")
print("机械臂将移动到对应位置")
print("按 q 退出")
print("================================")

# 主循环
while True:

    ret, frame = cap.read()

    if not ret:
        break

    cv2.imshow(
        "Verify UV XYZ",
        frame
    )

    key = cv2.waitKey(1)

    if key == ord('q'):
        break

# 释放
cap.release()

ser.close()
cv2.destroyAllWindows()

print()
print("程序结束")
