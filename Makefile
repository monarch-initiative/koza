# Note that Poetry is required, see https://python-poetry.org/docs/#installation

MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules
MAKEFLAGS += --no-builtin-variables

ifneq (,$(wildcard ./.env))
    include .env
    export
endif

.DEFAULT_GOAL := all
SHELL := bash
RUN := uv run

.PHONY: all
all: install test clean

.PHONY: install
install: 
	uv venv --allow-existing
	uv pip install -e .[dev]

.PHONY: build
build:
	uv build

.PHONY: test
test:
	$(RUN) pytest tests

.PHONY: docs
docs:
	$(RUN) typer src/koza/main.py utils docs --name koza --output docs/Usage/CLI.md
	$(RUN) mkdocs build

.PHONY: clean
clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -rf .pytest_cache
	rm -rf output test-output
	rm -rf dist

.PHONY: coverage
coverage:
	-$(RUN) coverage run -m pytest tests
	$(RUN) coverage report -m

.PHONY: lint
lint:
	$(RUN) ruff check --diff --exit-zero src/ tests/ examples/
	$(RUN) ruff format --check --diff src/ tests/ examples/

.PHONY: format
format:
	$(RUN) ruff check --fix --exit-zero src/ tests/ examples/
	$(RUN) ruff format src/ tests/ examples/
