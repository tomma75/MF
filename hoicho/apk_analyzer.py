"""마피아42 APK 정적 분석 하네스 (1단계).

목표: 통신 방식(엔진·전송 프로토콜·서버 엔드포인트·인증서 피닝)을 APK만으로 판별한다.

결정론 원칙:
- 판단은 전부 아래 시그니처 테이블 + 규칙 기반이다. LLM 추론에 의존하지 않으므로
  어떤 모델(예: Opus)이 이 하네스를 호출해도 동일 APK면 동일 리포트가 나온다.
- 외부 도구(aapt/apktool/strings)에 의존하지 않는다. 문자열 추출은 순수 파이썬으로
  구현해 환경 차이에 따른 결과 변동을 없앤다.
- 모든 집합 출력은 정렬한다. 시간·난수 등 비결정 요소는 리포트 본문에 넣지 않고,
  재현 검증용으로 분석 대상의 SHA-256만 기록한다.

입력: APK 경로 목록 (split APK면 여러 개). 출력: 마크다운 리포트 문자열.
"""

import hashlib
import os
import re
import zipfile

# ---- 시그니처 테이블 (여기만 고치면 판정이 바뀜, 코드 로직은 불변) ----

# 네이티브 라이브러리 파일명 → 엔진/런타임
ENGINE_LIB_SIGNS = [
    ("libil2cpp.so", "Unity (IL2CPP 백엔드)"),
    ("libunity.so", "Unity"),
    ("libmain.so", "Unity 런처(추정)"),
    ("libmono", "Unity (Mono 백엔드)"),
    ("libgodot", "Godot"),
    ("libcocos", "Cocos2d-x"),
    ("libunreal", "Unreal Engine"),
    ("libUE4", "Unreal Engine 4"),
    ("libflutter.so", "Flutter"),
    ("libreactnative", "React Native"),
]

# 네이티브 라이브러리 파일명 → 네트워킹 스택
NET_LIB_SIGNS = [
    ("libphoton", "Photon (Exit Games) — UDP 기반 실시간"),
    ("libwebsocket", "네이티브 WebSocket"),
    ("libssl", "OpenSSL/BoringSSL (TLS)"),
    ("libconscrypt", "Conscrypt (TLS)"),
]

# 문자열 시그니처 → 네트워킹 기술 (대소문자 무시, 정규식)
NET_STRING_SIGNS = [
    (r"socket\.io", "Socket.IO"),
    (r"engine\.io", "Engine.IO (Socket.IO 하위)"),
    (r"exitgames|photon|\bPUN\b", "Photon"),
    (r"websocket|ws://|wss://", "WebSocket"),
    (r"okhttp", "OkHttp (HTTP/WebSocket 클라이언트)"),
    (r"retrofit", "Retrofit (REST)"),
    (r"signalr", "SignalR"),
    (r"smartfox", "SmartFoxServer"),
    (r"nakama", "Nakama"),
    (r"\bgrpc\b", "gRPC"),
    (r"protobuf|protocol buffers", "Protocol Buffers 직렬화"),
    (r"messagepack", "MessagePack 직렬화"),
    (r"flatbuffers", "FlatBuffers 직렬화"),
    (r"newtonsoft|\bjson\b", "JSON 직렬화(가능성)"),
    (r"mirror\.|kcp|telepathy", "Unity Mirror/KCP"),
    (r"netty", "Netty"),
]

# 인증서 피닝 지표 (정규식)
PINNING_STRING_SIGNS = [
    (r"certificatepinner", "OkHttp CertificatePinner"),
    (r"trustkit", "TrustKit 피닝"),
    (r"sha256/[A-Za-z0-9+/=]{20,}", "SHA-256 핀 해시(하드코딩)"),
    (r"pinning|pinned", "명시적 pinning 문자열"),
    (r"x509trustmanager", "커스텀 TrustManager"),
]

# 엔드포인트로 관심 있는 호스트 키워드
INTERESTING_HOST_HINTS = [
    "mafia42", "team42", "amazonaws", "cloudfront", "photonengine",
    "exitgames", "gate", "ns.", "socket", "game", "api",
]

# 스캔 대상 zip 엔트리 (이 패턴에 맞는 파일만 문자열 추출 → 속도·결정성)
SCAN_ENTRY_PATTERNS = [
    re.compile(r"^lib/[^/]+/lib.*\.so$"),
    re.compile(r"^classes\d*\.dex$"),
    re.compile(r"global-metadata\.dat$"),
    re.compile(r"^assets/bin/Data/Managed/.*"),
    re.compile(r"^res/xml/.*\.xml$"),
    re.compile(r"^AndroidManifest\.xml$"),
]

URL_RE = re.compile(rb"(?:wss?|https?)://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]{4,200}")
DOMAIN_RE = re.compile(rb"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
                       rb"(?:com|net|io|kr|co|gg|dev|cloud|app)\b", re.IGNORECASE)

MAX_ENTRY_BYTES = 200 * 1024 * 1024  # 엔트리당 스캔 상한(메모리 보호)


# ---- 순수 파이썬 문자열 추출 (외부 strings 불필요) ----

def extract_ascii_strings(data, min_len=5):
    """바이트에서 출력 가능한 ASCII 런을 추출한다. 결정론적."""
    out = []
    run = bytearray()
    for b in data:
        if 0x20 <= b <= 0x7E:
            run.append(b)
        else:
            if len(run) >= min_len:
                out.append(run.decode("ascii"))
            run = bytearray()
    if len(run) >= min_len:
        out.append(run.decode("ascii"))
    return out


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---- 분석 본체 ----

class ApkAnalysis:
    def __init__(self):
        self.apk_files = []          # [(path, sha256, size)]
        self.abis = set()
        self.native_libs = set()     # lib 파일명(경로 제외)
        self.engines = []            # [(lib, 설명)]
        self.net_libs = []           # [(lib, 설명)]
        self.net_strings = {}        # 기술 → 예시 문자열
        self.urls = set()
        self.domains = set()
        self.pinning = {}            # 지표 → 예시
        self.has_network_security_config = False
        self.scanned_entries = []    # [(entry, sha256)]
        self._string_pool = set()

    # --- 수집 ---

    def add_apk(self, path):
        self.apk_files.append((path, sha256_of(path), os.path.getsize(path)))
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            for name in names:
                m = re.match(r"^lib/([^/]+)/(lib.*\.so)$", name)
                if m:
                    self.abis.add(m.group(1))
                    self.native_libs.add(m.group(2))
                if name in ("AndroidManifest.xml",) or name.startswith("res/xml/"):
                    if "network_security_config" in name.lower():
                        self.has_network_security_config = True
            for name in names:
                if any(p.search(name) for p in SCAN_ENTRY_PATTERNS):
                    self._scan_entry(zf, name)

    def _scan_entry(self, zf, name):
        info = zf.getinfo(name)
        if info.file_size > MAX_ENTRY_BYTES:
            return
        try:
            data = zf.read(name)
        except (zipfile.BadZipFile, RuntimeError, OSError):
            return
        self.scanned_entries.append((name, hashlib.sha256(data).hexdigest()))
        # URL / 도메인은 원시 바이트에서 직접 (문자열 최소길이에 안 걸리게)
        for m in URL_RE.findall(data):
            self.urls.add(m.decode("ascii", "replace"))
        if "network_security_config" in name.lower():
            self.has_network_security_config = True
        for m in DOMAIN_RE.findall(data):
            host = m.decode("ascii", "replace").lower()
            if any(h in host for h in INTERESTING_HOST_HINTS):
                self.domains.add(host)
        # ASCII 문자열 풀
        for s in extract_ascii_strings(data, min_len=5):
            self._string_pool.add(s)

    # --- 판정 (규칙 기반, 결정론) ---

    def finalize(self):
        for lib in sorted(self.native_libs):
            low = lib.lower()
            for sign, desc in ENGINE_LIB_SIGNS:
                if sign.lower() in low and (lib, desc) not in self.engines:
                    self.engines.append((lib, desc))
            for sign, desc in NET_LIB_SIGNS:
                if sign.lower() in low and (lib, desc) not in self.net_libs:
                    self.net_libs.append((lib, desc))

        pool_joined = self._string_pool
        for pattern, tech in NET_STRING_SIGNS:
            rx = re.compile(pattern, re.IGNORECASE)
            example = self._first_match(pool_joined, rx)
            if example is not None and tech not in self.net_strings:
                self.net_strings[tech] = example
        for pattern, label in PINNING_STRING_SIGNS:
            rx = re.compile(pattern, re.IGNORECASE)
            example = self._first_match(pool_joined, rx)
            if example is not None and label not in self.pinning:
                self.pinning[label] = example

    @staticmethod
    def _first_match(string_pool, rx):
        """정렬된 문자열 중 첫 매치를 반환(결정론). 없으면 None."""
        for s in sorted(string_pool):
            if rx.search(s):
                return s[:120]
        return None

    # --- 결론 규칙 (전부 결정론적 텍스트) ---

    def conclusions(self):
        c = []
        engine = self.engines[0][1] if self.engines else "판별 불가"
        c.append(f"엔진: {engine}")

        wss = any(u.startswith("wss://") for u in self.urls)
        ws = any(u.startswith("ws://") for u in self.urls)
        photon = any("Photon" in t for t in self.net_strings) or \
            any("Photon" in d for _, d in self.net_libs)
        if photon:
            transport = "Photon(UDP) 기반 실시간 통신 추정"
        elif wss:
            transport = "WebSocket over TLS (wss://) — 암호화된 실시간 소켓"
        elif ws:
            transport = "WebSocket (ws://, 평문) — 캡처로 바로 관찰 가능"
        elif any("Socket.IO" in t for t in self.net_strings):
            transport = "Socket.IO — 내부적으로 WebSocket/HTTP 롱폴링"
        elif self.net_strings:
            transport = "HTTP 계열 " + ", ".join(sorted(self.net_strings)[:3])
        else:
            transport = "전송 방식 문자열 미검출 (동적 분석 필요)"
        c.append(f"전송 방식: {transport}")

        pinned = bool(self.pinning) or self.has_network_security_config
        if pinned:
            c.append("인증서 피닝: 지표 발견 → MITM(mitmproxy)이 막힐 가능성 높음. "
                     "복호화하려면 Frida 언피닝 후킹 필요.")
        else:
            c.append("인증서 피닝: 뚜렷한 지표 미검출 → MITM 프록시로 트래픽 복호화 시도 가치 있음.")

        # 다음 단계 추천 (규칙 기반)
        if photon:
            c.append("다음 단계: Photon은 자체 바이너리 프로토콜이라 순수 캡처로는 해석이 어렵다. "
                     "2단계(PCAPdroid)로 host:port만 확인 후, 실질 데이터는 Frida 후킹 권장.")
        elif wss or any("Socket.IO" in t for t in self.net_strings):
            c.append("다음 단계: 2단계 PCAPdroid로 엔드포인트 확인 → 3단계 mitmproxy로 복호화 시도. "
                     "피닝에 막히면 4단계 Frida.")
        else:
            c.append("다음 단계: 문자열 근거가 부족하니 2단계 동적 캡처(PCAPdroid)부터 진행.")
        return c

    # --- 리포트 ---

    def to_markdown(self):
        self.finalize()
        lines = ["# 마피아42 APK 정적 분석 리포트 (1단계)", ""]
        lines.append("> 결정론적 하네스 출력 — 동일 APK 입력이면 실행 모델/환경과 무관하게 동일 결과.")
        lines.append("")

        lines.append("## 1. 분석 대상")
        for path, digest, size in sorted(self.apk_files):
            lines.append(f"- `{os.path.basename(path)}`  ({size:,} bytes)")
            lines.append(f"  - sha256: `{digest}`")
        lines.append(f"- ABI: {', '.join(sorted(self.abis)) or '(없음)'}")
        lines.append(f"- 스캔한 엔트리 수: {len(self.scanned_entries)}")
        lines.append("")

        lines.append("## 2. 엔진")
        if self.engines:
            for lib, desc in self.engines:
                lines.append(f"- `{lib}` → {desc}")
        else:
            lines.append("- 판별 불가 (네이티브 엔진 라이브러리 미검출)")
        lines.append("")

        lines.append("## 3. 네트워킹 스택")
        if self.net_libs:
            lines.append("### 네이티브 라이브러리")
            for lib, desc in self.net_libs:
                lines.append(f"- `{lib}` → {desc}")
        if self.net_strings:
            lines.append("### 문자열 시그니처")
            for tech in sorted(self.net_strings):
                lines.append(f"- **{tech}**  (예: `{self.net_strings[tech]}`)")
        if not self.net_libs and not self.net_strings:
            lines.append("- 검출된 네트워킹 시그니처 없음")
        lines.append("")

        lines.append("## 4. 서버 엔드포인트")
        if self.urls:
            lines.append("### URL")
            for u in sorted(self.urls)[:50]:
                lines.append(f"- `{u}`")
        if self.domains:
            lines.append("### 관심 도메인")
            for d in sorted(self.domains)[:50]:
                lines.append(f"- `{d}`")
        if not self.urls and not self.domains:
            lines.append("- 엔드포인트 문자열 미검출 (동적 분석 필요)")
        lines.append("")

        lines.append("## 5. 인증서 피닝 지표")
        if self.has_network_security_config:
            lines.append("- `network_security_config` 리소스 존재 (핀셋 정의 가능)")
        if self.pinning:
            for label in sorted(self.pinning):
                lines.append(f"- {label}  (예: `{self.pinning[label]}`)")
        if not self.pinning and not self.has_network_security_config:
            lines.append("- 뚜렷한 피닝 지표 미검출")
        lines.append("")

        lines.append("## 6. 결론 및 다음 단계")
        for c in self.conclusions():
            lines.append(f"- {c}")
        lines.append("")

        lines.append("## 부록: 스캔한 엔트리 (재현 검증용)")
        for name, digest in sorted(self.scanned_entries):
            lines.append(f"- `{name}`  sha256:`{digest[:16]}…`")
        lines.append("")
        return "\n".join(lines)


def analyze(apk_paths):
    """APK 경로 목록을 분석해 (마크다운 리포트, ApkAnalysis) 반환."""
    analysis = ApkAnalysis()
    for path in apk_paths:
        analysis.add_apk(path)
    return analysis.to_markdown(), analysis
