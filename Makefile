PY := .venv/bin/python

.PHONY: setup discover fetch fetch-all extract clean load report pipeline test inventory

setup:
	python3 -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt

discover:          ## CDX: list Wayback captures of every season roster page, 1998-2025
	$(PY) -m scrapers.discover

fetch:             ## newest usable capture per season (~1 min)
	$(PY) -m scrapers.fetch_rosters

fetch-all:         ## every unique capture per season (~3 min, ~77 MB)
	$(PY) -m scrapers.fetch_rosters --all-captures

extract:
	$(PY) -m scrapers.extract

clean:
	$(PY) -m pipeline.clean

load:
	$(PY) -m pipeline.load

report:
	$(PY) -m analysis.report

pipeline: discover fetch-all extract clean load report

test:
	$(PY) -m pytest -q

inventory:         ## capture counts per site era (slow: several minutes)
	$(PY) -m scrapers.discover --inventory
