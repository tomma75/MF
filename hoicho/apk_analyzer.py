"""마피아42 APK 정적 분석 하네스 (1단계).

목표: 통신 방식(엔진·전송 프로토콜·서버 엔드포인트·인증서 피닝)을 APK만으로 판별한다.

결정론 원칙:
- 판단은 전부 아래 시그니처 테이블 + 규칙 기반이다. LLM 추론에 의존하지 않으므로
  어떤 모델(예: Opus)이 이 하네스를 호출해도 동일 APK면 동일 리포트가 나온다.
- 외부 도구(aapt/apktool/strings)에 의존하지 않는다. 문자열 추출은 순수 파이썬으로
  구현해 환경 차이에 따른 결과 변동을 없앤다.
- 모든 집합 출력은 정렬한다(정렬 키는 파일 절대경로가 아니라 basename+해시).
  시간·난수 등 비결정 요소는 리포트 본문에 넣지 않고, 재현 검증용으로 SHA-256만 기록한다.

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
    ("libmono", "Unity (Mono 백엔드)"),
    ("libgodot", "Godot"),
    ("libcocos", "Cocos2d-x"),
    ("libunreal", "Unreal Engine"),
    ("libue4", "Unreal Engine 4"),
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

# 문자열 시그니처 → 네트워킹 기술 (대소문자 무시, 정규식). 오탐을 줄이기 위해
# 최대한 특이한 토큰을 쓴다.
NET_STRING_SIGNS = [
    (r"socket\.io", "Socket.IO", True),
    (r"engine\.io", "Engine.IO (Socket.IO 하위)", True),
    (r"exitgames|photonengine|photonnetwork|\bphoton\b", "Photon", True),
    (r"websocket|wss?://", "WebSocket", True),
    (r"okhttp", "OkHttp (HTTP/WebSocket 클라이언트)", True),
    (r"retrofit2?", "Retrofit (REST)", True),
    (r"signalr", "SignalR", True),
    (r"smartfox", "SmartFoxServer", True),
    (r"nakama", "Nakama", True),
    (r"\bgrpc\b", "gRPC", True),
    (r"protobuf|protocol buffers", "Protocol Buffers 직렬화", True),
    (r"messagepack", "MessagePack 직렬화", True),
    (r"flatbuffers", "FlatBuffers 직렬화", True),
    (r"newtonsoft\.json|litjson", "JSON 직렬화 라이브러리", True),
    (r"kcp|telepathy|\bmirror\.networking\b", "Unity Mirror/KCP", True),
    (r"netty", "Netty", True),
]

# 인증서 피닝 지표 (정규식, 대소문자 무시)
PINNING_STRING_SIGNS = [
    (r"certificatepinner", "OkHttp CertificatePinner"),
    (r"trustkit", "TrustKit 피닝"),
    (r"sha256/[A-Za-z0-9+/=]{20,}", "SHA-256 핀 해시(하드코딩)"),
    (r"\bpinning\b|\bpinned\b", "명시적 pinning 문자열"),
    (r"x509trustmanager", "커스텀 TrustManager"),
]

# 실제 서버가 아닌, 노이즈로 걸러낼 URL 호스트 (XML 네임스페이스 등)
IGNORE_URL_HOSTS = [
    "schemas.android.com", "www.w3.org", "apache.org", "xml.org",
    "java.sun.com", "ns.adobe.com", "specs.openid.net", "www.google.com/dtd",
]

# 엔드포인트로 관심 있는 호스트: STRONG는 부분문자열, LABEL은 점 구분 라벨 정확 일치
STRONG_HOST_HINTS = [
    "mafia42", "team42", "amazonaws", "cloudfront", "photonengine", "exitgames",
]
LABEL_HOST_HINTS = ["gate", "ns", "socket", "game", "api", "ws", "realtime", "gw"]

# 스캔 대상 zip 엔트리 (이 패턴에 맞는 파일만 문자열 추출 → 속도·결정성)
SCAN_ENTRY_PATTERNS = [
    re.compile(r"^lib/[^/]+/.*\.so$"),
    re.compile(r"^classes\d*\.dex$"),
    re.compile(r"global-metadata\.dat$"),
    re.compile(r"^assets/bin/Data/Managed/.*"),
    re.compile(r"^res/xml/.*"),
    re.compile(r"^AndroidManifest\.xml$"),
]

URL_RE = re.compile(rb"(?:wss?|https?)://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]{4,200}")
DOMAIN_RE = re.compile(rb"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
                       rb"(?:com|net|io|kr|co|gg|dev|cloud|app)\b", re.IGNORECASE)
NSC_TAG = b"network-security-config"
PINSET_TAGS = [b"<pin-set", b"pin-set", b"pin digest"]

MAX_ENTRY_BYTES = 200 * 1024 * 1024  # 엔트리당 스캔 상한(메모리 보호)


# ---- 순수 파이썬 문자열 추출 (외부 strings 불필요, 정규식으로 대용량 대응) ----

def extract_ascii_strings(data, min_len=5):
    """바이트에서 출력 가능한 ASCII 런을 추출한다. 결정론적."""
    rx = re.compile(b"[\x20-\x7e]{%d,}" % min_len)
    return [m.decode("ascii") for m in rx.findall(data)]


def extract_utf16le_strings(data, min_len=5):
    """UTF-16LE(ASCII 문자 + 0x00 인터리브) 런을 추출한다. Mono/.NET 문자열 대응."""
    rx = re.compile(b"(?:[\x20-\x7e]\x00){%d,}" % min_len)
    return [m.replace(b"\x00", b"").decode("ascii") for m in rx.findall(data)]


def contains_needle(data, needle):
    """ASCII/UTF-16LE 두 형태로 needle 존재를 검사한다(컴파일된 AXML 대응)."""
    if needle in data:
        return True
    return needle.decode("ascii").encode("utf-16-le") in data


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
        self.open_failures = []      # [(path, 이유)]
        self.pull_notes = []         # 외부에서 전달된 경고(예: split pull 실패)
        self.abis = set()
        self.native_libs = set()     # lib 파일명(경로 제외)
        self.engines = []            # [(lib, 설명)]
        self.net_libs = []           # [(lib, 설명)]
        self.net_strings = {}        # 기술 → 예시 문자열
        self.urls = set()
        self.domains = set()
        self.pinning = {}            # 지표 → 예시
        self.has_network_security_config = False
        self.pin_set_found = False
        self.scanned_entries = []    # [(entry, sha256)]
        self._string_pool = set()

    # --- 수집 ---

    def add_apk(self, path):
        """APK 하나를 분석에 추가한다. 손상/열기 실패는 기록하고 False 반환(중단 안 함)."""
        try:
            digest = sha256_of(path)
            size = os.path.getsize(path)
            with zipfile.ZipFile(path) as zf:
                names = zf.namelist()
        except (zipfile.BadZipFile, OSError, RuntimeError) as e:
            self.open_failures.append((path, f"{type(e).__name__}: {e}"))
            print(f"  경고: APK 열기 실패, 건너뜀: {path} ({e})")
            return False

        self.apk_files.append((path, digest, size))
        with zipfile.ZipFile(path) as zf:
            for name in names:
                m = re.match(r"^lib/([^/]+)/(.+\.so)$", name)
                if m:
                    self.abis.add(m.group(1))
                    self.native_libs.add(m.group(2))
            for name in names:
                if any(p.search(name) for p in SCAN_ENTRY_PATTERNS):
                    self._scan_entry(zf, name)
        return True

    def _scan_entry(self, zf, name):
        info = zf.getinfo(name)
        if info.file_size > MAX_ENTRY_BYTES:
            self.pull_notes.append(f"엔트리 {name} 가 상한({MAX_ENTRY_BYTES}B) 초과로 스캔 생략")
            return
        try:
            data = zf.read(name)
        except (zipfile.BadZipFile, RuntimeError, OSError):
            return
        self.scanned_entries.append((name, hashlib.sha256(data).hexdigest()))

        # ASCII + UTF-16LE 문자열 풀
        ascii_runs = extract_ascii_strings(data, min_len=5)
        utf16_runs = extract_utf16le_strings(data, min_len=5)
        for s in ascii_runs:
            self._string_pool.add(s)
        for s in utf16_runs:
            self._string_pool.add(s)

        # URL / 도메인: 원시 바이트 + UTF-16 복원 바이트 양쪽에서
        scan_blobs = [data]
        scan_blobs.extend(run.encode("ascii") for run in utf16_runs)
        for blob in scan_blobs:
            for m in URL_RE.findall(blob):
                url = m.decode("ascii", "replace")
                host = _url_host(url)
                if host and host not in IGNORE_URL_HOSTS:
                    self.urls.add(url)
            for m in DOMAIN_RE.findall(blob):
                host = m.decode("ascii", "replace").lower()
                if self._is_interesting_host(host):
                    self.domains.add(host)

        # 네트워크 보안 설정 / 핀셋: 내용 기반 검사 (파일명 의존 X)
        is_xml = name.startswith("res/xml/") or name == "AndroidManifest.xml"
        if is_xml and contains_needle(data, NSC_TAG):
            self.has_network_security_config = True
        if is_xml and any(contains_needle(data, tag) for tag in PINSET_TAGS):
            self.pin_set_found = True

    @staticmethod
    def _is_interesting_host(host):
        if any(h in host for h in STRONG_HOST_HINTS):
            return True
        labels = host.split(".")
        return any(h in labels for h in LABEL_HOST_HINTS)

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

        for pattern, tech, ignorecase in NET_STRING_SIGNS:
            flags = re.IGNORECASE if ignorecase else 0
            rx = re.compile(pattern, flags)
            example = self._first_match(self._string_pool, rx)
            if example is not None and tech not in self.net_strings:
                self.net_strings[tech] = example
        for pattern, label in PINNING_STRING_SIGNS:
            rx = re.compile(pattern, re.IGNORECASE)
            example = self._first_match(self._string_pool, rx)
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
            transport = "Photon 기반 실시간 통신 추정 (UDP 자체 프로토콜)"
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

        # 피닝은 '실제 핀셋/피닝 라이브러리'가 있을 때만 단정. NSC 존재만으로는 단정 금지.
        if self.pinning or self.pin_set_found:
            c.append("인증서 피닝: 실제 지표 발견(핀셋/피닝 API) → MITM(mitmproxy)이 막힐 "
                     "가능성 높음. 복호화하려면 Frida 언피닝 후킹 필요.")
        elif self.has_network_security_config:
            c.append("인증서 피닝: network_security_config는 있으나 핀셋(<pin-set>) 미검출 → "
                     "피닝이 아닐 수 있음(오히려 user CA 신뢰/cleartext 설정일 수 있음). "
                     "MITM 프록시 복호화 시도 가치 있음.")
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
        for path, digest, size in sorted(self.apk_files, key=lambda t: (os.path.basename(t[0]), t[1])):
            lines.append(f"- `{os.path.basename(path)}`  ({size:,} bytes)")
            lines.append(f"  - sha256: `{digest}`")
        for path, reason in sorted(self.open_failures, key=lambda t: os.path.basename(t[0])):
            lines.append(f"- (열기 실패) `{os.path.basename(path)}` — {_md(reason)}")
        for note in sorted(set(self.pull_notes)):
            lines.append(f"- 경고: {_md(note)}")
        lines.append(f"- ABI: {', '.join(sorted(self.abis)) or '(없음)'}")
        lines.append(f"- 스캔한 엔트리 수: {len(self.scanned_entries)}")
        lines.append("")

        lines.append("## 2. 엔진")
        if self.engines:
            for lib, desc in self.engines:
                lines.append(f"- `{_md(lib)}` → {desc}")
        else:
            lines.append("- 판별 불가 (네이티브 엔진 라이브러리 미검출)")
        lines.append("")

        lines.append("## 3. 네트워킹 스택")
        if self.net_libs:
            lines.append("### 네이티브 라이브러리")
            for lib, desc in self.net_libs:
                lines.append(f"- `{_md(lib)}` → {desc}")
        if self.net_strings:
            lines.append("### 문자열 시그니처")
            for tech in sorted(self.net_strings):
                lines.append(f"- **{tech}**  (예: `{_md(self.net_strings[tech])}`)")
        if not self.net_libs and not self.net_strings:
            lines.append("- 검출된 네트워킹 시그니처 없음")
        lines.append("")

        lines.append("## 4. 서버 엔드포인트")
        if self.urls:
            lines.append("### URL")
            for u in sorted(self.urls)[:50]:
                lines.append(f"- `{_md(u)}`")
        if self.domains:
            lines.append("### 관심 도메인")
            for d in sorted(self.domains)[:50]:
                lines.append(f"- `{_md(d)}`")
        if not self.urls and not self.domains:
            lines.append("- 엔드포인트 문자열 미검출 (동적 분석 필요)")
        lines.append("")

        lines.append("## 5. 인증서 피닝 지표")
        if self.has_network_security_config:
            lines.append("- `network_security_config` 존재 " +
                         ("(핀셋 <pin-set> 검출됨)" if self.pin_set_found else "(핀셋 미검출)"))
        if self.pinning:
            for label in sorted(self.pinning):
                lines.append(f"- {label}  (예: `{_md(self.pinning[label])}`)")
        if not self.pinning and not self.has_network_security_config and not self.pin_set_found:
            lines.append("- 뚜렷한 피닝 지표 미검출")
        lines.append("")

        lines.append("## 6. 결론 및 다음 단계")
        for c in self.conclusions():
            lines.append(f"- {c}")
        lines.append("")

        lines.append("## 부록: 스캔한 엔트리 (재현 검증용)")
        for name, digest in sorted(self.scanned_entries):
            lines.append(f"- `{_md(name)}`  sha256:`{digest[:16]}…`")
        lines.append("")
        return "\n".join(lines)


def _url_host(url):
    """URL에서 host(포트/경로 제외)를 소문자로 추출. 실패 시 ''。"""
    m = re.match(r"[a-z]+://([^/:?#]+)", url, re.IGNORECASE)
    return m.group(1).lower() if m else ""


def _md(s):
    """마크다운 코드스팬 안에 넣기 위해 백틱을 안전한 문자로 치환."""
    return s.replace("`", "ˋ")


def analyze(apk_paths, extra_notes=None):
    """APK 경로 목록을 분석해 (마크다운 리포트, ApkAnalysis) 반환."""
    analysis = ApkAnalysis()
    if extra_notes:
        analysis.pull_notes.extend(extra_notes)
    for path in apk_paths:
        analysis.add_apk(path)
    return analysis.to_markdown(), analysis
