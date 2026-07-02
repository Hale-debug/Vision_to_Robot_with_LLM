import time
import cv2
import numpy as np

from config import *


class VisionDetector:

    def __init__(self, camera_id=None):

        self.camera_ok = False
        cam_id = camera_id if camera_id is not None else CAMERA_ID

        # 在 Windows 上强制使用 DSHOW 后端，避免 MSMF 抓帧错误
        try:
            self.cap = cv2.VideoCapture(cam_id, cv2.CAP_DSHOW)
        except Exception as e:
            print(f"摄像头初始化异常: {e}")
            self.cap = None
            self.camera_ok = False
            return

        if self.cap is None or not self.cap.isOpened():
            print(f"警告: 摄像头 {cam_id} 无法打开，尝试摄像头 0 ...")
            try:
                self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            except Exception:
                self.cap = None

        if self.cap is None or not self.cap.isOpened():
            print("错误: 没有可用的摄像头")
            self.camera_ok = False
            return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

        # 验证摄像头真正可读
        ret, _ = self.cap.read()
        if ret:
            self.camera_ok = True
            print(f"摄像头 {CAMERA_ID} 初始化成功")
        else:
            print(f"警告: 摄像头 {CAMERA_ID} 已打开但无法读取帧")

        self.color_ranges = {
            'green': [
                (np.array([40, 80, 80]), np.array([80, 255, 255])),
            ],
            'orange': [
                (np.array([5, 120, 200]), np.array([8, 160, 255])),
            ],
            'purple': [
                (np.array([120, 125, 60]), np.array([140, 160, 255])),
            ],
            'pink': [
                (np.array([150, 110, 120]), np.array([175, 145, 255])),
            ],
            'blue': [
                (np.array([85, 75, 0]), np.array([125, 115, 255])),
            ],
            'yellow': [
                (np.array([0, 60, 0]), np.array([40, 145, 255])),
            ],
            'red': [
                (np.array([155, 155, 0]), np.array([195, 195, 255])),
            ],
        }

        self.box_color_ranges = {
            'red': [
                (np.array([0, 100, 100]), np.array([10, 255, 255])),
                (np.array([160, 100, 100]), np.array([180, 255, 255])),
            ],
            'blue': [
                (np.array([80, 180, 0]), np.array([140, 240, 255])),
            ],
            'green': [
                (np.array([40, 80, 80]), np.array([80, 255, 255])),
            ],
        }

    def check_camera(self):
        """验证摄像头是否可读，更新 camera_ok 标志"""
        if self.cap is None or not self.cap.isOpened():
            self.camera_ok = False
            return False

        try:
            ret, _ = self.cap.read()
            self.camera_ok = ret
            return ret
        except Exception:
            self.camera_ok = False
            return False

    def reconnect_camera(self):
        """尝试重新连接摄像头，最多 3 次"""
        self.release()
        cam_id = CAMERA_ID

        for attempt in range(3):
            try:
                self.cap = cv2.VideoCapture(cam_id, cv2.CAP_DSHOW)
                if not self.cap.isOpened():
                    if attempt < 2:
                        print(f"摄像头重连失败 (尝试 {attempt+1}/3)，重试...")
                        time.sleep(1)
                        continue
                    self.camera_ok = False
                    return False

                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

                ret, _ = self.cap.read()
                if ret:
                    self.camera_ok = True
                    print("摄像头重连成功")
                    return True

            except Exception as e:
                print(f"摄像头重连异常 (尝试 {attempt+1}/3): {e}")

        self.camera_ok = False
        print("摄像头重连失败 (3次重试已用尽)")
        return False

    def detect_object_by_color(self, color, timeout=10.0):

        color = color.lower()

        if not self.camera_ok:
            print(f"摄像头不可用，无法检测{color}色物块")
            return None

        if color not in self.color_ranges:
            raise ValueError(f'暂不支持识别颜色: {color}')

        ranges = self.color_ranges[color]

        start_time = time.time()

        while True:
            # 超时检查
            if time.time() - start_time > timeout:
                print(f"物块检测超时 ({timeout}s)，未找到{color}色物块")
                return None

            if not self.camera_ok:
                print("摄像头已断开，停止物块检测")
                return None

            try:
                ret, frame = self.cap.read()
            except Exception as e:
                print(f"摄像头读取异常: {e}")
                self.camera_ok = False
                return None

            if not ret:
                continue

            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            mask = None

            for lower, upper in ranges:
                current_mask = cv2.inRange(hsv, lower, upper)
                mask = current_mask if mask is None else mask + current_mask

            contours, _ = cv2.findContours(
                mask,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )

            if len(contours) > 0:

                largest = max(contours, key=cv2.contourArea)

                area = cv2.contourArea(largest)

                if area > 100 and area < 500:

                    x, y, w, h = cv2.boundingRect(largest)

                    cx = x + w // 2
                    cy = y + h // 2

                    cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)
                    cv2.putText(
                        frame,
                        color,
                        (x, max(20, y - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 255, 0),
                        2
                    )

                    cv2.imshow('Detection', frame)

                    key = cv2.waitKey(1)

                    if key == ord('q'):
                        break

                    return cx, cy

            cv2.imshow('Detection', frame)

            key = cv2.waitKey(1)

            if key == ord('q'):
                break

        return None

    def _fill_mask_holes(self, mask):

        h, w = mask.shape[:2]
        flood_mask = np.zeros((h + 2, w + 2), np.uint8)
        filled = mask.copy()

        cv2.floodFill(filled, flood_mask, (0, 0), 255)

        holes = cv2.bitwise_not(filled)

        return cv2.bitwise_or(mask, holes)

    def detect_box_by_color(self, color):

        color = color.lower()

        if not self.camera_ok:
            print(f"摄像头不可用，无法检测{color}色盒子")
            return None

        if color not in self.box_color_ranges:
            raise ValueError(f'暂不支持识别盒子颜色: {color}')

        ranges = self.box_color_ranges[color]

        try:
            ret, frame = self.cap.read()
        except Exception as e:
            print(f"摄像头读取异常: {e}")
            self.camera_ok = False
            return None

        if not ret:
            print('盒子检测拍照失败')
            return None

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        mask = None

        for lower, upper in ranges:
            current_mask = cv2.inRange(hsv, lower, upper)
            mask = current_mask if mask is None else cv2.bitwise_or(mask, current_mask)

        close_kernel = np.ones((11, 11), np.uint8)
        open_kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_kernel, iterations=2)
        mask = self._fill_mask_holes(mask)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, open_kernel)

        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        valid_contours = []
        contour_areas = []

        for contour in contours:
            area = cv2.contourArea(contour)
            contour_areas.append(area)

            if BOX_AREA_MIN < area < BOX_AREA_MAX:
                valid_contours.append(contour)

        sorted_areas = sorted(contour_areas, reverse=True)[:5]
        print(
            f'盒子拍照检测 color={color}, '
            f'contours={len(contours)}, '
            f'valid={len(valid_contours)}, '
            f'areas={sorted_areas}, '
            f'area_range=({BOX_AREA_MIN}, {BOX_AREA_MAX})'
        )

        if len(valid_contours) == 0:
            cv2.imshow('Detection', frame)
            cv2.imshow('Box Mask', mask)
            cv2.waitKey(1)
            return None

        largest = max(valid_contours, key=cv2.contourArea)

        area = cv2.contourArea(largest)

        x, y, w, h = cv2.boundingRect(largest)

        cx = x + w // 2
        cy = y + h // 2

        cv2.circle(frame, (cx, cy), 5, (255, 0, 0), -1)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
        cv2.putText(
            frame,
            f'box:{color} area:{int(area)}',
            (x, max(20, y - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 0, 0),
            2
        )

        cv2.imshow('Detection', frame)
        cv2.imshow('Box Mask', mask)
        cv2.waitKey(1)

        return cx, cy

    def release(self):

        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
        cv2.destroyAllWindows()
        self.camera_ok = False
