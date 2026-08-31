"""화면 OCR 모듈.

전체 화면에서 텍스트를 (내용, 중심좌표, bbox) 단위로 추출한다.
백엔드 우선순위:
  1. winocr  — Windows 내장 OCR(한국어 언어팩 필요), 가볍고 설치 간단
  2. easyocr — 크로스 플랫폼, torch 기반이라 무겁지만 인식률 좋음
"""


class OcrToken:
    def __init__(self, text, x, y, bbox):
        self.text = text
        self.x = int(x)
        self.y = int(y)
        self.bbox = bbox  # (x1, y1, x2, y2)

    def __repr__(self):
        return f"OcrToken({self.text!r}, ({self.x}, {self.y}))"


class OcrEngine:
    def __init__(self, backend="auto"):
        self.backend = None
        self._easyocr_reader = None
        if backend in ("auto", "winocr"):
            try:
                import winocr  # noqa: F401
                self.backend = "winocr"
            except ImportError:
                if backend == "winocr":
                    raise
        if self.backend is None and backend in ("auto", "tesseract"):
            try:
                import pytesseract  # noqa: F401
                self.backend = "tesseract"
            except ImportError:
                if backend == "tesseract":
                    raise
        if self.backend is None and backend in ("auto", "easyocr"):
            try:
                import easyocr
                self._easyocr_reader = easyocr.Reader(["ko", "en"], gpu=False)
                self.backend = "easyocr"
            except ImportError:
                if backend == "easyocr":
                    raise
        if self.backend is None:
            raise RuntimeError(
                "사용 가능한 OCR 백엔드가 없습니다. `pip install winocr`(Windows 권장) "
                "또는 `pip install easyocr` 후 다시 실행하세요."
            )
        print(f"OCR 백엔드: {self.backend}")

    def read(self, image_bgr):
        """BGR 이미지에서 OcrToken 목록을 y, x 순으로 정렬해 반환."""
        if self.backend == "winocr":
            tokens = self._read_winocr(image_bgr)
        elif self.backend == "tesseract":
            tokens = self._read_tesseract(image_bgr)
        else:
            tokens = self._read_easyocr(image_bgr)
        tokens.sort(key=lambda t: (t.y, t.x))
        return tokens

    def _read_winocr(self, image_bgr):
        import winocr

        result = winocr.recognize_cv2_sync(image_bgr, lang="ko")
        tokens = []
        for line in result.get("lines", []):
            words = line.get("words", [])
            if not words:
                continue
            text = line.get("text", "").strip()
            if not text:
                continue
            xs, ys = [], []
            for w in words:
                rect = w.get("bounding_rect", {})
                xs += [rect.get("x", 0), rect.get("x", 0) + rect.get("width", 0)]
                ys += [rect.get("y", 0), rect.get("y", 0) + rect.get("height", 0)]
            x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
            tokens.append(OcrToken(text, (x1 + x2) / 2, (y1 + y2) / 2, (x1, y1, x2, y2)))
        return tokens

    def _read_tesseract(self, image_bgr):
        """Termux 등 폰 환경용. tesseract 바이너리 + kor.traineddata 필요."""
        import cv2
        import pytesseract

        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        data = pytesseract.image_to_data(
            rgb, lang="kor+eng", output_type=pytesseract.Output.DICT)

        # tesseract는 단어 단위로 주므로, 줄 단위로 묶어 다른 백엔드와 입자를 맞춘다.
        lines = {}
        for i in range(len(data["text"])):
            text = (data["text"][i] or "").strip()
            if not text:
                continue
            try:
                conf = float(data["conf"][i])
            except (TypeError, ValueError):
                conf = -1.0
            if conf < 30:
                continue
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            x, y = data["left"][i], data["top"][i]
            w, h = data["width"][i], data["height"][i]
            entry = lines.setdefault(key, {"words": [], "box": [x, y, x + w, y + h]})
            entry["words"].append(text)
            box = entry["box"]
            box[0], box[1] = min(box[0], x), min(box[1], y)
            box[2], box[3] = max(box[2], x + w), max(box[3], y + h)

        tokens = []
        for entry in lines.values():
            x1, y1, x2, y2 = entry["box"]
            tokens.append(OcrToken(
                " ".join(entry["words"]), (x1 + x2) / 2, (y1 + y2) / 2, (x1, y1, x2, y2)))
        return tokens

    def _read_easyocr(self, image_bgr):
        results = self._easyocr_reader.readtext(image_bgr, detail=1)
        tokens = []
        for bbox, text, conf in results:
            text = text.strip()
            if not text or conf < 0.3:
                continue
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
            tokens.append(OcrToken(text, (x1 + x2) / 2, (y1 + y2) / 2, (x1, y1, x2, y2)))
        return tokens


def split_by_region(tokens, region):
    """region(x1, y1, x2, y2) 안의 토큰과 밖의 토큰을 나눈다."""
    x1, y1, x2, y2 = region
    inside, outside = [], []
    for t in tokens:
        if x1 <= t.x <= x2 and y1 <= t.y <= y2:
            inside.append(t)
        else:
            outside.append(t)
    return inside, outside


def tokens_to_chat_lines(tokens, line_gap=25):
    """채팅 영역 토큰을 y좌표 기준으로 묶어 줄 단위 문자열로 만든다."""
    lines = []
    current = []
    last_y = None
    for t in tokens:
        if last_y is not None and t.y - last_y > line_gap:
            lines.append(" ".join(w.text for w in current))
            current = []
        current.append(t)
        last_y = t.y
    if current:
        lines.append(" ".join(w.text for w in current))
    return [l for l in (line.strip() for line in lines) if l]
