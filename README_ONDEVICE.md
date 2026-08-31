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
3. Shizuku 앱 → **"무선 디버깅으로 시작"**
4. 페어링 — **코드가 나오는 곳과 넣는 곳이 반대라 헷갈리기 쉽습니다**:
   - 개발자 옵션 → 무선 디버깅 → **"페어링 코드로 기기 페어링"** 을 열면 6자리 코드가 **표시**됩니다
   - 그 코드를 **Shizuku가 띄운 알림의 입력란에 입력**합니다
5. Shizuku 상태가 **"실행 중"** 이 되면 완료

> 폰을 재부팅하면 Shizuku가 꺼집니다. 3번을 다시 하면 됩니다. (루팅 시에는 자동 시작 가능)

## 2. Termux 설치

**F-Droid 버전을 쓰세요.** Play 스토어 버전은 오래돼서 `pkg`가 깨집니다.
→ https://f-droid.org/packages/com.termux/

```bash
pkg update && pkg upgrade
pkg install python git
```

## 3. rish 연결 (Termux ↔ Shizuku)

Shizuku 앱 홈 화면의 **"터미널 앱에서 Shizuku 사용"** 카드를 열면 rish 파일을
내보내는 안내가 나옵니다. `rish` 와 `rish_shizuku.dex` 두 개를 저장하세요.

```bash
# 저장소 접근 권한 (한 번만)
termux-setup-storage

# 두 파일을 Termux 홈으로 복사 (다운로드에 저장했다면)
cp ~/storage/downloads/rish ~/storage/downloads/rish_shizuku.dex ~/
chmod +x ~/rish
```

**중요 — 패키지 이름 설정.** 내보낸 `rish` 안에는 `RISH_APPLICATION_ID` 가
`"PKG"` 라는 플레이스홀더로 들어 있습니다. Termux용으로 바꿔야 동작합니다:

```bash
sed -i 's/^RISH_APPLICATION_ID=.*/RISH_APPLICATION_ID="com.termux"/' ~/rish
grep RISH_APPLICATION_ID ~/rish     # com.termux 로 바뀌었는지 확인
```

동작 확인:

```bash
~/rish -c id
```

- **처음 실행하면 Shizuku가 권한 요청 팝업을 띄웁니다 → 허용하세요.**
- `uid=2000(shell)` 이 나오면 성공입니다.

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

> ⚠️ **Termux는 claude CLI의 공식 지원 환경이 아닙니다.** android-arm64용으로
> 배포되지 않는 네이티브 구성요소(ripgrep 등) 때문에 설치는 되어도 실행이 안 될 수
> 있습니다. `claude --version` 이 실패하면 판단 엔진이 없는 것이므로, 이 방식 전체가
> 막힙니다. 먼저 이것부터 확인하세요.

### 파이썬은 rish 안에서 실행할 수 없습니다

`~/rish` 로 셸을 연 뒤 그 안에서 `python run_hoicho.py` 를 돌리고 싶을 수 있지만,
**동작하지 않습니다.** rish 셸은 SELinux의 `shell` 도메인이라 Termux의 앱 데이터
영역에 있는 python 바이너리를 실행할 수 없고, `cd ~/MF` 조차 권한상 막힙니다.

올바른 구조는 하나뿐입니다 — **파이썬은 일반 Termux 셸에서 돌리고, 기기 조작
명령만 코드가 알아서 rish를 경유**합니다. `find_rish()` 가 `~/rish` 를 자동으로
찾으므로 별도 설정은 필요 없습니다.

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

# 한국어 데이터 (필수) — 패키지가 있는지 먼저 확인
pkg search tesseract
# 한국어 데이터 패키지가 없으면 수동으로 받으면 됩니다:
curl -L -o $PREFIX/share/tessdata/kor.traineddata \
  https://github.com/tesseract-ocr/tessdata_fast/raw/main/kor.traineddata

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
| rish가 권한 오류 / 아무 반응 없음 | `RISH_APPLICATION_ID` 가 `com.termux` 로 바뀌었는지 확인 (3번 참고) |
| ADBKeyboard 자동 설치 실패 | 브라우저로 [ADBKeyboard.apk](https://github.com/senzhk/ADBKeyBoard/raw/master/ADBKeyboard.apk)를 받아 일반 설치하면 됩니다. 설치만 돼 있으면 IME 활성화는 코드가 합니다 |
| `claude: not found` / 실행 실패 | Termux는 claude CLI 공식 지원 환경이 아닙니다. 4번의 경고 참고 |
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
