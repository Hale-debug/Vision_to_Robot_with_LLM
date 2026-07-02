import os

# =========================
# 标定目录
# =========================
CALIB_DIR = "calibration"

# =========================
# 需要删除的文件
# =========================
files_to_delete = [

    "new_ref.jpg",
    "new_image_points_uv.npy",
    "world_points_xy.npy",
    "homography.npy",

]

print()
print("================================")
print("开始清理标定文件")
print("================================")
print()

for filename in files_to_delete:

    path = os.path.join(
        CALIB_DIR,
        filename
    )

    if os.path.exists(path):

        try:

            os.remove(path)

            print(f"[删除成功] {path}")

        except Exception as e:

            print(f"[删除失败] {path}")
            print(e)

    else:

        print(f"[不存在] {path}")

print()
print("================================")
print("标定目录已清理完成")
print("================================")