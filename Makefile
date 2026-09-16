# All targets from PROJECT_BRIEF.md section 5. Later phases are declared now so
# the interface is stable; unimplemented ones say so rather than failing oddly.
PY ?= python3
APP ?= Stripe

.PHONY: setup test research research-one freeze-v1 verify sample score patterns \
        review site all clean

setup:                ## install pinned deps
	$(PY) -m pip install -r requirements.txt

test:                 ## run the unit tests
	$(PY) -m pytest -q

research:             ## pass 1 over all 100 apps (resumable)
	$(PY) -m agent.cli research

research-one:         ## the runnable trigger shown on the page: make research-one APP=Stripe
	$(PY) -m agent.cli research --app "$(APP)"

freeze-v1:            ## freeze results_v1.json + sha256
	$(PY) -m agent.cli freeze-v1

verify:               ## verification loops A-E -> results_v2.json
	$(PY) -m agent.cli verify

sample:               ## stratified sample -> ground_truth_template.csv
	$(PY) -m agent.cli sample

score:                ## accuracy v1 vs v2 vs v2+human -> score.json
	$(PY) -m agent.cli score

patterns:             ## stats + clusters -> patterns.json
	$(PY) -m agent.cli patterns

review:               ## print the needs_human queue (Loop F)
	$(PY) -m agent.cli review

site:                 ## render JSON -> site/dist/index.html
	$(PY) site/build.py

all: research freeze-v1 verify score patterns site

clean:
	rm -rf .pytest_cache **/__pycache__
