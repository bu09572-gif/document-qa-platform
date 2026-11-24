# Production RAG over SEC Filings, with a Golden-Set Evaluation Harness

[![ci](https://github.com/bu09572-gif/document-qa-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/bu09572-gif/document-qa-platform/actions/workflows/ci.yml)

Question answering over 84 real SEC filings, with page citations, and the evaluation work that a RAG system needs before anyone should trust it: a fixed golden set of 50 analyst questions, a retrieval comparison chosen on a separate dev split, answer grading that does not trust the LLM judge blindly, and a failure analysis that puts every wrong answer into one bucket with its fix. It ships as a Docker service with Prometheus metrics.

The short version, on the 50 golden questions:

- **Accuracy went from 20% to 34%** (38% with the 7B model), and retrieval failures fell from 34 to 17. The gain came from retrieval (picking the right filing, then hybrid BM25 + dense search), not from a bigger model.
- **The LLM judge alone would have reported 82 to 88%.** It graded most "not enough information" replies as correct, and passed 10 of the 15 wrong yes/no and text answers I checked by hand.
- **Both cross-encoder rerankers made retrieval worse** on these financial tables, and cost 2 to 10 seconds per question on CPU. So the service does not use one.

Three packages, in `src/`:

- **`docpipe`**: downloads filings, extracts page text, chunks it, and runs data checks
- **`docqa`**: retrieval (filing routing, BM25, dense, hybrid, optional reranker) and LLM answers with page citations, behind a FastAPI service
- **`evalkit`**: the golden set, retrieval and answer evaluation, failure analysis, and a regression gate in CI

Everything runs on free tools: Qwen2.5 (3B and 7B) through Ollama on CPU, BGE embeddings, GitHub Actions.

## Data

[FinanceBench](https://github.com/patronus-ai/financebench) (Islam et al., 2023, [arXiv 2311.11944](https://arxiv.org/abs/2311.11944)): 368 public-company filings (10-K, 10-Q, 8-K, earnings releases) and an open set of 150 questions written by financial analysts. Each question has a reference answer and the page where the evidence is. The PDFs are downloaded at run time and are not stored in this repo.

I only process the 84 filings that the 150 questions refer to.

## Pipeline

From `evals/results/financebench/pipeline_run.json`:

- 84 filings from 32 companies (165.5 MB of PDFs)
- 12,013 pages and 37,785 chunks
- all 9 data checks pass; 0.77% of pages have no text layer
- text extraction took 53 s on a 4-core machine

Before trusting any retrieval numbers, I checked that every evidence snippet in the dataset appears on the page number my extractor assigns it. All 189 do, so the page numbering lines up.

## The golden set (`evals/golden/`)

50 of the 150 questions, fixed once and used only to report results. The other 100 are the **dev split**: every retrieval choice below was made on dev first.

- **Stratified**: the 50 keep FinanceBench's mix of question types and of 10-K vs. other filings, picked in a fixed hash order (`python -m evalkit.golden`), so the set can be rebuilt exactly.
- **Labelled** for the failure analysis: answer type (18 number, 16 yes/no, 16 text), skill (24 lookup, 20 calculation, 6 judgment) and the evidence pages.
- **Reviewed by hand** against the evidence pages (`review.json`). One reference answer was wrong: for question 00283 (how much Pfizer still expects to pay for the Upjohn spin-off) the dataset says $77.78M, but the filing says costs of about $700M with about 90% already incurred, so about $70M is left. I grade against $70M and kept the note.

## Retrieval

hit@k: one of the expert's evidence pages is in the top k. "Right filing" is the share of questions where a page from the correct filing is in the top 5.

### All 150 questions, BM25 (each row adds one change)

| Setup | hit@1 | hit@5 | hit@10 | MRR | right filing in top 5 |
|---|---|---|---|---|---|
| BM25 over all 84 filings | 0.053 | 0.113 | 0.160 | 0.082 | 0.513 |
| + one result per page | 0.053 | 0.120 | 0.167 | 0.084 | 0.520 |
| + company / fiscal-year filter from the question | 0.113 | 0.233 | 0.313 | 0.160 | 0.800 |
| + finance term expansion ("capex" → "purchases of property, plant and equipment") | 0.107 | 0.307 | 0.413 | 0.194 | 0.760 |
| + filing routing v2 (company names and tickers, latest year that has a filing, quarter) | 0.127 | 0.380 | 0.547 | 0.239 | 0.953 |
| Reference: search only the correct filing | 0.167 | 0.433 | 0.620 | 0.289 | 1.000 |

Routing v2 fixed most "wrong filing" misses: questions like "JPM in Q2 2023" or "3M's FY2018" now land in the right 10-Q or 10-K 95% of the time. I wrote the company aliases after looking at failures across all 150 questions, golden ones included, so this row is a little optimistic for the golden set.

### Dense, hybrid and reranking (all with routing v2)

| Setup | Dev hit@5 | Dev hit@10 | Dev MRR | Golden hit@5 | Golden hit@10 | Golden MRR | Time per query |
|---|---|---|---|---|---|---|---|
| BM25 | 0.38 | 0.58 | 0.243 | 0.38 | 0.48 | 0.233 | 10 ms |
| Dense only (bge-small-en-v1.5) | 0.55 | 0.71 | 0.411 | 0.58 | 0.72 | 0.420 | 70 ms |
| **Hybrid: BM25 + dense, reciprocal rank fusion** | **0.60** | **0.73** | 0.379 | **0.66** | **0.76** | **0.426** | 65 ms |
| Hybrid + reranker bge-reranker-base (top 30) | 0.45 | 0.62 | 0.301 | 0.52 | 0.74 | 0.289 | 10.1 s |
| Hybrid + reranker ms-marco-MiniLM-L-6 (top 30) | 0.53 | 0.65 | 0.307 | 0.50 | 0.70 | 0.378 | 1.7 s |

I picked hybrid on dev, and the golden set agreed. Both rerankers were trained on web search passages, and my guess is that pages that are mostly tables of numbers look like poor matches to them. A reranker tuned on filings might help; these off-the-shelf ones do not.

## Answers on the golden set

Each setup answers the 50 golden questions from its top 5 pages. Llama-3.1-8B grades each answer against the expert answer, and then the rules and manual grades below decide the final grade. All models run on CPU through Ollama in GitHub Actions (`rag-eval.yml`), so the cost is $0.

| Setup | Accuracy | LLM judge alone | "Not enough information" | Wrong answer | Latency p50 |
|---|---|---|---|---|---|
| Baseline: BM25 + term expansion, Qwen2.5-3B | 20% | 66% | 64% | 16% | 53 s |
| **Hybrid retrieval + routing v2, Qwen2.5-3B** | **34%** | 82% | 42% | 24% | 69 s |
| Hybrid retrieval + routing v2, Qwen2.5-7B | 38% | 88% | 48% | 14% | 75 s |

Per-question answers, grades and summaries are in `evals/results/financebench/answers_golden_*`.

### How answers are graded (`evalkit.metrics.final_grade`)

1. **Refusals by rule.** "Not enough information" is a refusal, whatever the judge says. The judge called 63 to 88% of refusals correct.
2. **Numbers by rule.** For a question whose answer is a number, the reference number must appear in the answer (1% tolerance), and the judge must agree.
3. **Yes/no and text answers by hand.** I read all 41 answered yes/no and text questions across the three runs against the expert answer (`evals/golden/manual_grades.json`, with notes). The judge agreed with me on 31 of 41 (76%), and every disagreement was the judge passing a wrong answer: a "yes" when the answer was "no", the wrong region, a tax rate with its minus sign dropped.

So an LLM judge is a useful first pass, but on its own it would have reported more than double the real accuracy.

## Failure analysis (`evalkit.failures`)

Every golden answer goes into exactly one bucket, checked in order, so each bucket points to one fix:

| Bucket | Baseline | Hybrid, 3B | Hybrid, 7B | What would fix it |
|---|---|---|---|---|
| correct | 10 | 17 | 19 | |
| wrong filing | **14** | 2 | 2 | routing |
| right filing, evidence page missed | **18** | 9 | 12 | ranking, table-aware chunks |
| only some of the needed pages | 2 | 6 | 5 | one search per statement |
| refused although the evidence was in context | 2 | **8** | **8** | prompt or model |
| wrong number | 2 | 5 | 3 | extract line items first, calculator tool |
| wrong conclusion | 2 | 3 | 1 | reasoning, domain hints |
| **Retrieval failures / generation failures** | **34 / 6** | **17 / 16** | **19 / 12** | |

(Correct counts are 10, 17 and 19 of 50, so accuracy is 20%, 34% and 38%.)

What this says:

- **Retrieval was the problem, and it is now half of it.** The baseline lost 34 questions before the model saw the right page. Routing and hybrid search cut that to 17.
- **The next problem is the model refusing.** In 8 questions the evidence page was in the context and the model still said "not enough information". The 7B model did not fix this: it refused just as often and was more careful about wrong answers instead. A "find the line items first, then answer" prompt is the next thing to try.
- **Multi-page questions** (an income statement number plus a balance sheet number) need one search per statement. Top-5 retrieval often gets one of the two pages.

Full reports, with examples from each bucket: `evals/results/financebench/answers_golden_*_failures.md`.

## Serving (`src/docqa/api.py`, `Dockerfile`, `docker-compose.yml`)

`docker compose up --build` starts Ollama, pulls Qwen2.5-3B, downloads and indexes the filings on first start, and serves:

| Endpoint | What it does |
|---|---|
| `POST /search` | retrieval only, with the filing filters it chose (no LLM needed) |
| `POST /ask` | retrieval + cited answer, with token counts, cost and timing |
| `GET /metrics` | Prometheus: request, retrieval and LLM latency, tokens, cost, refusals, cache hits |
| `GET /health` | status and retrieval setting |

Repeated questions come from an in-memory LRU cache, because the LLM call is the slow and costly part. `DOCQA_RETRIEVAL` picks the retrieval setup (`+hybrid_bm25_dense` in Compose, `+filing_routing_v2` for a light BM25-only service). CI builds the image and smoke-tests `/search` and `/metrics` on every push.

## CI

- `ci.yml`: lint and tests, the pipeline and retrieval eval on the real filings, and a **regression gate**: the build fails if hit@5, hit@10, MRR or right-filing rate drops more than 0.02 below `evals/baseline/financebench.json`. Then the Docker image build and smoke test.
- `rag-eval.yml` (manual): stage `retrieval` runs every setup on dev and golden; stage `answers` answers the golden set for each setup and model in 5 parallel shards, grades, merges and runs the failure analysis.
- `mirror-models.yml`: copies the embedding and reranker models into a release with SHA-256 sums, so evaluation runs don't depend on another site being up.

## How it fits together

```
FinanceBench PDFs
      │
      ▼
docpipe   fetch with retries; bronze (PDFs + sha256 manifest) → silver (page text) → gold (chunks
          that never cross a page, with company / filing / page metadata); data checks; local or s3://
      │
      ▼
docqa     routing v2 (company, year, quarter → filing) → BM25 + bge-small dense → reciprocal rank fusion
          → optional cross-encoder → top 5 pages → LLM answer with [S#] tags mapped back to pages
          FastAPI: /search, /ask, /metrics
      │
      ▼
evalkit   golden / dev split, hit@k, MRR, LLM judge + rules + manual grades, failure buckets,
          citation precision, latency, cost; regression gate against evals/baseline/
```

## Limits

- **50 questions is a small test set.** One question is 2 points of accuracy, so 34% vs. 38% between the 3B and 7B models is not a real difference.
- **Manual grades are one person's reading** of the expert answer. The notes say why each disputed one went the way it did.
- **CPU only.** A p50 of about 70 seconds per answer is the cost of running free models on a 4-core runner, not what a GPU or hosted model would give.

## Running it

From the repository root:

The easiest way is a GitHub Codespace (Code → Codespaces → Create codespace). Ollama gets installed when the container is created.

```bash
make pipeline                # download and process the 84 filings (~1.5 min)
make eval                    # retrieval table
make test
make api                     # http://localhost:8000/docs
ollama pull qwen2.5:3b
make eval-answers LIMIT=20   # answer + grade 20 questions with the local model
docker compose up --build    # the full service with Ollama, http://localhost:8000/docs
```

LLM backend, set with `LLM_PROVIDER`:

| Value | Cost | Needs |
|---|---|---|
| `ollama` (default) | free | nothing; change the model with `LLM_MODEL` |
| `groq` | free tier | `GROQ_API_KEY` |

`DATA_ROOT=s3://bucket/prefix` writes the same layout to S3 (`pip install -e ".[aws]"`), where Athena can read the parquet files.

---

Part of my [AI/ML and data engineering portfolio](https://github.com/bu09572-gif/ai-ml-portfolio), where every project uses real public data and free, open-source tools.
