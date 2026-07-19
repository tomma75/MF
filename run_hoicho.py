"""마피아42 자동 획초 실행 스크립트.

사용 예:
    python run_hoicho.py --dry-run      # 읽기/판단만 하고 행동은 출력만
    python run_hoicho.py                # 전부 자동 (채팅/투표/스킬)
    python run_hoicho.py --once         # 한 사이클만 실행 (좌표/OCR 점검용)
"""

import argparse

from hoicho.agent import HoichoAgent, load_config


def main():
    parser = argparse.ArgumentParser(description="마피아42 자동 획초")
    parser.add_argument("--device", help="ADB device id (기본: device_id.txt)")
    parser.add_argument("--dry-run", action="store_true", help="행동을 실행하지 않고 출력만")
    parser.add_argument("--once", action="store_true", help="한 사이클만 실행")
    parser.add_argument("--config", default="hoicho/config.json", help="설정 파일 경로")
    parser.add_argument("--setup-keyboard", action="store_true",
                        help="ADBKeyboard IME 활성화 후 종료 (한글 채팅 입력용)")
    args = parser.parse_args()

    config = load_config(args.config)
    agent = HoichoAgent(config, device_id=args.device, dry_run=args.dry_run)

    if args.setup_keyboard:
        agent.adb.enable_adb_keyboard()
        print("ADBKeyboard IME 활성화 완료")
        return

    agent.run(once=args.once)


if __name__ == "__main__":
    main()
