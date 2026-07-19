"""knowledge/ 디렉터리의 md 파일을 읽고, Claude의 판단 결과로 갱신하는 저장소."""

import os
import time


class KnowledgeStore:
    ALLOWED_FILES = {"screens.md", "hoicho_rules.md", "game_log.md", "reflexes.json"}

    def __init__(self, knowledge_dir):
        self.knowledge_dir = knowledge_dir
        os.makedirs(knowledge_dir, exist_ok=True)

    def _path(self, filename):
        if filename not in self.ALLOWED_FILES:
            raise ValueError(f"허용되지 않은 knowledge 파일: {filename}")
        return os.path.join(self.knowledge_dir, filename)

    def load(self, filename):
        path = self._path(filename)
        if not os.path.exists(path):
            return ""
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def load_all(self):
        """모든 md를 파일명 헤더를 붙여 하나의 문자열로 합친다 (프롬프트용)."""
        parts = []
        for name in sorted(f for f in self.ALLOWED_FILES if f.endswith(".md")):
            content = self.load(name)
            if content.strip():
                parts.append(f"=== {name} ===\n{content.strip()}")
        return "\n\n".join(parts)

    def apply_updates(self, updates):
        """Claude가 반환한 memory_updates 목록을 반영한다.

        update 형식: {"file": "screens.md", "mode": "append"|"replace", "content": "..."}
        """
        for update in updates or []:
            filename = update.get("file")
            mode = update.get("mode", "append")
            content = update.get("content", "")
            if not filename or not content:
                continue
            try:
                path = self._path(filename)
            except ValueError as e:
                print(f"md 갱신 무시: {e}")
                continue
            if mode == "replace":
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content.rstrip() + "\n")
            else:
                with open(path, "a", encoding="utf-8") as f:
                    f.write("\n" + content.rstrip() + "\n")
            print(f"knowledge 갱신: {filename} ({mode})")

    def append_log(self, message):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(self._path("game_log.md"), "a", encoding="utf-8") as f:
            f.write(f"- [{timestamp}] {message}\n")
