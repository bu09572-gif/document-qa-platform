"""Answer a question from retrieved chunks, with page-level citations.

Two paths, same output:
  * free default (Ollama / Groq): sources are numbered [S1]..[Sk] in the prompt and the
    model is asked to cite them inline; we parse the [S#] markers back to filing pages.
  * optional Anthropic backend: each chunk is a `document` block with citations enabled,
    so the API itself links every cited sentence to its chunk.

Pick the backend with LLM_PROVIDER (see llm.py). If the sources don't contain the answer,
the model must say so instead of guessing.
"""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field

from . import llm
from .retrieve import Hit

SYSTEM = (
    "You answer questions about public-company SEC filings using ONLY the provided sources. "
    "Show the numbers you use and the arithmetic for any calculation. "
    "Give the final answer in the first sentence. "
    "If the sources do not contain enough information, reply exactly: "
    "\"Not enough information in the provided filings.\""
)
CITE_RULE = "Cite the sources you used inline with their tags, for example [S2]. Only cite sources you actually used."
REFUSAL_TEXT = "Not enough information in the provided filings."
TAG = re.compile(r"\[S(\d+)\]")


@dataclass
class Citation:
    chunk_id: str
    doc_id: str
    page_num: int
    cited_text: str = ""


@dataclass
class Answer:
    text: str
    citations: list[Citation] = field(default_factory=list)
    model: str = ""
    provider: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    stop_reason: str | None = None

    @property
    def cost_usd(self) -> float:
        pin, pout = llm.PRICES.get(self.model, (0.0, 0.0))
        return (self.input_tokens * pin + self.output_tokens * pout) / 1e6

    @property
    def refused(self) -> bool:
        return REFUSAL_TEXT.lower().rstrip(".") in self.text.lower()


def numbered_sources(hits: list[Hit]) -> str:
    return "\n\n".join(f"[S{i}] ({h.header})\n{h.text}" for i, h in enumerate(hits, 1))


def parse_citations(text: str, hits: list[Hit]) -> list[Citation]:
    seen, out = set(), []
    for m in TAG.finditer(text):
        i = int(m.group(1)) - 1
        if 0 <= i < len(hits) and i not in seen:     # ignore tags that point at no source
            seen.add(i)
            h = hits[i]
            out.append(Citation(h.chunk_id, h.doc_id, h.page_num))
    return out


def answer(question: str, hits: list[Hit], provider: str | None = None, client=None) -> Answer:
    provider = provider or llm.PROVIDER
    if provider == "anthropic":
        return _answer_anthropic(question, hits, client)
    user = f"Sources:\n\n{numbered_sources(hits)}\n\nQuestion: {question}\n\n{CITE_RULE}"
    c = llm.chat(SYSTEM, user, provider=provider, max_tokens=1024)
    return Answer(c.text.strip(), parse_citations(c.text, hits), c.model, c.provider,
                  c.input_tokens, c.output_tokens, c.latency_s)


# ---------- optional paid backend: Anthropic native citations ----------
def build_content(question: str, hits: list[Hit]) -> list[dict]:
    blocks = [{
        "type": "document",
        "source": {"type": "text", "media_type": "text/plain", "data": h.text},
        "title": h.header,
        "context": f"chunk_id={h.chunk_id}",
        "citations": {"enabled": True},
    } for h in hits]
    blocks.append({"type": "text", "text": question})
    return blocks


def _answer_anthropic(question: str, hits: list[Hit], client=None) -> Answer:
    if client is None:
        import anthropic
        client = anthropic.Anthropic()
    model = llm.model_name("anthropic")
    t0 = time.perf_counter()
    resp = client.beta.messages.create(
        model=model, max_tokens=4096, system=SYSTEM,
        output_config={"effort": os.environ.get("DOCQA_EFFORT", "medium")},
        betas=["server-side-fallback-2026-07-01"],   # a declined request is retried on a fallback model
        fallbacks="default",
        messages=[{"role": "user", "content": build_content(question, hits)}],
    )
    latency = time.perf_counter() - t0
    if resp.stop_reason == "refusal":
        return Answer("[declined by model safety system]", model=resp.model, provider="anthropic",
                      stop_reason=resp.stop_reason, latency_s=latency)
    texts, cites = [], []
    for block in resp.content:
        if block.type != "text":
            continue
        texts.append(block.text)
        for c in getattr(block, "citations", None) or []:
            h = hits[c.document_index]
            cites.append(Citation(h.chunk_id, h.doc_id, h.page_num, c.cited_text))
    return Answer("".join(texts).strip(), cites, resp.model, "anthropic", resp.usage.input_tokens,
                  resp.usage.output_tokens, latency, resp.stop_reason)
