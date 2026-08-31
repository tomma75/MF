# 마피아42 자동 획초 시스템

화면(채팅)을 OCR로 읽고, Claude CLI가 상황을 판단해 ADB로 채팅·투표·터치까지
자동 수행하는 획초(획득 한도 초과 파밍) 에이전트. 화면 구조와 방 규칙은
`hoicho/knowledge/`에 스스로 기록·갱신하며 학습한다.

## 실행 (세팅 불필요)
```
hoicho.cmd          (더블클릭)   또는   python run_hoicho.py
```
폰을 USB로 꽂거나 무선 디버깅만 켜 두면 나머지는 전부 자동이다:
- 기기 자동 감지 (연결될 때까지 대기)
- 해상도 감지 후 채팅 영역/입력창 좌표 자동 스케일링
- 한글 입력용 ADBKeyboard 자동 다운로드·설치·활성화
- OCR 백엔드(winocr/easyocr)와 파이썬 패키지 자동 설치

**유일한 수동 준비(최초 1회):** [Claude CLI](https://claude.com/claude-code) 설치 후 로그인.

## 실시간 구조
```
[화면 읽기 0.5s 주기]
   ├─ 1순위: uiautomator dump — UI 트리에서 텍스트+좌표 직접 추출 (OCR 불필요, 오인식 0)
   ├─ 폴백: 스크린샷 + OCR — 덤프가 실패하거나 텍스트가 안 잡히는 화면에서만
   │        (OCR 백엔드도 이때 처음 설치되므로, UI 덤프가 되는 한 OCR 세팅 자체가 없음)
   ├─ 화면 텍스트 변화 없으면 스킵
   ├─ 반사 규칙(reflexes.json) 매칭 → Claude 없이 즉시 실행   ← ms 단위 반응
   └─ 새 상황 → Claude 판단 (백그라운드 스레드, 기본 haiku 모델)
        → 행동 실행 + knowledge 갱신 (판단 중에도 읽기/반사는 계속 동작)
```
- **반사 규칙**: 반복 상황(밤 스킵, 다시하기 버튼, 자백자 지목 등)은 Claude가
  직접 `reflexes.json`에 규칙으로 기록하고, 이후에는 프레임마다 즉시 반응한다.
  게임을 할수록 Claude 호출이 줄고 반응이 빨라진다.
- **오탭 방지**: 판단이 돌아오는 사이 화면이 크게 바뀌었으면 좌표 탭은 폐기한다.

## 파일 구성
- `hoicho/bootstrap.py` — 제로 세팅 (기기/해상도/키보드/OCR/CLI 자동 준비)
- `hoicho/agent.py` — 실시간 메인 루프 (하이브리드 읽기, 변화 감지, 반사, 비동기 판단)
- `hoicho/ui_reader.py` — uiautomator dump 리더 (OCR 없는 1순위 화면 읽기)
- `hoicho/reflex.py` — 반사 규칙 엔진 (Claude 없는 fast path)
- `hoicho/brain.py` — `claude -p` 헤드리스 판단 (JSON 행동 + md 갱신)
- `hoicho/adb_client.py` — 스크린샷, 탭, 한글 채팅 입력
- `hoicho/ocr.py` — 텍스트+좌표 추출 (winocr/easyocr)
- `hoicho/knowledge/` — 자체 갱신 지식: 획초방 규칙, 화면 구조, 반사 규칙, 게임 로그
- `hoicho/config.json` — 선택적 오버라이드 (없어도 동작)

## 통신 방식 조사 (선택) — 정적 분석 하네스
패킷/메모리 경로를 검토하기 위한 1단계 정적 분석 도구. 폰만 연결하면 APK를
자동 추출해 엔진·전송 프로토콜·서버 엔드포인트·인증서 피닝을 판별한다.
```
python analyze_apk.py                    # 폰에서 APK 추출 후 분석
python analyze_apk.py --apk base.apk     # 로컬 APK 직접 분석 (폰 불필요)
```
- `hoicho/apk_analyzer.py` — 판정 로직이 전부 시그니처 테이블 + 규칙에 codified.
  외부 도구(strings/aapt) 없이 순수 파이썬으로 문자열을 추출하므로 **동일 APK면
  어떤 모델/환경에서 실행해도 동일 리포트**가 나온다(결정론).
- 결과는 `hoicho/knowledge/mafia42_protocol.md`에 저장된다.
- 이후 단계(PCAPdroid 캡처 → mitmproxy 복호화 → Frida 후킹)는 리포트의
  "다음 단계" 권장에 따라 본인 PC에서 진행한다.

## 주의
- 게임 자동화는 마피아42 이용약관 위반으로 계정 제재를 받을 수 있다. 본인 계정
  책임 하에 사용할 것.
- 판단 품질을 먼저 보고 싶으면 `python run_hoicho.py --dry-run`으로 행동 없이
  판단 로그만 확인할 수 있다.
