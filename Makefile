.PHONY: install dev test lint fmt clean build

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v --tb=short

test-cov:
	pytest tests/ -v --cov=sp_api --cov-report=term-missing --cov-report=html

lint:
	ruff check sp_api/ tests/

fmt:
	ruff format sp_api/ tests/

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .ruff_cache htmlcov/
	find . -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

build: clean
	python -m build

check: lint test
