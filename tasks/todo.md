# tasks/todo.md

Status: `[ ]` todo · `[~]` in progress · `[x]` done · 🛑 = human gate

## P0 — Setup (target 0:00–0:15)
- [x] Read PROJECT_BRIEF.md in full
- [x] Read agent-skills/skills/using-agent-skills/SKILL.md
- [x] Verify `claude --help` flags (-p, --output-format, --allowedTools, --model, --max-turns, --json-schema)
- [x] Smoke-test headless JSON output + WebFetch (both work, no permission denials)
- [x] Check Composio docs for toolkit listing (needs x-api-key; public page keyless but paginated)
- [x] Scaffold repo dirs + .gitignore
- [x] docs/DECISIONS.md with backend choices
- [x] tasks/todo.md (this file)
- [x] Commit `chore: P0 setup`

## P1 — Schema and rules (0:15–0:40) ✅
- [x] data/apps.csv — exactly 100 rows, ids 1–100, 10 categories × 10
- [x] agent/schema.py — pydantic v2 models + enums (`pass` alias, soft evidence flag)
- [x] agent/normalise.py — field-aware canonicalisation for scoring + Loop E
- [x] agent/rules.py — R1–R6 precedence + 11 Loop E consistency checks
- [x] tests/ — 90 tests green (apps.csv 13, schema 20, normalise 23, rules 34)
- [x] requirements.txt (pinned), .env.example, Makefile (all §5 targets)
- [x] D10–D15 + rule precedence table recorded in docs/DECISIONS.md

## P2 — Research agent + 5-app slice (0:40–1:30) ✅
- [x] agent/llm.py (claude_code default, anthropic_api optional) — LLMError now carries the CLI envelope for audit
- [x] agent/fetch.py (httpx + cache + text extract, playwright fallback)
- [x] agent/prompts.py (PROMPT_VERSION)
- [x] agent/research.py (concurrency 2-3, resumable, cached)
- [x] agent/composio_check.py — real API call verified (Stripe/Salesforce = yes, Sherlock/PitchBook/fanbasis = no)
- [x] Run slice: Stripe(81), Salesforce(1), Sherlock(58), PitchBook(90), fanbasis(50)
- [x] 🛑 HUMAN GATE: showed 5 records, human confirmed — continued to batch 1

## P2.5 — Holdout generalisation check (brief §6a) ✅
- [x] `--category`/`--hint` CLI flags so an app with no apps.csv row runs through the same command path
- [x] Ran Calendly (well-known) and Cal.com (obscure/OSS), completely unedited pipeline
- [x] data/holdout_examples.json + docs/holdout_run.log saved for the page's Proof section
- [x] Commit `feat: P2.5 holdout generalisation check`

## P3 — Full run + freeze v1 (1:30–2:15) ✅
- [x] Run all 100 (resumable, respects Pro limits) — batches 1–5, plus retries after the bug below
- [x] Found + fixed a real bug: an LLM error (session limit / structured-output retry
      exhaustion) fell through to apply_rules(), fabricating a not_viable verdict on
      empty data. 28 apps affected across batches 1–2. Added Verdict.NOT_RESEARCHED as
      a sentinel only the failure path can assign; re-ran every affected app for real.
- [x] Composio check for all
- [x] `make freeze-v1` → data/results_v1.json + .sha256, commit `freeze: v1 first pass`
      (58 ready, 31 ready_with_friction, 7 needs_outreach, 4 not_viable, 0 not_researched)

## P4 — Sample template (parallel from 1:30) ✅ (Claude side)
- [x] agent/sample.py → data/ground_truth_template.csv (120 rows: 20 apps × 6 fields,
      docs links pre-filled from cached records where known, NO values, NO agent answers)
- [x] tests/test_sample.py — 9 tests (stratification, blind-row shape, missing-record safety)
- [ ] 🛑 HUMAN GATE: human fills data/ground_truth.csv blind (Claude must NOT fill truth values)

## P5 — Verification loops — SKIPPED (time constraint)
- [ ] Not built: Loop A-E, results_v2.json, verify_log.json
- Stated explicitly as a limitation in README.md and on the results page.

## P6 — Human review queue — SKIPPED (time constraint)
- [ ] Not built: `make review`, human_overrides.csv, HUMAN_LOG.md resolution pass
- Stated explicitly as a limitation in README.md and on the results page.

## P7 — Score + patterns ✅ (reduced scope: v1 only, no v2)
- [x] agent/score.py → data/score.json — scored against 5 hand-labelled apps (30 fields,
      70% overall), exact match + Jaccard for lists, unknown-vs-unknown counted correct,
      every miss listed. No v2 to compare against (see P5).
- [x] agent/patterns.py → data/patterns.json — verdict/auth/access/MCP distributions per
      category, easy-wins list, 5 headline sentences traceable to patterns.json
- [x] tests/test_score.py (10) + tests/test_patterns.py (7) — 17 tests, all green
- [ ] 🛑 HUMAN GATE (headline approval): skipped — human directed a fast-path submission

## P8 — HTML page ✅ (reduced scope: no SVG charts/diagram)
- [x] site/build.py → site/dist/index.html — real build script reading results_v1.json,
      patterns.json, score.json (not hand-embedded data)
- [x] Readiness matrix (10×4, clickable cells filter the table), easy-wins/outreach/not-viable
      lists, full 100-row table with search + category/verdict/needs-human filters,
      verification section driven by score.json, holdout proof section
- [x] Light/dark via prefers-color-scheme; tables scroll horizontally in their own container
- [ ] Skipped: inline SVG charts, pipeline diagram — stated in the page's own limitations section

## P9 — Docs and review ✅
- [x] README.md — quick start, repo layout, human-in-the-loop points, honest limitations,
      AI-usage disclosure
- [x] docs/WALKTHROUGH.md — one-page plain-language file-by-file explanation for interview prep
- [x] Security check: no .env committed, no hardcoded secrets (one grep false-positive was a
      verbatim Stripe docs quote in results_v1.json)
- [ ] No formal code-review/simplify agent pass — time constraint

## P10 — Deploy ✅ (workflow only)
- [x] .github/workflows/deploy.yml — deploys site/dist/ to GitHub Pages on every push to main
- [x] Pushed to https://github.com/Piyush-docx/agent-toolkit-audit
- [ ] 🛑 Manual step still needed: Settings → Pages → Source → GitHub Actions (human must
      flip this switch; cannot be done via git push)
- [ ] Live URL not yet verified in incognito — pending the manual step above
