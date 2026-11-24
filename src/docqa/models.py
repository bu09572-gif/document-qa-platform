"""Embedding and reranking models (optional: pip install -e ".[dense]").

Models are loaded from DOCQA_MODEL_DIR if it holds a copy (see `python -m docqa.models --fetch`,
which downloads the pinned files from this repo's models-v1 release), otherwise from the
Hugging Face Hub by name.

    DOCQA_EMBED_MODEL   default BAAI/bge-small-en-v1.5
    DOCQA_RERANK_MODEL  default BAAI/bge-reranker-base
"""
from __future__ import annotations

import hashlib
import os
import tarfile
from pathlib import Path

import numpy as np

EMBED_MODEL = os.environ.get("DOCQA_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
RERANK_MODEL = os.environ.get("DOCQA_RERANK_MODEL", "BAAI/bge-reranker-base")
MODEL_DIR = Path(os.environ.get("DOCQA_MODEL_DIR", "models/cache"))
RELEASE = "https://github.com/bu09572-gif/document-qa-platform/releases/download/models-v1"
# BGE models are trained with this instruction in front of short queries (not passages).
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def _local(name: str) -> str:
    p = MODEL_DIR / name.replace("/", "_")
    return str(p) if p.exists() else name


def fetch(names: list[str]) -> None:
    """Download pinned model archives from the release and check their SHA-256."""
    import requests
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    sums = dict(line.split()[::-1] for line in requests.get(f"{RELEASE}/SHA256SUMS", timeout=60).text.splitlines())
    for name in names:
        fn = name.replace("/", "_") + ".tar.gz"
        if (MODEL_DIR / name.replace("/", "_")).exists():
            continue
        dest = MODEL_DIR / fn
        h = hashlib.sha256()
        with requests.get(f"{RELEASE}/{fn}", stream=True, timeout=600) as r, dest.open("wb") as fh:
            r.raise_for_status()
            for block in r.iter_content(1 << 20):
                h.update(block)
                fh.write(block)
        if h.hexdigest() != sums[fn]:
            raise RuntimeError(f"checksum mismatch for {fn}")
        with tarfile.open(dest) as t:
            t.extractall(MODEL_DIR, filter="data")
        dest.unlink()


class Encoder:
    def __init__(self, name: str = EMBED_MODEL):
        from sentence_transformers import SentenceTransformer
        self.name = name
        self.m = SentenceTransformer(_local(name), device="cpu")
        self.prefix = BGE_QUERY_PREFIX if "bge" in name.lower() else ""

    def encode(self, texts: list[str], query: bool = False) -> np.ndarray:
        if query:
            texts = [self.prefix + t for t in texts]
        return self.m.encode(texts, batch_size=32, show_progress_bar=False, normalize_embeddings=True,
                             convert_to_numpy=True)


class Reranker:
    def __init__(self, name: str = RERANK_MODEL, max_length: int = 512):
        from sentence_transformers import CrossEncoder
        self.name = name
        self.m = CrossEncoder(_local(name), device="cpu", max_length=max_length)

    def score(self, question: str, texts: list[str]) -> np.ndarray:
        return np.asarray(self.m.predict([(question, t) for t in texts], batch_size=16, show_progress_bar=False))


def embeddings_for(chunks, enc: Encoder, cache_dir: str | Path) -> np.ndarray:
    """Chunk embeddings, cached on disk by model name + chunk ids (37k chunks take ~30 min on 4 CPUs)."""
    key = hashlib.md5(("|".join(chunks.chunk_id) + enc.name).encode()).hexdigest()[:12]
    p = Path(cache_dir) / f"emb_{enc.name.replace('/', '_')}_{key}.npy"
    if p.exists():
        return np.load(p)
    e = enc.encode((chunks.header + " " + chunks.text).tolist()).astype(np.float32)
    p.parent.mkdir(parents=True, exist_ok=True)
    np.save(p, e)
    return e


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    a = ap.parse_args()
    if a.fetch:
        fetch([EMBED_MODEL, RERANK_MODEL])
        print("models in", MODEL_DIR)
