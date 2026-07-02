#!/usr/bin/env python3
"""F/U 라운드 결정론적 후처리기.
사용: python3 validation/harness/postprocess_fu.py <workflow_output_file> [--date YYYY-MM-DD] [--dry-run]
동작(모델 재량 없음):
 1) 워크플로우 출력 JSON 파싱 → 판정 정규화(코드 접두어 추출)
 2) daily_followup.md의 기존 'Round N' 최대값+1로 라운드 번호 자동 산정
 3) 고정 포맷 블록을 앵커 주석 앞에 삽입(과거 블록 불변)
 4) cohort_registry.json 상태 전이(고정 규칙): VOID→closed, MISS→closed,
    EARLY→closed(사후확인), preramp HIT→layer=collapse-watch(발화 후 감시), 그 외 유지
 5) 요약을 stdout으로 출력(드라이버는 이 요약을 사용자에게 전달만 하면 됨)
"""
import json, os, re, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REG_PATH = os.path.join(HERE, "cohort_registry.json")
LOG_PATH = os.path.normpath(os.path.join(HERE, "..", "daily_followup.md"))
ANCHOR = "<!-- 이후: ## YYYY-MM-DD (거래일) / 변동 종목 + 판정(HIT/MISS/EARLY/VOID) + 학습노트 + 출처 -->"
CODES = ("HIT", "MISS", "EARLY", "VOID", "PENDING", "NO_DATA")
ORDER = {c: i for i, c in enumerate(("HIT", "EARLY", "VOID", "MISS", "PENDING", "NO_DATA"))}

def cl(x, n=None):
    s = re.sub(r"\s+", " ", str(x or "")).strip()
    return s[:n] if n else s

def verdict_code(v):
    m = re.match(r"\s*(HIT|MISS|EARLY|VOID|PENDING|NO_DATA)", str(v or ""), re.I)
    return m.group(1).upper() if m else "NO_DATA"

def short_name(x):
    return cl(str(x or "").split("(")[0].split("—")[0])

def main():
    argv = sys.argv[1:]
    if not argv:
        sys.exit("usage: postprocess_fu.py <workflow_output_file> [--date YYYY-MM-DD] [--dry-run]")
    out_file = argv[0]
    dry = "--dry-run" in argv
    date = None
    if "--date" in argv:
        date = argv[argv.index("--date") + 1]
    if not date:
        date = datetime.date.today().isoformat()

    raw = json.load(open(out_file, encoding="utf-8"))
    res = raw.get("result", raw)
    if isinstance(res, str):
        res = json.loads(res)
    rc, syn = res["rc"], res.get("syn", {})

    # --- round number ---
    log = open(LOG_PATH, encoding="utf-8").read()
    rounds = [int(m) for m in re.findall(r"^## Round (\d+)", log, re.M)]
    rn = (max(rounds) + 1) if rounds else 1

    # --- verdict table ---
    items = []
    for x in rc:
        items.append({
            "name": short_name(x.get("name")), "layer": x.get("layer", "?"),
            "code": verdict_code(x.get("verdict")),
            "one": cl(x.get("change_since_baseline") or x.get("current_status"), 90),
            "note": cl(x.get("learning_note"), 420),
        })
    items.sort(key=lambda i: (ORDER.get(i["code"], 9), i["layer"], i["name"]))
    dist = {}
    for i in items:
        dist[i["code"]] = dist.get(i["code"], 0) + 1
    dist_s = " · ".join(f"{k} {v}" for k, v in sorted(dist.items(), key=lambda kv: ORDER.get(kv[0], 9)))

    L = []
    L.append(f"\n## Round {rn} — {date} ({len(items)}건)")
    L.append(f"판정 분포: **{dist_s}**.")
    L.append("\n| 판정 | 층 | 종목 | 요지 |")
    L.append("|---|---|---|---|")
    for i in items:
        L.append(f"| **{i['code']}** | {i['layer']} | {i['name']} | {i['one']} |")
    nonpend = [i for i in items if i["code"] not in ("PENDING",)]
    if nonpend:
        L.append("\n### 판정 근거·학습노트")
        for i in nonpend:
            L.append(f"- **[{i['code']}] {i['name']}** ({i['layer']}): {i['note']}")
    if syn.get("learning"):
        L.append("\n### 트리거 모델 업데이트")
        for h in syn["learning"]:
            L.append(f"- {cl(h, 400)}")
    if syn.get("next_priorities"):
        L.append("\n### 다음 라운드 관찰 우선순위")
        for h in syn["next_priorities"]:
            L.append(f"- {cl(h, 300)}")
    if syn.get("metrics_note"):
        L.append(f"\n### 라운드 메트릭\n{cl(syn['metrics_note'], 700)}")
    block = "\n".join(L)

    # --- registry transitions (deterministic; symbol 우선, 이름 fallback) ---
    def norm_sym(s):
        return re.sub(r"[^0-9A-Za-z]", "", str(s or "")).upper()

    reg = json.load(open(REG_PATH, encoding="utf-8"))
    by_name, by_sym = {}, {}
    for t in reg["targets"]:
        by_name[short_name(t["name"])] = t
        ns = norm_sym(t.get("symbol"))
        if ns:
            by_sym[ns] = t
    rc_sym = {}
    for x in rc:
        rc_sym[short_name(x.get("name"))] = norm_sym(x.get("symbol"))
    transitions = []
    for i in items:
        t = by_sym.get(rc_sym.get(i["name"], "")) or by_name.get(i["name"])
        if not t or t.get("status") != "active":
            continue
        c = i["code"]
        if c in ("VOID", "MISS", "EARLY"):
            t["status"] = "closed"
            t["closed_reason"] = f"R{rn} {c} — {i['note'][:160]}"
            transitions.append(f"{i['name']}: active→closed ({c})")
        elif c == "HIT" and t.get("layer") == "preramp":
            t["layer"] = "collapse-watch"
            transitions.append(f"{i['name']}: preramp→collapse-watch (HIT 발화)")
    reg["version"] = int(reg.get("version", 1)) + 1
    reg["as_of"] = date

    if dry:
        print(block)
        print("\n[dry-run] transitions:", transitions or "none")
        return

    assert ANCHOR in log, "anchor comment missing in daily_followup.md"
    log = log.replace(ANCHOR, block.strip() + "\n\n" + ANCHOR)
    open(LOG_PATH, "w", encoding="utf-8").write(log)
    json.dump(reg, open(REG_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"[postprocess] Round {rn} appended to {os.path.relpath(LOG_PATH)}")
    print(f"[postprocess] verdicts: {dist_s}")
    print(f"[postprocess] registry v{reg['version']}: transitions = {transitions or 'none'}")
    active = sum(1 for t in reg["targets"] if t.get("status") == "active")
    print(f"[postprocess] active targets remaining: {active}")

if __name__ == "__main__":
    main()
