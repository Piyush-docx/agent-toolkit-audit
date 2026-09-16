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
- [ ] Commit `chore: P0 setup`

## P1 — Schema and rules (0:15–0:40)
- [ ] data/apps.csv — exactly 100 rows from brief Section 2
- [ ] agent/schema.py — pydantic v2 models + enums
- [ ] agent/rules.py — deterministic verdict rules
- [ ] tests/ — schema, rules, normaliser unit tests
- [ ] requirements.txt (pinned), .env.example, Makefile
- [ ] `make test` green; apps.csv row count == 100

## P2 — Research agent + 5-app slice (0:40–1:30)
- [ ] agent/llm.py (claude_code default, anthropic_api optional)
- [ ] agent/fetch.py (httpx + cache + text extract, playwright fallback)
- [ ] agent/prompts.py (PROMPT_VERSION)
- [ ] agent/research.py (concurrency 2-3, resumable, cached)
- [ ] agent/composio_check.py
- [ ] Run slice: Stripe(81), Salesforce(1), Sherlock(58), PitchBook(90), fanbasis(50)
- [ ] 🛑 HUMAN GATE: show 5 records as a table, wait for "continue"

## P3 — Full run + freeze v1 (1:30–2:15)
- [ ] Run all 100 (resumable, respects Pro limits)
- [ ] Composio check for all
- [ ] `make freeze-v1` → results_v1.json + .sha256, commit `freeze: v1 first pass`

## P4 — Sample template (parallel from 1:30)
- [ ] agent/sample.py → data/ground_truth_template.csv (links only, NO values)
- [ ] 🛑 HUMAN GATE: human fills data/ground_truth.csv blind (Claude must NOT fill truth values)

## P5 — Verification loops (2:15–3:15)
- [ ] Loop A evidence existence (httpx→WebFetch→Playwright, rapidfuzz ≥90)
- [ ] Loop B entailment judge (fresh context, field+quote+url only)
- [ ] Loop C targeted re-research (max 2 rounds)
- [ ] Loop D independent cross-check (auth_methods, access, existing_mcp)
- [ ] Loop E consistency checks
- [ ] results_v2.json + verify_log.json + per-loop counts

## P6 — Human review queue (3:15–3:35)
- [ ] `make review` prints needs_human queue
- [ ] 🛑 HUMAN GATE: human resolves → data/human_overrides.csv + docs/HUMAN_LOG.md

## P7 — Score + patterns (3:35–4:05)
- [ ] agent/score.py → data/score.json (v1, v2, v2+human; misses with causes)
- [ ] agent/patterns.py → data/patterns.json
- [ ] 4–6 headline sentences (every number checked against patterns.json)
- [ ] 🛑 HUMAN GATE: human approves headlines

## P8 — HTML page (4:05–5:05)
- [ ] site/build.py + template.html → site/dist/index.html
- [ ] Agent outputs: results.json, results.csv, patterns.json, score.json, summary.md, llms.txt
- [ ] Test at 375px and 1440px, filters work, no console errors, evidence links real

## P9 — Docs and review (5:05–5:30)
- [ ] README.md, docs/WALKTHROUGH.md
- [ ] code-review + simplify pass; security check (no secrets)

## P10 — Deploy (5:30–5:50)
- [ ] GitHub Pages workflow / Vercel config
- [ ] 🛑 HUMAN GATE: human creates public repo, pushes, enables Pages
- [ ] Verify live URL in incognito; final acceptance checklist (brief §14)
