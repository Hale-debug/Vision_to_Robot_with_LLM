import cv2
import numpy as np

# 摄像头参数
CAMERA_ID = 1

FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# 区域大小
# 500左右面积 -> 22x22 ≈ 484
ROI_SIZE = 11

# 全局变量
frame_global = None


# 鼠标点击回调
def mouse_callback(event, x, y, flags, param):

    global frame_global

    if event != cv2.EVENT_LBUTTONDOWN:
        return

    if frame_global is None:
        return

    frame = frame_global.copy()

    h, w = frame.shape[:2]

    half = ROI_SIZE // 2

    # =====================================
    # ROI范围
    # =====================================
    x1 = max(0, x - half)
    y1 = max(0, y - half)

    x2 = min(w, x + half)
    y2 = min(h, y + half)

    # =====================================
    # 提取区域
    # =====================================
    roi = frame[y1:y2, x1:x2]

    if roi.size == 0:
        return

    # =====================================
    # BGR平均值
    # =====================================
    b_mean = np.mean(roi[:, :, 0])
    g_mean = np.mean(roi[:, :, 1])
    r_mean = np.mean(roi[:, :, 2])

    # =====================================
    # HSV平均值
    # =====================================
    hsv_roi = cv2.cvtColor(
        roi,
        cv2.COLOR_BGR2HSV
    )

    h_mean = np.mean(hsv_roi[:, :, 0])
    s_mean = np.mean(hsv_roi[:, :, 1])
    v_mean = np.mean(hsv_roi[:, :, 2])

    # =====================================
    # 输出信息
    # =====================================
    print()
    print("====================================")
    print(f"点击坐标: ({x}, {y})")
    print(f"ROI区域: {ROI_SIZE} x {ROI_SIZE}")
    print()

    print("BGR 平均值:")
    print(
        f"B={b_mean:.1f}, "
        f"G={g_mean:.1f}, "
        f"R={r_mean:.1f}"
    )

    print()

    print("HSV 平均值:")
    print(
        f"H={h_mean:.1f}, "
        f"S={s_mean:.1f}, "
        f"V={v_mean:.1f}"
    )

    print("====================================")

    # =====================================
    # 可视化ROI
    # =====================================
    cv2.rectangle(
        frame,
        (x1, y1),
        (x2, y2),
        (0, 255, 0),
        2
    )

    cv2.circle(
        frame,
        (x, y),
        4,
        (0, 0, 255),
        -1
    )

    # 显示文字
    text = (
        f"H:{int(h_mean)} "
        f"S:{int(s_mean)} "
        f"V:{int(v_mean)}"
    )

    cv2.putText(
        frame,
        text,
        (x + 10, y - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 255, 0),
        2
    )

    cv2.imshow("Color Picker", frame)


# =========================================
# 主函数
# =========================================
def main():

    global frame_global

    cap = cv2.VideoCapture(CAMERA_ID)

    cap.set(
        cv2.CAP_PROP_FRAME_WIDTH,
        FRAME_WIDTH
    )

    cap.set(
        cv2.CAP_PROP_FRAME_HEIGHT,
        FRAME_HEIGHT
    )

    cv2.namedWindow("Color Picker")

    cv2.setMouseCallback(
        "Color Picker",
        mouse_callback
    )

    print()
    print("====================================")
    print("鼠标左键点击目标区域")
    print("程序会输出该区域平均RGB/HSV")
    print("按 q 退出")
    print("====================================")

    while True:

        ret, frame = cap.read()

        if not ret:
            continue

        frame_global = frame.copy()

        cv2.imshow(
            "Color Picker",
            frame
        )

        key = cv2.waitKey(1)

        if key == ord('q'):
            break

    cap.release()

    cv2.destroyAllWindows()


# =========================================
# 入口
# =========================================
if __name__ == "__main__":

    main()