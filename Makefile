# Use bash, stop on the first error, and let a failure inside a pipe fail the
# rule. Without pipefail a script that dies still "succeeds" because `tee` is
# the last command in the pipe, and make carries on as if nothing happened.
SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c

.PHONY: all venv deps check post01 post02 clean

# Override if your interpreter is named something else: make PY=python3.12
PY ?= python3
POST01 = post-01-the-last-place-optimal-means-anything
POST02 = post-02-rows-columns-and-what-they-cost

all: check post01 post02

# Installs into the SAME interpreter that will run the scripts. Calling `pip`
# on its own is the usual way to end up with the packages in one Python and
# the code in another, which fails later and confusingly.
# make cannot activate anything for you: activation edits the shell it runs
# in, and make runs in a child. So this creates the environment and prints the
# one line you have to type yourself.
venv:
	$(PY) -m venv .venv
	@echo ""
	@echo "Created .venv. Activate it in this shell, then install:"
	@echo "    source .venv/bin/activate"
	@echo "    python3 -m pip install -r requirements.txt"
	@echo ""

deps:
	$(PY) -m pip install -r requirements.txt

check:
	@$(PY) -c "import pulp, highspy" 2>/dev/null || { \
	  echo ""; \
	  echo "PuLP or HiGHS is missing from the interpreter make is about to use:"; \
	  echo "    $$($(PY) -c 'import sys; print(sys.executable)')"; \
	  echo ""; \
	  echo "Install into that same interpreter:"; \
	  echo "    $(PY) -m pip install -r requirements.txt"; \
	  echo ""; \
	  echo "Two things usually cause this."; \
	  echo "  1. 'pip install' succeeded into a different Python from 'python3'."; \
	  echo "     'python3 -m pip' cannot make that mistake."; \
	  echo "  2. pip refused with 'externally-managed-environment' (PEP 668)."; \
	  echo "     Then you need a virtual environment:"; \
	  echo "         make venv"; \
	  echo "         source .venv/bin/activate"; \
	  echo "         python3 -m pip install -r requirements.txt"; \
	  echo ""; \
	  exit 1; }

# No `cd` here on purpose. The scripts resolve their own paths from __file__,
# so they can be run from anywhere, and not changing directory means a relative
# PY such as .venv/bin/python3 keeps working.
post01:
	$(PY) $(POST01)/build_data.py
	$(PY) $(POST01)/stigler.py | tee $(POST01)/out/stigler.txt
	$(PY) $(POST01)/blend.py   | tee $(POST01)/out/blend.txt
	$(PY) $(POST01)/make_figures.py

post02:
	$(PY) $(POST02)/analyze_structure.py | tee $(POST02)/out/structure.txt
	$(PY) $(POST02)/make_figures.py

clean:
	rm -rf */out/*.txt */__pycache__
