import numpy as np
import sys
import os

# 获取上一级目录
parent_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')
)

# 加入Python搜索路径
sys.path.append(parent_dir)

from kinematics import forward_kinematics

# =========================
# 你手动记录的角度
# 顺序必须和 uv 点一致
# =========================
joint_angles = [

    [38,144,114],
    [150,144,114],
    [120,165,65],
    [75,165,65],

]

points_xy = []

for angles in joint_angles:

    s1,s2,s3 = angles

    x,y,z = forward_kinematics(
        s1,
        s2,
        s3
    )

    print(f"x={x:.2f}, y={y:.2f}, z={z:.2f}")

    points_xy.append([x,y])

points_xy = np.array(
    points_xy,
    dtype=np.float32
)

# 保存
np.save(
    "world_points_xy.npy",
    points_xy
)

print()
print("Saved world_points_xy.npy")