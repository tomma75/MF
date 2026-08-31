"""온디바이스 실행 클라이언트 — PC/adb 없이 폰 안에서 직접 명령을 실행한다.

AdbClient와 완전히 같은 인터페이스라, agent 입장에서는 무엇을 쓰는지 몰라도 된다.
차이는 명령을 보내는 방식뿐이다.

    AdbClient    :  PC ──adb──> 폰      `adb shell input tap 100 200`
    LocalShellClient : 폰 안에서 직접    `input tap 100 200`

권한:
    screencap / input / uiautomator / pm 은 전부 shell 권한(uid 2000)을 요구한다.
    루팅 없이 이 권한을 얻는 방법이 Shizuku + rish 이며, 안드로이드 11+ 에서는
    무선 디버깅으로 폰 자체에서 활성화할 수 있어 PC가 전혀 필요 없다.
    (README_ONDEVICE.md 참고)

    - rish 셸 안에서 파이썬을 실행한 경우: 프로세스가 이미 uid 2000 → 직접 실행
    - 일반 Termux 셸에서 실행한 경우: 명령마다 rish를 경유 (rish_path 지정)
"""

import base64
import os
import shlex
import subprocess

# 시스템 바이너리 위치. Termux PATH에 없을 수 있어 명시적으로 붙인다.
_SYSTEM_PATH = "/system/bin:/system/xbin"

# uiautomator dump는 /dev/tty가 tty가 아닐 때 실패하므로 파일로 받아 읽는다.
_UIDUMP_TMP = "/data/local/tmp/hoicho_dump.xml"


class LocalShellClient:
    """폰 내부에서 실행되는 기기 조작 클라이언트."""

    def __init__(self, rish_path=None):
        self.rish_path = rish_path
        self.device_id = None  # 인터페이스 호환용 (온디바이스는 자기 자신)
        self._env = dict(os.environ)
        self._env["PATH"] = self._env.get("PATH", "") + ":" + _SYSTEM_PATH

    # ---- 실행 기반 ----

    def _exec(self, command, timeout):
        """셸 명령 문자열을 실행한다. rish_path가 있으면 그것을 경유한다."""
        if self.rish_path:
            argv = [self.rish_path, "-c", command]
        else:
            argv = ["/system/bin/sh", "-c", command]
        return subprocess.run(argv, capture_output=True, timeout=timeout, env=self._env)

    def run(self, args, timeout=15):
        """AdbClient.run과 같은 인자를 받아 adb 접두사를 걷어내고 로컬 실행한다."""
        args = list(args)
        if args and args[0] in ("shell", "exec-out"):
            args = args[1:]
        elif args and args[0] == "install":
            args = ["pm", "install"] + args[1:]

        if len(args) == 1:
            command = args[0]  # shell("wm size") 처럼 이미 문자열인 경우
        else:
            command = " ".join(shlex.quote(a) for a in args)

        # uiautomator dump: /dev/tty 대신 파일 경유로 바꿔 stdout에 실어 준다.
        if command.startswith("uiautomator dump"):
            command = (f"uiautomator dump {_UIDUMP_TMP} >/dev/null 2>&1 "
                       f"&& cat {_UIDUMP_TMP}")

        return self._exec(command, timeout)

    def shell(self, command, timeout=15):
        return self.run([command], timeout=timeout)

    # ---- AdbClient와 동일한 조작 API ----

    def screenshot(self):
        """화면을 캡처해 BGR ndarray로 반환. 실패 시 None."""
        import cv2
        import numpy as np

        result = self.run(["screencap", "-p"], timeout=30)
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
        """한글 입력은 ADBKeyboard IME의 base64 브로드캐스트를 사용한다."""
        if text.isascii():
            escaped = text.replace(" ", "%s")
            self.shell(f"input text {escaped}")
            return
        b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
        self.shell(f"am broadcast -a ADB_INPUT_B64 --es msg {b64}")

    def enable_adb_keyboard(self):
        self.shell("ime enable com.android.adbkeyboard/.AdbIME")
        self.shell("ime set com.android.adbkeyboard/.AdbIME")
