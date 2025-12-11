# Note that uv is required, see https://docs.astral.sh/uv/getting-started/installation/

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

# This nifty grep/sort/awk pipeline collects all comments headed by the double "#" symbols next to each target and recycles them as comments
.PHONY: help
help: ## Print this help message
	@grep -hE '^[[:alnum:]_/.-]+:.*## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'


.PHONY: all
all: install test clean ## Install, test, and clean

.PHONY: install
install:  ## Install development environment
	uv venv --allow-existing
	uv pip install -e .[dev]
	uv lock

.PHONY: build
build:  ## Build the package
	uv build

.PHONY: test
test:  ## Run the test suite
	$(RUN) pytest tests

.PHONY: docs
docs:  ## Build the documentation
	$(RUN) typer src/koza/main.py utils docs --name koza --output docs/Usage/CLI.md
	$(RUN) mkdocs build

.PHONY: clean
clean:  ## Clean up build artifacts, etc.
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -rf .pytest_cache
	rm -rf output test-output
	rm -rf dist

.PHONY: coverage
coverage:  ## Run the test suite with coverage reporting
	-$(RUN) coverage run -m pytest tests
	$(RUN) coverage report -m

.PHONY: lint
lint:  ## Lint the codebase
	$(RUN) ruff check --diff --exit-zero src/ tests/ examples/
	$(RUN) ruff format --check --diff src/ tests/ examples/

.PHONY: format
format:  ## Format the codebase
	$(RUN) ruff check --fix --exit-zero src/ tests/ examples/
	$(RUN) ruff format src/ tests/ examples/
