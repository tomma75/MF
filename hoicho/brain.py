"""Claude CLI(claude -p)를 판단 엔진으로 쓰는 두뇌 모듈."""

import json
import re
import subprocess

SYSTEM_RULES = """너는 마피아42 '획초방'(획득 한도 초과 파밍방)을 자동 진행하는 에이전트다.
매 턴 화면 OCR 결과(채팅 줄, 화면 요소와 좌표)와 knowledge md 문서를 받는다.
목표: 획초방 규칙과 방장의 공지에 따라 게임을 최대한 빨리, 매너 있게 끝내는 것.

반드시 아래 JSON 형식으로만 응답한다. JSON 앞뒤에 다른 텍스트를 붙이지 마라.
{
  "situation": "현재 상황 한 줄 요약",
  "actions": [
    {"type": "chat", "text": "보낼 채팅 내용"},
    {"type": "tap", "x": 540, "y": 1200, "label": "무엇을 누르는지"},
    {"type": "wait", "seconds": 2}
  ],
  "memory_updates": [
    {"file": "screens.md", "mode": "append", "content": "새로 알아낸 화면 구조"}
  ]
}

규칙:
- actions는 이번 턴에 실행할 행동을 순서대로 나열한다. 할 게 없으면 빈 배열.
- tap 좌표는 반드시 이번 화면 요소 목록(텍스트+좌표)이나 screens.md에 근거해서 정한다. 추측 금지.
- 화면 구조(버튼 위치, 화면 종류 판별법)를 새로 알아냈으면 screens.md에 기록해라.
- 획초방 규칙이 채팅 공지로 갱신되면 hoicho_rules.md에 기록해라.
- 게임의 중요한 사건(직업 확인, 자백, 투표 결과)은 game_log.md에 기록해라.
- 확신이 없으면 행동하지 말고 wait를 반환해라. 오판으로 게임을 그르치는 것이 최악이다.

실시간성 (매우 중요):
- 너의 판단은 수 초가 걸리므로, 같은 패턴이 반복되는 상황은 반사 규칙으로 만들어라.
- 반사 규칙은 memory_updates로 reflexes.json 전체를 mode="replace"로 갱신한다. 형식:
  {"rules": [{"name": "...", "where": "chat"|"screen", "match": "정규식",
              "actions": [...], "cooldown_sec": 10}]}
- 반사 규칙으로 만들기 좋은 것: 밤 스킵, 게임 종료 후 다시하기 버튼, 준비 버튼,
  자백 키워드에 대한 지목 채팅 등 좌표/반응이 검증된 반복 동작.
- 이미 반사 규칙이 처리하는 상황에는 중복 행동을 반환하지 마라.
"""


class ClaudeBrain:
    def __init__(self, claude_command="claude", timeout=60, model="haiku"):
        self.claude_command = claude_command
        self.timeout = timeout
        self.model = model  # 실시간성을 위해 기본은 빠른 모델
        self._model_supported = True

    def decide(self, knowledge_text, chat_lines, screen_elements, extra_context=""):
        prompt = self._build_prompt(knowledge_text, chat_lines, screen_elements, extra_context)
        raw = self._call_claude(prompt)
        if raw is None:
            return None
        return self._parse_decision(raw)

    def _build_prompt(self, knowledge_text, chat_lines, screen_elements, extra_context):
        elements_text = "\n".join(
            f"- \"{t.text}\" @ ({t.x}, {t.y})" for t in screen_elements
        ) or "(없음)"
        chat_text = "\n".join(chat_lines) or "(없음)"
        parts = [
            SYSTEM_RULES,
            f"## knowledge 문서\n{knowledge_text or '(비어 있음)'}",
            f"## 현재 채팅 (위→아래 순서)\n{chat_text}",
            f"## 화면 요소 (OCR 텍스트 @ 중심좌표)\n{elements_text}",
        ]
        if extra_context:
            parts.append(f"## 추가 컨텍스트\n{extra_context}")
        parts.append("위 상황을 판단해 JSON으로만 응답하라.")
        return "\n\n".join(parts)

    def _call_claude(self, prompt):
        cmd = [self.claude_command, "-p", "--output-format", "json"]
        if self.model and self._model_supported:
            cmd += ["--model", self.model]
        try:
            result = subprocess.run(
                cmd,
                input=prompt.encode("utf-8"),
                capture_output=True,
                timeout=self.timeout,
            )
        except FileNotFoundError:
            print(f"claude CLI를 찾을 수 없습니다: {self.claude_command}")
            return None
        except subprocess.TimeoutExpired:
            print("claude CLI 응답 시간 초과")
            return None
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace").strip()
            if self.model and self._model_supported and "model" in stderr.lower():
                # 모델 별칭 미지원 CLI 버전이면 기본 모델로 폴백
                print(f"모델 '{self.model}' 미지원, 기본 모델로 재시도")
                self._model_supported = False
                return self._call_claude(prompt)
            print("claude CLI 오류:", stderr[:500])
            return None
        try:
            envelope = json.loads(result.stdout.decode("utf-8"))
            return envelope.get("result", "")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return result.stdout.decode("utf-8", errors="replace")

    def _parse_decision(self, raw_text):
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if not match:
            print("판단 결과에서 JSON을 찾지 못함:", raw_text[:200])
            return None
        try:
            decision = json.loads(match.group(0))
        except json.JSONDecodeError as e:
            print(f"판단 JSON 파싱 실패: {e}")
            return None
        decision.setdefault("actions", [])
        decision.setdefault("memory_updates", [])
        return decision
