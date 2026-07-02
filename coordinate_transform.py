import numpy as np

# 延迟加载单应矩阵（避免导入时文件不存在导致崩溃）
H = None


def _ensure_homography():
    """尝试加载单应矩阵，成功返回 True，失败返回 False"""
    global H
    if H is not None:
        return True
    try:
        H = np.load("calibration/homography.npy")
        print("单应矩阵加载成功")
        return True
    except FileNotFoundError:
        print("警告: 标定文件 calibration/homography.npy 不存在，坐标变换不可用")
        print("请先运行标定流程: calibration/generate_world_points.py → capture_calibration_image.py → click_points.py → compute_homography.py")
        return False
    except Exception as e:
        print(f"警告: 单应矩阵加载失败: {e}")
        return False


def pixel_to_world(u, v):
    """像素坐标 → 世界坐标。单应矩阵不可用时返回 None"""
    if not _ensure_homography():
        return None

    p_img = np.array([
        [u],
        [v],
        [1]
    ], dtype=np.float32)

    p_world = H @ p_img

    p_world /= p_world[2]

    x = p_world[0][0]
    y = p_world[1][0]

    return x, y
