import cv2
import numpy as np
import os

# ===============================
# 配置
# ===============================
IMAGE_PATH = "new_ref.jpg"  # 你拍的那一张棋盘格图
SAVE_PATH = "new_image_points_uv.npy"

assert os.path.exists(IMAGE_PATH), f"{IMAGE_PATH} not found"

# ===============================
# 全局变量
# ===============================
points_uv = []
img = cv2.imread(IMAGE_PATH)
vis = img.copy()

# ===============================
# 鼠标回调
# ===============================
def on_mouse(event, x, y, flags, param):
    global vis, points_uv

    if event == cv2.EVENT_LBUTTONDOWN:
        points_uv.append([x, y])

        # 画点
        cv2.circle(vis, (x, y), 5, (0, 0, 255), -1)
        cv2.putText(
            vis,
            str(len(points_uv) - 1),
            (x + 5, y - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1,
            cv2.LINE_AA
        )

        print(f"Point {len(points_uv)-1}: (u={x}, v={y})")

# ===============================
# 主程序
# ===============================
cv2.namedWindow("click points")
cv2.setMouseCallback("click points", on_mouse)

print("Left click: add point")
print("Press 'u' : undo last point")
print("Press 's' : save and exit")
print("Press 'q' : quit without saving")

while True:
    cv2.imshow("click points", vis)
    key = cv2.waitKey(20) & 0xFF

    if key == ord('u'):  # undo
        if len(points_uv) > 0:
            points_uv.pop()
            vis = img.copy()
            for i, (u, v) in enumerate(points_uv):
                cv2.circle(vis, (u, v), 5, (0, 0, 255), -1)
                cv2.putText(
                    vis,
                    str(i),
                    (u + 5, v - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    1,
                    cv2.LINE_AA
                )
            print("Undo last point")

    elif key == ord('s'):  # save
        if len(points_uv) < 4:
            print("Need at least 4 points to save")
            continue
        uv = np.array(points_uv, dtype=np.float32)
        np.save(SAVE_PATH, uv)
        print(f"Saved {len(uv)} points to {SAVE_PATH}")
        break

    elif key == ord('q'):  # quit
        print("Quit without saving")
        break

cv2.destroyAllWindows()
