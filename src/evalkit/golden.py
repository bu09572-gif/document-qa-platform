"""The golden set: 50 FinanceBench questions held out as a fixed test set.

    python -m evalkit.golden            # (re)build evals/golden/financebench_golden50.jsonl

Selection is stratified by question type (domain-relevant / metrics-generated /
novel-generated) and filing type (10-K vs. 10-Q / 8-K / earnings release), with a
hash of the question id as the order inside each group, so it is the same on
every machine. The other 100 questions are the dev set: every retrieval and prompt
setting is tuned on dev only, and the golden 50 are used to report results.

I read every item against its evidence page (evals/golden/review.json). One dataset
answer was wrong and is corrected there; the original is kept under tags.dataset_answer.

Each golden item also carries labels used by the failure analysis:
  answer_type  number | yes_no | text
  skill        lookup (the answer is stated, or is one table value) | calculation (arithmetic on
               several values) | judgment (needs domain reasoning, e.g. "gross margin is not a bank metric")
  pages        how many evidence pages the expert answer needs
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from . import metrics as M
from .dataset import EvalItem, from_financebench

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "evals" / "golden" / "financebench_golden50.jsonl"
REVIEW = ROOT / "evals" / "golden" / "review.json"
SIZE = 50


def _order(i: EvalItem) -> str:
    return hashlib.sha256(i.id.encode()).hexdigest()


def stratum(i: EvalItem) -> tuple[str, str]:
    return i.tags.get("question_type", ""), "10k" if (i.doc_id or "").upper().find("10K") >= 0 else "other"


def select(items: list[EvalItem], size: int = SIZE) -> list[EvalItem]:
    groups: dict[tuple, list[EvalItem]] = {}
    for it in items:
        groups.setdefault(stratum(it), []).append(it)
    quota = {k: size * len(v) / len(items) for k, v in groups.items()}
    take = {k: int(q) for k, q in quota.items()}
    for k in sorted(quota, key=lambda k: (take[k] - quota[k], k))[: size - sum(take.values())]:
        take[k] += 1                                  # largest remainder, so the total is exactly `size`
    out = []
    for k in sorted(groups):
        out += sorted(groups[k], key=_order)[: take[k]]
    return sorted(out, key=lambda i: i.id)


def answer_type(gold: str) -> str:
    g = gold.strip().lower()
    if g.startswith(("yes", "no")) and len(g) < 400:
        return "yes_no"
    if M.numbers(gold) and len(gold) < 60:
        return "number"
    return "text"


def skill(it: EvalItem) -> str:
    r = str(it.tags.get("reasoning") or "").lower()
    if answer_type(it.gold_answer) != "number":
        return "judgment"
    return "calculation" if "numerical" in r else "lookup"


def label(it: EvalItem) -> dict:
    pages = {(e["doc_id"], e["page_num"]) for e in it.gold_evidence}
    return {"answer_type": answer_type(it.gold_answer), "skill": skill(it), "pages": len(pages)}


def build() -> list[EvalItem]:
    items = select(from_financebench())
    review = json.loads(REVIEW.read_text()) if REVIEW.exists() else {}
    for it in items:
        it.tags.update(label(it))
        r = review.get(it.id, {})
        it.tags.update(r.get("tags", {}))                         # manual corrections win
        if "gold_answer" in r:
            it.tags["dataset_answer"] = it.gold_answer
            it.gold_answer = r["gold_answer"]
        if "note" in r:
            it.tags["review_note"] = r["note"]
    GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN.write_text("\n".join(json.dumps(asdict(i)) for i in items) + "\n")
    return items


def golden_ids() -> set[str]:
    return {json.loads(line)["id"] for line in GOLDEN.read_text().splitlines() if line.strip()}


def split(items: list[EvalItem], part: str) -> list[EvalItem]:
    """part: all | golden | dev"""
    if part == "all":
        return items
    ids = golden_ids()
    return [i for i in items if (i.id in ids) == (part == "golden")]


if __name__ == "__main__":
    from collections import Counter
    its = build()
    print(len(its), "items ->", GOLDEN)
    print(Counter(stratum(i) for i in its))
    print(Counter(i.tags["answer_type"] for i in its), Counter(i.tags["skill"] for i in its))
