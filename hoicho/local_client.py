"""온디바이스 실행 클라이언트 — PC/adb 없이 폰 안에서 직접 명령을 실행한다.

AdbClient와 완전히 같은 인터페이스라, agent 입장에서는 무엇을 쓰는지 몰라도 된다.
차이는 명령을 보내는 방식뿐이다.

    AdbClient        :  PC ──adb──> 폰    `adb shell input tap 100 200`
    LocalShellClient :  폰 안에서 직접     `input tap 100 200`

권한:
    screencap / input / uiautomator / pm 은 전부 shell 권한(uid 2000)을 요구한다.
    루팅 없이 이 권한을 얻는 방법이 Shizuku + rish 이며, 안드로이드 11+ 에서는
    무선 디버깅으로 폰 자체에서 활성화할 수 있어 PC가 전혀 필요 없다.
    (README_ONDEVICE.md 참고)

실행 구조:
    파이썬은 일반 Termux 권한(uid 10xxx)으로 돌고, 기기 조작 명령만 rish를 거쳐
    shell 권한으로 실행된다. rish 셸 안에서 파이썬을 띄우는 것은 불가능하다 —
    SELinux가 shell 도메인에서 앱 데이터 영역(Termux의 python)의 실행을 막는다.
"""

import base64
import os
import shlex
import subprocess

# 시스템 바이너리 위치. 원격 셸의 기본 PATH에는 이미 들어 있지만,
# rish를 안 거치는 경우(이미 shell 권한)를 위해 로컬 env에도 보강한다.
_SYSTEM_PATH = "/system/bin:/system/xbin"

# uiautomator dump는 /dev/tty가 tty가 아닐 때 실패하므로 파일로 받아 읽는다.
# 인스턴스가 겹쳐도 충돌하지 않도록 pid를 붙인다.
_UIDUMP_TMP = "/data/local/tmp/hoicho_dump_%d.xml" % os.getpid()

# APK 설치 경유지. shell uid가 읽을 수 있는 곳이어야 한다.
_APK_TMP = "/data/local/tmp/hoicho_install_%d.apk" % os.getpid()

_PNG_MAGIC = b"\x89PNG"


class LocalShellClient:
    """폰 내부에서 실행되는 기기 조작 클라이언트."""

    def __init__(self, rish_path=None):
        self.rish_path = rish_path
        self.device_id = None  # 인터페이스 호환용 (온디바이스는 자기 자신)
        self._env = dict(os.environ)
        self._env["PATH"] = self._env.get("PATH", "") + ":" + _SYSTEM_PATH
        # screencap 출력이 pty를 거치며 깨지는 구현이 있어, 한 번 확인 후 경로를 고정한다.
        self._screencap_b64 = None
        self._warned_no_cv2 = False

    # ---- 실행 기반 ----

    def _exec(self, command, timeout, stdin=None):
        """셸 명령 문자열을 실행한다. rish_path가 있으면 그것을 경유한다."""
        if self.rish_path:
            argv = [self.rish_path, "-c", command]
        else:
            if not os.path.exists("/system/bin/sh"):
                raise RuntimeError(
                    "온디바이스 모드는 안드로이드에서만 동작합니다. "
                    "PC에서는 --mode adb 를 쓰세요.")
            argv = ["/system/bin/sh", "-c", command]
        return subprocess.run(
            argv, input=stdin, capture_output=True, timeout=timeout, env=self._env)

    def run(self, args, timeout=15):
        """AdbClient.run과 같은 인자를 받아 adb 접두사를 걷어내고 로컬 실행한다."""
        args = list(args)
        if args and args[0] in ("shell", "exec-out"):
            args = args[1:]

        if len(args) == 1:
            command = args[0]  # shell("wm size") 처럼 이미 문자열인 경우
        else:
            command = " ".join(shlex.quote(a) for a in args)

        # uiautomator dump: /dev/tty 대신 파일 경유로 바꿔 stdout에 실어 준다.
        if command.startswith("uiautomator dump"):
            command = (f"uiautomator dump {_UIDUMP_TMP} >/dev/null 2>&1 "
                       f"&& cat {_UIDUMP_TMP}; rm -f {_UIDUMP_TMP}")

        return self._exec(command, timeout)

    def shell(self, command, timeout=15):
        return self.run([command], timeout=timeout)

    # ---- AdbClient와 동일한 조작 API ----

    def install_apk(self, apk_path, timeout=120):
        """APK를 설치한다.

        Termux의 홈은 mode 700이라 shell uid(uid 2000)가 traverse조차 못 한다.
        따라서 `pm install <termux경로>`는 반드시 실패한다. 파일 내용을 stdin으로
        흘려 /data/local/tmp에 옮긴 뒤 거기서 설치한다.
        """
        try:
            with open(apk_path, "rb") as f:
                data = f.read()
        except OSError as e:
            print(f"APK 읽기 실패: {e}")
            return subprocess.CompletedProcess([], 1, b"", str(e).encode())

        copy = self._exec(f"cat > {_APK_TMP}", timeout, stdin=data)
        if copy.returncode != 0:
            print("APK 복사 실패:", copy.stderr.decode(errors="replace").strip())
            return copy
        result = self._exec(f"pm install -r {_APK_TMP}", timeout)
        self._exec(f"rm -f {_APK_TMP}", 10)
        return result

    def screenshot(self):
        """화면을 캡처해 BGR ndarray로 반환. 실패 시 None."""
        try:
            import cv2
            import numpy as np
        except ImportError:
            if not self._warned_no_cv2:
                print("OCR 폴백에 필요한 패키지가 없습니다. 설치:\n"
                      "  pkg install python-numpy opencv-python")
                self._warned_no_cv2 = True
            return None

        raw = self._capture_png()
        if raw is None:
            return None
        image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            print("스크린샷 디코딩 실패")
        return image

    def _capture_png(self):
        """screencap PNG 바이트를 얻는다. 경로가 바이너리를 깨면 base64로 전환한다."""
        if self._screencap_b64 is None:
            result = self._exec("screencap -p", 30)
            if result.returncode == 0 and result.stdout.startswith(_PNG_MAGIC):
                self._screencap_b64 = False
                return result.stdout
            # raw가 깨졌거나 실패 — base64 경로로 확정하고 재시도
            self._screencap_b64 = True

        result = self._exec("screencap -p | base64", 30)
        if result.returncode != 0 or not result.stdout:
            print("스크린샷 실패:", result.stderr.decode(errors="replace").strip())
            return None
        try:
            return base64.b64decode(b"".join(result.stdout.split()))
        except Exception as e:
            print(f"스크린샷 base64 디코딩 실패: {e}")
            return None

    def tap(self, x, y):
        self.shell(f"input tap {int(x)} {int(y)}")

    def swipe(self, x1, y1, x2, y2, duration_ms=300):
        self.shell(f"input swipe {int(x1)} {int(y1)} {int(x2)} {int(y2)} {int(duration_ms)}")

    def key(self, keycode):
        self.shell(f"input keyevent {int(keycode)}")

    def input_text(self, text):
        """텍스트 입력. 셸을 거치므로 인용 처리가 필수다.

        한글이거나 특수문자가 섞이면 ADBKeyboard IME의 base64 브로드캐스트를 쓴다.
        (base64 문자셋은 셸에서 전부 안전하다.)
        """
        if _is_shell_safe(text):
            self.shell(f"input text {shlex.quote(text.replace(' ', '%s'))}")
            return
        b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
        self.shell(f"am broadcast -a ADB_INPUT_B64 --es msg {b64}")

    def enable_adb_keyboard(self):
        self.shell("ime enable com.android.adbkeyboard/.AdbIME")
        self.shell("ime set com.android.adbkeyboard/.AdbIME")


def _is_shell_safe(text):
    """`input text`로 그냥 보내도 되는, 영숫자와 공백뿐인 문자열인지."""
    return text.isascii() and text.replace(" ", "").isalnum()
