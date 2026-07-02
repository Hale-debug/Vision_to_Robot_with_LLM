import numpy as np

# 机械臂参数
A1 = 16.0
A2 = 160.0
A3 = 190.0
D1 = 81.0

# 逆运动学
# XYZ -> Servo Angles
def solve_ik(x, y, z):  

    # theta1
    theta1 = np.degrees(
        np.arctan2(y, x)
    )

    # =========================
    # 投影平面
    # =========================
    r_prime = np.sqrt(
        x**2 + y**2
    ) 

    z_prime = z - D1

    # =========================
    # theta3
    # =========================
    L2 = r_prime**2 + z_prime**2

    cos3 = (
        L2 - A2**2 - A3**2
    ) / (2 * A2 * A3)

    if abs(cos3) > 1:
        return None

    sin3 = np.sqrt(
        1 - cos3**2
    )

    theta3 = np.degrees(
        np.arctan2(
            sin3,
            cos3
        )
    )

    # =========================
    # theta2
    # =========================
    k1 = A2 + A3 * cos3
    k2 = A3 * sin3

    theta2 = (
        np.degrees(
            np.arctan2(
                z_prime,
                r_prime
            )
        )
        +
        np.degrees(
            np.arctan2(
                k2,
                k1
            )
        )
    )

    # =========================
    # Servo Mapping
    # =========================
    s1 = 90 + theta1
    s2 = 180 - theta2
    s3 = theta3

    return [s1, s2, s3]

# ==========================================================
# 正运动学
# Servo Angles -> XYZ
# ==========================================================
def forward_kinematics(
    s1,
    s2,
    s3
):

    # =========================
    # Servo -> theta
    # =========================
    theta1 = s1 - 90

    theta2 = 180 - s2

    theta3 = s3

    # 转弧度
    t1 = np.radians(theta1)

    t2 = np.radians(theta2)

    t3 = np.radians(theta3)

    # =========================
    # 平面坐标
    # =========================
    r = (
        A2 * np.cos(t2)
        +
        A3 * np.cos(t2 - t3)
    )

    z = (
        D1
        +
        A2 * np.sin(t2)
        +
        A3 * np.sin(t2 - t3)
    )

    # =========================
    # 转回3D
    # =========================
    x = r * np.cos(t1)

    y = r * np.sin(t1)

    return x, y, z