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
install-flit:
	flit install --deps production --symlink

.PHONY: install-dev
install-testing:
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

