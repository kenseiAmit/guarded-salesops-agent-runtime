.PHONY: install demo test eval report lint

install:
	uv pip install -e ".[dev]"

demo:
	uv run python examples/demo_walkthrough.py

test:
	uv run pytest -v --cov=salesops_agent --cov-report=term-missing

eval:
	uv run evaluate

report:
	uv run generate-monitoring-report

lint:
	uv run ruff check src tests examples
