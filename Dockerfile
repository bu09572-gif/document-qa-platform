# RAG API image. The filings are downloaded and indexed on first start (about 2 minutes) into /app/data,
# which compose keeps in a volume. DOCQA_RETRIEVAL=+reranker needs the dense extra (built by default).
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/src DOCQA_MODEL_DIR=/app/models/cache
WORKDIR /app
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir ".[dense]"
RUN useradd --create-home --uid 1000 app && mkdir -p data models && chown -R app /app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=300s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["sh", "-c", "[ -f data/gold/financebench/chunks.parquet ] || python -m docpipe.run --scope eval; [ \"$DOCQA_RETRIEVAL\" != '+reranker' ] || python -m docqa.models --fetch; uvicorn docqa.api:app --host 0.0.0.0 --port 8000"]
