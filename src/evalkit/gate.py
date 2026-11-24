"""Regression gate for CI: fail the build if a metric drops versus the committed baseline.

    python -m evalkit.gate --dataset financebench

Baseline lives in evals/baseline/<dataset>.json and is updated on purpose
(`--update`) when a change is reviewed and accepted, never automatically.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOLERANCE = 0.02          # allowed absolute drop before we call it a regression
WATCH = {"retrieval": ("+filing_routing_v2", ["hit@5", "hit@10", "mrr", "doc_hit@5"]),
         "answers": ["accuracy", "citation_page_precision"]}


def current(dataset: str) -> dict:
    res = ROOT / "evals" / "results" / dataset
    ret = json.loads((res / "retrieval_summary.json").read_text())
    cfg, keys = WATCH["retrieval"]
    out = {f"retrieval.{k}": ret[cfg]["overall"][k] for k in keys}
    ans = res / "answers_summary.json"
    if ans.exists():
        a = json.loads(ans.read_text())
        out.update({f"answers.{k}": a[k] for k in WATCH["answers"] if a.get(k) is not None})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="financebench")
    ap.add_argument("--update", action="store_true")
    a = ap.parse_args(argv)
    base_path = ROOT / "evals" / "baseline" / f"{a.dataset}.json"
    now = current(a.dataset)
    if a.update or not base_path.exists():
        base_path.parent.mkdir(parents=True, exist_ok=True)
        base_path.write_text(json.dumps(now, indent=2))
        print(f"baseline written: {base_path}")
        return 0
    base = json.loads(base_path.read_text())
    failed = False
    for k, b in base.items():
        if k not in now:
            print(f"  [SKIP] {k}: not measured in this run")
            continue
        delta = now[k] - b
        bad = delta < -TOLERANCE
        failed |= bad
        print(f"  [{'FAIL' if bad else 'OK'}] {k}: baseline {b:.3f} -> now {now[k]:.3f} ({delta:+.3f})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
