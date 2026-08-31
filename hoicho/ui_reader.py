"""uiautomator dump 기반 화면 읽기 — OCR 없이 UI 트리에서 텍스트+좌표를 직접 추출.

앱이 네이티브 UI를 쓰면 OCR보다 빠르고 오인식이 없다.
커스텀 렌더링 화면에서는 텍스트가 안 잡히므로 agent가 OCR로 폴백한다.
"""

import re
import xml.etree.ElementTree as ET

from .ocr import OcrToken

_BOUNDS_RE = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")


class UiDumpReader:
    def __init__(self, adb):
        self.adb = adb

    def read(self):
        """텍스트 노드를 OcrToken 목록으로 반환. 덤프 실패 시 None."""
        try:
            result = self.adb.run(
                ["exec-out", "uiautomator", "dump", "/dev/tty"], timeout=10)
        except Exception:
            return None
        out = result.stdout.decode("utf-8", errors="replace")
        start = out.find("<hierarchy")
        end = out.rfind("</hierarchy>")
        if start < 0 or end < 0:
            return None
        try:
            root = ET.fromstring(out[start:end + len("</hierarchy>")])
        except ET.ParseError:
            return None

        tokens = []
        for node in root.iter("node"):
            text = (node.get("text") or "").strip() or (node.get("content-desc") or "").strip()
            if not text:
                continue
            match = _BOUNDS_RE.match(node.get("bounds", ""))
            if not match:
                continue
            x1, y1, x2, y2 = map(int, match.groups())
            if x2 <= x1 or y2 <= y1:
                continue
            tokens.append(OcrToken(text, (x1 + x2) / 2, (y1 + y2) / 2, (x1, y1, x2, y2)))
        tokens.sort(key=lambda t: (t.y, t.x))
        return tokens
