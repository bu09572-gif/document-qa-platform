"""Answer a question from retrieved chunks, with page-level citations.

Sources are numbered [S1]..[Sk] in the prompt and the model is asked to cite them
inline; we parse the [S#] markers back to filing pages.

Pick the backend with LLM_PROVIDER (see llm.py). If the sources don't contain the answer,
the model must say so instead of guessing.
"""
from __future__ import annotations

import re
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


def answer(question: str, hits: list[Hit], provider: str | None = None) -> Answer:
    provider = provider or llm.PROVIDER
    user = f"Sources:\n\n{numbered_sources(hits)}\n\nQuestion: {question}\n\n{CITE_RULE}"
    c = llm.chat(SYSTEM, user, provider=provider, max_tokens=1024)
    return Answer(c.text.strip(), parse_citations(c.text, hits), c.model, c.provider,
                  c.input_tokens, c.output_tokens, c.latency_s)

