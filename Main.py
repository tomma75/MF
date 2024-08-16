import os
import subprocess
import time
import cv2
import numpy as np
from PIL import Image
import keyboard 
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt5.QtCore import QThread, pyqtSignal

class ADBController:
    def __init__(self, adb_path, device_id = None):
        self.adb_path = adb_path
        self.device_id = device_id

    def start_adb_process(self):
        adb_command = [self.adb_path]
        if self.device_id:
            adb_command += ["-s", self.device_id]
        adb_command += ["shell"]
        self.adb_process = subprocess.Popen(adb_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        print("연결완료")

    def capture_screenshot(self):
        if self.adb_process is None:
            raise Exception("ADB process not started")

        self.adb_process.stdin.write(b"screencap -p\n")
        self.adb_process.stdin.flush()

        screenshot_data = b''
        while True:
            chunk = os.read(self.adb_process.stdout.fileno(), 8192)
            if not chunk:
                print("is not chunk")
                break
            screenshot_data += chunk
            if b'IEND\xaeB`\x82' in screenshot_data:
                print("finished chunk")
                break

        screenshot_data = screenshot_data.replace(b'\r\n', b'\n')
        if not screenshot_data:
            print("do not find screenshot_data")
            return None

        image = cv2.imdecode(np.frombuffer(screenshot_data, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            print("do not find screenshot_data2")
            return None

        return image

    def extract_and_save_subimages(self, image):
        upper_image = image[300:1400, :]
        lower_image = image[1400:2230, :]
        return upper_image, lower_image

    def find_pattern(self, image):
        if not isinstance(image, np.ndarray):
            raise ValueError("Must get numpy")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        blurred = cv2.GaussianBlur(gray, (15, 15), 0)

        circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, dp=1.2, minDist=100,
                                param1=50, param2=30, minRadius=20, maxRadius=50)
        Re_match = []
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            for (x, y, r) in circles:
                cv2.circle(image, (x, y), r, (0, 255, 0), 4)
                
                center_color_bgr = image[y, x]
                center_color_rgb = center_color_bgr[::-1]  
                Re_match.append(((x, y), center_color_rgb.tolist()))
                print(f"coordinate: ({x}, {y}), color: {center_color_rgb}")

            groups = self.group_elements(Re_match)
            sorted_result = self.sort_groups(groups)

        else:
            print("Couldn't find anything")
            return None
        
        return sorted_result

    def group_elements(self, elements):
        elements.sort(key=lambda x: x[0][1])
        groups = []
        current_group = [elements[0]]
        for item in elements[1:]:
            if abs(item[0][1] - current_group[-1][0][1]) <= 20:
                current_group.append(item)
            else:
                groups.append(current_group)
                current_group = [item]
        groups.append(current_group)
        return groups

    def sort_groups(self, groups):
        groups.sort(key=lambda g: sum(item[0][1] for item in g) / len(g))
        sorted_result = []
        for group in groups:
            sorted_result.extend(sorted(group, key=lambda x: x[0][0]))
        return sorted_result

    def adjust_coordinates(self, touch_points, section_start_y):
        adjusted_points = [((x, y + section_start_y), color) for (x, y), color in touch_points]
        return adjusted_points

    def match_coordinates(self, upper_touch_points, lower_touch_points):
        new_touch_range = []
        lower_touch_dict = {tuple(color): (x, y) for (x, y), color in lower_touch_points}

        for (x, y), color in upper_touch_points:
            matched_coord = lower_touch_dict.get(tuple(color))
            if matched_coord:
                new_touch_range.append(matched_coord)
            else:
                new_touch_range.append('Nan')
        return new_touch_range

    def remove_consecutive_nans(self, touch_range):
        cleaned_touch_range = []
        previous_value = None
        
        for value in touch_range:
            if value == 'Nan':
                if previous_value != 'Nan':
                    cleaned_touch_range.append(value)
            else:
                cleaned_touch_range.append(value)
            previous_value = value

        return cleaned_touch_range

    def watch_and_input(self, touch_range):
        while touch_range:
            if 'Nan' in touch_range:
                nan_index = touch_range.index('Nan')
                coords_to_tap = touch_range[:nan_index]

                # 'Nan' 앞의 좌표들을 터치
                for coord in coords_to_tap:
                    if coord != 'Nan':
                        x, y = coord
                        self.adb_tap(x, y)
                        time.sleep(0.1)

                # 'Nan' 이후의 리스트로 갱신
                touch_range = touch_range[nan_index + 1:]

                # 'left ctrl' 키가 눌릴 때까지 대기
                while not keyboard.is_pressed('left ctrl'):
                    time.sleep(0.05)

                # 'left ctrl' 키가 눌렸을 때 대기 해제
                while keyboard.is_pressed('left ctrl'):
                    time.sleep(0.05)

            else:
                # 'Nan'이 없을 경우 남은 좌표들을 터치하고 종료
                for coord in touch_range:
                    if coord != 'Nan':
                        x, y = coord
                        self.adb_tap(x, y)
                return True

    def adb_tap(self, x, y):
        if self.adb_process is None:
            raise Exception("ADB process not started")
        tap_command = f"input tap {x} {y}\n"
        self.adb_process.stdin.write(tap_command.encode())
        self.adb_process.stdin.flush()

    def remove_consecutive_nans(self, touch_range):
        cleaned_touch_range = []
        previous_value = None
        
        for value in touch_range:
            if value == 'Nan':
                if previous_value != 'Nan':
                    cleaned_touch_range.append(value)
            else:
                cleaned_touch_range.append(value)
            previous_value = value

        return cleaned_touch_range

    def main(self):
        self.start_adb_process()
        while True:
            image = self.capture_screenshot()
            if image is None:
                continue
            upper_image, lower_image = self.extract_and_save_subimages(image)
            
            upper_touch_points = self.find_pattern(upper_image)
            if upper_touch_points is None:
                continue
            lower_touch_points = self.find_pattern(lower_image)
            if lower_touch_points is None:
                continue

            upper_adjusted = self.adjust_coordinates(upper_touch_points, 300)
            lower_adjusted = self.adjust_coordinates(lower_touch_points, 1400)
            # Match coordinates
            new_touch_range = self.match_coordinates(upper_adjusted, lower_adjusted)
            cleaned_touch_range = self.remove_consecutive_nans(new_touch_range)

            print(cleaned_touch_range)
            if self.watch_and_input(cleaned_touch_range):
                continue
            
class AppDemo(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle('ADB Controller')
        self.setGeometry(100, 100, 300, 150)
        
        layout = QVBoxLayout()

        self.label = QLabel('Enter Device ID:')
        layout.addWidget(self.label)

        self.device_id_input = QLineEdit(self)
        layout.addWidget(self.device_id_input)

        self.run_button = QPushButton('Run', self)
        self.run_button.clicked.connect(self.run_main)
        layout.addWidget(self.run_button)

        self.setLayout(layout)

    def run_main(self):
        device_id = self.device_id_input.text()
        self.controller.device_id = device_id
        self.controller.main()
        
class ADBControllerThread(QThread):
    update_signal = pyqtSignal(str)

    def __init__(self, controller):
        super().__init__()
        self.controller = controller

    def run(self):
        self.controller.main()

class AppDemo(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle('ADB Controller')
        self.setGeometry(100, 100, 300, 150)
        
        layout = QVBoxLayout()

        self.label = QLabel('Enter Device ID:')
        layout.addWidget(self.label)

        self.device_id_input = QLineEdit(self)
        layout.addWidget(self.device_id_input)

        try:
            with open('./device_id.txt', 'r') as file:
                device_id = file.read().strip()
                self.device_id_input.setText(device_id)
        except FileNotFoundError:
            print("device_id.txt 파일을 찾을 수 없습니다.")

        self.run_button = QPushButton('Run', self)
        self.run_button.clicked.connect(self.run_main)
        layout.addWidget(self.run_button)

        self.setLayout(layout)

    def run_main(self):
        device_id = self.device_id_input.text()
        self.controller.device_id = device_id

        self.thread = ADBControllerThread(self.controller)
        self.thread.update_signal.connect(self.update_status)
        self.thread.start()

    def update_status(self, message):
        # 상태 업데이트 시 사용할 수 있습니다.
        print(message)

if __name__ == "__main__":
    adb_path = r".\platform-tools-latest-windows\platform-tools\adb.exe"
    device_id = None  # 초기에는 device_id가 없음
    controller = ADBController(adb_path, device_id)

    app = QApplication(sys.argv)
    demo = AppDemo(controller)
    demo.show()
    sys.exit(app.exec_())