"""제로 세팅 부트스트랩: 기기·해상도·키보드·OCR을 전부 자동으로 준비한다."""

import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

ADBKEYBOARD_APK_URL = "https://github.com/senzhk/ADBKeyBoard/raw/master/ADBKeyboard.apk"
ADBKEYBOARD_IME = "com.android.adbkeyboard/.AdbIME"

# 좌표 기준 해상도 (이 기준으로 정의된 좌표를 실제 해상도로 스케일링)
BASE_WIDTH, BASE_HEIGHT = 1080, 2400


def find_adb(configured_path=None):
    """설정 경로 → 저장소 동봉 adb → PATH 순으로 adb를 찾는다."""
    candidates = []
    if configured_path:
        candidates.append(configured_path)
    candidates.append(os.path.join(
        "platform-tools-latest-windows", "platform-tools",
        "adb.exe" if os.name == "nt" else "adb"))
    for path in candidates:
        if os.path.exists(path):
            return path
    on_path = shutil.which("adb")
    if on_path:
        return on_path
    raise RuntimeError("adb를 찾을 수 없습니다. platform-tools 폴더를 확인하세요.")


def wait_for_device(adb_path, poll_sec=3):
    """연결된 첫 기기를 기다렸다가 device id를 반환한다. 사용자는 폰만 꽂으면 된다."""
    subprocess.run([adb_path, "start-server"], capture_output=True)
    announced = False
    while True:
        result = subprocess.run([adb_path, "devices"], capture_output=True, text=True)
        devices = [
            line.split()[0]
            for line in result.stdout.splitlines()[1:]
            if line.strip() and line.split()[-1] == "device"
        ]
        if devices:
            print(f"기기 연결됨: {devices[0]}")
            return devices[0]
        if not announced:
            print("기기 대기 중... USB 연결 또는 무선 디버깅을 켜 주세요.")
            announced = True
        time.sleep(poll_sec)


def get_resolution(adb):
    """실제 화면 해상도 (width, height)를 감지한다."""
    result = adb.shell("wm size")
    text = result.stdout.decode(errors="replace")
    # Override size가 있으면 그것이 실제 표시 해상도
    matches = re.findall(r"(\d+)x(\d+)", text)
    if not matches:
        print("해상도 감지 실패, 기준 해상도로 가정")
        return BASE_WIDTH, BASE_HEIGHT
    w, h = map(int, matches[-1])
    if w > h:  # 가로 값이 크면 세로 모드 기준으로 뒤집기
        w, h = h, w
    print(f"해상도: {w}x{h}")
    return w, h


def scale_config_coords(config, width, height):
    """기준 해상도(1080x2400)로 정의된 좌표/영역을 실제 해상도로 변환한다."""
    sx, sy = width / BASE_WIDTH, height / BASE_HEIGHT
    x1, y1, x2, y2 = config["chat_region"]
    config["chat_region"] = [int(x1 * sx), int(y1 * sy), int(x2 * sx), int(y2 * sy)]
    for key in ("chat_input", "send_button"):
        point = config[key]
        config[key] = {"x": int(point["x"] * sx), "y": int(point["y"] * sy)}
    return config


def ensure_adb_keyboard(adb, cache_dir):
    """한글 입력용 ADBKeyboard가 없으면 내려받아 설치하고 IME로 활성화한다."""
    result = adb.shell("ime list -s")
    imes = result.stdout.decode(errors="replace")
    if "adbkeyboard" not in imes.lower():
        apk_path = os.path.join(cache_dir, "ADBKeyboard.apk")
        if not os.path.exists(apk_path):
            print("ADBKeyboard.apk 다운로드 중...")
            try:
                os.makedirs(cache_dir, exist_ok=True)
                urllib.request.urlretrieve(ADBKEYBOARD_APK_URL, apk_path)
            except Exception as e:
                print(f"ADBKeyboard 다운로드 실패({e}) — 한글 채팅 입력이 제한됩니다.")
                return False
        print("ADBKeyboard 설치 중...")
        install = adb.run(["install", "-r", apk_path], timeout=60)
        if install.returncode != 0:
            print("ADBKeyboard 설치 실패 — 한글 채팅 입력이 제한됩니다.")
            return False
    adb.shell(f"ime enable {ADBKEYBOARD_IME}")
    adb.shell(f"ime set {ADBKEYBOARD_IME}")
    print("한글 입력(ADBKeyboard) 준비 완료")
    return True


def pip_install(*packages):
    print(f"패키지 설치 중: {' '.join(packages)}")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", *packages])
    return result.returncode == 0


def ensure_ocr_backend():
    """플랫폼에 맞는 OCR 백엔드를 확보한다. 없으면 자동 설치."""
    if sys.platform == "win32":
        try:
            import winocr  # noqa: F401
            return "winocr"
        except ImportError:
            if pip_install("winocr"):
                return "winocr"
    try:
        import easyocr  # noqa: F401
        return "easyocr"
    except ImportError:
        print("easyocr 설치 중... (torch 포함, 수 분 걸릴 수 있음)")
        if pip_install("easyocr"):
            return "easyocr"
    raise RuntimeError("OCR 백엔드를 준비하지 못했습니다.")


def check_claude(claude_command):
    """claude CLI가 실행 가능한지 확인한다. 로그인은 사용자가 이미 되어 있어야 한다."""
    try:
        result = subprocess.run(
            [claude_command, "--version"], capture_output=True, timeout=30)
        if result.returncode == 0:
            version = result.stdout.decode(errors="replace").strip()
            print(f"Claude CLI 확인: {version}")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    raise RuntimeError(
        "claude CLI를 실행할 수 없습니다. https://claude.com/claude-code 에서 설치 후 "
        "로그인(claude 실행 → 로그인)만 한 번 해주세요. 이후 세팅은 전부 자동입니다.")
