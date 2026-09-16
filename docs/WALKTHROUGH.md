# Walkthrough — explain every file in plain language

This is prep material for talking through the codebase, not documentation for a user. Read
top to bottom in the order data actually flows: CSV → schema → research → rules → freeze →
score/patterns → page.

## The data contract (`agent/schema.py`)

One pydantic model, `AppRecord`, is the single shape every piece of code agrees on — the
prompt asks the LLM to fill it, `rules.py` reads it, `score.py` compares it to ground truth,
the page renders it. Every field has an honest default (`unknown`, empty list, `None`) so a
partial LLM response still parses instead of crashing a whole batch.

Two things worth being able to explain:
- **`pass` is a Python keyword**, so the attribute is `pass_` with a pydantic alias mapping it
  back to `"pass"` on the wire. `dump_record()` is the one place that always dumps by alias, so
  this quirk never leaks into three different call sites.
- **`needs_human` is computed, not asserted.** A `@model_validator` checks which required
  evidence fields are missing and sets the flag automatically — the LLM can't "forget" to flag
  itself, and a human never has to trust the model's self-assessment.

## Turning research into a verdict (`agent/rules.py`)

The brief gives four verdict rules that overlap and don't cover every case. `apply_rules()` is
a **pure function** — same input, same output, never mutates, never raises — that resolves the
overlap with an explicit precedence order (R1 through R6, most restrictive first) and a named
fallback (R6, `covered=False`) for anything the brief didn't anticipate. The rule's verdict
always wins over whatever the LLM guessed; disagreements are recorded, not hidden.

`check_consistency()` is a separate, smaller set of checks (Loop E from the brief) that catch
self-contradictory records — e.g. a `primary_auth` that isn't in `auth_methods`.

## The research pipeline (`agent/research.py`, `agent/llm.py`, `agent/fetch.py`)

`llm.py` wraps the Claude Code CLI (`claude -p ... --json-schema ...`) as one function:
`complete_claude_code()`. It runs the CLI, parses whatever JSON envelope comes back, and
raises `LLMError` on genuine failure — carrying the full envelope so a hard failure still
leaves an audit trail.

`research.py`'s `research_app()` is the per-app loop: call the LLM, validate against the
schema, one repair attempt if validation fails, then `finalise()` which runs `apply_rules()`.
`run()` wraps that in a thread pool for concurrency, and is **resumable** — it checks
`cache/records/v1/{id}.json` before doing any work, so an interrupted run picks up where it
left off instead of re-paying for apps already done.

**The one real bug found and fixed in this project** lived here: when the LLM call failed
outright (a usage-limit error, or the CLI's structured-output retries being exhausted), the
resulting empty-data record still fell through to `apply_rules()`, which read the empty
`api_type`/`access` fields as genuine evidence of "no API" and returned `not_viable`. That's a
crash masquerading as a finding. The fix: `Verdict.NOT_RESEARCHED` is a sentinel only the
failure path can assign, and `finalise_failed()` explicitly skips rule application for records
with no real data behind them. 28 apps had gotten a fabricated verdict this way; all 28 were
re-researched for real after the fix. See `docs/DECISIONS.md` D21+ and the git log for the
full story — it's a good failure-mode story to be able to tell.

## Proving the pipeline isn't hard-coded (P2.5 holdout check)

`research.py` takes any `{name, category, hint}` — nothing in it references the specific 100
apps. To prove that rather than assert it, `agent/cli.py` has a holdout mode
(`--category`/`--hint` flags) that runs the exact same code path on an app with no
`apps.csv` row. Two apps never in the list (Calendly, Cal.com) were researched unedited; the
results are in `data/holdout_examples.json`.

## Checking against Composio (`agent/composio_check.py`)

Composio's public toolkit-listing API needs a key, but `docs.composio.dev/toolkits.md`
doesn't — it's a complete, keyless index. That distinction matters: a paginated, key-gated
listing can never prove absence ("not on this page" isn't "not on Composio"), but a complete
index can. This is why "not on Composio" is a trustworthy negative in the results, not a guess.

## Freezing v1 (`agent/cli.py`'s `cmd_freeze_v1`)

Collects every cached record into one `data/results_v1.json`, hashes it, refuses to run if any
app is missing (a partial freeze would silently ship gaps as "done"). After this, v1 is never
edited — any later correction becomes a new pass (v2), never a silent rewrite of v1.

## Scoring and patterns (`agent/score.py`, `agent/patterns.py`)

`score.py` compares v1's answers to `data/ground_truth.csv` field by field: exact match for
scalar fields, exact-set match (plus Jaccard, reported but not the headline number) for list
fields like `auth_methods`. `unknown` vs `unknown` counts as correct — the agent saying "I
don't know" when the truth is genuinely unknown is the right answer, not a miss. Blank
ground-truth rows (not yet labelled) are skipped, never scored as wrong.

`patterns.py` aggregates the whole 100-app population — verdict counts per category, auth
distribution, an "easy wins" list (ready today but not yet on Composio) — and generates the
page's headline sentences. Every number in a headline is pulled directly from the same
`patterns.json` a reviewer can open and check.

**Honest gap:** only v1 exists here. The brief's full verification pipeline
(`agent/verify.py`, Loops A–E: automated evidence re-check, an LLM entailment judge, targeted
re-research, an independent cross-check) was scoped out under the final time constraint, so
there's no v2 to compare v1 against. `score.py`'s output says this explicitly rather than
faking a v2 number.

## The page (`site/build.py` → `site/dist/index.html`)

A build script, not a hand-written file — it reads `results_v1.json`, `patterns.json`, and
`score.json` and generates the HTML/CSS/JS from them, so the page is reproducible from source
data rather than a one-off snapshot. Single file, no framework, works offline once loaded,
light/dark via `prefers-color-scheme`. The results table, readiness matrix, and lists are all
driven by the same embedded JSON so there's exactly one source of truth on the page.

## What to say if asked "what would you do with more time"

In order of value: (1) run the actual Loops A–E verification pipeline so there's a real v2 to
compare against, (2) fill the full 20-app stratified ground truth instead of the 5-app
subset, (3) build the human review queue (Loop F) so `needs_human` records have a resolution
path, (4) add the inline SVG charts and pipeline diagram the page spec called for. None of
these are hidden — they're listed on the page itself and in the README.
