"""Unit tests. Tiny hand-written inputs check the logic; the real numbers come from
running the pipeline and evals on FinanceBench (see README)."""

import pandas as pd
import pytest

from docpipe.chunk import build_chunks, chunk_page
from docpipe.quality import run_checks
from docqa.answer import Answer, answer
from docqa.retrieve import Retriever, detect_filters, expand_query, rrf
from evalkit import metrics as M


def _chunks():
    rows = [
        ("a1", "ACME_2022_10K", 10, "ACME", 2022, "Net sales were $1,577 million in 2022 driven by industrial demand."),
        ("a2", "ACME_2022_10K", 40, "ACME", 2022, "Purchases of property, plant and equipment were $300 million."),
        ("b1", "BETA_2021_10K", 12, "Beta Corp", 2021, "Net sales were $900 million. Purchases of property plant and equipment $50 million."),
    ]
    return pd.DataFrame([{"chunk_id": c, "doc_id": d, "page_num": p, "part": 0, "company": co, "doc_type": "10K",
                          "period": y, "sector": "Industrials", "header": f"{co} | 10K {y} | page {p}", "text": t,
                          "n_words": len(t.split())} for c, d, p, co, y, t in rows])


# ---------- pipeline ----------
def test_chunk_page_windows_overlap():
    words = " ".join(f"w{i}" for i in range(500))
    parts = chunk_page(words, size=220, overlap=40)
    assert len(parts) == 3 and parts[1].split()[0] == "w180"
    assert chunk_page("too short") == []


def test_build_chunks_keeps_page_and_metadata():
    pages = pd.DataFrame([{"doc_id": "D", "page_num": 3, "text": "word " * 30, "n_chars": 150}])
    man = pd.DataFrame([{"doc_id": "D", "company": "ACME", "doc_type": "10K", "period": 2022, "sector": "X"}])
    c = build_chunks(pages, man)
    assert c.page_num.tolist() == [3] and c.header[0] == "ACME | 10K 2022 | page 3"


def test_quality_checks_catch_missing_pages():
    man = pd.DataFrame([{"doc_id": "D1", "sha256": "x"}, {"doc_id": "D2", "sha256": "y"}])
    pages = pd.DataFrame([{"doc_id": "D1", "page_num": 0, "text": "t" * 100, "n_chars": 100}])
    checks = {c.name: c for c in run_checks(man, pages, _chunks().assign(doc_id="D1"))}
    assert not checks["every_doc_has_pages"].passed and checks["every_doc_has_pages"].observed == ["D2"]


# ---------- retrieval ----------
def test_filters_detect_company_and_year():
    assert detect_filters("What was Beta Corp's FY2021 capex?", ["ACME", "Beta Corp"]) == {"company": "Beta Corp", "period": 2021}


def test_query_expansion_bridges_vocabulary():
    assert "purchases of property plant and equipment" in expand_query("FY2022 capital expenditure")


def test_retriever_uses_filters_and_expansion():
    r = Retriever(_chunks())
    hits, f = r.search("What is ACME's FY2022 capital expenditure?", k=1)
    assert f == {"company": "ACME", "period": 2022} and hits[0].chunk_id == "a2"


def test_rrf_rewards_agreement():
    import numpy as np
    fused = rrf([np.array([0, 1, 2]), np.array([0, 2, 1])])
    assert fused.argmax() == 0


# ---------- answer ----------
def test_free_path_parses_source_tags(monkeypatch):
    from docqa import llm
    hits, _ = Retriever(_chunks()).search("ACME FY2022 net sales", k=2)
    fake = llm.Completion("Net sales were $1,577 million [S1]. Also see [S9] and [S1].", 900, 40, 1.2,
                          "qwen2.5:3b", "ollama")
    monkeypatch.setattr(llm, "chat", lambda *a, **kw: fake)
    a = answer("ACME FY2022 net sales?", hits, provider="ollama")
    assert [c.page_num for c in a.citations] == [hits[0].page_num]     # [S9] doesn't exist, duplicate [S1] dropped
    assert a.cost_usd == 0.0


def test_summary_from_rows():
    from evalkit.run import summarize
    rows = pd.DataFrame([
        {"grade": "correct", "numeric_match": 1.0, "retrieval_hit": 1.0, "citations": ["a:1"], "citation_page_precision": 1.0,
         "question_type": "x", "cost_usd": 0.0, "latency_s": 2.0},
        {"grade": "refused", "numeric_match": None, "retrieval_hit": 0.0, "citations": [], "citation_page_precision": None,
         "question_type": "x", "cost_usd": 0.0, "latency_s": 4.0},
    ]).assign(config="c", k=5, provider="ollama", model="m", judge_model="j")
    rows = rows.assign(answer=["The value is $1,577 million [S1].", "Not enough information in the provided filings."],
                       gold_answer=["$1577.00", "Yes"])
    rows.loc[1, "grade"] = "correct"          # a lenient judge calling a refusal correct...
    s = summarize(rows)
    assert s["refusal_rate"] == 0.5 and s["accuracy"] == 0.5   # ...is overridden by the rule
    assert s["judge_called_refusals_correct"] == 1.0 and s["answers_with_citations"] == 0.5
    assert s["accuracy_when_retrieval_hit_vs_miss"] == {"hit": 1.0, "miss": 0.0}


def test_refusal_detection():
    assert Answer("Not enough information in the provided filings.").refused


# ---------- eval metrics ----------
@pytest.mark.parametrize("ans,gold,exp", [
    ("Capex was $1,577 million.", "$1577.00", 1.0),
    ("About 1.7 billion", "$1577.00", 0.0),           # outside 1% tolerance
    ("Margin of 24.5%", "24.5%", 1.0),
    ("Capex was $1.577 billion", "$1577.00", 1.0),
    ("No", "Yes, it is capital intensive", None),
    ("Not in sources [S1] for Q2 of FY2023", "0.96", 0.0),   # citation tags and years are not answers
])
def test_numeric_match(ans, gold, exp):
    assert M.numeric_match(ans, gold) == exp


def test_hit_and_mrr():
    assert M.hit_at_k(["a", "b"], {"b"}, 1) == 0 and M.hit_at_k(["a", "b"], {"b"}, 2) == 1
    assert M.mrr(["a", "b", "c"], {"c"}) == pytest.approx(1 / 3)
    assert M.citation_page_precision(["x", "y"], {"x"}) == 0.5


# ---------- v2: routing, golden set, failure buckets ----------
def _docs():
    return pd.DataFrame([{"doc_id": d, "company": c, "period": p, "doc_type": t} for d, c, p, t in [
        ("JPMORGAN_2022_10K", "JPMorgan", 2022, "10K"), ("JPMORGAN_2022Q2_10Q", "JPMorgan", 2022, "10Q"),
        ("WALMART_2020_10K", "Walmart", 2020, "10K"), ("WALMART_2018_10K", "Walmart", 2018, "10K"),
        ("BOEING_2022_10K", "Boeing", 2022, "10K")]])


def test_route_alias_quarter_and_latest_year():
    from docqa.retrieve import route
    assert route("In 2022 Q2, which of JPM's segments had the highest net income?", _docs())[0] == ["JPMORGAN_2022Q2_10Q"]
    assert route("FY2018 - FY2020 3 year average EBITDA margin for Walmart?", _docs())[0] == ["WALMART_2020_10K"]
    ids, info = route("What production rate changes is Boeing forecasting for FY2023?", _docs())
    assert ids == ["BOEING_2022_10K"] and "period" not in info      # no 2023 filing: don't filter to nothing
    assert route("What is the capital of France?", _docs())[0] is None


def test_golden_selection_is_stratified_and_stable():
    from evalkit.dataset import EvalItem
    from evalkit.golden import select
    items = [EvalItem(f"q{i}", "q", "1", tags={"question_type": "abc"[i % 3]}, doc_id="X_10K") for i in range(150)]
    a, b = select(items), select(list(reversed(items)))
    assert len(a) == 50 and [i.id for i in a] == [i.id for i in b]
    assert sorted(sum(i.tags["question_type"] == t for i in a) for t in "abc") == [16, 17, 17]


def test_failure_buckets():
    from types import SimpleNamespace as S

    from evalkit.failures import bucket
    base = dict(final_grade="incorrect", doc_hit=True, gold_pages=["a:1"], evidence_pages_found=1,
                answer_type="number", numeric_match=0.0)
    assert bucket(S(**{**base, "final_grade": "correct"})) == "correct"
    assert bucket(S(**{**base, "doc_hit": False})) == "wrong_filing"
    assert bucket(S(**{**base, "evidence_pages_found": 0})) == "evidence_page_missed"
    assert bucket(S(**{**base, "gold_pages": ["a:1", "a:2"]})) == "partial_evidence"
    assert bucket(S(**{**base, "final_grade": "refused"})) == "refused_with_evidence"
    assert bucket(S(**base)) == "wrong_number"
    assert bucket(S(**{**base, "answer_type": "text", "numeric_match": None})) == "wrong_conclusion"


def test_final_grade_order():
    from evalkit.metrics import final_grade
    assert final_grade("correct", True, None) == "refused"                      # refusals by rule
    assert final_grade("correct", False, 0.0, answer_type="number") == "incorrect"
    assert final_grade("correct", False, 0.0, answer_type="text") == "correct"  # a text answer may skip the number
    assert final_grade("correct", False, None, manual="incorrect") == "incorrect"
