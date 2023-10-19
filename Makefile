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
RUN := poetry run

.PHONY: all
all: install test clean

.PHONY: install
install: 
	poetry install

.PHONY: build
build:
	poetry build

.PHONY: test
test: install
	$(RUN) python -m pytest

.PHONY: docs
docs: install
	$(RUN) typer src/koza/main.py utils docs --name koza --output docs/Usage/CLI.md
	$(RUN) mkdocs build

.PHONY: clean
clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -rf .pytest_cache
	rm -rf output test-output
	rm -rf dist

.PHONY: lint
lint:
	$(RUN) ruff check --diff --exit-zero src/ tests/ examples/
	$(RUN) black --check --diff -l 120 src/ tests/ examples/

.PHONY: format
format:
	$(RUN) ruff check --fix --exit-zero src/ tests/ examples/
	$(RUN) black -l 120 src/ tests/ examples/
