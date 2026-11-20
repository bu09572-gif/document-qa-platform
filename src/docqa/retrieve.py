"""Retrieval over the gold chunks: BM25 (sparse), optional dense embeddings, hybrid fusion.

BM25 is implemented directly on a scipy sparse matrix so it is fast on ~40k
chunks and easy to explain:  score(q, d) = sum over query terms t of
    idf(t) * tf(t,d) * (k1 + 1) / (tf(t,d) + k1 * (1 - b + b * len(d) / avg_len))

Metadata filters (company, period, doc type) are applied before ranking. In
finance, "revenue" without the right company and year is the wrong answer, so
we detect the company and fiscal year in the question and filter on them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer

TOKEN = r"(?u)\b[\w$%.]*\w\b"
STOP = "english"


@dataclass
class Hit:
    chunk_id: str
    doc_id: str
    page_num: int
    score: float
    text: str
    header: str


class BM25Index:
    def __init__(self, chunks: pd.DataFrame, k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks.reset_index(drop=True)
        self.vec = CountVectorizer(token_pattern=TOKEN, stop_words=STOP, lowercase=True, dtype=np.float32)
        docs = (self.chunks.header + " " + self.chunks.text).tolist()
        tf = self.vec.fit_transform(docs).tocsc()
        n = tf.shape[0]
        df = np.diff(tf.indptr)
        self.idf = np.log(1 + (n - df + 0.5) / (df + 0.5)).astype(np.float32)
        lens = np.asarray(tf.sum(axis=1)).ravel()
        norm = k1 * (1 - b + b * lens / lens.mean())
        tf = tf.tocsr()
        rows = np.repeat(np.arange(n), np.diff(tf.indptr))
        tf.data = tf.data * (k1 + 1) / (tf.data + norm[rows])
        self.weights = tf.tocsc()

    def scores(self, query: str) -> np.ndarray:
        q = self.vec.transform([query])
        cols = q.indices
        if len(cols) == 0:
            return np.zeros(len(self.chunks), dtype=np.float32)
        return np.asarray(self.weights[:, cols] @ (self.idf[cols] * q.data)).ravel()


def detect_filters(question: str, companies: list[str]) -> dict:
    """Find the company and fiscal year mentioned in a question (simple, transparent rules)."""
    out = {}
    ql = question.lower()
    for c in sorted(companies, key=len, reverse=True):          # longest name first: "American Express" before "Express"
        if c.lower() in ql:
            out["company"] = c
            break
    years = re.findall(r"\b(?:FY\s?)?(20\d\d)\b", question)
    if years:
        out["period"] = int(years[0])
    return out


# Analysts ask for metric names; filings use line-item names. A small, auditable
# glossary bridges that vocabulary gap (query expansion).
FINANCE_SYNONYMS = {
    "capital expenditure": "purchases of property plant and equipment capex additions to property",
    "capex": "purchases of property plant and equipment capital expenditures",
    "revenue": "net sales total revenues net revenues",
    "net income": "net earnings attributable",
    "cogs": "cost of goods sold cost of sales cost of revenue",
    "cost of goods sold": "cost of sales cost of revenue",
    "operating income": "operating profit income from operations",
    "cash from operations": "net cash provided by operating activities",
    "operating cash flow": "net cash provided by operating activities",
    "free cash flow": "net cash provided by operating activities purchases of property plant and equipment",
    "ebitda": "operating income depreciation and amortization",
    "dividend": "dividends declared per share cash dividends paid",
    "inventory": "inventories",
    "accounts payable": "trade payables",
    "accounts receivable": "trade receivables receivables net",
    "total assets": "balance sheet total assets",
    "working capital": "total current assets total current liabilities",
    "debt": "long-term debt borrowings notes payable",
    "eps": "earnings per share diluted basic",
    "margin": "gross profit net sales",
    "effective tax rate": "provision for income taxes effective tax rate",
    "segment": "segment reporting operating segments",
}


def expand_query(q: str) -> str:
    ql = q.lower()
    extra = [v for k, v in FINANCE_SYNONYMS.items() if k in ql]
    return q + (" " + " ".join(extra) if extra else "")


def rrf(rankings: list[np.ndarray], k: int = 60) -> np.ndarray:
    """Reciprocal rank fusion: combine several rankings without tuning score scales."""
    n = len(rankings[0])
    fused = np.zeros(n)
    for ranking in rankings:
        ranks = np.empty(n)
        ranks[ranking] = np.arange(1, n + 1)
        fused += 1.0 / (k + ranks)
    return fused


class Retriever:
    def __init__(self, chunks: pd.DataFrame, encoder=None):
        """encoder: optional object with .encode(list[str]) -> np.ndarray (e.g. a sentence-transformers model)."""
        self.chunks = chunks.reset_index(drop=True)
        self.bm25 = BM25Index(self.chunks)
        self.companies = sorted(self.chunks.company.dropna().unique())
        self.encoder = encoder
        self.emb = None
        if encoder is not None:
            e = encoder.encode((self.chunks.header + " " + self.chunks.text).tolist())
            self.emb = e / np.linalg.norm(e, axis=1, keepdims=True)

    def search(self, question: str, k: int = 5, use_filters: bool = True, doc_id: str | None = None,
               mode: str = "bm25", expand: bool = True, dedupe_pages: bool = True) -> tuple[list[Hit], dict]:
        mask = np.ones(len(self.chunks), dtype=bool)
        filters = detect_filters(question, self.companies) if use_filters else {}
        if doc_id:
            filters = {"doc_id": doc_id}
        for col, val in filters.items():
            m = (self.chunks[col] == val).to_numpy()
            if m.any():               # never filter down to nothing because of a bad guess
                mask &= m
        s = self.bm25.scores(expand_query(question) if expand else question)
        if mode in ("dense", "hybrid") and self.emb is not None:
            qv = self.encoder.encode([question])[0]
            d = self.emb @ (qv / np.linalg.norm(qv))
            s = d if mode == "dense" else rrf([np.argsort(-s), np.argsort(-d)])
        s = np.where(mask, s, -np.inf)
        order = np.argsort(-s)
        if dedupe_pages:   # overlapping windows of one page shouldn't use up several of the k slots
            pages = self.chunks.doc_id.to_numpy()[order] + ":" + self.chunks.page_num.astype(str).to_numpy()[order]
            _, first = np.unique(pages[: k * 20], return_index=True)
            order = order[np.sort(first)]
        top = order[:k]
        hits = [Hit(r.chunk_id, r.doc_id, int(r.page_num), float(s[i]), r.text, r.header)
                for i, r in zip(top, self.chunks.iloc[top].itertuples(index=False))]
        return hits, filters
