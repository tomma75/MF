# 마피아42 자동 획초 시스템

화면(채팅)을 OCR로 읽고, Claude CLI가 상황을 판단해 ADB로 채팅·투표·터치까지
자동 수행하는 획초(획득 한도 초과 파밍) 에이전트. 화면 구조와 방 규칙은
`hoicho/knowledge/*.md`에 스스로 기록·갱신하며 학습한다.

## 동작 구조
```
[ADB screencap] → [OCR: 채팅 줄 + 화면 요소(텍스트@좌표)]
      → [Claude CLI 판단: 상황 요약 / 행동 JSON / md 갱신]
      → [ADB 실행: 채팅 입력, 탭(투표·스킬·버튼)]
      → [knowledge/*.md 갱신] → 반복
```

- `hoicho/adb_client.py` — 스크린샷(exec-out), 탭, 한글 채팅 입력(ADBKeyboard)
- `hoicho/ocr.py` — winocr(Windows 권장) 또는 easyocr로 텍스트+좌표 추출
- `hoicho/brain.py` — `claude -p --output-format json` 헤드리스 호출, 행동 JSON 파싱
- `hoicho/memory.py` — knowledge md 로드/갱신 (screens.md, hoicho_rules.md, game_log.md)
- `hoicho/agent.py` — 메인 루프 (새 채팅 감지 → 판단 → 실행)

## 사전 준비 (Windows)
1. **Claude CLI**: `claude` 명령이 로그인된 상태로 동작해야 함 (`claude -p "hi"`로 확인).
2. **OCR**: `pip install winocr` (Windows 설정에서 한국어 언어팩 필요)
   또는 `pip install easyocr` (무겁지만 인식률 좋음).
3. **한글 채팅 입력**: 기기에 [ADBKeyboard.apk](https://github.com/senzhk/ADBKeyBoard) 설치 후
   `python run_hoicho.py --setup-keyboard` 실행. (영문/숫자만 쓸 거면 생략 가능)
4. **좌표 설정**: `hoicho/config.json`의 `chat_region`(채팅 영역),
   `chat_input`/`send_button`(입력창·전송 버튼 좌표)을 기기 해상도에 맞게 조정.

## 실행
```bash
python run_hoicho.py --once --dry-run   # 1사이클: OCR/판단 결과만 확인 (권장 첫 실행)
python run_hoicho.py --dry-run          # 계속 읽고 판단하되 행동은 출력만
python run_hoicho.py                    # 전부 자동 (채팅/투표/터치 실제 수행)
```

## 학습 방식
- `knowledge/screens.md` — 화면 판별 단서와 버튼 좌표. 처음엔 미학습 상태이며,
  에이전트가 OCR 좌표를 근거로 채워 나간다. 직접 채워 넣으면 정확도가 크게 올라간다.
- `knowledge/hoicho_rules.md` — 획초방 공통 규칙 + 방장 공지로 갱신되는 현재 방 규칙.
- `knowledge/game_log.md` — 판별 주요 사건 기록.

## 주의
- 게임 자동화는 마피아42 이용약관 위반으로 계정 제재를 받을 수 있다. 본인 계정
  책임 하에 사용할 것.
- 처음에는 반드시 `--dry-run`으로 판단 품질과 좌표를 검증한 뒤 자동 실행으로 넘어갈 것.
- Claude CLI 호출은 판단마다 API 사용량을 소모한다. `poll_interval_sec`을 늘리면
  호출 빈도가 줄어든다.
