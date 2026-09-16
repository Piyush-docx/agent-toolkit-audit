"""All prompts, versioned in one place (brief section 5).

Bump PROMPT_VERSION on any wording change: it is recorded in run_stats.json and
printed in the page footer, so a result can always be traced to the prompt that
produced it.

Note (D3): the research prompt must NOT say "reply with JSON only" -- the CLI's
--json-schema already enforces structure, and asking for both double-encodes the
answer. Describe the fields in prose; let the schema do the shaping.
"""

from __future__ import annotations

PROMPT_VERSION = "v1.0"

RESEARCH = """You are researching whether **{name}** ({category}) could be built \
into a tool toolkit that AI agents can call today.

Start from this hint: {hint}

Research method, in order of preference:
1. The official developer/API documentation site.
2. The official pricing or plans page (to decide how someone actually gets credentials).
3. The company's official GitHub organisation.
4. The MCP registry or well-known community MCP lists (to check for an existing MCP server).
Third-party blogs are a last resort. If you use one, say so in the access_notes.

Rules you must follow:
- Use WebSearch and WebFetch. Every evidence quote must be copied VERBATIM from a \
page you actually fetched in this session. Do not paraphrase a quote.
- NEVER invent a URL, a quote, a number or a fact. If you cannot find something, \
say so using the "unknown"/"none_found" values and lower your confidence.
- Provide at least one evidence item for each of: auth_methods, access, api_type, \
existing_mcp, verdict. Each quote must be 40 words or fewer.
- Set needs_human to true, with a reason, if the docs are thin or contradictory, \
if the product identity is ambiguous, or if you had to guess anything.

Field guidance:
- one_liner: at most 15 words describing what the product does.
- auth_methods: every method the public API supports. primary_auth: the one a \
toolkit would realistically use.
- access: how a developer obtains working credentials.
  self_serve_free  = sign up and get API access on a free tier
  self_serve_trial = a time-limited trial gives API access
  paid_plan        = API access requires a paid plan
  admin_approval   = a workspace admin must enable or approve access
  partner_gated    = partnership, sales contact or an application is required
  no_public_api    = there is no public API at all
- api_type: rest, graphql, websocket, soap, sdk_only, cli_or_library, or none. \
Use cli_or_library for a local tool with no hosted API.
- api_breadth: broad (many resources with CRUD), moderate, narrow (a few \
endpoints), none, or unknown if you could not determine it.
- existing_mcp: official (published by the vendor), community, or none_found. \
Include mcp_url when you find one.
- verdict: your own judgement of buildability. A deterministic rule set may \
override it later; answer honestly anyway.
- confidence: your genuine confidence in this record, from 0 to 1.

Be accurate rather than complete. "unknown" is a correct and valuable answer."""


REPAIR = """The JSON you produced for **{name}** did not match the required schema.

Validation error:
{error}

Return the corrected record for the same app. Keep every value you already \
verified and only fix what the error describes. Do not invent new evidence."""


# Loop B: the judge sees ONLY the claim and the quote -- never the original
# reasoning. Fresh context is what makes this real doubt rather than a rubber stamp.
ENTAILMENT_JUDGE = """You are checking one factual claim against one quotation.

Claim: the field "{field}" for {name} has the value "{value}".
Quote from {url}:
\"\"\"{quote}\"\"\"

Does this quote, on its own, support that value?
- "yes"     the quote clearly supports the value
- "partial" the quote is related and consistent but does not establish the value
- "no"      the quote does not support it, or contradicts it

Judge only what the quote says. Do not use outside knowledge about {name}. \
Give a one-sentence reason."""


# Loop D: a deliberately different framing of the same question, so agreement
# means something. Asks for the mechanism first, then the label.
CROSS_CHECK = """For the API of **{name}** ({hint}), answer these narrowly:

1. What exactly does a developer send on an API request to authenticate? \
Describe the mechanism (header, token type, flow), then name it using one or \
more of: oauth2, api_key, basic, bearer_token, jwt, hmac_signature, other, none.
2. What must a developer do to obtain working API credentials? Then classify as \
one of: self_serve_free, self_serve_trial, paid_plan, admin_approval, \
partner_gated, no_public_api.
3. Does an MCP server exist for this product? Answer official, community, or \
none_found, and give the URL if one exists.

Use WebSearch and WebFetch on primary sources. Cite the URL you used for each \
answer. If you cannot determine one, say unknown rather than guessing."""


# Loop C: states what failed and demands a different source.
RERESEARCH = """Earlier research on **{name}** ({hint}) produced answers that \
could not be verified.

What failed:
{failures}

Re-research ONLY these fields: {fields}.

Find DIFFERENT primary sources than the ones listed above -- prefer the official \
API reference, the official pricing page, or the vendor's own GitHub. For each \
field give a fresh URL and a verbatim quote of 40 words or fewer from a page you \
actually fetched. If the answer genuinely cannot be established from primary \
sources, say unknown and set needs_human with the reason."""


HEADLINES = """Write {count} plain, factual sentences summarising these findings \
for a reviewer who has 30 seconds.

DATA (the only source you may use):
{patterns_json}

Rules:
- Every number you write must appear in the data above. Do not compute new \
percentages and do not round differently.
- No adjectives like "impressive" or "surprising". State what is true.
- Lead with the most decision-useful fact: how many apps are buildable today.
- Cover: dominant auth, self-serve vs gated, the most common blocker, and easy wins.
- One sentence per line, no bullet characters, no preamble."""
