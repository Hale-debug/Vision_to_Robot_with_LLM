import cv2
import numpy as np

# =========================
# 加载数据
# =========================
uv = np.load("new_image_points_uv.npy")

xy = np.load("world_points_xy.npy")

print("uv shape:", uv.shape)
print("xy shape:", xy.shape)

# =========================
# 计算单应矩阵
# =========================
H, mask = cv2.findHomography(
    uv,
    xy,
    cv2.RANSAC
)

print()
print("Homography Matrix:")
print(H)

# 保存
np.save("homography.npy", H)

print()
print("Saved homography.npy")