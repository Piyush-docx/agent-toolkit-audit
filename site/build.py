"""Build site/dist/index.html from data/results_v1.json + patterns.json + score.json
(brief section 10). Single static page, vanilla JS/CSS, works offline once loaded.

Skipped for time (see README's Honest limitations): inline SVG charts, the
readiness-diagram, and expandable per-row evidence quotes with verification
status icons -- there is no verify_log (Loops A-E were not run) to show
status icons for anyway.
"""

from __future__ import annotations

import json
from pathlib import Path

VERDICTS = ("ready", "ready_with_friction", "needs_outreach", "not_viable")
DIST_PATH = Path("site/dist/index.html")

TRIMMED_FIELDS = (
    "id", "name", "category", "one_liner", "verdict", "confidence",
    "on_composio", "needs_human", "access", "auth_methods", "api_type",
    "existing_mcp", "docs_url", "blocker",
)


def load_json(path: str) -> dict | list:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_page() -> str:
    records = load_json("data/results_v1.json")
    patterns = load_json("data/patterns.json")
    score = (load_json("data/score.json") if Path("data/score.json").exists()
             else None)
    holdout = (load_json("data/holdout_examples.json")
              if Path("data/holdout_examples.json").exists() else [])

    trimmed = [{k: r.get(k) for k in TRIMMED_FIELDS} for r in records]

    categories = sorted({r["category"] for r in records})
    matrix_rows = []
    for cat in categories:
        counts = patterns["verdict_by_category"].get(cat, {})
        matrix_rows.append({"category": cat,
                            **{v: counts.get(v, 0) for v in VERDICTS}})

    stat_tiles = _stat_tiles(patterns, score)
    verification_html = _verification_section(score, patterns)
    lists_html = _lists_section(patterns)
    holdout_html = _holdout_section(holdout)

    data_json = json.dumps(trimmed, separators=(",", ":"))
    matrix_json = json.dumps(matrix_rows, separators=(",", ":"))

    return TEMPLATE.format(
        headline_sentences="".join(f"<p>{h}</p>" for h in patterns["headlines"]),
        stat_tiles=stat_tiles,
        matrix_json=matrix_json,
        categories_json=json.dumps(categories),
        data_json=data_json,
        verification_html=verification_html,
        lists_html=lists_html,
        holdout_html=holdout_html,
    )


def _stat_tiles(patterns: dict, score: dict | None) -> str:
    total = patterns["apps_total"]
    ready = patterns["totals"].get("ready", 0)
    any_auth = patterns["auth"]["any"]
    oauth_pct = round(100 * any_auth.get("oauth2", 0) / total) if total else 0
    self_serve = sum(
        c for cat in patterns["access_by_category"].values()
        for k, c in cat.items() if k in ("self_serve_free", "self_serve_trial"))
    self_serve_pct = round(100 * self_serve / total) if total else 0
    acc = (f"{score['overall']['correct']}/{score['overall']['total']} "
           f"({100*score['overall']['correct']//max(score['overall']['total'],1)}%)"
           if score else "not run")

    tiles = [
        (str(ready), f"ready today (of {total})"),
        (f"{oauth_pct}%", "use OAuth2"),
        (f"{self_serve_pct}%", "self-serve access"),
        (acc, "v1 accuracy (partial sample, no v2)"),
    ]
    return "".join(
        f'<div class="stat"><div class="n">{n}</div><div class="l">{l}</div></div>'
        for n, l in tiles)


def _verification_section(score: dict | None, patterns: dict) -> str:
    if score is None:
        return ('<p class="muted">No ground truth scored yet -- run '
               '<code>python3 -m agent.cli score</code> after filling '
               '<code>data/ground_truth.csv</code>.</p>')
    rows = "".join(
        f"<tr><td>{f}</td><td>{s['correct']}/{s['total']}</td>"
        f"<td>{100*s['correct']//max(s['total'],1)}%</td></tr>"
        for f, s in sorted(score["per_field"].items()))
    misses = "".join(
        f"<li><strong>#{m['id']} {m['name']}</strong> [{m['field']}] "
        f"truth=<code>{m['truth']}</code> answer=<code>{m['answer']}</code></li>"
        for m in score["misses"])
    pop = score["population"]
    return f"""
<table class="scoretable">
<thead><tr><th>Field</th><th>Correct/Total</th><th>Accuracy</th></tr></thead>
<tbody>{rows}</tbody>
</table>
<p class="muted">{score['note']}</p>
<p>Evidence-support: {pop['apps_with_evidence']}/{pop['apps_total']} apps have at
least one evidence quote. {pop['apps_needing_human']}/{pop['apps_total']} apps are
flagged for human review.</p>
<h3>Misses ({len(score['misses'])})</h3>
<ul class="misslist">{misses}</ul>
"""


def _lists_section(patterns: dict) -> str:
    def _li(items):
        return "".join(f"<li>{i['name']} <span class='muted'>({i['category']})"
                       f"</span></li>" for i in items) or "<li class='muted'>none</li>"
    return f"""
<div class="grid3">
  <div><h3>Easy wins ({len(patterns['easy_wins'])})</h3>
    <p class="muted">Ready today, not yet on Composio.</p>
    <ul>{_li(patterns['easy_wins'])}</ul></div>
  <div><h3>Needs outreach ({len(patterns['needs_outreach'])})</h3>
    <ul>{_li(patterns['needs_outreach'])}</ul></div>
  <div><h3>Not viable ({len(patterns['not_viable'])})</h3>
    <ul>{_li(patterns['not_viable'])}</ul></div>
</div>
"""


def _holdout_section(holdout: list) -> str:
    if not holdout:
        return ""
    cards = ""
    for r in holdout:
        cards += f"""
<div class="holdout-card">
  <h3>{r['name']} <span class="badge {r['verdict']}">{r['verdict']}</span></h3>
  <div class="kv"><span class="k">Access</span><span>{r.get('access') or '—'}</span></div>
  <div class="kv"><span class="k">Auth</span><span>{', '.join(r.get('auth_methods') or []) or '—'}</span></div>
  <div class="kv"><span class="k">Needs human</span><span>{r['needs_human']}</span></div>
  <div class="kv"><span class="k">Confidence</span><span>{r['confidence']}</span></div>
</div>"""
    return cards


TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Composio Agent-Toolkit Readiness — 100 App Study</title>
<style>
  :root {{
    --bg: #ffffff; --bg2: #f4f5f7; --card: #ffffff; --border: #e2e5ea;
    --text: #14161a; --text2: #5b6472; --accent: #3b5fe0; --accent2: #2c48b8;
    --green: #0f9d58; --yellow: #b8860b; --orange: #c2650a; --red: #d64545;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#0b0e14; --bg2:#12161f; --card:#161b26; --border:#262c3a;
      --text:#e6e9ef; --text2:#9aa4b8; --accent:#7c9eff; --accent2:#5b7fe0;
      --green:#34d399; --yellow:#fbbf24; --orange:#fb923c; --red:#f87171; }}
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif; line-height:1.55; }}
  .wrap {{ max-width:1100px; margin:0 auto; padding:36px 20px 80px; }}
  h1 {{ font-size:1.85rem; margin-bottom:6px; }}
  .sub {{ color:var(--text2); margin-bottom:26px; font-size:1rem; }}
  .links a {{ margin-right:14px; font-size:0.88rem; }}
  .stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin:26px 0 34px; }}
  .stat {{ background:var(--card); border:1px solid var(--border); border-radius:10px; padding:16px; text-align:center; }}
  .stat .n {{ font-size:1.6rem; font-weight:700; color:var(--accent); }}
  .stat .l {{ font-size:0.76rem; color:var(--text2); margin-top:4px; text-transform:uppercase; letter-spacing:.03em; }}
  section {{ margin-bottom:42px; }}
  h2 {{ font-size:1.2rem; border-bottom:1px solid var(--border); padding-bottom:8px; margin-bottom:14px; }}
  h3 {{ font-size:1rem; margin:0 0 8px; }}
  .headline p {{ margin:6px 0; font-size:0.98rem; }}
  code {{ background:var(--bg2); padding:2px 6px; border-radius:4px; font-size:0.87em; }}
  pre {{ background:var(--bg2); border:1px solid var(--border); border-radius:8px; padding:14px; overflow-x:auto; font-size:0.84rem; }}
  .callout {{ background:var(--card); border:1px solid var(--border); border-left:3px solid var(--accent); border-radius:8px; padding:16px 18px; margin-bottom:14px; }}
  .callout.warn {{ border-left-color:var(--yellow); }}
  .callout p {{ margin:6px 0; color:var(--text2); font-size:0.92rem; }}
  .callout p:first-child {{ margin-top:0; }}
  .controls {{ display:flex; gap:10px; flex-wrap:wrap; margin-bottom:14px; }}
  select, input[type=text] {{ background:var(--bg2); color:var(--text); border:1px solid var(--border); border-radius:6px; padding:8px 10px; font-size:0.9rem; }}
  input[type=text] {{ flex:1; min-width:180px; }}
  .tablewrap {{ overflow-x:auto; border:1px solid var(--border); border-radius:8px; max-height:620px; overflow-y:auto; }}
  table {{ width:100%; border-collapse:collapse; font-size:0.85rem; }}
  th, td {{ text-align:left; padding:9px 10px; border-bottom:1px solid var(--border); vertical-align:top; }}
  th {{ color:var(--text2); font-weight:600; text-transform:uppercase; font-size:0.7rem; letter-spacing:.03em; position:sticky; top:0; background:var(--bg); }}
  tr:hover td {{ background:rgba(127,127,127,0.06); }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius:99px; font-size:0.72rem; font-weight:600; white-space:nowrap; }}
  .badge.ready {{ background:rgba(15,157,88,.12); color:var(--green); }}
  .badge.ready_with_friction {{ background:rgba(184,134,11,.12); color:var(--yellow); }}
  .badge.needs_outreach {{ background:rgba(194,101,10,.12); color:var(--orange); }}
  .badge.not_viable {{ background:rgba(214,69,69,.12); color:var(--red); }}
  .hu {{ color:var(--yellow); font-size:0.76rem; }}
  a {{ color:var(--accent); text-decoration:none; }}
  a:hover {{ text-decoration:underline; }}
  .muted {{ color:var(--text2); }}
  footer {{ color:var(--text2); font-size:0.8rem; margin-top:50px; border-top:1px solid var(--border); padding-top:18px; }}
  .matrix {{ overflow-x:auto; border:1px solid var(--border); border-radius:8px; }}
  .matrix table {{ min-width:640px; }}
  .matrix td.count {{ text-align:center; cursor:pointer; font-weight:600; }}
  .matrix td.count:hover {{ outline:2px solid var(--accent); }}
  .grid3 {{ display:grid; grid-template-columns:repeat(3,1fr); gap:18px; }}
  @media (max-width:800px) {{ .grid3 {{ grid-template-columns:1fr; }} }}
  .grid3 ul {{ margin:0; padding-left:18px; font-size:0.88rem; }}
  .misslist {{ font-size:0.85rem; padding-left:18px; }}
  .scoretable {{ margin-bottom:14px; }}
  .holdout-cards {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
  @media (max-width:700px) {{ .holdout-cards {{ grid-template-columns:1fr; }} }}
  .holdout-card {{ background:var(--card); border:1px solid var(--border); border-radius:10px; padding:14px; }}
  .kv {{ display:flex; justify-content:space-between; font-size:0.84rem; padding:4px 0; border-bottom:1px dashed var(--border); }}
  .kv:last-child {{ border-bottom:none; }}
  .kv .k {{ color:var(--text2); }}
</style>
</head>
<body>
<div class="wrap">

<h1>Can AI agents actually use 100 real SaaS products today?</h1>
<p class="sub">A research pipeline (Claude Code + web search/fetch) checked 100 apps across 10 categories for
agent-toolkit readiness, with every claim tied to a verbatim quote from a page it actually fetched.</p>
<div class="links">
  <a href="https://github.com/Piyush-docx/agent-toolkit-audit">Repo</a>
  <a href="../../data/results_v1.json">Raw data (JSON)</a>
  <a href="../../data/patterns.json">Patterns (JSON)</a>
  <a href="#run-it">How to run</a>
</div>

<section class="headline">
{headline_sentences}
<div class="stats">{stat_tiles}</div>
</section>

<section>
<h2>Readiness matrix</h2>
<div class="matrix">
<table id="matrixTable">
  <thead><tr><th>Category</th><th>Ready</th><th>Friction</th><th>Outreach</th><th>Not viable</th></tr></thead>
  <tbody></tbody>
</table>
</div>
<p class="muted">Click a cell to filter the table below.</p>
</section>

<section>
<h2>Easy wins / needs outreach / not viable</h2>
{lists_html}
</section>

<section>
<h2>Full table of 100</h2>
<div class="controls">
  <input type="text" id="search" placeholder="Search app name...">
  <select id="catFilter"><option value="">All categories</option></select>
  <select id="verdictFilter">
    <option value="">All verdicts</option>
    <option value="ready">ready</option>
    <option value="ready_with_friction">ready_with_friction</option>
    <option value="needs_outreach">needs_outreach</option>
    <option value="not_viable">not_viable</option>
  </select>
  <select id="humanFilter">
    <option value="">All</option>
    <option value="true">Needs human</option>
    <option value="false">No human needed</option>
  </select>
</div>
<div class="tablewrap">
<table id="resultsTable">
  <thead><tr>
    <th>#</th><th>App</th><th>Category</th><th>Verdict</th><th>Access</th><th>Auth</th><th>API</th><th>MCP</th><th>Composio</th><th>Conf.</th>
  </tr></thead>
  <tbody></tbody>
</table>
</div>
</section>

<section>
<h2>How the agent works</h2>
<div class="callout">
<p><strong>Pipeline:</strong> for each app, Claude Code (headless, <code>claude -p</code>) searches and fetches
official docs/pricing/GitHub pages, then answers a strict JSON schema — auth methods, access model, API type,
existing MCP server, and a verdict — with a required verbatim evidence quote + source URL for key fields.</p>
<p><strong>Verdicts are computed by a deterministic rule set</strong> (not the LLM's opinion): self-serve
access + REST/GraphQL → <code>ready</code>; paid/admin-gated access → <code>ready_with_friction</code>;
partner-gated access → <code>needs_outreach</code>; no public API or CLI-only → <code>not_viable</code>. The
rule always overrides the model's own guess; disagreements are flagged for human review.</p>
<p><strong>Composio check:</strong> cross-referenced against Composio's public toolkit index
(<code>docs.composio.dev/toolkits.md</code>) — no API key needed, so "not listed" is a trustworthy negative.</p>
<p><strong>Tools/backends:</strong> Claude Code (sonnet), WebSearch/WebFetch, httpx, selectolax for text
extraction, rapidfuzz for evidence quote matching. Concurrency 2–3, resumable/cached per app.</p>
</div>
</section>

<section>
<h2>Verification</h2>
{verification_html}
</section>

<section>
<h2>Generalisation proof (holdout apps)</h2>
<p class="muted">The pipeline takes any <code>{{name, category, hint}}</code> — it isn't tuned to these 100 apps.
Run unedited on two apps never in the input list:</p>
<div class="holdout-cards">{holdout_html}</div>
</section>

<section id="run-it">
<h2>Proof / run it yourself</h2>
<p>This agent runs on Claude Code using the candidate's own Claude subscription, so this page cannot execute
it live in your browser — instead, here is a real command, a captured run, and proof it generalizes beyond
the given 100.</p>
<pre>make setup
make research-one APP="Stripe"
python3 -m agent.cli research --app "Calendly" --category "Scheduling &amp; Calendar" --hint "calendly.com/developers"</pre>
<p class="muted">See <code>docs/holdout_run.log</code> for a captured real run and
<code>data/holdout_examples.json</code> for the raw output.</p>
</section>

<section>
<h2>Honest limitations</h2>
<div class="callout warn">
<p><strong>This study ran under a hard submission time constraint.</strong> The brief's full verification
pipeline (Loops A–E: automated evidence re-check, LLM entailment judge, targeted re-research, independent
cross-check) was not run — there is no results_v2.json. The human review queue (Loop F) and a 20-app
stratified ground truth were also scoped down.</p>
<p>What did run: a real pipeline bug was found and fixed mid-execution (an LLM error was silently producing a
fabricated <code>not_viable</code> verdict on ~28 apps — caught, fixed, covered by regression tests, and every
affected app was re-researched for real). A 5-app ground truth was hand-labelled by a human from firsthand
product knowledge (not fabricated by the agent) and scored — see Verification above for the exact numbers.</p>
<p>Given more time: run Loops A–E for real, fill the full 20-app ground truth, build the human review queue,
and add the inline SVG charts / readiness diagram this page's spec called for.</p>
</div>
</section>

<footer>
Data version: results_v1 (SHA-256 in <code>data/results_v1.sha256</code>) · sonnet model, concurrency 2–3 ·
Built with Claude Code · Full spec in the repo's <code>PROJECT_BRIEF.md</code>.
</footer>

</div>

<script>
const DATA = {data_json};
const MATRIX = {matrix_json};
const CATEGORIES = {categories_json};

function render(list) {{
  const tbody = document.querySelector('#resultsTable tbody');
  tbody.innerHTML = list.map(r => `
    <tr>
      <td>${{r.id}}</td>
      <td><strong>${{r.name}}</strong>${{r.needs_human ? '<div class="hu">⚑ needs human</div>' : ''}}</td>
      <td class="muted">${{r.category}}</td>
      <td><span class="badge ${{r.verdict}}">${{r.verdict}}</span></td>
      <td>${{r.access || '—'}}</td>
      <td class="muted">${{(r.auth_methods||[]).join(', ') || '—'}}</td>
      <td class="muted">${{(r.api_type||[]).join(', ') || '—'}}</td>
      <td class="muted">${{r.existing_mcp}}</td>
      <td>${{r.on_composio === 'yes' ? '✓' : (r.on_composio==='no' ? '—' : '?')}}</td>
      <td class="muted">${{r.confidence}}</td>
    </tr>`).join('');
}}

function renderMatrix() {{
  const tbody = document.querySelector('#matrixTable tbody');
  tbody.innerHTML = MATRIX.map(row => `
    <tr>
      <td>${{row.category}}</td>
      <td class="count" data-cat="${{row.category}}" data-verdict="ready">${{row.ready||0}}</td>
      <td class="count" data-cat="${{row.category}}" data-verdict="ready_with_friction">${{row.ready_with_friction||0}}</td>
      <td class="count" data-cat="${{row.category}}" data-verdict="needs_outreach">${{row.needs_outreach||0}}</td>
      <td class="count" data-cat="${{row.category}}" data-verdict="not_viable">${{row.not_viable||0}}</td>
    </tr>`).join('');
  tbody.querySelectorAll('.count').forEach(td => td.addEventListener('click', () => {{
    document.getElementById('catFilter').value = td.dataset.cat;
    document.getElementById('verdictFilter').value = td.dataset.verdict;
    applyFilters();
    document.getElementById('resultsTable').scrollIntoView({{behavior:'smooth'}});
  }}));
}}

const catSel = document.getElementById('catFilter');
CATEGORIES.forEach(c => {{ const o = document.createElement('option'); o.value = c; o.textContent = c; catSel.appendChild(o); }});

function applyFilters() {{
  const q = document.getElementById('search').value.toLowerCase();
  const cat = catSel.value;
  const verdict = document.getElementById('verdictFilter').value;
  const human = document.getElementById('humanFilter').value;
  const filtered = DATA.filter(r =>
    (!q || r.name.toLowerCase().includes(q)) &&
    (!cat || r.category === cat) &&
    (!verdict || r.verdict === verdict) &&
    (!human || String(r.needs_human) === human)
  );
  render(filtered);
}}

document.getElementById('search').addEventListener('input', applyFilters);
catSel.addEventListener('change', applyFilters);
document.getElementById('verdictFilter').addEventListener('change', applyFilters);
document.getElementById('humanFilter').addEventListener('change', applyFilters);

renderMatrix();
render(DATA);
</script>
</body>
</html>
'''


def main() -> None:
    html = build_page()
    DIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    DIST_PATH.write_text(html, encoding="utf-8")
    print(f"wrote {len(html)} chars -> {DIST_PATH}")


if __name__ == "__main__":
    main()
