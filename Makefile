.PHONY: install test cov lint clean

install:
	pip install -e ".[dev]"

test:
	pytest -q

cov:
	pytest -q --cov=liftlog --cov-report=term-missing

lint:
	ruff check src tests

clean:
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage build dist *.egg-info
