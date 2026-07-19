"""메인 루프: 화면 캡처 → OCR → Claude 판단 → ADB 실행 → md 갱신."""

import json
import os
import time

from .adb_client import AdbClient
from .brain import ClaudeBrain
from .memory import KnowledgeStore
from .ocr import OcrEngine, split_by_region, tokens_to_chat_lines

DEFAULT_CONFIG = {
    "adb_path": r".\platform-tools-latest-windows\platform-tools\adb.exe",
    "device_id_file": "device_id.txt",
    "poll_interval_sec": 3.0,
    "chat_region": [0, 300, 1080, 1700],
    "chat_input": {"x": 400, "y": 2300},
    "send_button": {"x": 1000, "y": 2300},
    "claude_command": "claude",
    "claude_timeout_sec": 120,
    "ocr_backend": "auto",
    "knowledge_dir": "hoicho/knowledge",
    "max_chat_lines": 30,
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
        if device_id is None:
            device_id = self._load_device_id()
        self.adb = AdbClient(config["adb_path"], device_id)
        self.ocr = OcrEngine(config["ocr_backend"])
        self.brain = ClaudeBrain(config["claude_command"], config["claude_timeout_sec"])
        self.knowledge = KnowledgeStore(config["knowledge_dir"])
        self.seen_chat_lines = []

    def _load_device_id(self):
        path = self.config["device_id_file"]
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                device_id = f.read().strip()
                return device_id or None
        return None

    def run(self, once=False):
        print("자동 획초 시작" + (" (dry-run: 행동은 출력만)" if self.dry_run else ""))
        while True:
            try:
                self.step()
            except KeyboardInterrupt:
                print("중단됨")
                return
            except Exception as e:
                print(f"루프 오류(계속 진행): {e}")
            if once:
                return
            time.sleep(self.config["poll_interval_sec"])

    def step(self):
        image = self.adb.screenshot()
        if image is None:
            return

        tokens = self.ocr.read(image)
        chat_tokens, screen_tokens = split_by_region(tokens, self.config["chat_region"])
        chat_lines = tokens_to_chat_lines(chat_tokens)[-self.config["max_chat_lines"]:]

        new_lines = self._diff_chat(chat_lines)
        if not new_lines and not screen_tokens:
            return

        decision = self.brain.decide(
            knowledge_text=self.knowledge.load_all(),
            chat_lines=chat_lines,
            screen_elements=screen_tokens,
            extra_context=f"이번에 새로 올라온 채팅 줄: {new_lines or '(없음)'}",
        )
        if decision is None:
            return

        print(f"[판단] {decision.get('situation', '')}")
        self.knowledge.apply_updates(decision.get("memory_updates"))
        self.execute_actions(decision.get("actions", []))

    def _diff_chat(self, chat_lines):
        """직전 캡처와 비교해 새로 나타난 채팅 줄만 골라낸다."""
        previous = self.seen_chat_lines
        new_lines = list(chat_lines)
        # 이전 마지막 줄이 현재 목록에 있으면 그 이후 줄만 신규로 취급
        for anchor in reversed(previous):
            if anchor in chat_lines:
                new_lines = chat_lines[chat_lines.index(anchor) + 1:]
                break
        self.seen_chat_lines = chat_lines
        return new_lines

    def execute_actions(self, actions):
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
                seconds = float(action.get("seconds", 1))
                time.sleep(min(seconds, 30))
            else:
                print(f"알 수 없는 action, 무시: {action}")
            time.sleep(0.3)

    def _send_chat(self, text):
        if not text:
            return
        print(f"[채팅] {text}")
        chat_input = self.config["chat_input"]
        send_button = self.config["send_button"]
        self.adb.tap(chat_input["x"], chat_input["y"])
        time.sleep(0.5)
        self.adb.input_text(text)
        time.sleep(0.3)
        self.adb.tap(send_button["x"], send_button["y"])
