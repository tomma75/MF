# 온디바이스 실행 — PC 없이 폰 단독으로 자동 획초

PC도, 루팅도 없이 폰 하나로 돌리는 방법입니다. 핵심은 **Shizuku**입니다.

## 왜 Shizuku가 필요한가

안드로이드는 앱이 다른 앱(마피아42)의 화면을 읽거나 터치를 넣는 걸 막습니다.
이 벽을 넘는 방법은 세 가지뿐입니다.

| 방법 | 루팅 | PC | 우리 코드 |
|---|---|---|---|
| adb | 불필요 | **필요** | 그대로 |
| root | **필요** | 불필요 | 그대로 |
| **Shizuku** | 불필요 | 불필요\* | 그대로 |

Shizuku는 앱·스크립트에 **shell 권한(uid 2000)** 을 줍니다. adb가 갖는 것과 똑같은
권한이라, `screencap` · `input tap` · `uiautomator dump` 가 전부 동작합니다.

\* 안드로이드 11+ 는 **무선 디버깅으로 폰 자체에서** Shizuku를 켤 수 있어 PC가 필요 없습니다.
안드로이드 10 이하는 부팅할 때마다 PC에서 adb로 한 번 켜 줘야 합니다.

> ⚠️ 계정 위험: 화면 자동 조작은 게임 이용약관 위반일 수 있고, 루팅·접근성·Shizuku는
> 탐지 대상이 되기도 합니다. 본인 계정으로 감수할 범위인지 판단하고 쓰세요.

---

## 1. Shizuku 설치 및 실행

1. Play 스토어에서 **Shizuku** 설치
2. 폰: 설정 → 개발자 옵션 → **무선 디버깅 켜기**
3. Shizuku 앱 → **"무선 디버깅으로 시작"** → 안내대로 페어링
   - 페어링 코드 입력 화면이 뜨면, 알림에 뜬 6자리 코드를 넣습니다
4. Shizuku 상태가 **"실행 중"** 이 되면 완료

> 폰을 재부팅하면 Shizuku가 꺼집니다. 3번을 다시 하면 됩니다. (루팅 시에는 자동 시작 가능)

## 2. Termux 설치

**F-Droid 버전을 쓰세요.** Play 스토어 버전은 오래돼서 `pkg`가 깨집니다.
→ https://f-droid.org/packages/com.termux/

```bash
pkg update && pkg upgrade
pkg install python git
```

## 3. rish 연결 (Termux ↔ Shizuku)

Shizuku 앱 → 우측 하단 메뉴 → **"Termux용 rish 파일 추출"**(Extract rish files) →
저장 위치를 Termux 홈으로 지정합니다. 그다음 Termux에서:

```bash
# 저장소 접근 권한 (한 번만)
termux-setup-storage

# rish 파일을 홈으로 복사 (다운로드에 저장했다면)
cp ~/storage/downloads/rish ~/storage/downloads/rish_shizuku.dex ~/
chmod +x ~/rish
```

동작 확인:

```bash
~/rish -c id
```

`uid=2000(shell)` 이 나오면 성공입니다.

## 4. 코드 받고 실행

```bash
git clone -b claude/code-analysis-ylvapq https://github.com/tomma75/MF.git
cd MF

# claude CLI (판단 엔진) — 최초 1회 로그인 필요
pkg install nodejs
npm install -g @anthropic-ai/claude-code
claude          # 로그인 후 종료

# 실행
python run_hoicho.py --once --dry-run    # 먼저 인식만 확인
python run_hoicho.py                     # 실제 구동
```

`mode`는 기본 `auto`라 폰에서 실행하면 온디바이스로 자동 전환됩니다.
명시하려면 `--mode ondevice`.

### rish를 매번 거치지 않으려면

rish 셸 안에서 파이썬을 띄우면 프로세스가 이미 shell 권한이라 더 빠릅니다:

```bash
~/rish
cd MF && python run_hoicho.py
```

---

## 화면 인식에 대해

읽기는 2단계입니다.

1. **UI 덤프**(`uiautomator dump`) — 1순위. OCR 불필요, 오인식 없음
2. **스크린샷 + OCR** — 덤프에 텍스트가 안 잡힐 때 자동 폴백

마피아42는 Unity로 그려서 UI 덤프에 텍스트가 거의 안 잡힐 수 있습니다.
그러면 OCR이 필요하고, 폰에서는 tesseract를 씁니다 (easyocr은 torch라 Termux에서 사실상 불가):

```bash
pkg install tesseract
pip install pytesseract

# 한국어 데이터 (필수)
pkg install tesseract-data-kor
# 위 패키지가 없으면 수동으로:
#   curl -L -o $PREFIX/share/tessdata/kor.traineddata \
#     https://github.com/tesseract-ocr/tessdata_fast/raw/main/kor.traineddata

# 스크린샷 디코딩용
pkg install python-numpy opencv-python
```

`--once --dry-run` 출력에 `화면 읽기: UI 덤프 (텍스트 N개 감지)` 가 뜨면 OCR은 아예
설치할 필요가 없습니다. 먼저 그것부터 확인하세요.

---

## 문제 해결

| 증상 | 원인 / 해결 |
|---|---|
| `shell 권한이 없습니다 (uid=10xxx)` | Shizuku가 꺼졌거나 rish를 못 찾음. Shizuku 재시작 후 `~/rish -c id` 확인 |
| 재부팅 후 안 됨 | Shizuku는 재부팅 시 꺼집니다. 1번 3단계 재실행 |
| `rish: not found` | `chmod +x ~/rish`, 또는 config.json에 `"rish_path": "/data/data/com.termux/files/home/rish"` |
| UI 덤프가 비어 있음 | Unity 화면이라 정상. 위의 OCR 설치 진행 |
| 한글 입력 안 됨 | ADBKeyboard가 IME로 안 잡힌 것. `~/rish -c "ime list -s"` 확인 |
| `pip install opencv-python` 이 빌드 실패 | pip 말고 `pkg install opencv-python` 을 쓰세요 |

## PC 방식(adb)과의 비교

| | PC(adb) | 폰 단독(Shizuku) |
|---|---|---|
| 준비물 | PC + 케이블/같은 WiFi | Shizuku + Termux |
| 재부팅 후 | 다시 연결 | Shizuku 다시 켜기 |
| OCR | winocr/easyocr (좋음) | tesseract (다소 낮음) |
| 속도 | 빠름 | 폰 성능에 좌우 |

두 방식 모두 같은 코드가 돌고, `mode`만 다릅니다.
