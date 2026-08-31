"""메인 루프: 화면 읽기 → 변화 감지 → (반사 즉시 실행 | Claude 비동기 판단) → ADB 실행.

화면 읽기 (하이브리드):
- 1순위 uiautomator dump: UI 트리에서 텍스트+좌표를 직접 추출. OCR 불필요, 오인식 0.
- 덤프가 연속 실패하거나 텍스트가 안 잡히면 스크린샷+OCR로 자동 폴백.
  OCR 백엔드는 이때 처음으로 준비(설치)하므로, UI 덤프가 되는 한 OCR 세팅도 안 한다.

실시간 설계:
- 짧은 주기로 계속 돌고, 화면 텍스트가 변하지 않으면 판단을 생략한다.
- 반사 규칙(reflexes.json)에 걸리는 상황은 Claude 없이 즉시 실행한다.
- Claude 판단은 백그라운드 스레드에서 돌리고, 그동안 읽기/반사는 계속 동작한다.
- 판단이 돌아왔을 때 화면 요소가 크게 바뀌었으면 탭 액션은 버린다(오탭 방지).
"""

import json
import os
import threading
import time

from . import bootstrap
from .adb_client import AdbClient
from .brain import ClaudeBrain
from .memory import KnowledgeStore
from .ocr import split_by_region, tokens_to_chat_lines
from .reflex import ReflexEngine
from .ui_reader import UiDumpReader

DEFAULT_CONFIG = {
    "mode": "auto",                 # "auto" | "adb"(PC→폰) | "ondevice"(폰 단독)
    "adb_path": None,               # None이면 자동 탐색
    "rish_path": None,              # 온디바이스 전용. None이면 자동 탐색
    "reader": "auto",               # "auto" | "ui" | "ocr"
    "poll_interval_sec": 0.5,       # 읽기 주기 (실시간)
    "chat_region": [0, 300, 1080, 1700],   # 기준 해상도(1080x2400) 좌표, 자동 스케일링됨
    "chat_input": {"x": 400, "y": 2300},
    "send_button": {"x": 1000, "y": 2300},
    "claude_command": "claude",
    "claude_timeout_sec": 60,
    "claude_model": "haiku",
    "ocr_backend": "auto",
    "knowledge_dir": "hoicho/knowledge",
    "max_chat_lines": 30,
    "ui_min_tokens": 5,             # 덤프에서 이보다 적은 텍스트만 잡히면 OCR 병행 고려
    "ui_max_failures": 5,           # 덤프 연속 실패 허용 횟수 (초과 시 OCR 전환)
    "stale_overlap_ratio": 0.5,     # 판단 전후 화면 요소 겹침이 이 미만이면 탭 폐기
    "min_decision_interval_sec": 8.0,  # 새 채팅이 없을 때 Claude 재호출 최소 간격
}


def load_config(path="hoicho/config.json"):
    config = dict(DEFAULT_CONFIG)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            config.update(json.load(f))
    return config


class HoichoAgent:
    def __init__(self, config, device_id=None, dry_run=False):
        self.config = config
        self.dry_run = dry_run

        # ---- 제로 세팅 부트스트랩 ----
        # mode: "adb"(PC에서 폰 조작) | "ondevice"(폰 안에서 직접) | "auto"(자동 판별)
        mode = config.get("mode", "auto")
        if mode == "auto":
            mode = "ondevice" if bootstrap.is_android() else "adb"

        if mode == "ondevice":
            if not bootstrap.is_android():
                raise RuntimeError(
                    "온디바이스 모드는 폰(Termux) 안에서만 동작합니다. "
                    "PC에서 실행 중이라면 --mode adb 를 쓰세요.")
            from .local_client import LocalShellClient
            rish = bootstrap.find_rish(config.get("rish_path"))
            self.adb = LocalShellClient(rish)
            print(f"실행 모드: 온디바이스 (rish={rish or '불필요 — 이미 shell 권한'})")
            bootstrap.ensure_shell_access(self.adb)
        else:
            adb_path = bootstrap.find_adb(config.get("adb_path"))
            if device_id is None:
                device_id = bootstrap.wait_for_device(adb_path)
            self.adb = AdbClient(adb_path, device_id)
            print("실행 모드: adb (PC → 폰)")

        width, height = bootstrap.get_resolution(self.adb)
        self.config = bootstrap.scale_config_coords(dict(config), width, height)

        cache_dir = os.path.normpath(os.path.join(config["knowledge_dir"], "..", "cache"))
        bootstrap.ensure_adb_keyboard(self.adb, cache_dir)
        bootstrap.check_claude(config["claude_command"])

        # 화면 리더: UI 덤프 우선, OCR은 실제 필요해질 때 lazy 준비
        self.ui_reader = UiDumpReader(self.adb)
        self.use_ui = self.config["reader"] in ("auto", "ui")
        self._ui_failures = 0
        self._ocr = None
        if self.use_ui:
            probe = self.ui_reader.read()
            if probe:
                print(f"화면 읽기: UI 덤프 (텍스트 {len(probe)}개 감지, OCR 불필요)")
            elif self.config["reader"] == "ui":
                print("경고: UI 덤프가 지금은 비어 있음 (게임 화면에서 다시 시도됨)")
            else:
                print("UI 덤프 미동작 — OCR 모드로 시작")
                self.use_ui = False

        self.brain = ClaudeBrain(
            config["claude_command"], config["claude_timeout_sec"],
            model=config.get("claude_model"))
        self.knowledge = KnowledgeStore(config["knowledge_dir"])
        self.reflex = ReflexEngine()
        self.reflex.load(self.knowledge.load("reflexes.json"))

        self.seen_chat_lines = []
        self._last_signature = None
        self._last_screen_texts = frozenset()
        self._last_decision_at = 0.0
        self._decision_thread = None
        self._decision_result = None
        self._decision_screen_texts = frozenset()
        self._act_lock = threading.Lock()

    # ---- 화면 읽기 (하이브리드) ----

    def _get_ocr(self):
        if self._ocr is None:
            from .ocr import OcrEngine
            backend = self.config["ocr_backend"]
            if backend == "auto":
                backend = bootstrap.ensure_ocr_backend()
            self._ocr = OcrEngine(backend)
        return self._ocr

    def _read_tokens(self):
        """토큰 목록을 반환. 읽기 실패 시 None."""
        if self.use_ui:
            tokens = self.ui_reader.read()
            if tokens is not None:
                self._ui_failures = 0
                if len(tokens) >= self.config["ui_min_tokens"]:
                    return tokens
                # 텍스트가 거의 없음 = 커스텀 렌더링 화면일 가능성 → OCR로 보강
                if self.config["reader"] == "ui":
                    return tokens
            else:
                self._ui_failures += 1
                if (self.config["reader"] == "auto"
                        and self._ui_failures >= self.config["ui_max_failures"]):
                    print("UI 덤프 연속 실패 — OCR 모드로 전환")
                    self.use_ui = False
        image = self.adb.screenshot()
        if image is None:
            return None
        return self._get_ocr().read(image)

    # ---- 메인 루프 ----

    def run(self, once=False):
        print("자동 획초 시작" + (" (dry-run: 행동은 출력만)" if self.dry_run else ""))
        while True:
            started = time.time()
            try:
                self.step()
            except KeyboardInterrupt:
                print("중단됨")
                return
            except Exception as e:
                print(f"루프 오류(계속 진행): {e}")
            if once:
                return
            elapsed = time.time() - started
            time.sleep(max(0.05, self.config["poll_interval_sec"] - elapsed))

    def step(self):
        self._collect_finished_decision()

        tokens = self._read_tokens()
        if tokens is None:
            return
        chat_tokens, screen_tokens = split_by_region(tokens, self.config["chat_region"])
        chat_lines = tokens_to_chat_lines(chat_tokens)[-self.config["max_chat_lines"]:]
        screen_texts = [t.text for t in screen_tokens]

        signature = hash((tuple(chat_lines), tuple(screen_texts)))
        self._last_screen_texts = frozenset(screen_texts)
        if signature == self._last_signature:
            return  # 화면 정지 상태: 판단 생략
        self._last_signature = signature

        new_lines = self._diff_chat(chat_lines)

        # 1) 반사 규칙: Claude 없이 즉시 실행
        reflex_actions = self.reflex.match(new_lines, screen_texts)
        if reflex_actions:
            self.execute_actions(reflex_actions)

        # 2) Claude 판단: 새 채팅이 있으면 즉시, 그 외 화면 변화는 최소 간격을 두고 요청.
        #    반사 규칙이 이미 처리한 변화는 Claude까지 갈 필요 없다.
        should_consult = bool(new_lines) or (
            not reflex_actions
            and time.time() - self._last_decision_at
            > self.config["min_decision_interval_sec"]
        )
        if should_consult and not self._decision_in_flight():
            self._last_decision_at = time.time()
            self._request_decision(chat_lines, new_lines, screen_tokens)

    # ---- 비동기 판단 ----

    def _decision_in_flight(self):
        return self._decision_thread is not None and self._decision_thread.is_alive()

    def _request_decision(self, chat_lines, new_lines, screen_tokens):
        knowledge_text = self.knowledge.load_all()
        reflexes = self.knowledge.load("reflexes.json").strip()
        if reflexes:
            knowledge_text += f"\n\n=== reflexes.json (현재 반사 규칙) ===\n{reflexes}"
        self._decision_screen_texts = frozenset(t.text for t in screen_tokens)

        def worker():
            self._decision_result = self.brain.decide(
                knowledge_text=knowledge_text,
                chat_lines=chat_lines,
                screen_elements=screen_tokens,
                extra_context=f"이번에 새로 올라온 채팅 줄: {new_lines or '(없음)'}",
            )

        self._decision_thread = threading.Thread(target=worker, daemon=True)
        self._decision_thread.start()

    def _collect_finished_decision(self):
        if self._decision_thread is None or self._decision_thread.is_alive():
            return
        decision, self._decision_result = self._decision_result, None
        self._decision_thread = None
        if decision is None:
            return

        print(f"[판단] {decision.get('situation', '')}")
        self.knowledge.apply_updates(decision.get("memory_updates"))
        self.reflex.load(self.knowledge.load("reflexes.json"))

        actions = decision.get("actions", [])
        # 판단하는 사이 화면 요소가 크게 바뀌었으면 좌표 기반 액션은 위험하므로 버린다
        requested = self._decision_screen_texts
        if requested:
            overlap = len(requested & self._last_screen_texts) / len(requested)
            if overlap < self.config["stale_overlap_ratio"]:
                dropped = [a for a in actions if a.get("type") == "tap"]
                if dropped:
                    print(f"화면이 바뀌어 탭 {len(dropped)}건 폐기")
                actions = [a for a in actions if a.get("type") != "tap"]
        self.execute_actions(actions)

    # ---- 채팅 diff / 실행 ----

    def _diff_chat(self, chat_lines):
        """직전 읽기와 비교해 새로 나타난 채팅 줄만 골라낸다."""
        previous = self.seen_chat_lines
        new_lines = list(chat_lines)
        for anchor in reversed(previous):
            if anchor in chat_lines:
                new_lines = chat_lines[chat_lines.index(anchor) + 1:]
                break
        self.seen_chat_lines = chat_lines
        return new_lines

    def execute_actions(self, actions):
        with self._act_lock:
            for action in actions:
                action_type = action.get("type")
                if self.dry_run:
                    print(f"[dry-run] {action}")
                    continue
                if action_type == "chat":
                    self._send_chat(action.get("text", ""))
                elif action_type == "tap":
                    x, y = action.get("x"), action.get("y")
                    if x is None or y is None:
                        print(f"tap 좌표 없음, 무시: {action}")
                        continue
                    print(f"[탭] ({x}, {y}) {action.get('label', '')}")
                    self.adb.tap(x, y)
                elif action_type == "wait":
                    time.sleep(min(float(action.get("seconds", 1)), 10))
                else:
                    print(f"알 수 없는 action, 무시: {action}")
                time.sleep(0.2)

    def _send_chat(self, text):
        if not text:
            return
        print(f"[채팅] {text}")
        chat_input = self.config["chat_input"]
        send_button = self.config["send_button"]
        self.adb.tap(chat_input["x"], chat_input["y"])
        time.sleep(0.4)
        self.adb.input_text(text)
        time.sleep(0.2)
        self.adb.tap(send_button["x"], send_button["y"])
