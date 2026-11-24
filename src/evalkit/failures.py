"""Failure analysis: put every graded answer into exactly one bucket, so the fix for each bucket is clear.

    python -m evalkit.failures evals/results/financebench/answers_golden_<config>_<model>.jsonl

Buckets, checked in this order:
  correct
  wrong_filing            no retrieved page is from the filing the question is about  -> routing
  evidence_page_missed    right filing, but none of the expert's evidence pages in the top k -> ranking
  partial_evidence        the answer needs 2+ pages and only some were retrieved      -> multi-page retrieval
  refused_with_evidence   evidence was in the context, the model still said "not enough information"
  wrong_number            evidence in context, numeric answer, wrong number           -> reading / arithmetic
  wrong_conclusion        evidence in context, yes/no or text answer judged wrong     -> reasoning

The first three are retrieval failures, the last three are generation failures.
Writes <name>_failures.json and <name>_failures.md next to the input.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from . import metrics as M

BUCKETS = ["correct", "wrong_filing", "evidence_page_missed", "partial_evidence", "refused_with_evidence",
           "wrong_number", "wrong_conclusion"]
FIX = {
    "wrong_filing": "routing: company / year / quarter detection, or ask the user which filing",
    "evidence_page_missed": "ranking: better embeddings or reranker, table-aware chunks",
    "partial_evidence": "multi-page retrieval: one search per statement (income statement AND balance sheet)",
    "refused_with_evidence": "prompt / model: the context had the numbers; a bigger model or a 'find the line items first' step",
    "wrong_number": "reading tables: line-item extraction before arithmetic, use a calculator tool",
    "wrong_conclusion": "reasoning: bigger model, or domain hints (e.g. 'gross margin does not apply to banks')",
}


def grade_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Same final grade as the summary: refusals by rule, numeric answers checked against the gold number."""
    from docqa.answer import Answer
    df = df.copy()
    df["refused"] = df.answer.map(lambda t: Answer(str(t)).refused)
    df["numeric_match"] = [M.numeric_match(str(a), str(g)) if not r else None
                           for a, g, r in zip(df.answer, df.gold_answer, df.refused)]
    manual = M.manual_grades(M.run_name(df.config.iloc[0], df.provider.iloc[0], df.model.iloc[0]))
    atype = df.answer_type if "answer_type" in df else [None] * len(df)
    df["final_grade"] = [M.final_grade(j, r, n if pd.notna(n) else None, manual.get(i), t)
                         for j, r, n, i, t in zip(df.grade, df.refused, df.numeric_match, df.id, atype)]
    return df


def bucket(r) -> str:
    if r.final_grade == "correct":
        return "correct"
    if not r.doc_hit:
        return "wrong_filing"
    need = len(r.gold_pages)
    if r.evidence_pages_found == 0:
        return "evidence_page_missed"
    if r.evidence_pages_found < need:
        return "partial_evidence"
    if r.final_grade == "refused":
        return "refused_with_evidence"
    if r.answer_type == "number" or r.numeric_match == 0.0:
        return "wrong_number"
    return "wrong_conclusion"


def analyse(path: Path) -> dict:
    df = grade_rows(pd.read_json(path, lines=True))
    df["bucket"] = [bucket(r) for r in df.itertuples()]
    n = len(df)
    counts = df.bucket.value_counts().reindex(BUCKETS, fill_value=0)
    by_skill = pd.crosstab(df.bucket, df.skill).reindex(BUCKETS, fill_value=0) if "skill" in df else None
    out = {
        "file": path.name, "n": n, "model": df.model.iloc[0], "config": df.config.iloc[0],
        "buckets": {b: {"count": int(c), "share": round(c / n, 3)} for b, c in counts.items()},
        "retrieval_failures": int(counts[["wrong_filing", "evidence_page_missed", "partial_evidence"]].sum()),
        "generation_failures": int(counts[["refused_with_evidence", "wrong_number", "wrong_conclusion"]].sum()),
        "by_skill": by_skill.to_dict() if by_skill is not None else {},
        "examples": {b: df[df.bucket == b].head(3)[["id", "question", "gold_answer", "answer"]]
                     .assign(question=lambda x: x.question.str[:220], answer=lambda x: x.answer.str[:300])
                     .to_dict("records") for b in BUCKETS if b != "correct"},
        "per_question": df[["id", "bucket", "final_grade", "skill", "answer_type", "evidence_pages_found"]]
        .to_dict("records"),
    }
    stem = path.with_suffix("")
    Path(f"{stem}_failures.json").write_text(json.dumps(out, indent=2, default=str))
    Path(f"{stem}_failures.md").write_text(markdown(out))
    return out


def markdown(o: dict) -> str:
    lines = [f"# Failure analysis: {o['model']}, retrieval `{o['config']}`, {o['n']} golden questions", "",
             "| Bucket | Count | Share | What would fix it |", "|---|---|---|---|"]
    for b, v in o["buckets"].items():
        lines.append(f"| {b} | {v['count']} | {v['share']:.0%} | {FIX.get(b, '')} |")
    lines += ["", f"Retrieval failures: {o['retrieval_failures']}. Generation failures: {o['generation_failures']}.", ""]
    if o["by_skill"]:
        skills = sorted(o["by_skill"])
        lines += ["| Bucket | " + " | ".join(skills) + " |", "|---|" + "---|" * len(skills)]
        for b in BUCKETS:
            lines.append(f"| {b} | " + " | ".join(str(o["by_skill"][s].get(b, 0)) for s in skills) + " |")
        lines.append("")
    for b, ex in o["examples"].items():
        if not ex:
            continue
        lines += [f"## {b}", ""]
        for e in ex:
            ans = " ".join(str(e["answer"]).split())
            lines += [f"- **{e['id']}**: {e['question']}", f"  - expert: {e['gold_answer']}", f"  - model: {ans}"]
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        o = analyse(Path(p))
        print(json.dumps({k: o[k] for k in ("n", "buckets", "retrieval_failures", "generation_failures")}, indent=2))
