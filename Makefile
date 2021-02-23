# Note that you should in your virtual environment of choice
# before running make

MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules
MAKEFLAGS += --no-builtin-variables

.DEFAULT_GOAL := all
SHELL := bash

.PHONY: all
all: install-flit install-bioweave install-dev test

.PHONY: install-flit
install-flit:
	pip install flit

.PHONY: install-bioweave
install-bioweave:
	flit install --deps production --symlink

.PHONY: install-dev
install-dev:
	flit install --deps develop --symlink

.PHONY: test
test:
	python -m pytest

.PHONY: build
build:
	flit build

.PHONY: publish
publish:
	flit publish

.PHONY: lint
lint:
	flake8 --exit-zero --max-line-length 120 bioweave/ tests/
	black --check --diff bioweave tests
	isort --check-only --diff bioweave tests

.PHONY: format
format:
	autoflake --remove-all-unused-imports --recursive --remove-unused-variables --in-place bioweave fastapi --exclude=__init__.py
	isort bioweave tests
	black bioweave tests
