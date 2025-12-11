### Help ###

define HELP
╭───────────────────────────────────────────────────────────╮
  Makefile for upheno_cross_species_ingest			    
│ ───────────────────────────────────────────────────────── │
│ Usage:                                                    │
│     make <target>                                         │
│                                                           │
│ Targets:                                                  │
│     help                Print this help message           │
│                                                           │
│     all                 Install everything and test       │
│     fresh               Clean and install everything      │
│     clean               Clean up build artifacts          │
│     clobber             Clean up generated files          │
│                                                           │
│     install             Poetry install package            │
│     download            Download data                     │
│     run                 Run the transform                 │
│                                                           │
│     docs                Generate documentation            │
│                                                           │
│     test                Run all tests                     │
│                                                           │
│     lint                Lint all code                     │
│     format              Format all code                   │
╰───────────────────────────────────────────────────────────╯
endef
export HELP

.PHONY: help
help:
	@printf "$${HELP}"

# Note that uv is required, see https://docs.astral.sh/uv/

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
ROOTDIR = $(shell pwd)
VERSION = $(shell uv -C src/koza -s) #TODO: test this command.


.PHONY: all
all: install test clean

.PHONY: install
install: 
	uv sync

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
