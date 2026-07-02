import cv2

# =========================
# 摄像头ID
# =========================
CAMERA_ID = 1

# =========================
# 保存文件名
# =========================
SAVE_NAME = "new_ref.jpg"

# =========================
# 打开摄像头
# =========================
cap = cv2.VideoCapture(CAMERA_ID)

if not cap.isOpened():

    print("摄像头打开失败")
    exit()

print()
print("================================")
print("按 s 保存图片")
print("按 q 退出")
print("================================")
print()

while True:

    ret, frame = cap.read()

    if not ret:

        print("读取摄像头失败")
        break

    # 显示画面
    cv2.imshow(
        "Calibration Camera",
        frame
    )

    key = cv2.waitKey(1) & 0xFF

    # 保存图片
    if key == ord('s'):

        cv2.imwrite(
            SAVE_NAME,
            frame
        )

        print()
        print(f"图片已保存: {SAVE_NAME}")
        print()

    # 退出
    elif key == ord('q'):

        break

# =========================
# 释放资源
# =========================
cap.release()

cv2.destroyAllWindows()