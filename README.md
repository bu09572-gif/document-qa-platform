# Document Q&A Platform for SEC Filings

This is three projects that work together. Their code lives in `src/`, so other projects can import it:

- **Filing Ingestion Pipeline** ([`src/docpipe`](../../../src/docpipe)): downloads filings, extracts page text, chunks it, and runs data checks
- **SEC Filing Q&A with Page Citations** ([`src/docqa`](../../../src/docqa)): retrieval (BM25 with metadata filters) and LLM answers with page citations
- **LLM Evaluation Harness** ([`src/evalkit`](../../../src/evalkit)): evaluation of retrieval and answers, plus a regression check that runs in CI

Everything runs on free tools. The default LLM is Qwen2.5-3B through Ollama, so no API key is needed. Groq and Claude are optional backends.

## Data

[FinanceBench](https://github.com/patronus-ai/financebench) (Islam et al., 2023, [arXiv 2311.11944](https://arxiv.org/abs/2311.11944)): 368 public-company filings (10-K, 10-Q, 8-K, earnings releases) and an open set of 150 questions written by financial analysts. Each question has a reference answer and the page where the evidence is. The PDFs are downloaded at run time and are not stored in this repo.

I only process the 84 filings that the 150 questions refer to.

## Results

### Pipeline

From `../../../evals/results/financebench/pipeline_run.json`:

- 84 filings from 32 companies (165.5 MB of PDFs)
- 12,013 pages and 37,785 chunks
- all 9 data checks pass; 0.77% of pages have no text layer
- text extraction took 53 s on a 4-core machine

Before trusting any retrieval numbers, I checked that every evidence snippet in the dataset appears on the page number my extractor assigns it. All 189 do, so the page numbering lines up.

### Retrieval

150 questions. hit@k means one of the evidence pages is in the top k results. Each row adds one change to the row above.

| Setup | hit@1 | hit@5 | hit@10 | MRR | right filing in top 5 |
|---|---|---|---|---|---|
| BM25 over all 84 filings | 0.053 | 0.113 | 0.160 | 0.082 | 0.513 |
| + one result per page | 0.053 | 0.120 | 0.167 | 0.084 | 0.520 |
| + company / fiscal-year filter from the question | 0.113 | 0.233 | 0.313 | 0.160 | 0.800 |
| + finance term expansion ("capex" → "purchases of property, plant and equipment") | 0.107 | 0.307 | 0.413 | 0.194 | 0.760 |
| Reference: search only the correct filing | 0.167 | 0.433 | 0.620 | 0.289 | 1.000 |

The company/year filter roughly doubled hit@5, and the term expansion added about 7 more points. A query takes about 14 ms on CPU.

The term list is generic accounting vocabulary, but I tested it on the same 150 questions, so the last row is probably a bit optimistic.

### Answers

All 150 questions, answered by Qwen2.5-3B from the top 5 retrieved pages and graded by Llama-3.2-3B. Both run on CPU through Ollama in GitHub Actions, so the cost is $0. Per-question results are in `../../../evals/results/financebench/answers_ollama_qwen2.5-3b.jsonl`.

| Metric | Value |
|---|---|
| Accuracy | 19.3% (29 / 150) |
| Said "not enough information" | 67.3% |
| Accuracy when it gave an answer | 59.2% |
| Numeric answers within 1% of the reference | 48.6% (of 37 checked) |
| Accuracy: evidence page retrieved vs. not | 45.7% vs. 7.7% |
| "Not enough information": evidence page retrieved vs. not | 28.3% vs. 84.6% |
| Answers with a citation / citations pointing at an evidence page | 35.3% / 35.5% |
| Latency p50 / p95 | 42 s / 97 s |

Notes:

- The LLM judge on its own gave 94%. When I looked at the graded answers, it was marking most "not enough information" replies as correct (93% of them). So the final grade now treats those replies as refusals by rule, and a numeric answer that misses the reference number can't be graded correct (`evalkit.metrics.final_grade`). That is where the 19.3% comes from.
- 12 of the 49 answered questions have no number to check. For those the grade still comes from the small judge, so the 59.2% may be a little high.
- Most of the misses come from retrieval. With the evidence page in context, accuracy goes from 8% to 46%. Better retrieval (dense or hybrid search, a reranker, picking the right filing first) is the next step, more than a bigger model.
- For rough context only: the FinanceBench paper reports GPT-4-Turbo with a shared vector store at about 19% correct. The setups are different.

The CI workflow also runs dense and hybrid retrieval (`--dense`).

## How it fits together

```
FinanceBench PDFs
      │
      ▼
docpipe   fetch with retries; skip files already downloaded
          bronze: raw PDFs + manifest with sha256
          silver: page text (pypdfium2)
          gold:   chunks that never cross a page, with company / filing / page metadata
          data checks + run report; local disk or s3:// (DATA_ROOT)
      │
      ▼
docqa     BM25 on a scipy sparse matrix, company/year filters, term expansion,
          optional dense embeddings + reciprocal rank fusion
          LLM answer with [S#] source tags mapped back to pages
          FastAPI: /search, /ask
      │
      ▼
evalkit   hit@k, MRR, LLM judge + rule checks, citation precision, latency, cost
          regression gate against evals/baseline/
```

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
```

LLM backend, set with `LLM_PROVIDER`:

| Value | Cost | Needs |
|---|---|---|
| `ollama` (default) | free | nothing; change the model with `LLM_MODEL` |
| `groq` | free tier | `GROQ_API_KEY` |
| `anthropic` | paid | `ANTHROPIC_API_KEY` |

`DATA_ROOT=s3://bucket/prefix` writes the same layout to S3 (`pip install -e ".[aws]"`), where Athena can read the parquet files.
