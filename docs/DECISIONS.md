# Decisions

One line per decision: what, why. Newest at the bottom of each phase.

## P0 — Environment and backend choices (2026-09-16)

All items below were **verified by running the command**, not assumed from the brief.

| # | Decision | Why |
|---|---|---|
| D1 | LLM backend = Claude Code headless (`claude -p`), called via `subprocess` | No `ANTHROPIC_API_KEY` in env (checked); Claude Pro includes Claude Code. |
| D2 | Flags used: `-p`, `--output-format json`, `--allowedTools WebSearch WebFetch`, `--model`, `--max-turns`, `--json-schema` | All confirmed present in `claude --help` on this machine. `--json-schema` exists, so structured output is enforced by the CLI rather than by parsing prose. |
| D3 | Do **not** ask for "JSON only" in the prompt when `--json-schema` is used | Smoke test returned a double-encoded string (`{"capital":"{\"capital\": \"Paris\"}"}`). With a schema, describe fields in prose and let the CLI enforce shape. |
| D4 | Track usage via `total_cost_usd`, `num_turns` and wall time from the result JSON | The `usage.server_tool_use` web-fetch counters stayed at 0 even on a successful WebFetch run, so they are not a reliable call count for the local tools. |
| D5 | WebSearch/WebFetch are usable headlessly with no permission prompt | Smoke test fetched docs.stripe.com and returned the correct auth answer with `permission_denials: []`. |
| D6 | Bulk extraction on `sonnet`, verification judgments on `opus` | Brief asks for cheaper model for bulk, stronger for judging. Both aliases accepted by `--model`. |
| D7 | Composio `on_composio` check = public toolkits page (keyless), upgraded to the REST API when `COMPOSIO_API_KEY` is set | `GET https://backend.composio.dev/api/v3.1/toolkits` returns **401 without a key** (verified). Public page `https://composio.dev/toolkits` returns 200 keyless. |
| D8 | Keyless Composio result may only be `yes` or `unknown`, never `no` | The public page is client-paginated: one fetch exposes ~62 of 1000+ slugs, and `?search=` is not server-side. Absence therefore cannot be proven without a key. This limitation is stated on the page. |
| D9 | `site/dist/` is committed, not gitignored | It is the GitHub Pages deploy folder. |

### Composio API facts (from docs, for later use)
- Base: `https://backend.composio.dev/api/v3.1`
- List toolkits: `GET /toolkits`, header `x-api-key`, params include `search`, `limit` (max 1000), `cursor`.
- Source: https://docs.composio.dev/reference/api-reference/toolkits/getToolkits

## P1 — Schema and rules (2026-09-16)

The brief's four verdict rules overlap and are not exhaustive. These four calls change
published results, so they were confirmed with the human before implementing.

| # | Decision | Why |
|---|---|---|
| D10 | `api_type == [cli_or_library]` → `not_viable`, blocker `local_only_tool` | Brief §2 asked us to "say which" for Sherlock (58) and Mermaid CLI (98). They are viable as *local skills* but not as *hosted toolkits*; `blocker_notes` carries that nuance so the page can state it. |
| D11 | `blocker == app_review` outranks self-serve access → `ready_with_friction` | App review is a real onboarding gate even on a free tier. Brief §2 says app review "is usually the blocker" for the Meta family (28, 32, 39). Prevents overstating "ready today". |
| D12 | `ApiBreadth` gains `unknown` (spec deviation) | The brief's `none` asserts "this app has no API", which is a different claim from "we did not determine breadth". Defaulting an unanswered field to `none` would publish a false claim. |
| D13 | Missing evidence is a computed `needs_human` flag, not a validation error | A hard error forces a repair loop whose only escape is inventing a URL/quote — which CLAUDE.md forbids. Missing evidence is a *finding* that feeds the evidence-support rate on the page. |
| D14 | `rules.apply_rules` is pure and total; compares enums by value | Never mutates the record (caller applies), always returns a valid verdict. Compares via `_value()` because `model_copy(update=...)` skips validation, so `verify.py` can hand it raw strings when applying a correction. |
| D15 | `verdict` is `Optional` on the model; `None` = "the LLM did not answer" | Lets a partial response parse. Invariant: never None on disk, because `research.py` always applies the rules before persisting (checked by consistency check E15). |

### Verdict rule precedence (most restrictive first)

| id | condition | verdict |
|----|-----------|---------|
| R1 | `access == no_public_api` | `not_viable` |
| R2 | `api_type` empty, `[none]`, or `[cli_or_library]` | `not_viable` |
| R3 | `access == partner_gated` | `needs_outreach` |
| R4 | `access in (paid_plan, admin_approval)` or `blocker == app_review` | `ready_with_friction` |
| R5 | `access` self-serve **and** `api_type ∩ {rest, graphql}` | `ready` |
| R6 | fallback — the brief is silent | `ready_with_friction`, `covered=False` → always needs_human |

R6 is the honesty valve: a shape the spec never described (e.g. self-serve + `sdk_only`, or a
missing `access`) is never silently called "ready". `covered=False` always escalates to a human.
