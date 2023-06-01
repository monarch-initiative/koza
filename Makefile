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
	$(RUN) flake8 --exit-zero --max-line-length 120 koza/ tests/ examples/
	$(RUN) black --check --diff koza tests
	$(RUN) isort --check-only --diff koza tests

.PHONY: format
format:
	$(RUN) autoflake \
		--recursive \
		--remove-all-unused-imports \
		--remove-unused-variables \
		--ignore-init-module-imports \
		--in-place koza tests examples
	$(RUN) isort koza tests examples
	$(RUN) black koza tests examples
