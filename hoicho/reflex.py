"""반사 규칙 엔진: Claude 호출 없이 즉시 반응하는 실시간 fast path.

반복적인 상황(예: "밤이 되었습니다" → 스킵 버튼 탭)은 Claude가 knowledge의
reflexes.json에 규칙으로 기록해 두고, 이후에는 이 엔진이 프레임마다 즉시 처리한다.

reflexes.json 형식:
{
  "rules": [
    {
      "name": "밤 스킵",
      "where": "chat",            // "chat": 새 채팅 줄, "screen": 화면 요소 텍스트
      "match": "밤이 되었습니다",   // 정규식
      "actions": [{"type": "tap", "x": 540, "y": 2100, "label": "스킵"}],
      "cooldown_sec": 10
    }
  ]
}
"""

import json
import re
import time


class ReflexEngine:
    def __init__(self):
        self.rules = []
        self._last_fired = {}

    def load(self, reflexes_json_text):
        self.rules = []
        if not reflexes_json_text.strip():
            return
        try:
            data = json.loads(reflexes_json_text)
        except json.JSONDecodeError as e:
            print(f"reflexes.json 파싱 실패, 반사 규칙 비활성: {e}")
            return
        for rule in data.get("rules", []):
            try:
                re.compile(rule.get("match", ""))
            except re.error:
                print(f"잘못된 반사 규칙 정규식, 무시: {rule.get('name')}")
                continue
            self.rules.append(rule)

    def match(self, new_chat_lines, screen_texts):
        """조건에 맞는 규칙들의 action 목록을 순서대로 반환한다."""
        actions = []
        now = time.time()
        for rule in self.rules:
            name = rule.get("name", "?")
            cooldown = float(rule.get("cooldown_sec", 5))
            if now - self._last_fired.get(name, 0) < cooldown:
                continue
            where = rule.get("where", "chat")
            haystack = new_chat_lines if where == "chat" else screen_texts
            pattern = rule.get("match", "")
            if any(re.search(pattern, text) for text in haystack):
                print(f"[반사] {name}")
                self._last_fired[name] = now
                actions.extend(rule.get("actions", []))
        return actions
