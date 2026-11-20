export PYTHONPATH := src
LIMIT ?= 150
.PHONY: install test lint pipeline eval eval-dense eval-answers gate api
install:      ; pip install -e ".[dev]"
test:         ; python -m pytest -q
lint:         ; ruff check src tests
pipeline:     ; python -m docpipe.run --scope eval
eval:         ; python -m evalkit.run --dataset financebench
eval-dense:   ; pip install -e ".[dense]" && python -m evalkit.run --dataset financebench --dense
eval-answers: ; python -m evalkit.run --dataset financebench --answers --limit $(LIMIT)
gate:         ; python -m evalkit.gate --dataset financebench
api:          ; uvicorn docqa.api:app --reload --port 8000
