"""마피아42 통신 방식 조사 — 1단계 정적 분석 실행 스크립트.

세팅 없이 폰만 연결하면 자동으로:
  1. 기기에서 마피아42 APK(스플릿 포함)를 PC로 복사
  2. 엔진/전송 프로토콜/서버 엔드포인트/인증서 피닝을 정적 분석
  3. 결정론적 마크다운 리포트를 hoicho/knowledge/mafia42_protocol.md 에 저장

사용:
  python analyze_apk.py                 # 폰에서 APK 자동 추출 후 분석
  python analyze_apk.py --apk a.apk b.apk   # 로컬 APK 파일 직접 분석 (폰 불필요)
  python analyze_apk.py --package com.foo.bar  # 다른 패키지 지정

판정 로직은 hoicho/apk_analyzer.py의 시그니처 테이블에 전부 codified 되어 있어,
어떤 모델/환경에서 실행해도 동일 APK면 동일 리포트가 나온다.
"""

import argparse
import os
import sys

DEFAULT_PACKAGE = "com.sopt.mafia42.client"
DEFAULT_OUT = "hoicho/knowledge/mafia42_protocol.md"


def pull_apks_from_device(package, dest_dir):
    """`pm path`로 스플릿 APK 경로를 모두 얻어 PC로 복사. 로컬 경로 목록 반환."""
    from hoicho import bootstrap
    from hoicho.adb_client import AdbClient

    adb_path = bootstrap.find_adb(None)
    device_id = bootstrap.wait_for_device(adb_path)
    adb = AdbClient(adb_path, device_id)

    result = adb.shell(f"pm path {package}")
    text = result.stdout.decode("utf-8", errors="replace")
    remote_paths = [
        line.strip()[len("package:"):]
        for line in text.splitlines()
        if line.strip().startswith("package:")
    ]
    if not remote_paths:
        raise RuntimeError(
            f"기기에서 {package} 를 찾지 못했습니다. 설치되어 있고 USB 디버깅이 켜졌는지 확인하세요.")

    os.makedirs(dest_dir, exist_ok=True)
    local_paths = []
    for i, remote in enumerate(sorted(remote_paths)):
        name = os.path.basename(remote) or f"split_{i}.apk"
        local = os.path.join(dest_dir, name)
        print(f"복사 중: {remote} → {local}")
        pull = adb.run(["pull", remote, local], timeout=180)
        if pull.returncode != 0 or not os.path.exists(local):
            print("  경고: 복사 실패:", pull.stderr.decode(errors="replace").strip())
            continue
        local_paths.append(local)
    if not local_paths:
        raise RuntimeError("APK를 하나도 복사하지 못했습니다.")
    return local_paths


def main():
    parser = argparse.ArgumentParser(description="마피아42 APK 정적 분석 (통신 방식 조사)")
    parser.add_argument("--apk", nargs="+", help="로컬 APK 파일 직접 지정 (폰 불필요)")
    parser.add_argument("--package", default=DEFAULT_PACKAGE, help="분석할 패키지명")
    parser.add_argument("--out", default=DEFAULT_OUT, help="리포트 저장 경로")
    parser.add_argument("--cache-dir", default="hoicho/cache/apk", help="APK 복사 위치")
    args = parser.parse_args()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from hoicho.apk_analyzer import analyze

    if args.apk:
        apk_paths = args.apk
        for p in apk_paths:
            if not os.path.exists(p):
                print(f"APK 파일 없음: {p}")
                return 1
    else:
        apk_paths = pull_apks_from_device(args.package, args.cache_dir)

    print(f"분석 대상 {len(apk_paths)}개 APK...")
    report, _ = analyze(apk_paths)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(report + "\n")

    print("\n" + report)
    print(f"\n리포트 저장: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
