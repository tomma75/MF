"""마피아42 자동 획초 실행 스크립트 — 세팅 없이 그냥 실행하면 된다.

    python run_hoicho.py            # 전부 자동 (기기/키보드/OCR 준비도 자동)
    python run_hoicho.py --dry-run  # 행동은 출력만 (판단 품질 확인용)
    python run_hoicho.py --once     # 한 사이클만 실행

실행 위치는 두 가지 다 된다 (기본 auto로 자동 판별):
    PC에서   — 폰을 USB/무선 adb로 연결해 조작
    폰에서   — Termux + Shizuku로 PC 없이 폰 단독 실행 (README_ONDEVICE.md)

필요한 유일한 수동 준비: claude CLI 로그인 (최초 1회).
"""

import argparse
import subprocess
import sys


def ensure_base_packages():
    """opencv/numpy가 없으면 자동 설치한 뒤 계속 진행한다.

    이 둘은 OCR 폴백(스크린샷 디코딩)에만 쓰인다. UI 덤프로 화면이 읽히면 없어도
    되므로, pip 빌드가 사실상 불가능한 폰(Termux)에서는 설치를 강행하지 않는다.
    """
    missing = []
    for module, package in (("cv2", "opencv-python"), ("numpy", "numpy")):
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    if not missing:
        return

    from hoicho import bootstrap
    if bootstrap.is_android():
        print(f"참고: {' '.join(missing)} 없음 — UI 덤프만으로 동작합니다.\n"
              "      OCR 폴백까지 쓰려면: pkg install python-numpy opencv-python")
        return

    print(f"필수 패키지 설치 중: {' '.join(missing)}")
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", *missing],
                   check=True)


def main():
    parser = argparse.ArgumentParser(description="마피아42 자동 획초")
    parser.add_argument("--device", help="ADB device id (기본: 첫 번째 연결 기기 자동)")
    parser.add_argument("--dry-run", action="store_true", help="행동을 실행하지 않고 출력만")
    parser.add_argument("--once", action="store_true", help="한 사이클만 실행")
    parser.add_argument("--config", default="hoicho/config.json",
                        help="설정 오버라이드 파일 (없어도 됨)")
    parser.add_argument("--mode", choices=["auto", "adb", "ondevice"],
                        help="auto=자동 판별, adb=PC에서 폰 조작, ondevice=폰 단독(Shizuku)")
    args = parser.parse_args()

    ensure_base_packages()
    from hoicho.agent import HoichoAgent, load_config

    config = load_config(args.config)
    if args.mode:
        config["mode"] = args.mode
    agent = HoichoAgent(config, device_id=args.device, dry_run=args.dry_run)
    agent.run(once=args.once)


if __name__ == "__main__":
    main()
