#!/usr/bin/env python3
"""F/U 워크플로우 args 생성기 — cohort_registry.json에서 active 대상만 추출해 JSON 출력.
사용: python3 validation/harness/build_args.py
출력(stdout): Workflow args로 그대로 전달할 JSON 배열. 결정론적(정렬 고정)."""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, "cohort_registry.json")

def main():
    reg = json.load(open(REG, encoding="utf-8"))
    targets = [t for t in reg["targets"] if t.get("status") == "active"]
    # 결정론: (layer, name) 정렬 고정
    targets.sort(key=lambda t: (t.get("layer", ""), t.get("name", "")))
    out = [
        {
            "name": t["name"], "symbol": t.get("symbol", ""), "mkt": t.get("mkt", ""),
            "layer": t.get("layer", ""), "window": t.get("window", ""),
            "trigger": t.get("trigger", ""), "falsify": t.get("falsify", ""),
        }
        for t in targets
    ]
    json.dump(out, sys.stdout, ensure_ascii=False)
    print(file=sys.stderr)
    print(f"[build_args] active {len(out)} / total {len(reg['targets'])} (registry v{reg.get('version')})", file=sys.stderr)

if __name__ == "__main__":
    main()
