# PROJECT BRIEF — App Toolkit Readiness Research Agent (Composio take-home)

> This file is the single source of truth for building this project.
> It is written for Claude Code working in this repo together with a human (the candidate).
> Read it top to bottom before writing any code. Follow the phases in order.
> 🛑 = HUMAN GATE: stop, show the result, and wait for the human to say "continue".

---

## 0. How to use this brief (for Claude Code)

1. Read `agent-skills/skills/using-agent-skills/SKILL.md` first. Use the skills as mapped below.
2. Create `tasks/todo.md` from Section 13 (the phase list) and keep it updated.
3. Work phase by phase. Each phase has "Done when" checks. Do not start the next phase until they pass.
4. Commit after every task (`git-workflow-and-versioning`).
5. If something in this brief is wrong or impossible (a CLI flag doesn't exist, a library changed),
   **check the official docs** (`source-driven-development`), pick the closest working option,
   and record the decision in `docs/DECISIONS.md` (one line: what, why).
6. Do not over-engineer. Simple, explainable code wins. The candidate will be asked to explain every part in an interview.

### Skill mapping
| Phase | Skills to apply (in `agent-skills/skills/`) |
|---|---|
| Spec / plan | `spec-driven-development`, `planning-and-task-breakdown` |
| Build pipeline | `incremental-implementation`, `source-driven-development`, `api-and-interface-design` |
| Tests | `test-driven-development` (unit tests for schema, normaliser, scorer, evidence checker) |
| Verification design | `doubt-driven-development` |
| Failures | `debugging-and-error-recovery` |
| HTML page | `frontend-ui-engineering`, `references/accessibility-checklist.md`, `browser-testing-with-devtools` if available |
| Review | `code-review-and-quality`, `code-simplification`, `security-and-hardening` (no secrets in repo) |
| Ship | `documentation-and-adrs`, `shipping-and-launch` |

---

## 1. The assignment (what Composio asked for — do not lose any of this)

**Role:** AI Product Ops Intern at Composio. **Time budget:** 6–8 h; submitting early is better.

**Context:** Composio turns apps into tools that AI agents can call. Before building a toolkit
for an app, they research: auth type, self-serve vs partner-gated, API surface, and whether it
can be an MCP server or agent-callable skills. Doing this by hand across hundreds of apps does
not scale. This assignment is a small, real version of that problem.

**For each of the 100 apps, capture:**
- Category + one-line description
- Auth method(s): OAuth2, API key, Basic, token, other
- Self-serve vs gated: free/trial credentials vs paid plan, admin approval, partnership/contact-sales
- API surface: documented public REST/GraphQL, rough breadth, any existing MCP
- Buildability verdict: could it be an agent toolkit today; main blocker if not
- Evidence: docs URL / article behind each answer
- "and more" → we add extra useful fields (Section 4)

**The actual point:**
1. **Find the patterns.** Cluster results; say which auth dominates, which categories are self-serve vs gated,
   the most common blocker, easy wins vs what needs outreach. Insight over raw table.
2. **Do it with an agent.** Build an agent/pipeline that researches all 100. Using Composio's own SDK/MCP is in
   the spirit of the role. Explain what it does and where it needed a human.
3. **Verify accuracy (matters most).** Sample the 100, cross-check against real docs by hand, report right/wrong.
   Build real verification loops (agent, browser, other) plus human checks. Show accuracy moving from a lower
   first pass to a higher one because of those loops.

**Deliverable:** one self-explanatory HTML page (case study) a reviewer understands in ~2 minutes with no
narration. It must show on its own:
- the **patterns** (top, plainly stated, the headline)
- the **findings** (clean, skimmable table/matrix)
- the **agent** (what was built, where a human was needed)
- the **proof** (the app built: live link or runnable trigger)
- the **verification** (accuracy on a sample, hits AND misses shown honestly)
- both the final output and the process/workflow
- easy for **both a human and an agent** to consume

**Constraints:** AI tools allowed, but the candidate must understand everything. If the agent got things
wrong or an app defeated us, say so on the page. No paid accounts needed; "gated, with evidence" is a correct finding.

**Submit:** (a) live link to the deployed page, (b) link to source repo with a short README on how to run the agent.

---

## 2. The 100 apps

Create `data/apps.csv` with columns `id,name,category,hint` containing exactly these 100 rows.

| id | name | category | hint |
|---|---|---|---|
| 1 | Salesforce | CRM & Sales | salesforce.com |
| 2 | HubSpot | CRM & Sales | hubspot.com |
| 3 | Pipedrive | CRM & Sales | pipedrive.com |
| 4 | Attio | CRM & Sales | attio.com |
| 5 | Twenty | CRM & Sales | twenty.com (open-source CRM) |
| 6 | Podio | CRM & Sales | podio.com |
| 7 | Zoho CRM | CRM & Sales | zoho.com/crm |
| 8 | Close | CRM & Sales | close.com |
| 9 | Copper | CRM & Sales | copper.com |
| 10 | DealCloud | CRM & Sales | api.docs.dealcloud.com |
| 11 | Zendesk | Support & Helpdesk | zendesk.com |
| 12 | Intercom | Support & Helpdesk | intercom.com |
| 13 | Freshdesk | Support & Helpdesk | freshdesk.com |
| 14 | Front | Support & Helpdesk | front.com |
| 15 | Pylon | Support & Helpdesk | usepylon.com |
| 16 | LiveAgent | Support & Helpdesk | liveagent.com |
| 17 | Plain | Support & Helpdesk | plain.com |
| 18 | Help Scout | Support & Helpdesk | helpscout.com |
| 19 | Gorgias | Support & Helpdesk | gorgias.com |
| 20 | Gladly | Support & Helpdesk | gladly.com |
| 21 | Slack | Communications & Messaging | slack.com |
| 22 | Twilio | Communications & Messaging | twilio.com |
| 23 | Zoho Cliq | Communications & Messaging | zoho.com/cliq |
| 24 | Lark (Larksuite) | Communications & Messaging | open.larksuite.com |
| 25 | Pumble | Communications & Messaging | pumble.com |
| 26 | Discord | Communications & Messaging | discord.com |
| 27 | Telegram | Communications & Messaging | core.telegram.org |
| 28 | WhatsApp Business | Communications & Messaging | developers.facebook.com/docs/whatsapp |
| 29 | Aircall | Communications & Messaging | aircall.io |
| 30 | Vonage | Communications & Messaging | developer.vonage.com |
| 31 | Google Ads | Marketing, Ads, Email & Social | developers.google.com/google-ads |
| 32 | Meta Ads | Marketing, Ads, Email & Social | developers.facebook.com/docs/marketing-apis |
| 33 | LinkedIn Ads | Marketing, Ads, Email & Social | learn.microsoft.com/linkedin/marketing |
| 34 | GoHighLevel | Marketing, Ads, Email & Social | highlevel.stoplight.io |
| 35 | Mailchimp | Marketing, Ads, Email & Social | mailchimp.com/developer |
| 36 | Klaviyo | Marketing, Ads, Email & Social | developers.klaviyo.com |
| 37 | systeme.io | Marketing, Ads, Email & Social | systeme.io (funnel builder) |
| 38 | Pinterest | Marketing, Ads, Email & Social | developers.pinterest.com |
| 39 | Threads (Meta) | Marketing, Ads, Email & Social | developers.facebook.com/docs/threads |
| 40 | SendGrid | Marketing, Ads, Email & Social | sendgrid.com |
| 41 | Shopify | Ecommerce | shopify.dev |
| 42 | WooCommerce | Ecommerce | woocommerce.com/document/woocommerce-rest-api |
| 43 | BigCommerce | Ecommerce | developer.bigcommerce.com |
| 44 | Salesforce Commerce Cloud | Ecommerce | developer.salesforce.com/docs/commerce |
| 45 | Magento (Adobe Commerce) | Ecommerce | developer.adobe.com/commerce |
| 46 | Squarespace | Ecommerce | developers.squarespace.com |
| 47 | Ecwid | Ecommerce | api-docs.ecwid.com |
| 48 | Gumroad | Ecommerce | gumroad.com/api |
| 49 | Amazon Selling Partner | Ecommerce | developer-docs.amazon.com/sp-api |
| 50 | fanbasis | Ecommerce | fanbasis.com |
| 51 | DataForSEO | Data, SEO & Scraping | docs.dataforseo.com |
| 52 | SE Ranking | Data, SEO & Scraping | seranking.com/api |
| 53 | Ahrefs | Data, SEO & Scraping | ahrefs.com/api |
| 54 | MrScraper | Data, SEO & Scraping | docs.mrscraper.com |
| 55 | Apify | Data, SEO & Scraping | docs.apify.com |
| 56 | Firecrawl | Data, SEO & Scraping | firecrawl.dev |
| 57 | Bright Data | Data, SEO & Scraping | brightdata.com |
| 58 | Sherlock | Data, SEO & Scraping | github.com/sherlock-project/sherlock |
| 59 | Waterfall.io | Data, SEO & Scraping | waterfall.io (contact/company intel) |
| 60 | Clay | Data, SEO & Scraping | clay.com |
| 61 | GitHub | Developer, Infra & Data | docs.github.com/rest |
| 62 | Vercel | Developer, Infra & Data | vercel.com/docs/rest-api |
| 63 | Netlify | Developer, Infra & Data | docs.netlify.com/api |
| 64 | Cloudflare | Developer, Infra & Data | developers.cloudflare.com/api |
| 65 | Supabase | Developer, Infra & Data | supabase.com/docs |
| 66 | Neo4j | Developer, Infra & Data | neo4j.com/docs/api |
| 67 | Snowflake | Developer, Infra & Data | docs.snowflake.com |
| 68 | MongoDB Atlas | Developer, Infra & Data | mongodb.com/docs/atlas/api |
| 69 | Datadog | Developer, Infra & Data | docs.datadoghq.com/api |
| 70 | Sentry | Developer, Infra & Data | docs.sentry.io/api |
| 71 | Notion | Productivity & PM | developers.notion.com |
| 72 | Airtable | Productivity & PM | airtable.com/developers |
| 73 | Linear | Productivity & PM | developers.linear.app |
| 74 | Jira | Productivity & PM | developer.atlassian.com |
| 75 | Asana | Productivity & PM | developers.asana.com |
| 76 | Monday.com | Productivity & PM | developer.monday.com |
| 77 | ClickUp | Productivity & PM | clickup.com/api |
| 78 | Coda | Productivity & PM | coda.io/developers |
| 79 | Smartsheet | Productivity & PM | smartsheet.com/developers |
| 80 | Harvest | Productivity & PM | harvestapp.com (help.getharvest.com/api-v2) |
| 81 | Stripe | Finance & Fintech | stripe.com/docs/api |
| 82 | Plaid | Finance & Fintech | plaid.com/docs |
| 83 | Binance | Finance & Fintech | binance-docs.github.io |
| 84 | Paygent Connect | Finance & Fintech | paygent (NMI-powered) |
| 85 | iPayX | Finance & Fintech | ipayx.ai/docs |
| 86 | QuickBooks | Finance & Fintech | developer.intuit.com |
| 87 | Xero | Finance & Fintech | developer.xero.com |
| 88 | Brex | Finance & Fintech | developer.brex.com |
| 89 | Ramp | Finance & Fintech | docs.ramp.com |
| 90 | PitchBook | Finance & Fintech | pitchbook.com (research API) |
| 91 | NotebookLM | AI, Research & Media | cloud.google.com/gemini (Enterprise API) |
| 92 | Otter AI | AI, Research & Media | help.otter.ai (MCP server) |
| 93 | Fathom | AI, Research & Media | fathom.video |
| 94 | Consensus | AI, Research & Media | consensus.app (OAuth requested) |
| 95 | Reducto | AI, Research & Media | reducto.ai (document parsing) |
| 96 | Devin | AI, Research & Media | docs.devin.ai (MCP) |
| 97 | higgsfield | AI, Research & Media | higgsfield.ai/cli (content suite) |
| 98 | Mermaid CLI | AI, Research & Media | github.com/mermaid-js/mermaid-cli |
| 99 | YouTube Transcript | AI, Research & Media | transcriptapi.com |
| 100 | Grain | AI, Research & Media | grain.com (meeting notes) |

**Known hard cases** (the agent must handle these without guessing):
- No hosted API / local tool: Sherlock (58), Mermaid CLI (98) → `api_type` cli/library, verdict likely not_viable as hosted toolkit or "wrap as local skill"; say which.
- Likely sales/partner-gated: DealCloud (10), Gladly (20), PitchBook (90), Salesforce Commerce Cloud (44), Amazon SP-API (49, developer registration/approval), NotebookLM (91, enterprise), LinkedIn Ads (33, partner program).
- Thin/obscure docs: Paygent Connect (84), iPayX (85), fanbasis (50), Waterfall.io (59), systeme.io (37), MrScraper (54), higgsfield (97).
- Ambiguous identity: "Close" (the CRM, close.com), "Plain" (plain.com support platform), "Twenty" (twenty.com CRM), "YouTube Transcript" (transcriptapi.com, a third-party API — not YouTube itself).
- Hint says MCP exists: Otter AI (92), Devin (96) → verify, don't assume.
- Hint "OAuth requested" (Consensus 94) → find out whether public OAuth actually exists; if not, say so.
- Meta family (28, 32, 39) → app review / business verification is usually the blocker; verify.

---

## 3. Environment and constraints (read carefully)

- The candidate has **Claude Pro** (includes Claude Code). There may be **no Anthropic API key**.
- Therefore the default LLM backend is **Claude Code headless mode** (`claude -p`), called from Python via
  `subprocess`, with only the `WebSearch` and `WebFetch` tools allowed.
  - Verify exact flags with `claude --help` before coding (expected: `-p/--print`, `--output-format json`,
    `--allowedTools`, `--max-turns`, `--model`; possibly `--json-schema`). Record what you used in `docs/DECISIONS.md`.
  - Pro has **usage limits per rolling window**. Design for this: concurrency 2–3, a disk cache per app,
    `--resume`-safe runs (skip apps already done), and graceful handling of limit errors (save progress, print
    "limit reached, rerun later"). Prefer a smaller model for bulk extraction if `--model` allows it, and the
    stronger model for verification judgments. Measure and report usage (calls, wall time).
- Backend must be **pluggable** (`agent/llm.py`): `claude_code` (default) and `anthropic_api` (used only if
  `ANTHROPIC_API_KEY` is set). Same interface: `complete(prompt, schema, tools) -> dict`.
- **Composio (spirit of the role):** implement an optional `composio` integration, and do it in a way that works
  on a free account. Check current docs at docs.composio.dev first (source-driven — do not code from memory).
  Two cheap, meaningful uses, in order of preference:
  1. **"Already on Composio?" field:** check whether each app already exists as a Composio toolkit
     (via SDK toolkit listing or the public toolkits page). This is a genuinely useful extra field for Composio.
  2. Use a Composio-hosted search/scrape toolkit (or Composio MCP added to Claude Code) as an alternate fetch backend.
  If Composio setup blocks for >30 min, 🛑 ask the human; do not let it block the pipeline. Record what worked on the page.
- Deterministic work (fetching pages for evidence checks, schema validation, normalisation, scoring, stats,
  HTML build) is **plain Python**, not LLM. Use `httpx` (timeouts, retries, UA header), `selectolax` or
  `beautifulsoup4` for text extraction, `pydantic` v2 for the schema, `pytest` for tests.
- Some docs sites are JS-rendered (Notion-hosted, Stoplight, Readme.io). If `httpx` text is empty, try Claude Code
  `WebFetch`, then optionally Playwright (`playwright` Python, headless Chromium) as a "browser" verifier. Log which method succeeded.
- Secrets only in `.env` (gitignored). Provide `.env.example`. Never commit keys.
- Python 3.11+. Dependencies pinned in `requirements.txt`. Everything runnable with `make` targets.

---

## 4. Data schema (`agent/schema.py`, pydantic v2)

One `AppRecord` per app. Enums are strict — the LLM must choose from them.

| field | type | allowed values / notes |
|---|---|---|
| `id`, `name`, `category` | int, str, str | copied from apps.csv, never LLM-generated |
| `one_liner` | str | ≤ 15 words, what the product does |
| `docs_url` | str \| null | main API docs page |
| `auth_methods` | list[enum] | `oauth2`, `api_key`, `basic`, `bearer_token`, `jwt`, `hmac_signature`, `other`, `none` |
| `primary_auth` | enum | the one a toolkit would use |
| `access` | enum | `self_serve_free`, `self_serve_trial`, `paid_plan`, `admin_approval`, `partner_gated`, `no_public_api` |
| `access_notes` | str | one sentence, e.g. "API only on Enterprise plan" |
| `api_type` | list[enum] | `rest`, `graphql`, `websocket`, `soap`, `sdk_only`, `cli_or_library`, `none` |
| `api_breadth` | enum | `broad` (many resources, CRUD), `moderate`, `narrow` (few endpoints), `none` |
| `openapi_spec` | enum | `yes`, `no`, `unknown` |
| `existing_mcp` | enum | `official`, `community`, `none_found` |
| `mcp_url` | str \| null | |
| `webhooks` | enum | `yes`, `no`, `unknown` |
| `sandbox_or_test_mode` | enum | `yes`, `no`, `unknown` |
| `rate_limits_documented` | enum | `yes`, `no`, `unknown` |
| `on_composio` | enum | `yes`, `no`, `unknown` (from Composio check, not LLM guess) |
| `verdict` | enum | `ready` (self-serve + documented API), `ready_with_friction` (works but app review / OAuth app approval / paid tier for some scopes), `needs_outreach` (partner/sales gate), `not_viable` (no usable API) |
| `blocker` | enum \| null | `none`, `paid_plan`, `partner_program`, `app_review`, `admin_approval`, `no_public_api`, `sparse_docs`, `local_only_tool`, `other` |
| `blocker_notes` | str \| null | |
| `evidence` | list[Evidence] | `{field, url, quote}`; **at least one per field among** auth_methods, access, api_type, existing_mcp, verdict. `quote` ≤ 40 words copied verbatim from the page |
| `confidence` | float 0–1 | model self-report |
| `needs_human` | bool | |
| `needs_human_reason` | str \| null | |
| `pass` | str | `v1`, `v2` |
| `verification` | dict | filled by verifier: per-field `supported / unsupported / unreachable`, method used |

Also define the **verdict rules** in code (`agent/rules.py`) so verdict is partly deterministic:
- `access == no_public_api` or `api_type == [none]` → `not_viable`
- `access == partner_gated` → `needs_outreach`
- `access in (paid_plan, admin_approval)` or blocker `app_review` → `ready_with_friction` (unless evidence says otherwise)
- `access in (self_serve_free, self_serve_trial)` and api_type has rest/graphql → `ready`
If the LLM verdict disagrees with the rule, keep the rule, flag `needs_human`, log it. Document rules on the page.

Unit-test the schema, the rules and the normaliser (`tests/`).

---

## 5. Repo structure

```
.
├── CLAUDE.md
├── PROJECT_BRIEF.md
├── README.md
├── Makefile
├── requirements.txt
├── .env.example
├── .gitignore               # .env, cache/, .venv/, __pycache__/
├── agent-skills/            # provided skills pack (do not modify)
├── agent/
│   ├── __init__.py
│   ├── schema.py            # pydantic models + enums
│   ├── rules.py             # deterministic verdict rules
│   ├── llm.py               # backends: claude_code (default), anthropic_api
│   ├── prompts.py           # all prompts in one place, versioned (PROMPT_VERSION)
│   ├── fetch.py             # httpx fetch + text extract + cache; playwright fallback
│   ├── composio_check.py    # "already on Composio?" + optional search backend
│   ├── research.py          # pass 1 → data/results_v1.json
│   ├── verify.py            # loops → data/results_v2.json + data/verify_log.json
│   ├── sample.py            # stratified sample → data/ground_truth_template.csv
│   ├── score.py             # accuracy v1 vs v2 → data/score.json
│   ├── patterns.py          # stats + clusters → data/patterns.json
│   └── cli.py               # `python -m agent.cli ...`
├── site/
│   ├── build.py             # renders JSON → site/dist/index.html (Jinja2)
│   ├── template.html
│   └── dist/                # deployed folder: index.html, results.json, results.csv, summary.md, llms.txt
├── data/
│   ├── apps.csv
│   ├── results_v1.json      # FROZEN after Phase 3
│   ├── results_v2.json
│   ├── verify_log.json
│   ├── ground_truth.csv     # filled by HUMAN only
│   ├── score.json
│   ├── patterns.json
│   └── run_stats.json       # calls, time, failures, per pass
├── cache/                   # fetched pages + raw LLM outputs (gitignored except a small sample)
├── docs/
│   ├── DECISIONS.md
│   └── HUMAN_LOG.md         # every human intervention: when, what, why
├── tasks/
│   └── todo.md
└── tests/
```

Makefile targets: `setup`, `test`, `research` (all), `research-one APP="Stripe"`, `freeze-v1`, `verify`,
`sample`, `score`, `patterns`, `site`, `all`. `make research-one APP=Stripe` is the **runnable trigger** shown on the page.

---

## 6. Research agent — pass 1 (`agent/research.py`)

Per app (concurrency 2–3, resumable, cached):
1. Build the prompt from `prompts.RESEARCH` with name, category, hint, schema (JSON), enum definitions, and rules:
   - Use WebSearch/WebFetch; start from the hint URL; prefer official docs, developer portals, pricing/plan pages,
     official GitHub. Third-party blogs only as last resort and must be labelled.
   - Every evidence quote must be copied **verbatim** from a page actually fetched in this session.
   - If not found: use `unknown`/`none_found`, lower confidence, set `needs_human` with reason. Never guess.
   - Check for an MCP server: official docs, official GitHub org, and the MCP registry/community lists.
   - Output **only JSON** matching the schema.
2. Parse → validate with pydantic → if invalid, one repair attempt with the validation error → else store as
   `{id, error}` with `needs_human = true`.
3. Apply `rules.py`, add `on_composio` from `composio_check.py`.
4. Save raw output to `cache/llm/v1/{id}.json`, record timing/usage in `run_stats.json`.

**Slice first:** run on 5 apps — Stripe (81), Salesforce (1), Sherlock (58), PitchBook (90), fanbasis (50).
🛑 HUMAN GATE: show the 5 records in a readable table. Human confirms they look right before running all 100.

Then run all 100. Then `make freeze-v1`: copy to `data/results_v1.json`, compute its SHA-256 into
`data/results_v1.sha256`, commit with message `freeze: v1 first pass`. v1 is never edited after this.

### 6a. Holdout generalisation check (P2.5 — do this right after freezing v1)

The 100 apps are the input data, not something baked into the pipeline — `research.py` takes any
`{name, category, hint}` and runs the same generic prompt regardless of which app it is. Prove this instead
of just asserting it: pick **2–3 apps NOT in `data/apps.csv`** (one well-known, one obscure — e.g. Calendly and
a niche SaaS tool of the human's choosing), run `make research-one APP=<name>` completely unedited, and save the
raw output to `data/holdout_examples.json` alongside a captured terminal log in `docs/holdout_run.log`. This
is the primary evidence, shown on the page (Section 10, Proof), that the agent generalises beyond the given list.

---

## 7. Verification loops (`agent/verify.py`) — the most important part

Apply `doubt-driven-development`. Produce `results_v2.json` and `verify_log.json` (every change: app, field, old, new, reason, loop).

**Loop A — Evidence existence (deterministic).** For each evidence item: fetch URL (httpx → WebFetch → Playwright
fallback). Normalise whitespace/case; check the quote exists (exact, then fuzzy ≥ 90 with `rapidfuzz`). Mark
`supported_text / quote_not_found / unreachable`. Dead URL or missing quote = the field is **unproven**.

**Loop B — Evidence entailment (LLM judge, fresh context).** For each field with an existing quote, ask a
separate prompt with ONLY `{field, claimed value, quote, url}`: "Does this quote support this value? yes/no/partial
+ reason." The judge must not see the original reasoning (fresh context = real doubt).

**Loop C — Targeted re-research.** For every app with any unproven/unsupported field, confidence < 0.7, schema
repair, or rule/LLM verdict disagreement: rerun research **for those fields only**, with a prompt that states what
failed and why, and asks for different, primary sources. Re-run A and B on the new evidence. Max 2 rounds per app.

**Loop D — Independent cross-check on the high-value fields.** For `auth_methods`, `access`, `existing_mcp`:
a second independent extraction with a different prompt (and different model if available). Disagreement →
`needs_human = true` with both answers stored.

**Loop E — Consistency checks (deterministic).** e.g. `access = no_public_api` but `api_breadth = broad`;
`existing_mcp = official` but no `mcp_url`; `verdict = ready` but blocker set. Violations → re-research or flag.

**Loop F — Human review queue.** `make review` prints all `needs_human` apps with both answers and links.
The human resolves them; every resolution is logged in `docs/HUMAN_LOG.md` and applied via
`data/human_overrides.csv` (never by hand-editing JSON). Overrides are shown on the page as "human-corrected".

Report per loop: how many fields checked, failed, changed. This feeds the "accuracy went up because…" story.

---

## 8. Accuracy measurement (`agent/sample.py`, `agent/score.py`)

**Sample:** 20 apps, stratified: 2 per category, one "easy/well-known" + one "hard/obscure". Default:
HubSpot, DealCloud | Zendesk, Gladly | Slack, WhatsApp Business | Meta Ads, systeme.io | Shopify, fanbasis |
Firecrawl, Sherlock | GitHub, Neo4j | Notion, Harvest | Stripe, Paygent Connect | Otter AI, NotebookLM.
(Human may swap. Fixed seed if random.)

`make sample` writes `data/ground_truth_template.csv` with columns:
`id,name,field,truth_value,source_url,notes` for fields: `auth_methods, access, api_type, existing_mcp, webhooks, verdict`,
**pre-filled only with the official docs links to check — no values, and no agent answers** (blind labelling).

🛑 HUMAN GATE (can start in parallel as soon as Phase 3 is running): the human fills `data/ground_truth.csv`
from real docs. **Claude Code must not fill truth values.** Claude may help the human find a page, but the human decides.

**Scoring rules** (`score.py`, unit-tested):
- enum fields: exact match after normalisation
- list fields (`auth_methods`, `api_type`): report exact-set match AND Jaccard; headline uses exact-set
- `unknown` when truth is known = wrong; `unknown` when truth is also unknown = right
- Output: per-field and overall accuracy for v1, v2, and v2+human; list of every miss with truth, answer, cause
  category (`wrong_source`, `stale_docs`, `hallucinated`, `ambiguous_definition`, `unreachable_page`, `other`)
- Also report: evidence-support rate across **all 100** (from Loop A/B), and how many apps needed a human.

Be honest if v2 does not beat v1 on some field — show it and explain.

---

## 9. Patterns (`agent/patterns.py`)

Compute from `results_v2.json` (+ overrides) into `patterns.json`:
- Auth distribution overall and per category (primary_auth and any-auth)
- Access (self-serve vs gated) per category
- Verdict counts per category (for the readiness matrix)
- Blocker frequency ranking
- Existing MCP: how many official / community / none; per category
- On Composio already: yes/no split; **ready but not on Composio = easy wins list**
- Needs-outreach list (with the gate reason)
- Not-viable list (with why)
- Webhooks / sandbox availability rates

Then generate **4–6 headline sentences** (LLM drafts from `patterns.json` only; every number must be taken from
the JSON — add a check that each number in a sentence exists in patterns.json). Examples of the shape (not the content):
"X of 100 apps are ready today; OAuth2 is the primary auth for Y%." / "Gating clusters in Z and W categories…"
🛑 HUMAN GATE: human approves/edit headlines.

---

## 10. The HTML page (`site/build.py` → `site/dist/index.html`)

Single static page, no framework required (vanilla JS + inline CSS). Reads embedded JSON. Must work offline once
loaded. Light/dark via `prefers-color-scheme`. Responsive (laptop and phone). Accessible (semantic HTML, contrast,
keyboard-usable filters). Tables scroll horizontally inside their container, never the page.

Order (a reviewer must get it in ~2 minutes):
1. **Header:** title, one-sentence summary, links: Repo · Raw data (JSON/CSV) · How to run.
2. **Headline patterns** (the 4–6 sentences) + **4 stat tiles**: # ready today · % OAuth2 primary ·
   % self-serve · accuracy v1 → v2 (e.g. "71% → 92%").
3. **Readiness matrix:** 10 categories × 4 verdicts, colored cells with counts; clicking a cell filters the table.
4. **Charts** (inline SVG, no external libs needed): auth by category (stacked bar), blockers ranking (bar).
5. **Easy wins vs needs outreach vs not viable:** three short lists.
6. **Full table of 100:** search box + filters (category, verdict, access, auth, needs_human). Columns: #, app,
   category, one-liner, auth, access, API, MCP, on Composio, verdict, blocker, confidence, evidence (links).
   Expandable row shows all evidence quotes with verification status icons and any human override.
7. **How the agent works:** a simple diagram (inline SVG or Mermaid) of research → verify loops → human → score →
   page; which tools/backends were used (Claude Code headless, WebSearch/WebFetch, httpx, Playwright, Composio);
   run stats (calls, time, failures); **where a human was needed** (from HUMAN_LOG.md, with counts and examples).
8. **Verification:** per-field accuracy table v1 / v2 / v2+human; bar chart v1 vs v2; what each loop caught
   (counts from verify_log); **list of misses** with cause; evidence-support rate across all 100.
9. **Proof / run it yourself:** open with one explicit sentence: *"This agent runs on Claude Code using the
   candidate's own Claude subscription, so this page cannot execute it live in your browser — instead, here is
   a real command, a captured run, and proof it generalizes beyond the given 100."* Then show: the exact commands
   (`make setup`, `make research-one APP=Stripe`), a real captured terminal log of one run, a sample raw output,
   and the **holdout results** (Section 6a) run on 2–3 apps not in the original 100, unedited pipeline, to prove
   the code is generic and not tuned to this list. If a GitHub Actions `workflow_dispatch` trigger was set up
   (Section 11), link it as the closest thing to a live trigger.
10. **Honest limitations:** apps that defeated the agent, known weak fields, what we'd do with more time.
11. **Footer:** generated timestamp, prompt version, data version (v1 sha).

**Agent-friendly outputs** in `site/dist/`: `results.json`, `results.csv`, `patterns.json`, `score.json`,
`summary.md` (headlines + tables in markdown), `llms.txt` (what this page is + links to the files). Add
`<link rel="alternate" type="application/json" href="results.json">` in the HTML head.

Every number on the page comes from the JSON files — nothing typed by hand.

Test the page: open locally, check at 375px and 1440px widths, check filters, check no console errors,
check all evidence links are real URLs from the data.

---

## 11. Deployment

Default: **GitHub Pages** from `site/dist` (via a GitHub Action on push to `main`) or Vercel/Netlify (static,
root `site/dist`). Prepare configs; 🛑 HUMAN GATE: the human creates the public repo, pushes, and enables
Pages/connects Vercel (needs their accounts). Verify the live URL in an incognito window.

Optional runnable trigger: `.github/workflows/research-one.yml` with `workflow_dispatch` input `app`, running
`make research-one`. Only if a credential for CI is available (e.g. `ANTHROPIC_API_KEY` secret, or a Claude Code
token if the official docs allow it for this use). If not possible, the page shows the local command + captured log instead,
and says why.

---

## 12. README.md (short, must be enough to run it)

Sections: What this is (2 lines + live link) · Results at a glance (the headline sentences) · How it works (5
bullets + diagram link) · Requirements (Python 3.11, Claude Code logged in OR ANTHROPIC_API_KEY; optional
COMPOSIO_API_KEY; optional Playwright) · Quick start (`make setup`, `make research-one APP=Stripe`, `make all`) ·
Pipeline commands table · **Note on execution:** the agent runs on the maintainer's own Claude Code / Claude
subscription — there is no hosted "click to run" demo, since that would require sharing paid credentials; a
reviewer with their own Claude Code login or `ANTHROPIC_API_KEY` can rerun any command above, and
`data/holdout_examples.json` + `docs/holdout_run.log` show it already run successfully on apps outside the
given 100 · Where a human is involved · Verification method + accuracy numbers · Repo layout · Limitations ·
How AI tools were used (honest: Claude Code + agent-skills built most of the code; the candidate designed,
reviewed, labelled ground truth and made the calls).

---

## 13. Phases, timeline and gates (target: submit in ≤ 6 h)

| # | Phase | Target time | Done when |
|---|---|---|---|
| P0 | Read brief + skills, write `tasks/todo.md`, confirm `claude --help` flags, Composio docs check | 0:00–0:15 | todo exists; DECISIONS.md has backend choices |
| P1 | Scaffold repo, apps.csv (exactly 100 rows), schema, rules, tests | 0:15–0:40 | `make test` green; apps.csv row count = 100 |
| P2 | llm.py, fetch.py, prompts, research.py; run 5-app slice | 0:40–1:30 | 5 valid records with evidence → 🛑 human check |
| P2.5 | Holdout check: run on 2–3 apps NOT in apps.csv, unedited pipeline | 1:30–1:40 | holdout_examples.json + captured log saved |
| P3 | Run all 100 (resumable) + composio check → freeze v1 | 1:40–2:25 | 100 records (errors allowed, flagged); v1 committed + sha |
| P4 | sample.py → template; **human starts labelling in parallel** | 1:30 (parallel) | template exists → 🛑 human fills ground_truth.csv |
| P5 | verify.py loops A–E → v2 | 2:25–3:25 | results_v2.json, verify_log.json, per-loop counts |
| P6 | review queue + human overrides (Loop F) | 3:25–3:45 | 🛑 human resolved queue; HUMAN_LOG.md updated |
| P7 | score.py + patterns.py + headlines | 3:45–4:15 | score.json, patterns.json; 🛑 human approves headlines |
| P8 | site build + page testing | 4:15–5:15 | page passes checks in Section 10 |
| P9 | README, code review/simplify pass, security check (no secrets) | 5:15–5:40 | review notes addressed |
| P10 | Deploy + final acceptance checklist | 5:40–6:00 | 🛑 human deploys; live URL verified; submit |

If Pro usage limits hit during P3/P5: commit progress, work on P4/P8 (page with partial data) while waiting, then resume.
Never spend > 20 min on one app — mark `needs_human` and move on.

---

## 14. Final acceptance checklist (map to what Composio asked)

Findings
- [ ] 100 rows; every row has category, one-liner, auth, access, API surface, MCP, verdict, blocker, evidence
- [ ] Every non-unknown key field has ≥ 1 evidence URL; evidence-support rate shown
- [ ] Extra fields present (webhooks, sandbox, OpenAPI, rate limits, on_composio)

Patterns
- [ ] Headline at top, plain sentences, numbers match the data
- [ ] Answers: dominant auth · self-serve vs gated by category · most common blocker · easy wins · outreach list

Agent
- [ ] Explains what it does, tools used, Composio usage (or honest note why limited)
- [ ] Shows where a human was needed, with counts and examples

Proof
- [ ] Runnable command + captured log (and/or live trigger); repo public; README runs on a fresh clone
- [ ] Page states plainly that the agent runs on the candidate's own Claude subscription (not a live in-browser demo)
- [ ] Holdout results (2–3 apps outside the original 100) shown as evidence the pipeline generalises

Verification
- [ ] Human-labelled sample of 20, labelled blind
- [ ] v1 → v2 (→ v2+human) accuracy per field, with the reason for the change
- [ ] Misses listed honestly with causes; apps that defeated the agent named

Presentation
- [ ] Understandable in ~2 minutes without narration; works on phone; no console errors
- [ ] Agent-consumable: results.json, results.csv, summary.md, llms.txt linked
- [ ] Every number generated from data

Honesty and quality
- [ ] No invented URLs/quotes (spot-check 10 random evidence links by hand)
- [ ] No secrets in repo; `.env.example` present
- [ ] Candidate can explain every file (Claude: write a 1-page `docs/WALKTHROUGH.md` explaining the code in plain language to help the candidate prepare)