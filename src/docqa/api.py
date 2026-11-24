"""FastAPI service for document Q&A.

    GET  /health
    POST /search   {"question": "...", "k": 5}           retrieval only (no LLM needed)
    POST /ask      {"question": "...", "k": 5}           retrieval + cited answer from the LLM
    GET  /metrics  Prometheus: request, retrieval and LLM latency, tokens, refusals, cost, cache hits

Settings (environment):
    DOCQA_RETRIEVAL   "+hybrid_bm25_dense" (routing v2 + BM25 and dense fused, needs the [dense] extra; the best
                      setting on the dev split), "+reranker" (the same plus a cross-encoder; slower and worse on
                      this data) or "+filing_routing_v2" (BM25 only, light; the default when nothing is set)
    LLM_PROVIDER / LLM_MODEL   see docqa.llm (default: Ollama, qwen2.5:3b, free)

Run:  uvicorn docqa.api:app --port 8000   (PYTHONPATH=src, after `python -m docpipe.run`)
"""
from __future__ import annotations

import os
import time
from collections import OrderedDict
from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field

from docpipe import storage

from .retrieve import Retriever

SOURCE = os.environ.get("DOCQA_SOURCE", "financebench")
RETRIEVAL = os.environ.get("DOCQA_RETRIEVAL", "+filing_routing_v2")
CACHE_SIZE = int(os.environ.get("DOCQA_CACHE_SIZE", "256"))
app = FastAPI(title="Document Q&A with citations", version="2.0")

REQ = Histogram("docqa_request_seconds", "Request time", ["endpoint"], buckets=(.01, .05, .1, .25, .5, 1, 2.5, 5, 10, 30, 60, 120))
RET = Histogram("docqa_retrieval_seconds", "Retrieval time", buckets=(.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5))
GEN = Histogram("docqa_llm_seconds", "LLM answer time", buckets=(.5, 1, 2.5, 5, 10, 20, 40, 80, 160))
TOK = Counter("docqa_llm_tokens_total", "LLM tokens", ["kind"])
COST = Counter("docqa_llm_cost_usd_total", "LLM cost in USD (0 for local and free-tier models)")
ANS = Counter("docqa_answers_total", "Answers", ["outcome"])          # answered / refused / error / cache_hit
_cache: OrderedDict = OrderedDict()


@lru_cache(maxsize=1)
def retriever() -> Retriever:
    p = storage.path("gold", SOURCE, "chunks.parquet")
    if not storage.exists(p):
        raise RuntimeError(f"{p} not found: run `python -m docpipe.run` first")
    chunks = pd.read_parquet(p)
    if RETRIEVAL in ("+hybrid_bm25_dense", "+reranker"):
        from .models import Encoder, Reranker, embeddings_for
        enc = Encoder()
        return Retriever(chunks, encoder=enc, reranker=Reranker() if RETRIEVAL == "+reranker" else None,
                         embeddings=embeddings_for(chunks, enc, storage.path("gold", SOURCE)))
    return Retriever(chunks)


def _search(q):
    kw = dict(routing="v2")
    if RETRIEVAL == "+hybrid_bm25_dense":
        kw.update(mode="hybrid")
    elif RETRIEVAL == "+reranker":
        kw.update(mode="hybrid", rerank=30)
    t0 = time.perf_counter()
    hits, filters = retriever().search(q.question, k=q.k, doc_id=q.doc_id, **kw)
    RET.observe(time.perf_counter() - t0)
    return hits, filters


class Query(BaseModel):
    question: str = Field(min_length=5, max_length=2000)
    k: int = Field(5, ge=1, le=20)
    doc_id: str | None = None


@app.get("/health")
def health():
    return {"status": "ok", "chunks": len(retriever().chunks), "retrieval": RETRIEVAL}


@app.post("/search")
def search(q: Query):
    t0 = time.perf_counter()
    hits, filters = _search(q)
    REQ.labels(endpoint="/search").observe(time.perf_counter() - t0)
    return {"filters": filters, "hits": [h.__dict__ for h in hits]}


@app.post("/ask")
def ask(q: Query):
    from . import llm
    from .answer import answer
    t0 = time.perf_counter()
    key = (q.question.strip().lower(), q.k, q.doc_id, llm.model_name())
    if key in _cache:                         # same question, same model: reuse (LLM calls are the cost)
        _cache.move_to_end(key)
        ANS.labels(outcome="cache_hit").inc()
        return _cache[key] | {"cached": True}
    hits, filters = _search(q)
    try:
        a = answer(q.question, hits)
    except Exception as e:  # noqa: BLE001  model server down, missing key, etc.
        ANS.labels(outcome="error").inc()
        raise HTTPException(503, f"LLM backend unavailable ({type(e).__name__}); /search still works") from e
    GEN.observe(a.latency_s)
    TOK.labels(kind="input").inc(a.input_tokens)
    TOK.labels(kind="output").inc(a.output_tokens)
    COST.inc(a.cost_usd)
    ANS.labels(outcome="refused" if a.refused else "answered").inc()
    out = {"answer": a.text, "refused": a.refused, "filters": filters, "model": a.model,
           "citations": [c.__dict__ for c in a.citations],
           "usage": {"input_tokens": a.input_tokens, "output_tokens": a.output_tokens,
                     "cost_usd": round(a.cost_usd, 5), "llm_s": round(a.latency_s, 2),
                     "total_s": round(time.perf_counter() - t0, 2)}}
    _cache[key] = out
    if len(_cache) > CACHE_SIZE:
        _cache.popitem(last=False)
    REQ.labels(endpoint="/ask").observe(time.perf_counter() - t0)
    return out | {"cached": False}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
