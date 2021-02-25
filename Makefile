# Note that you should be in your virtual environment of choice before running make

MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules
MAKEFLAGS += --no-builtin-variables

.DEFAULT_GOAL := all
SHELL := bash

.PHONY: all
all: install-flit install-koza install-dev test

.PHONY: install-flit
install-flit:
	pip install flit

.PHONY: install-koza
install-koza: install-flit
	flit install --deps production --symlink

.PHONY: install-dev
install-dev: install-flit
	flit install --deps develop --symlink

.PHONY: test
test: install-flit install-dev
	python -m pytest

.PHONY: build
build:
	flit build

.PHONY: publish
publish:
	flit publish

.PHONY: clean
clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -rf .pytest_cache
	rm -rf dist

.PHONY: lint
lint:
	flake8 --exit-zero --max-line-length 120 koza/ tests/
	black --check --diff koza tests
	isort --check-only --diff koza tests

.PHONY: format
format:
	autoflake --remove-all-unused-imports --recursive --remove-unused-variables --in-place koza tests --exclude=__init__.py
	isort koza tests
	black koza tests
