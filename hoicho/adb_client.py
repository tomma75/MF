import base64
import subprocess


class AdbClient:
    """adb 명령 단위 실행 클라이언트.

    기존 Main.py의 persistent shell 방식과 달리 명령마다 프로세스를 새로 띄운다.
    screencap은 exec-out을 쓰므로 \r\n 치환 같은 바이너리 보정이 필요 없다.
    """

    def __init__(self, adb_path, device_id=None):
        self.adb_path = adb_path
        self.device_id = device_id

    def _base_cmd(self):
        cmd = [self.adb_path]
        if self.device_id:
            cmd += ["-s", self.device_id]
        return cmd

    def run(self, args, timeout=15):
        result = subprocess.run(
            self._base_cmd() + args,
            capture_output=True,
            timeout=timeout,
        )
        return result

    def shell(self, command, timeout=15):
        return self.run(["shell", command], timeout=timeout)

    def screenshot(self):
        """화면을 캡처해 BGR ndarray로 반환. 실패 시 None.

        OCR 폴백 경로에서만 쓰이므로 cv2/numpy는 여기서 지연 임포트한다.
        """
        import cv2
        import numpy as np

        result = self.run(["exec-out", "screencap", "-p"], timeout=30)
        if result.returncode != 0 or not result.stdout:
            print("스크린샷 실패:", result.stderr.decode(errors="replace").strip())
            return None
        image = cv2.imdecode(np.frombuffer(result.stdout, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            print("스크린샷 디코딩 실패")
        return image

    def tap(self, x, y):
        self.shell(f"input tap {int(x)} {int(y)}")

    def swipe(self, x1, y1, x2, y2, duration_ms=300):
        self.shell(f"input swipe {int(x1)} {int(y1)} {int(x2)} {int(y2)} {int(duration_ms)}")

    def key(self, keycode):
        self.shell(f"input keyevent {int(keycode)}")

    def input_text(self, text):
        """한글 입력은 ADBKeyboard IME의 base64 브로드캐스트를 사용한다.

        기기에 ADBKeyboard.apk가 설치되어 있고 IME로 활성화되어 있어야 한다.
        (README_HOICHO.md 참고)
        """
        if text.isascii():
            escaped = text.replace(" ", "%s")
            self.shell(f"input text {escaped}")
            return
        b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
        self.shell(f"am broadcast -a ADB_INPUT_B64 --es msg {b64}")

    def enable_adb_keyboard(self):
        self.shell("ime enable com.android.adbkeyboard/.AdbIME")
        self.shell("ime set com.android.adbkeyboard/.AdbIME")
