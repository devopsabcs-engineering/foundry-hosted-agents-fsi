<!-- markdownlint-disable-file -->
# Implementation Details: Bring foundry-hosted-agents-fsi to parity with sibling foundry-hosted-agents

## Context Reference

Sources:
* .copilot-tracking/research/2026-09-14/foundry-hosted-agents-parity-research.md
* .copilot-tracking/research/subagents/2026-09-14/web-chat-app-research.md
* .copilot-tracking/research/subagents/2026-09-14/wiki-and-pages-research.md
* .copilot-tracking/plans/logs/2026-09-14/hosted-agents-sibling-parity-log.md

## Implementation Phase 1: Fix GitHub Pages configuration and add bilingual nav include

<!-- parallelizable: true -->

### Step 1.1: Switch the repo's GitHub Pages source to `legacy` + `/docs`

Local Pages is already enabled but misconfigured (`build_type: workflow`, `source.path: "/"`, `status: null`). Change it to match the sibling's working configuration so it builds immediately from the existing Jekyll content in `docs/`.

Files:
* None (this is a GitHub repo Settings API call, not a file change)

Commands (lead with the JSON-body form, since the flat `-f source[branch]=...` shape is unconfirmed against this API):
* `echo '{"build_type":"legacy","source":{"branch":"main","path":"/docs"}}' | gh api -X PUT repos/devopsabcs-engineering/foundry-hosted-agents-fsi/pages --input -`
* Verify: `gh api repos/devopsabcs-engineering/foundry-hosted-agents-fsi/pages --jq '{build_type,source,status}'`
* If the JSON-body PUT is rejected, fall back to: `gh api -X PUT repos/devopsabcs-engineering/foundry-hosted-agents-fsi/pages -f "build_type=legacy" -f "source[branch]=main" -f "source[path]=/docs"`

Note: this mutates live GitHub repo settings (not tracked in git history). It is reversible (Pages source can be switched back), but flag it to the user before running, consistent with this session's general caution around infrastructure-affecting changes.

Discrepancy references:
* None (this step directly implements the Selected implementation path)

Success criteria:
* `gh api repos/.../pages` reports `build_type: legacy`, `source: {branch: main, path: /docs}`.
* A subsequent `gh api repos/.../actions/workflows --jq '.workflows[].name'` includes `pages-build-deployment` (may take a few minutes to register after the first build).

Context references:
* .copilot-tracking/research/subagents/2026-09-14/wiki-and-pages-research.md (Lines 669-908, "GitHub Pages / docs folder comparison" and "Exact gap list for the Planner")

Dependencies:
* `gh` CLI authenticated with repo admin scope (`repo` + Pages settings permission).

### Step 1.2: Add the bilingual nav-hiding Jekyll include

Files:
* docs/_includes/head_custom.html - create; copy verbatim from sibling (generic just-the-docs Liquid/CSS/JS, hides the other language's left-nav links per page)

Content (verbatim from sibling, confirmed non-domain-specific):
```html
{%- assign is_fr_page = false -%}
{%- if page.lang == 'fr' or page.url contains '/fr/' -%}
  {%- assign is_fr_page = true -%}
{%- endif -%}
<style>
  /* Left nav is built once for the whole site; hide the other language's links per page. */
  {%- if is_fr_page %}
  #site-nav .nav-list-item:has(> a.nav-list-link[href]:not([href="/fr"]):not([href^="/fr/"])) { display: none; }
  {%- else %}
  #site-nav .nav-list-item:has(> a.nav-list-link:is([href="/fr"], [href^="/fr/"])) { display: none; }
  {%- endif %}
  .nav-list-item.lang-hidden { display: none !important; }
</style>
<script>
  // Fallback for browsers without CSS :has() support.
  document.addEventListener('DOMContentLoaded', function () {
    var isFrPage = {{ is_fr_page }};
    document.querySelectorAll('#site-nav .nav-list-item').forEach(function (item) {
      var link = item.querySelector('a.nav-list-link');
      if (!link || !link.hasAttribute('href')) return;
      var href = link.getAttribute('href') || '';
      var isFrLink = href === '/fr' || href.indexOf('/fr/') === 0;
      if (isFrPage !== isFrLink) item.classList.add('lang-hidden');
    });
  });
</script>
```

Discrepancy references:
* None

Success criteria:
* File exists at `docs/_includes/head_custom.html` with the content above.

Context references:
* .copilot-tracking/research/subagents/2026-09-14/wiki-and-pages-research.md (Lines 669-908, `docs/_includes/head_custom.html` full content)

Dependencies:
* None

### Step 1.3: Update `docs/_config.yml` url placeholder (only after Step 1.1 has built)

Files:
* docs/_config.yml - modify: replace the `url: ""  # TODO: set once GitHub Pages is enabled for this repository` line with the real assigned `html_url` from `gh api repos/.../pages --jq '.html_url'`

Discrepancy references:
* None

Success criteria:
* `url:` field in `docs/_config.yml` matches the live `*.pages.github.io` URL (trailing slash stripped, matching the sibling's convention of no trailing slash).

Context references:
* .copilot-tracking/research/subagents/2026-09-14/wiki-and-pages-research.md (Lines 669-908, local `docs/_config.yml` full content)

Dependencies:
* Step 1.1 completed and Pages has built at least once (`status: built`).

## Implementation Phase 2: Port `apps/web-chat` application, adapted for Desjardins

<!-- parallelizable: true -->

### Step 2.1: Create backend files (verbatim port)

Files:
* apps/web-chat/requirements.txt - create; verbatim: `fastapi==0.135.1`, `uvicorn==0.41.0`, `httpx==0.28.1`, `httpx-sse==0.4.3`, `PyJWT[crypto]==2.12.1`, `azure-identity==1.25.3`, `aiohttp>=3.13.3,<4`
* apps/web-chat/app.py - create; verbatim port of sibling's `app.py` (FastAPI factory `create_app`, `Settings.from_env()`, `SessionStore`, `FoundryClient`, SSE streaming, idempotency-key replay, security-header middleware) -- no domain-specific strings in this file, safe to port unchanged
* apps/web-chat/auth.py - create; verbatim port of sibling's `auth.py` (`PilotAuth`/`Identity`, RS256 JWT verification against Entra, `Chat.Access` scope + pilot-group-membership checks) -- fully generic, no domain strings
* apps/web-chat/Dockerfile - create; verbatim port (multi-stage: Node 22 build+test frontend, Python 3.13-slim backend with build-time `azure-identity` smoke import, non-root UID 10001, port 8000)
* apps/web-chat/.dockerignore - create; verbatim deny-all-then-allowlist port

Discrepancy references:
* None (directly implements Selected path)

Success criteria:
* All 5 files exist with content matching the research doc's captured sources exactly (only reference: file paths / any local import paths, no content edits needed).
* `python -m py_compile apps/web-chat/app.py apps/web-chat/auth.py` succeeds (syntax check).

Context references:
* .copilot-tracking/research/subagents/2026-09-14/web-chat-app-research.md (Lines 38-434, full `requirements.txt`, `app.py`, `auth.py`, `Dockerfile`, `.dockerignore` contents)

Dependencies:
* None

### Step 2.2: Create backend tests (verbatim port)

Files:
* apps/web-chat/tests/test_app.py - create; verbatim port (uses `TestClient`, `FakeAgent`, `TestAuth` test doubles -- no domain strings beyond generic "Assessment complete." style fixture text, acceptable as-is since it's test-only fixture data)
* apps/web-chat/tests/test_auth.py - create; verbatim port (full content confirmed captured in web-chat-app-research.md, no re-fetch needed)

Discrepancy references:
* None

Success criteria:
* `python -m pytest apps/web-chat/tests -q` passes once `requirements.txt` (Step 2.1) is installed in the active environment.

Context references:
* .copilot-tracking/research/subagents/2026-09-14/web-chat-app-research.md (Lines ~850-1135, `test_app.py` and `test_auth.py` full contents, both confirmed complete -- no re-fetch needed)

Dependencies:
* Step 2.1 (backend source files must exist for tests to import `app`/`auth`)

### Step 2.3: Create frontend scaffolding and generic modules (verbatim port)

Files:
* apps/web-chat/frontend/vite.config.js - create; verbatim (React plugin, dev proxy `/api` -> `http://127.0.0.1:8000`)
* apps/web-chat/frontend/.gitignore - create; verbatim (`node_modules/`, `dist/`)
* apps/web-chat/frontend/src/request.js - create; verbatim (`messageRequest` idempotency-key helper)
* apps/web-chat/frontend/src/stream.js - create; verbatim (`consumeResponse` SSE parser using `eventsource-parser`)
* apps/web-chat/frontend/src/style.css - create; verbatim (green/red design-token theme; not domain-specific beyond color choice, acceptable to keep or restyle later as a follow-on, not required for parity)
* apps/web-chat/frontend/tests/request.test.js - create; verbatim
* apps/web-chat/frontend/tests/stream.test.js - create; verbatim
* apps/web-chat/frontend/tests/samples.test.js - create; port structure, update any fixture data to match the rewritten `samples.js` from Step 2.4

Discrepancy references:
* None

Success criteria:
* Files exist matching sibling content (style.css theme retained; content is not domain-specific enough to require changes for parity).
* `apps/web-chat/frontend/package-lock.json` is generated/updated (via `npm install`) once `package.json`'s `name` field changes in Step 2.4, so `npm ci` (used by `Dockerfile` and `web-chat-build.yml`) has a lockfile in sync with the renamed package.

Context references:
* .copilot-tracking/research/subagents/2026-09-14/web-chat-app-research.md (Lines 434-1000, `vite.config.js`, `.gitignore`, `request.js`, `stream.js`, `style.css` full contents)

Dependencies:
* None

### Step 2.4: Rewrite domain-specific frontend files for Desjardins

Files:
* apps/web-chat/frontend/package.json - create; port sibling structure, change `name` field from `foundry-threat-assessment-web-chat` to `foundry-quote-preparation-web-chat` (dependencies list unchanged: `@azure/msal-browser`, `@fontsource-variable/dm-sans`, `@fontsource-variable/newsreader`, `@vitejs/plugin-react`, `eventsource-parser`, `lucide-react`, `react`, `react-dom`, `react-markdown`, `remark-gfm`, `vite`)
* apps/web-chat/frontend/index.html - create; change `<title>` from "Threat Assessment | Foundry Pilot" to "Quote Preparation | Foundry Pilot" and update `theme-color` if desired to match the repo's existing branding (check `assets/` for an established color, else keep `#184c40`)
* apps/web-chat/frontend/src/main.jsx - create; port structure/logic verbatim (auth flow, streaming, session list UI, composer) but replace domain copy: `"AIR CANADA / SECURITY OPERATIONS"` -> `"DESJARDINS / QUOTE PREPARATION"` (or equivalent), `"Threat assessment"` -> `"Quote preparation"`, `"ASSESSMENT WORKSPACE"` brand sub-label -> `"QUOTE WORKSPACE"`, `"A new assessment."` -> `"A new quote."`, `"Security starts with access."` -> an access-gated equivalent for insurance quoting, `"ASSESSMENT AGENT"` message label -> `"QUOTE AGENT"`, `"Assessment in progress"` -> `"Preparing quote"`, placeholder text `"Describe the incident or ask a follow-up..."` -> `"Describe the quote request or ask a follow-up..."`, disclaimer text adjusted to reference synthetic insurance data, and swap the `ShieldCheck` icon import/usage for an insurance-appropriate `lucide-react` icon (e.g. `FileText` or `ClipboardList`)
* apps/web-chat/frontend/src/samples.js - create; replace the 3 threat-assessment sample queries with 3 quote-preparation sample queries derived from this repo's existing `data/synthetic/fixtures/case-syn-*.json` fixtures (read 2-3 fixture files to build realistic prompts; keep the same `{id, title, prompt}` shape, drop the unused `tools` field or keep it empty for structural parity)

Discrepancy references:
* None (directly implements Selected path's domain-adaptation requirement)

Success criteria:
* `node --test apps/web-chat/frontend/tests/*.test.js` passes.
* `npm run build` succeeds from `apps/web-chat/frontend/` and produces `dist/`.
* No remaining "Air Canada", "Threat Assessment", or "Security Operations" strings in any ported file (`grep -ri "air canada\|threat assessment\|security operations" apps/web-chat/` returns nothing).

Context references:
* .copilot-tracking/research/subagents/2026-09-14/web-chat-app-research.md (Lines 434-960, `package.json`, `index.html`, `main.jsx`, `samples.js` full contents and the "Notable domain-specific... behaviors" callouts)
* data/synthetic/fixtures/ - source of realistic sample-query content (inspect during implementation)

Dependencies:
* Step 2.3 (shared frontend modules must exist first)

## Implementation Phase 3: Port supporting scripts, infra template, and the build workflow

<!-- parallelizable: false -->

### Step 3.1: Port generic scripts verbatim

Files:
* scripts/validate-agent-response.jq - create; verbatim (generic Responses-protocol SSE validator)
* scripts/test-agent-response.sh - create; verbatim (unit test for the jq validator)
* scripts/record-production-version.sh - create; verbatim (already parameterized by agent-name argument)
* scripts/test-production-version.sh - create; verbatim, but update the hardcoded test literal `threat-assessment-agent` / env key `AGENT_THREAT_ASSESSMENT_AGENT_NAME` to `quote-preparation-agent` / `AGENT_QUOTE_PREPARATION_AGENT_NAME` to match this repo's actual agent name
* scripts/capture-release-evidence.ps1 - create; verbatim (headless-Edge screenshot capture; the 4 anchor IDs `pipeline`/`evaluations`/`tools`/`production` are generic and only matter once/if `build-release-evidence.js` is rewritten per WI-03 -- not blocking for this phase)

Discrepancy references:
* Relates to DR-03 (build-release-evidence.js deferred; this script is ported anyway since it's generic and low-cost, ready for when WI-03 is picked up)

Success criteria:
* `bash scripts/test-agent-response.sh` passes.
* `bash scripts/test-production-version.sh` passes (after the literal rename).
* `pwsh -File scripts/capture-release-evidence.ps1 -WhatIf` or equivalent dry-run does not error on syntax (`pwsh -NoProfile -Command "Get-Command -Syntax (Get-Content scripts/capture-release-evidence.ps1 -Raw)"` is not valid; instead use `pwsh -NoProfile -Command "[void][System.Management.Automation.PSParser]::Tokenize((Get-Content scripts/capture-release-evidence.ps1 -Raw), [ref]$null)"` or simply `pwsh -NoProfile -File scripts/capture-release-evidence.ps1 -ErrorAction Stop -WhatIf` if the script supports `-WhatIf`; at minimum confirm no parse errors via `Get-Command -Syntax` is unavailable for scripts, so use: `pwsh -NoProfile -Command "$null = [scriptblock]::Create((Get-Content -Raw scripts/capture-release-evidence.ps1))"` to validate parse-ability without executing.

Context references:
* .copilot-tracking/research/subagents/2026-09-14/web-chat-app-research.md (Lines 1949-2210, full contents of `validate-agent-response.jq`, `test-agent-response.sh`, `record-production-version.sh`, `test-production-version.sh`, `capture-release-evidence.ps1`)

Dependencies:
* None

### Step 3.2: Adapt `setup-web-chat-identity.ps1` and rewrite `deployment_summary.py`

Files:
* scripts/setup-web-chat-identity.ps1 - create; port structure verbatim, replace sibling-specific default parameter values (tenant/client/pilot-group display names, any hardcoded sibling app-registration display name) with Desjardins-neutral placeholders/parameters that must be supplied by the operator at run time (do NOT invent real Entra IDs)
* scripts/deployment_summary.py - create; **rewrite**, not port verbatim -- replace all hardcoded subscription ID, resource group name, ACR name, container app name, and MCP-server hostname literals with values sourced from environment variables or `azd env get-values` (matching the parameterization pattern already used elsewhere in this repo's scripts), and rename "Defender"/"anomaly" MCP references to this repo's actual `application-server`/`rulebook-server` MCP naming

Discrepancy references:
* Addresses DD-01 (no real Azure values invented; script reads from env/azd at run time instead)

Success criteria:
* `python -m py_compile scripts/deployment_summary.py` succeeds.
* `grep -ri "air canada\|defender\|acraircanadapoc" scripts/deployment_summary.py scripts/setup-web-chat-identity.ps1` returns nothing.

Context references:
* .copilot-tracking/research/subagents/2026-09-14/web-chat-app-research.md (Lines 1139-1320, full `setup-web-chat-identity.ps1` and `deployment_summary.py` contents, and the "Summary for Planner" rewrite guidance)

Dependencies:
* None

### Step 3.3: Verify and port `ci_results.py`

Files:
* scripts/ci_results.py - create; port near-verbatim (generic multi-workflow JUnit evidence aggregator that already recognizes `backend.xml`/`frontend.xml` as "Web chat backend"/"Web chat frontend" labels)

Before porting, confirm compatibility:
* Read local `eval/evaluation_gate.py` and verify it exposes a `METRICS` list and `validate_results(...)` callable with a shape compatible with what `ci_results.py` imports (`from eval.evaluation_gate import METRICS, validate_results`). If the local module's shape differs, adapt only the import/usage lines in `ci_results.py` (not the local `evaluation_gate.py`, which is out of scope for this plan).

Discrepancy references:
* None

Success criteria:
* `python -m py_compile scripts/ci_results.py` succeeds.
* `python scripts/ci_results.py --junit web-chat-evidence` runs without import errors against a directory containing sample JUnit XML (can smoke-test with an empty/minimal fixture directory during validation).

Context references:
* .copilot-tracking/research/subagents/2026-09-14/web-chat-app-research.md (Lines 1320-1919, full `ci_results.py` contents)
* eval/evaluation_gate.py (local, inspect during implementation for `METRICS`/`validate_results` shape)

Dependencies:
* Step 2.2 (test evidence file names it aggregates come from the ported test suite)

### Step 3.4: Port `infra/web-chat.bicep`, parameterized for local naming conventions

Files:
* infra/web-chat.bicep - create; port structure from sibling, with these parameter default changes:
  * `appName` default: `'foundry-quote-chat-staging'` (was `'foundry-threat-chat-staging'`)
  * `environmentName` default: keep as a required-with-sensible-default pattern matching local `mcp-container-apps.bicep`'s `${namePrefix}-mcp-env` (e.g. default `'mcp-staging-mcp-env'` for the staging azd environment, consistent with `infra/main.bicep`'s `effectiveMcpNamePrefix` logic)
  * `acrName` - remove the hardcoded sibling default (`'acraircanadapoc001'`); make it a required parameter (no default) or source it the same way `mcp-container-apps.bicep` does (env-var-driven `MCP_ACR_NAME` via the calling `main.bicep`/deployment command), matching this repo's existing convention
  * `tenantId` / `clientId` / `pilotGroupId` - remove hardcoded sibling GUID defaults; make these required parameters with no default (operator must supply real Desjardins-tenant values at deploy time)
  * `foundryAccountName` default: `'aif-desjardins-quote-preparation-staging'` (matches local `infra/main.bicep`'s `accountName = 'aif-${environmentName}'` pattern)
  * `foundryProjectName` default: `'proj-desjardins-quote-preparation-staging'` (matches local `infra/main.bicep`'s `projectName = 'proj-${environmentName}'` pattern)
  * Container `env` block's `AGENT_ENDPOINT` value: update the agent-name path segment from `threat-assessment-agent` to `quote-preparation-agent`
  * Container name / tags / role-assignment logic: unchanged (generic Azure Container Apps + AcrPull + custom Foundry-project-role pattern)

Discrepancy references:
* Addresses DD-01 (bicep file is authored/parameterized but this plan does not run `az deployment group create` against it)

Success criteria:
* `az bicep build --file infra/web-chat.bicep` (or the `mcp_azure_bicep_m_build_bicep` tool) succeeds with no errors.
* No hardcoded sibling subscription/tenant/client/ACR/GUID literals remain (`grep -E "acraircanadapoc001|aa93b9d9-037d-4f08-a26d-783cff0e2369|9cfb9dc7-f433-47f6-826b-14bc90a817bc|201b962a-8619-401e-a1f0-733bca2cd7b2" infra/web-chat.bicep` returns nothing).

Context references:
* .copilot-tracking/research/subagents/2026-09-14/web-chat-app-research.md (Lines 2296-2410, full `infra/web-chat.bicep` contents)
* infra/modules/mcp-container-apps.bicep (local, Lines 28-90 for `namePrefix`/`environmentName`/`acrName` conventions to mirror)
* infra/main.bicep (local, Lines 14-72 for `accountName`/`projectName`/`environmentName` conventions to mirror)

Dependencies:
* None

### Step 3.5: Port `.github/workflows/web-chat-build.yml`

Files:
* .github/workflows/web-chat-build.yml - create; port sibling structure verbatim (trigger paths already generically reference `apps/web-chat/**`, `.github/workflows/web-chat-build.yml`, `scripts/deployment_summary.py`; Node 22 + Python 3.13 setup; backend pytest with `PYTHONPATH=apps/web-chat`; frontend `npm ci`/`npm install` + `node --test` + `npm run build`; artifact uploads; summary step calling `scripts/ci_results.py` then `scripts/deployment_summary.py`) -- no content changes needed since none of the YAML itself contains sibling-domain strings

Discrepancy references:
* None

Success criteria:
* `python -c "import yaml, sys; yaml.safe_load(open('.github/workflows/web-chat-build.yml')); print('YAML OK')"` prints `YAML OK`.
* Workflow name registers via `gh api repos/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/workflows --jq '.workflows[].name'` including `Web Chat Build` after push (verified in final validation phase, not locally).

Context references:
* .copilot-tracking/research/subagents/2026-09-14/web-chat-app-research.md (Lines 2208-2296, full `web-chat-build.yml` contents)

Dependencies:
* Step 2.1-2.4 (apps/web-chat must exist for the workflow's paths/tests to be meaningful)
* Step 3.2, Step 3.3 (deployment_summary.py, ci_results.py must exist for the summary step to succeed)

## Implementation Phase 4: Update wiki content

<!-- parallelizable: false -->

Note: the wiki is a separate git repository (`foundry-hosted-agents-fsi.wiki.git`), not part of this repo's main working tree. Implementation must clone it separately (e.g. to a scratch path), edit, commit, and push to that remote -- these files are NOT created under the main repo's tracked paths.

### Step 4.1: Update `Home.md` with Quick facts and Useful commands sections

**Precondition -- confirm before writing content:** `azure.yaml`'s top-of-file banner states "AUTHOR-ONLY / NOT DEPLOYED. Gated behind G2/G3/G6... Do not run `azd provision`, `azd deploy`, `azd up`... until all three gates are explicitly cleared", and `.github/workflows/hosted-agent-cd.yml` is `workflow_dispatch`-only with the same "DO NOT DISPATCH UNTIL GATES CLEAR" banner. `kind: hosted` in `azure.yaml` declares the *service type*, not that it has actually been deployed/gate-cleared. Do not assume `quote-preparation-agent` is live; confirm the current gate status with the user/repo owner before publishing commands that imply it is safe to run against a real environment.

Files (in the wiki repo clone, e.g. `<scratch>/Home.md`):
* Home.md - modify: add a `## Quick facts` section (repository name `foundry-hosted-agents-fsi`, azd environments `desjardins-quote-preparation-staging`/`desjardins-quote-preparation-poc`, region, Foundry account/project naming pattern `aif-${environmentName}`/`proj-${environmentName}`, hosted agent name `quote-preparation-agent`) and a `## Useful commands` section listing the same command shapes as the sibling (`azd provision --no-prompt`, `azd deploy --no-prompt`, `azd ai agent invoke quote-preparation-agent "..." --no-prompt`, `azd ai agent show quote-preparation-agent --no-prompt`, `azd ai agent monitor quote-preparation-agent --no-prompt`) with an FSI-appropriate sample invocation prompt (derive from `data/synthetic/fixtures/`) -- **explicitly labeled** (matching `Workflows.md`'s existing gating-callout style) as applicable only once Gates G2/G3/G6 have cleared, not asserted as already-safe-to-run today
* Do not add a "Try the staging web chatbot" section or a "Verified release" callout yet (no live URL, no verified production run to report per DD-01) -- leave those as follow-on (WI-01)
* Update the `## Pages` list to include the new pages added in Steps 4.2-4.4 (`Architecture`, `Operations`, `Release Evidence`) alongside the existing `Workflows` link

Discrepancy references:
* Relates to DD-01 (no web-chat URL/verified-release content added, since none exists yet)

Success criteria:
* `Home.md` contains `## Quick facts`, `## Useful commands`, and an updated `## Pages` list with working relative wiki links.
* The `## Useful commands` section carries a gating disclaimer consistent with `azure.yaml`'s and `hosted-agent-cd.yml`'s "AUTHOR-ONLY / NOT DEPLOYED" banners, not presented as ready-to-run today.
* No literal "Air Canada", "threat-assessment", or sibling subscription/RG names remain.

Context references:
* .copilot-tracking/research/subagents/2026-09-14/wiki-and-pages-research.md (Lines 1-95, full sibling `Home.md`; Lines 637-669, diff table)

Dependencies:
* None (independent of Phases 1-3, but should be sequenced after them so the "Pages" list and workflow references are accurate)

### Step 4.2: Author `Architecture.md`

Files (wiki repo clone):
* Architecture.md - create; adapt the sibling's structural pattern (LangGraph/agent topology section, `azd services` table sourced from this repo's actual `azure.yaml`, MCP tool servers section describing `application-server`/`rulebook-server`) using this repo's actual `azure.yaml`, `src/quote-preparation-agent/`, and `mcp/` contents (read these during implementation, do not guess)

Discrepancy references:
* None

Success criteria:
* Page accurately reflects this repo's real `azure.yaml` services table and MCP server names (cross-check against `azure.yaml` read in Step 4.1's research).

Context references:
* .copilot-tracking/research/subagents/2026-09-14/wiki-and-pages-research.md (Lines 146-274, sibling `Architecture.md` full content for structural pattern)
* azure.yaml (local, already read this session -- Lines 1-72 shown in research doc's Consolidated Findings)

Dependencies:
* None

### Step 4.3: Author `Operations.md`

Files (wiki repo clone):
* Operations.md - create; adapt sibling's structural pattern (release approvals, identity checks, immutable image promotion) using this repo's actual `deploy-and-evaluate.yml`/`hosted-agent-cd.yml` content -- explicitly OMIT a "Monitoring and recovery" subsection per DR-04 (do not fabricate a non-existent monitoring step)

Discrepancy references:
* Addresses DR-04 (omits fabricated monitoring content; logs WI-04 instead)

Success criteria:
* Page describes only pipeline behavior that actually exists in this repo's workflows (verified by reading them during implementation).

Context references:
* .copilot-tracking/research/subagents/2026-09-14/wiki-and-pages-research.md (Lines 274-333, sibling `Operations.md` equivalent content and "Environments and CI/CD" section)

Dependencies:
* Phase 3 complete (so the workflow list described is accurate/final)

### Step 4.4: Author `Release-Evidence.md`

Files (wiki repo clone):
* Release-Evidence.md - create; adapt sibling's structural pattern (pipeline proof, evaluation proof, tool/safety proof, production proof, "Reproduce the evidence" steps) using this repo's actual evaluation gate (`eval/evaluation_gate.py`) metrics and any existing evidence artifacts already produced by this repo's CI -- if no such evidence run yet exists locally, write the page describing HOW to reproduce evidence (the reproducible steps) without fabricating specific past run numbers/dates

Discrepancy references:
* None

Success criteria:
* Page contains no fabricated run IDs, dates, or metric values that don't correspond to an actual local run; if no historical run exists, the page is framed as a how-to/reproduction guide instead of a report of a specific past event.

Context references:
* .copilot-tracking/research/subagents/2026-09-14/wiki-and-pages-research.md (Lines 562-637, sibling `Release-Evidence.md` full content for structural pattern)

Dependencies:
* None

### Step 4.5: Update `_Sidebar.md` and `Workflows.md`

Files (wiki repo clone):
* _Sidebar.md - modify: add nav entries for `Architecture`, `Operations`, `Release Evidence` alongside the existing entries
* Workflows.md - modify: add a row/section for the new `Web Chat Build` workflow (Step 3.5) and the auto-registered `pages-build-deployment` workflow (Step 1.1) in the existing workflow table

Discrepancy references:
* None

Success criteria:
* `_Sidebar.md` links resolve to the pages created in Steps 4.2-4.4.
* `Workflows.md`'s workflow table lists all 6 workflows (4 existing + `Web Chat Build` + `pages-build-deployment`).

Context references:
* .copilot-tracking/research/subagents/2026-09-14/wiki-and-pages-research.md (Lines 95-146, sibling `_Sidebar.md`)

Dependencies:
* Step 1.1, Step 3.5 (both new workflows must exist to be listed accurately)

### Step 4.6: Commit and push wiki changes

Commands (from the wiki scratch clone directory):
* `git add -A && git commit -m "docs(wiki): add architecture, operations, release-evidence pages and update home/workflows for parity"`
* `git push origin master` (GitHub wikis default to `master`, not `main` -- verify branch name with `git branch` before pushing)

Success criteria:
* The wiki has exactly 6 pages: `_Sidebar`, `Home`, `Workflows` (existing 3, updated) plus `Architecture`, `Operations`, `Release-Evidence` (3 newly authored) -- verify via the wiki repo clone's file listing.

Dependencies:
* Steps 4.1-4.5

## Implementation Phase 5: Validation

<!-- parallelizable: false -->

### Step 5.1: Run full project validation

Execute:
* `python -m py_compile apps/web-chat/app.py apps/web-chat/auth.py scripts/deployment_summary.py scripts/ci_results.py`
* `python -m pytest apps/web-chat/tests -q` (after `pip install -r apps/web-chat/requirements.txt pytest` in an appropriate environment)
* `cd apps/web-chat/frontend && npm install && npm run build && npm test` (or `node --test tests/*.test.js`)
* `python -c "import yaml; yaml.safe_load(open('.github/workflows/web-chat-build.yml')); print('YAML OK')"`
* `az bicep build --file infra/web-chat.bicep` (or `mcp_azure_bicep_m_build_bicep` tool)
* `bash scripts/test-agent-response.sh` and `bash scripts/test-production-version.sh`

### Step 5.2: Fix minor validation issues

Iterate on lint/test failures directly when corrections are small and isolated (missing import, syntax typo, path mismatch).

### Step 5.3: Report blocking issues

If Pages fails to build after the Step 1.1 source-config change (e.g. Jekyll build error in `docs/`), or if the web-chat frontend/backend tests reveal a deeper compatibility issue with `eval/evaluation_gate.py` (Step 3.3), document the specific failure and recommend targeted follow-up research/planning rather than large-scale rework within this validation phase.

## Dependencies

* `gh` CLI authenticated with repo-admin scope (Pages settings change)
* Python 3.13, Node.js 22 (matching `web-chat-build.yml`'s toolchain)
* Azure CLI + Bicep CLI (or `mcp_azure_bicep_m_build_bicep` tool) for `infra/web-chat.bicep` validation only (no deployment)
* Git access to `https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi.wiki.git`

## Success Criteria

* Local repo has 6 registered Actions workflows (4 existing + `Web Chat Build` + auto `pages-build-deployment`), matching the sibling's count.
* `apps/web-chat/` exists, builds, and its test suites pass, fully adapted to the Desjardins quote-preparation domain (no residual sibling-domain strings).
* `infra/web-chat.bicep` exists, is parameterized for this repo's naming conventions, and validates with `az bicep build`, but is NOT executed against Azure by this plan.
* GitHub Pages builds successfully from `docs/` (source `legacy` + `/docs`), publishing the labs ("lab published").
* Wiki has 6 pages (`_Sidebar`, `Home`, `Workflows`, `Architecture`, `Operations`, `Release-Evidence`) with FSI-accurate content and no fabricated facts.
