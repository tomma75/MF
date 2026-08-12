#!/usr/bin/env python3
"""대시보드 생성기 — cohort_registry.json + daily_followup.md + candidate_scan_*.md 를 결합해
validation/dashboard.html 을 생성한다. 재현 가능(리포 내 영구 저장).
사용: python3 validation/harness/gen_dashboard.py
"""
import json, re, os, glob

HERE = os.path.dirname(os.path.abspath(__file__))
VDIR = os.path.normpath(os.path.join(HERE, ".."))
REG = os.path.join(HERE, "cohort_registry.json")
LOG = os.path.join(VDIR, "daily_followup.md")
OUT = os.path.join(VDIR, "dashboard.html")

sn = lambda s: str(s or "").split("(")[0].split("—")[0].strip()
norm = lambda s: re.sub(r"[^0-9A-Za-z]", "", str(s or "")).upper()

def build_data():
    reg = json.load(open(REG, encoding="utf-8"))
    log = open(LOG, encoding="utf-8").read()
    # latest learning note per name across all rounds
    notes = {}
    for rm in re.finditer(r"## Round (\d+).*?(?=\n## Round |\Z)", log, re.S):
        rn = int(rm.group(1)); blk = rm.group(0)
        for bm in re.finditer(r"^- \*\*\[(HIT|MISS|EARLY|VOID|PENDING|NO_DATA)\] ([^\]]+?)\*\* \(([^)]+)\): (.+)$", blk, re.M):
            notes[sn(bm.group(2))] = {"code": bm.group(1), "note": bm.group(4).strip(), "round": rn}
    # dossiers (why_matches / counterview) from persisted scan markdown(s)
    doss = {}
    for md in glob.glob(os.path.join(VDIR, "candidate_scan_*.md")):
        txt = open(md, encoding="utf-8").read()
        for blk in re.split(r"(?=^### )", txt, flags=re.M):
            if not blk.startswith("### "): continue
            hm = re.search(r"\((\d{6}|[A-Z]{2,6})\)", blk)
            key = norm(hm.group(1)) if hm else None
            why = re.search(r"- \*\*시그니처 부합\*\*: (.+)", blk)
            ct = re.search(r"- \*\*적대적 반대해석[^*]*\*\*: (.+)", blk)
            sig = re.search(r"· sig ([A-F,]+)", blk)
            sc = re.search(r"^### \[(\d+)\]", blk)
            if key:
                doss[key] = {"why": why.group(1).strip() if why else None,
                             "counter": ct.group(1).strip() if ct else None,
                             "sig": sig.group(1) if sig else None,
                             "score": int(sc.group(1)) if sc else None}
    # enrich targets
    for t in reg["targets"]:
        nm = sn(t["name"]); ln = notes.get(nm)
        if ln:
            t["learning_note"] = ln["note"]; t["learning_round"] = ln["round"]; t["learning_code"] = ln["code"]
        ds = doss.get(norm(t.get("symbol")))
        if ds:
            if ds["sig"]: t["sig"] = ds["sig"]
            if ds["score"] is not None: t["setup_score"] = ds["score"]
            if ds["why"]: t["why_matches"] = ds["why"]
            if ds["counter"]: t["counterview"] = ds["counter"]
    # rounds + latest verdicts
    rounds = []
    for m in re.finditer(r"## Round (\d+) — (\S+) \((\d+)건\)\n판정 분포: \*\*(.+?)\*\*", log):
        rounds.append({"round": int(m.group(1)), "date": m.group(2), "n": int(m.group(3)), "dist": m.group(4)})
    blocks = [b for b in re.split(r"(?=^## Round \d+)", log, flags=re.M) if b.startswith("## Round")]
    verd = {}
    if blocks:
        for row in re.finditer(r"^\| \*\*(HIT|MISS|EARLY|VOID|PENDING|NO_DATA)\*\* \| ([^|]+?) \| ([^|]+?) \|", blocks[-1], re.M):
            verd[row.group(3).strip()] = row.group(1)
    # ignition ranking (top5 폭등 유력), if present — 현재 active+preramp 종목만(스테일 방지)
    ignition = []
    ig_asof = None
    rp = os.path.join(HERE, "ignition_rank.json")
    if os.path.exists(rp):
        ig = json.load(open(rp, encoding="utf-8"))
        ig_asof = ig.get("as_of")
        def _tradeable(t):
            f = t.get("note_flag", "") or ""
            return not ("정지" in f or "상방" in f)  # 거래정지·이미 급등(상방제한)은 폭등 Top 제외
        live = {norm(t.get("symbol")) for t in reg["targets"]
                if t.get("status") == "active" and t.get("layer") == "preramp" and _tradeable(t)}
        ranked = [d for d in ig.get("ranked", []) if norm(d.get("symbol")) in live]
        ignition = ranked[:5]
    # LR calibration summary, if present
    lr = None
    lp = os.path.join(HERE, "lr_summary.json")
    if os.path.exists(lp):
        lr = json.load(open(lp, encoding="utf-8"))
    return {"version": reg["version"], "as_of": reg["as_of"], "targets": reg["targets"],
            "rounds": rounds, "latest_verdicts": verd, "ignition": ignition, "ignition_asof": ig_asof, "lr": lr}

TPL = os.path.join(HERE, "dashboard_template.html")

def main():
    data = build_data()
    template = open(TPL, encoding="utf-8").read()
    html = template.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    open(OUT, "w", encoding="utf-8").write(html)
    active = sum(1 for t in data["targets"] if t.get("status") == "active")
    print(f"[gen_dashboard] wrote {os.path.relpath(OUT)} — v{data['version']}, active {active}, rounds {len(data['rounds'])}, {len(html)} bytes")

if __name__ == "__main__":
    main()
