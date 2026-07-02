from vision_detector import VisionDetector
from coordinate_transform import pixel_to_world
from grab_interface import GrabInterface
from llm_client import RobotTaskParser

from config import *


def main():

    command = input('请输入机械臂任务，例如：抓取绿色物块到红色盒子\n> ').strip()

    if not command:
        print('未输入任务指令')
        return

    parser = RobotTaskParser()

    try:
        task = parser.parse_grab_command(command)
    except Exception as e:
        print(f'大语言模型解析失败: {e}')
        return

    if task['action'] != 'grab':
        print(f"暂不支持该动作: {task['action']}")
        return

    color = task['color']
    box_color = task.get('box_color', 'unknown')

    if color == 'unknown':
        print('未能从指令中识别目标物块颜色')
        return

    if box_color == 'unknown':
        print('未能从指令中识别目标盒子颜色')
        return

    detector = VisionDetector()

    arm = GrabInterface()

    if not arm.connect():
        detector.release()
        return

    try:

        print(f'开始视觉识别，目标物块颜色: {color}')

        result = detector.detect_object_by_color(color)

        if result is None:
            print('未检测到目标物块')
            return

        px, py = result

        print(f'目标物块像素坐标: ({px}, {py})')

        x, y = pixel_to_world(px, py)

        z = 20

        print(f'物块机械臂坐标: ({x:.2f}, {y:.2f}, {z:.2f})')

        def detect_place_box():

            print(f'开始视觉识别，目标盒子颜色: {box_color}')

            box_result = detector.detect_box_by_color(box_color)

            if box_result is None:
                print('未检测到目标盒子')
                return None

            box_px, box_py = box_result

            print(f'目标盒子像素坐标: ({box_px}, {box_py})')

            box_x, box_y = pixel_to_world(box_px, box_py)
            box_z = BOX_HEIGHT

            print(f'盒子机械臂坐标: ({box_x:.2f}, {box_y:.2f}, {box_z:.2f})')

            return box_x, box_y, box_z

        arm.execute_grab(
            x,
            y,
            z,
            place_pos=detect_place_box
        )

    except Exception as e:
        print('运行错误:', e)

    finally:

        detector.release()
        arm.disconnect()


if __name__ == '__main__':
    main()
