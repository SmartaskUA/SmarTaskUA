# schema_v4 -- validator, conformance suite, and the worked example.
#
# Everything runs inside .venv, because this machine's Python is
# externally-managed (PEP 668) and `pip install pytest` fails against it.
#
#   make                          this help
#   make test                     the conformance suite
#   make validate                 examples/ and templates/
#   make validate DIR=some/path   any folder or file
#   make validate DIR=x ARGS=-v   extra flags go in ARGS

VENV    := .venv
PY      := $(VENV)/bin/python
PIP     := $(VENV)/bin/pip
STAMP   := $(VENV)/.installed

# What `make validate` looks at when DIR is not given. Both are packages.
DIR     ?= examples templates
ARGS    ?=

export PYTHONPATH := $(CURDIR)/src

.DEFAULT_GOAL := help
.PHONY: help install test validate result check lint clean distclean

help:
	@echo 'schema_v4 -- make targets'
	@echo
	@echo '  make install                 create .venv and install requirements'
	@echo '  make test                    run the conformance suite'
	@echo '  make validate                validate examples/ and templates/'
	@echo '  make validate DIR=path/      validate any folder or file'
	@echo '  make validate DIR=p ARGS=-v  pass flags through (-v, -j, --against X)'
	@echo '  make result                  rebuild the worked example result'
	@echo '  make check                   test + validate'
	@echo '  make lint                    pyflakes over src/ and tests/'
	@echo '  make clean                   remove caches'
	@echo '  make distclean               also remove .venv'

$(STAMP): requirements.txt
	@test -d $(VENV) || python3 -m venv $(VENV)
	@$(PIP) install -q --upgrade pip
	@$(PIP) install -q -r requirements.txt
	@touch $@

install: $(STAMP)

test: $(STAMP)
	@$(PY) -m pytest

# The validator CLI takes one target at a time, so walk DIR and stop on the
# first failure rather than reporting a misleading overall pass.
validate: $(STAMP)
	@rc=0; for t in $(DIR); do \
		echo "== $$t"; \
		$(PY) -m schema_v4.validator "$$t" $(ARGS) || rc=1; \
	done; exit $$rc

result: $(STAMP)
	@$(PY) -m schema_v4.build_example_result

check: test validate

lint: $(STAMP)
	@$(PIP) install -q pyflakes
	@$(PY) -m pyflakes src/schema_v4/*.py tests/*.py && echo 'pyflakes: clean'

clean:
	@find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache
	@echo 'caches removed'

distclean: clean
	@rm -rf $(VENV)
	@echo '.venv removed'
