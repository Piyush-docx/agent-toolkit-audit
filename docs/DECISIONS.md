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
