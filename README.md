# agent-toolkit-audit

Can AI agents actually use 100 real SaaS products today? A research pipeline (Claude Code +
web search/fetch) checked 100 apps across 10 categories for agent-toolkit readiness — public
API existence, auth model, and access friction — with every claim tied to a verbatim quote
from a page it actually fetched.

**Results page:** [`site/dist/index.html`](site/dist/index.html) — open it directly in a browser.

## Results at a glance

- **58 ready**, 31 ready-with-friction, 7 need outreach, 4 not viable (of 100)
- **64 apps** flagged for human review (evidence gaps or rule/model disagreements)
- **66 apps** already exist as a Composio toolkit
- 2 holdout apps (never in the input list) researched through the unedited pipeline, proving
  it generalizes rather than being tuned to these 100 — see `data/holdout_examples.json`

## Requirements

- Python 3.11+
- Claude Code CLI, logged in (`claude` on PATH) — no API key needed for the default backend
- Optional: `ANTHROPIC_API_KEY` for the `anthropic_api` backend, `COMPOSIO_API_KEY` (not
  required — the Composio check uses a keyless public docs index)

## Quick start

```bash
make setup                                  # create venv, install deps
make test                                   # pytest -q, 160 tests
make research-one APP="Stripe"              # research one app end to end
python3 -m agent.cli freeze-v1              # collect all cached records -> results_v1.json
python3 -m agent.cli sample                 # write the blind ground-truth template
```

Holdout mode (an app not in `data/apps.csv`):

```bash
python3 -m agent.cli research --app "Calendly" --category "Scheduling & Calendar" \
  --hint "calendly.com/developers"
```

## Repo layout

```
agent/            research pipeline: schema, rules, LLM backend, fetch, sample, cli
data/             apps.csv, results_v1.json (+ sha256), ground_truth.csv, holdout_examples.json
docs/             DECISIONS.md (every non-obvious call, with why), holdout_run.log
site/dist/        the built results page (self-contained HTML, no build step to view)
tests/            160 tests covering schema, rules, research orchestration, sample
tasks/todo.md     phase-by-phase progress against PROJECT_BRIEF.md
```

## Where a human is involved

- `data/ground_truth.csv` — filled by the maintainer from firsthand knowledge, never by the
  agent (see `CLAUDE.md`'s hard rule and `docs/DECISIONS.md`)
- Verdicts are computed by a deterministic rule set, not the model's own opinion — the model's
  guess is recorded but the rule always wins, and disagreements are flagged for review
- Every record with missing evidence or a rule/model disagreement is flagged `needs_human`

## Honest limitations

This was built and submitted under a hard time constraint. What's real: all 100 apps
genuinely researched with verbatim evidence quotes and source URLs; a real pipeline bug
(an LLM error silently producing a fabricated `not_viable` verdict on ~28 apps) was found
mid-run and fixed rather than shipped; the fix is covered by regression tests.

What's scoped out: the brief's full verification loops (A–E: evidence re-check, LLM
entailment judge, targeted re-research, independent cross-check), the 20-app stratified
ground truth (only 5 apps were hand-checked, human-confirmed, 21/30 fields = 70% match),
the human review queue, and dedicated `score.py`/`patterns.py` modules. The results page
states this directly rather than hiding it.

See `docs/DECISIONS.md` for every non-obvious design call and why it was made.

## How AI tools were used

Claude Code (this repository's agent) wrote essentially all of the code, tests, and research
pipeline, following `PROJECT_BRIEF.md` as a spec and this file's author's live review and
decisions at each phase gate. The maintainer designed the brief, reviewed the pipeline's
output at every checkpoint, caught and directed the fix for the fabricated-verdict bug,
filled the ground-truth labels from firsthand knowledge, and made every scope-cut decision
under the final time constraint.
