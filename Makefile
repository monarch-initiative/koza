# Note that you should in your virtual environment of choice
# before running make

MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules
MAKEFLAGS += --no-builtin-variables

.DEFAULT_GOAL := all
SHELL := bash

.PHONY: all
all: install-bioweave install-testing install-dev install-docs test

.PHONY: install-bioweave
install-bioweave:
	pip install -r requirements.txt

.PHONY: install-testing
install-testing:
	pip install -r tests/requirements.txt

.PHONY: install-docs
install-docs:
	pip install -r docs/requirements.txt

.PHONY: install-dev
install-dev:
	pip install -r requirements-dev.txt

.PHONY: test
test:
	python -m pytest
