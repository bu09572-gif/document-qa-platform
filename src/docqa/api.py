"""FastAPI service for document Q&A.

    GET  /health
    POST /search   {"question": "...", "k": 5}           retrieval only (no API key needed)
    POST /ask      {"question": "...", "k": 5}           retrieval + cited answer from the LLM

Run:  uvicorn docqa.api:app --reload   (PYTHONPATH=src, after running the pipeline)
"""
from __future__ import annotations

import os
from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from docpipe import storage

from .retrieve import Retriever

SOURCE = os.environ.get("DOCQA_SOURCE", "financebench")
app = FastAPI(title="Document Q&A with citations", version="1.0")


@lru_cache(maxsize=1)
def retriever() -> Retriever:
    p = storage.path("gold", SOURCE, "chunks.parquet")
    if not storage.exists(p):
        raise RuntimeError(f"{p} not found: run `python -m docpipe.run` first")
    return Retriever(pd.read_parquet(p))


class Query(BaseModel):
    question: str = Field(min_length=5, max_length=2000)
    k: int = Field(5, ge=1, le=20)
    doc_id: str | None = None


@app.get("/health")
def health():
    return {"status": "ok", "chunks": len(retriever().chunks)}


@app.post("/search")
def search(q: Query):
    hits, filters = retriever().search(q.question, k=q.k, doc_id=q.doc_id)
    return {"filters": filters, "hits": [h.__dict__ for h in hits]}


@app.post("/ask")
def ask(q: Query):
    from .answer import answer
    hits, filters = retriever().search(q.question, k=q.k, doc_id=q.doc_id)
    try:
        a = answer(q.question, hits)
    except Exception as e:  # noqa: BLE001  model server down, missing key, etc.
        raise HTTPException(503, f"LLM backend unavailable ({type(e).__name__}); /search still works") from e
    return {"answer": a.text, "refused": a.refused, "filters": filters, "model": a.model,
            "citations": [c.__dict__ for c in a.citations],
            "usage": {"input_tokens": a.input_tokens, "output_tokens": a.output_tokens,
                      "cost_usd": round(a.cost_usd, 5), "latency_s": round(a.latency_s, 2)}}
