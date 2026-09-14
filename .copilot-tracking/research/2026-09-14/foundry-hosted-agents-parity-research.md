<!-- markdownlint-disable-file -->
# Task Research: Bring foundry-hosted-agents-fsi to parity with sibling foundry-hosted-agents

## Research Executed

### File Searches

* `.github/workflows/` (this repo, foundry-hosted-agents-fsi)
  * Found 4 workflow files: `continuous-validation.yml`, `deploy-and-evaluate.yml`, `hosted-agent-cd.yml`, `publish-test-trends.yml`
* `.copilot-tracking/plans/` (this repo)
  * Only existing plan: `2026-09-13/desjardins-bilingual-hosted-agents-workshop-plan.instructions.md` -- scoped to bilingual workshop labs/calculator/approval-repo/MCP servers/agent content, does NOT cover web-chat app, GitHub Pages, or wiki parity.
* Top-level repo layout (this repo): `apps/` (contains only `workshop/`), `assets/`, `azure.yaml`, `data/`, `docs/`, `eval/`, `infra/`, `mcp/`, `scripts/` (contains only `build-workshop-deck.js`), `src/`

### Sibling repo inspection (GitHub API, read-only, via `gh api`)

* Sibling: `devopsabcs-engineering/foundry-hosted-agents`
* `.github/workflows/` contents (5 files committed): `continuous-validation.yml`, `deploy-and-evaluate.yml`, `hosted-agent-cd.yml`, `publish-test-trends.yml`, `web-chat-build.yml`
* Full registered Actions workflow list (`gh api repos/.../actions/workflows`) -- 6 entries total:
  1. Continuous Validation
  2. Deploy and Evaluate (Staging -> Production)
  3. Hosted Agent CI/CD
  4. Publish Test Trends
  5. Web Chat Build
  6. `pages-build-deployment` (path `dynamic/pages/pages-build-deployment`) -- auto-registered by GitHub the moment Pages is enabled; not a file in the repo.
* `gh api repos/devopsabcs-engineering/foundry-hosted-agents/pages` returns:
  ```json
  {
    "html_url": "https://vigilant-guacamole-y8qe3rw.pages.github.io/",
    "build_type": "legacy",
    "source": {"branch": "main", "path": "/docs"},
    "public": false
  }
  ```
  Confirms sibling's Pages site is built from `main` branch, `/docs` folder, classic ("legacy"/Jekyll) build -- this is what "publishes the lab" (the `docs/` labs content) and is the reason the 6th (`pages-build-deployment`) workflow exists there.
* `apps/` in sibling: `workshop/`, `web-chat/` (this repo is missing `web-chat/` entirely)
* `scripts/` in sibling (this repo only has `build-workshop-deck.js`): `build-deck.js`, `build-release-evidence.js`, `build-workshop-deck.js`, `capture-release-evidence.ps1`, `ci_results.py`, `configure-agent-rbac.sh`, `deployment_summary.py`, `invoke-agent.sh`, `record-production-version.sh`, `release-slides.js`, `remove-workshop.ps1`, `render-presentations.ps1`, `setup-web-chat-identity.ps1`, `test-agent-rbac.sh`, `test-agent-response.sh`, `test-production-version.sh`, `test_mcp_servers.py`, `tests/`, `validate-agent-response.jq`
* Full content of sibling `.github/workflows/web-chat-build.yml` retrieved (raw). Key facts:
  * Triggers on push/PR to `main` touching `apps/web-chat/**`, the workflow file itself, or `scripts/deployment_summary.py`
  * Installs Node 22 + Python 3.13
  * Backend tests: `python -m pip install -r apps/web-chat/requirements.txt pytest` then `pytest apps/web-chat/tests -q --junitxml=web-chat-evidence/backend.xml` with `PYTHONPATH=apps/web-chat`
  * Frontend: `apps/web-chat/frontend` -- `npm ci`/`npm install`, `node --test` (JUnit reporter) against `tests/*.test.js`, then `npm run build`
  * Uploads `apps/web-chat/frontend/dist/` + `package-lock.json` as artifact `web-chat-frontend-${{ github.sha }}`
  * Uploads test evidence artifact `web-chat-tests-${{ github.run_attempt }}` (always)
  * Build summary step runs `python scripts/ci_results.py --junit web-chat-evidence` then `python scripts/deployment_summary.py`, writes to `$GITHUB_STEP_SUMMARY`
  * No Azure deployment step in this workflow -- deployment happens elsewhere (likely via `deploy-and-evaluate.yml` or a separate mechanism using `setup-web-chat-identity.ps1`/`record-production-version.sh`); NOT YET CONFIRMED, needs follow-up research.

### Wiki inspection (git clone of `.wiki.git` repos)

* Sibling wiki (`foundry-hosted-agents.wiki.git`) -- 8 pages: `_Sidebar.md`, `Architecture.md`, `Continuous-Test-Trends.md`, `Home.md`, `Manual-Agent-Workaround.md`, `Operations.md`, `RBAC-401-Investigation.md`, `Release-Evidence.md`, `Web-Chat-Pilot.md`
* This repo's wiki (`foundry-hosted-agents-fsi.wiki.git`) -- only 3 pages: `_Sidebar.md`, `Home.md`, `Workflows.md`
* Content of individual sibling wiki pages NOT YET read (only filenames known) -- needs follow-up research to determine what's portable vs. sibling-specific (e.g., `RBAC-401-Investigation` may describe a sibling-specific incident not applicable here).

## Key Discoveries

### Root cause chain (per user's own hypothesis, confirmed)

"Lab not published" == GitHub Pages not enabled on this repo. Sibling publishes `docs/` (the labs content) via Pages (`main` branch, `/docs` path, legacy/Jekyll build). Enabling the equivalent here should:
1. Make the labs publicly browsable (matches "lab published").
2. Auto-register the `pages-build-deployment` workflow, closing part of the 4-vs-6 workflow gap.
3. Requires this repo's `docs/` folder to already be Jekyll/Pages-compatible (has index, front matter) -- NOT YET VERIFIED for this repo; needs follow-up research (compare `docs/` structure + any `_config.yml` between repos).

### Missing web app

`apps/web-chat/` does not exist in this repo at all. It is a two-part app (Python backend + Node/frontend) with its own test suite, and is built (not deployed) by `web-chat-build.yml`. Actual deployment mechanism is unconfirmed -- likely tied to `setup-web-chat-identity.ps1` (RBAC/identity setup script) and possibly wired into `deploy-and-evaluate.yml` or a manual step. This is the single largest area of missing functionality and the primary driver of "web app not deployed."

### Missing workflow file

`.github/workflows/web-chat-build.yml` does not exist in this repo. Straightforward to port (self-contained CI workflow), but it references `apps/web-chat/**`, `apps/web-chat/requirements.txt`, `apps/web-chat/frontend`, and `scripts/deployment_summary.py`/`scripts/ci_results.py` -- all of which must exist first (dependency order: port `apps/web-chat` + `scripts/ci_results.py` + `scripts/deployment_summary.py` before/with this workflow).

### Wiki gap

5 pages exist in sibling that don't exist here: `Architecture`, `Continuous-Test-Trends`, `Manual-Agent-Workaround`, `Operations`, `Release-Evidence`, `Web-Chat-Pilot` (6 actually, plus `RBAC-401-Investigation` = 7 net-new candidates, some may be sibling-specific and not portable as-is). `Home.md` and `Workflows.md` already exist here and may need diffing/updating rather than wholesale replacement.

## Unresolved Questions / Follow-up Research Needed (ORIGINAL -- see Consolidated Findings below, all resolved)

1. Full directory tree + key file contents of sibling `apps/web-chat/` (backend entrypoint, `requirements.txt`, `frontend/package.json`, `frontend/src` structure, `tests/`) to know what to port and how to adapt it to the Desjardins quote-preparation agent.
2. Full contents of the 8 missing/existing sibling scripts listed above (especially `setup-web-chat-identity.ps1`, `deployment_summary.py`, `ci_results.py`, `record-production-version.sh`, `test-agent-response.sh`, `validate-agent-response.jq`, `build-release-evidence.js`, `capture-release-evidence.ps1`) to determine adaptation effort.
3. Content of all 8 sibling wiki pages (especially `Web-Chat-Pilot.md`, `Continuous-Test-Trends.md`, `Architecture.md`, `Operations.md`) to determine what's portable vs. sibling-specific.
4. This repo's current `docs/` folder structure vs. sibling's `docs/` folder (Jekyll config, `_config.yml`, `index.md`, nav) to determine what's needed to make Pages build succeed here.
5. Where/how the sibling's web-chat app is actually deployed to Azure (Container App? Static Web App? App Service?) -- not found in `web-chat-build.yml` itself; check `deploy-and-evaluate.yml` in sibling and `infra/` for a web-chat-related Bicep module.
6. Confirm current diff between this repo's existing `Home.md`/`Workflows.md` wiki pages and sibling's, to know whether to patch or replace.

## Consolidated Findings (from subagent research, 2026-09-14)

Full detail in:
* .copilot-tracking/research/subagents/2026-09-14/web-chat-app-research.md
* .copilot-tracking/research/subagents/2026-09-14/wiki-and-pages-research.md

### apps/web-chat port (see web-chat-app-research.md)

* Files to port (verbatim or near-verbatim): `apps/web-chat/app.py`, `auth.py`, `Dockerfile`, `.dockerignore`, `requirements.txt`, `frontend/{package.json,vite.config.js,index.html,.gitignore}`, `frontend/src/{request.js,stream.js,style.css}`, `frontend/tests/{request.test.js,stream.test.js}`, `tests/{test_app.py,test_auth.py}`.
* Files needing domain-copy rewrite for Desjardins (insurance quote-prep, not threat-assessment): `frontend/src/main.jsx` (UI copy/labels/icon), `frontend/src/samples.js` (sample queries -> quote scenarios, reuse `data/synthetic/fixtures/case-syn-*.json`), `frontend/index.html` (title), `frontend/package.json` (`name` field), `frontend/tests/samples.test.js` (not inspected -- low risk, rewritten alongside samples.js).
* Azure deployment mechanism: Azure Container Apps (`Microsoft.App/containerApps`), via a **standalone** `infra/web-chat.bicep` (not part of `main.bicep`, not `azd`-driven), applied by a human operator via `az deployment group create`. `azure.yaml` has no web-chat service entry in the sibling and should not gain one here either -- consistent with this repo's existing `azure.yaml` "AUTHOR-ONLY / NOT DEPLOYED" gate (G2/G3/G6). **Decision: port the app + bicep + scripts as code only; do not execute any deployment command against Azure as part of this plan** -- matches both the sibling's own manual-operator model and this repo's explicit deployment gate.
* Local Container Apps environment name to reuse in `infra/web-chat.bicep`: `${mcpNamePrefix}-mcp-env` per `infra/modules/mcp-container-apps.bicep` (confirmed locally) -- for staging this resolves to `mcp-staging-mcp-env` (same literal the sibling bicep uses, coincidentally, but must remain parameterized, not hardcoded).
* ACR name must stay parameterized (`acrName`/`mcpAcrName` pattern, env-var driven via `${MCP_ACR_NAME}`), not hardcoded like the sibling's `acraircanadapoc001` literal.
* Foundry account/project names follow local `infra/main.bicep` convention: `aif-${environmentName}` / `proj-${environmentName}` (e.g. `aif-desjardins-quote-preparation-staging`). Agent name is `quote-preparation-agent` (from local `azure.yaml`, `kind: hosted`, `protocol: responses v2.0.0`) -- so the ported bicep's `AGENT_ENDPOINT` env var should target `.../agents/quote-preparation-agent/endpoint/protocols/openai/responses?api-version=v1`.
* `azure.yaml` declares `quote-preparation-agent` as a Foundry **hosted-agent service** (`host: azure.ai.agent`, `kind: hosted`) -- this is a declared service *type*, not confirmation it is actually deployed/running. `azure.yaml`'s own top-of-file banner states "AUTHOR-ONLY / NOT DEPLOYED. Gated behind G2 (platform/security), G3 (reproducible compatibility), and G6 (regulatory/privacy) sign-off", and `.github/workflows/hosted-agent-cd.yml` is `workflow_dispatch`-only with a matching "DO NOT DISPATCH UNTIL GATES CLEAR" banner. So `azd ai agent invoke/show/monitor quote-preparation-agent` command *shapes* are structurally correct and worth documenting, but must be presented as applicable once gates clear, not as already-safe-to-run today -- confirm current gate status with the user/repo owner before publishing a "Useful commands" wiki section that could be read as an invitation to run them now.
* Scripts: port verbatim -- `scripts/validate-agent-response.jq`, `scripts/test-agent-response.sh`, `scripts/record-production-version.sh`, `scripts/capture-release-evidence.ps1`. Port with parameter/default changes only -- `scripts/setup-web-chat-identity.ps1`. Needs a substantial rewrite (re-parameterize away from hardcoded sibling subscription/RG/ACR/hostnames) -- `scripts/deployment_summary.py` (required by the ported `web-chat-build.yml`, so in-scope). Verify compatibility before porting -- `scripts/ci_results.py` (imports `eval.evaluation_gate.METRICS`/`validate_results`; confirm shape matches local `eval/evaluation_gate.py`).
* Deferred as follow-on work (not required for parity's core 3 asks): `scripts/build-release-evidence.js` (hardcoded to one historical sibling run/metric set, belongs to a separate agent-release-evidence concern, not web-chat or the 4-vs-6 workflow gap).
* `.github/workflows/web-chat-build.yml`: port structure as-is (Node 22 + Python 3.13, backend pytest, frontend `node --test`, Vite build, artifact upload, `ci_results.py` + `deployment_summary.py` summary step); paths already match local conventions once `apps/web-chat/` and the two scripts exist.

### Wiki + GitHub Pages (see wiki-and-pages-research.md)

* **Local `docs/` folder is already Jekyll-scaffolded** (`_config.yml` with `remote_theme: just-the-docs/just-the-docs`, `Gemfile`, `index.md`, full 10-lab EN+FR curriculum) -- this is NOT a from-scratch scaffolding task.
* **Root cause confirmed**: local GitHub Pages is already enabled but misconfigured (`build_type: workflow`, `source.path: "/"`, `status: null`, no matching deploy-pages workflow exists) vs. sibling's working config (`build_type: legacy`, `source: {branch: main, path: /docs}`, `status: built`). **Fix = change Pages source config to `legacy` + `/docs`** (repo Settings change, e.g. via `gh api -X PUT repos/.../pages`) -- this alone should make Pages build immediately from the existing `docs/` content, without any new workflow file, and will surface the `pages-build-deployment` 6th workflow.
* One directly portable file: `docs/_includes/head_custom.html` (generic just-the-docs bilingual EN/FR nav-hiding include) -- copy verbatim.
* Once Pages builds successfully, update `docs/_config.yml`'s `url:` field to the real assigned `*.pages.github.io` URL (currently empty with a TODO comment).
* Wiki pages -- ADAPT (author fresh FSI content using the sibling's *structural pattern*, not its content): `Architecture.md`, `Operations.md`, `Release-Evidence.md`, `_Sidebar.md`, and two `Home.md` subsections ("Quick facts", "Useful commands"). SKIP entirely (sibling-specific, no FSI analog): `Manual-Agent-Workaround.md`, `RBAC-401-Investigation.md`, `Web-Chat-Pilot.md` -- portable *only after* the web-chat app is actually deployed to a real URL, which this plan explicitly does not do (see above); a `Web-Chat-Pilot` FSI wiki page is therefore also deferred to follow-on work, not authored in this plan. `Continuous-Test-Trends.md` -- SKIP (would require extending `publish-test-trends.yml` to push wiki updates, out of scope; logged as follow-on).
* "Monitoring and recovery" wiki subsection (sibling's `Operations.md`) is NOT portable yet -- confirmed local `deploy-and-evaluate.yml` has no Kusto/exception-count monitoring step to document. Logged as follow-on work rather than fabricated content.
* `Home.md` "Quick facts" section: repo name, azd environments (`desjardins-quote-preparation-staging`/`-poc` per session context), region, Foundry account/project naming pattern (`aif-${environmentName}`/`proj-${environmentName}`), hosted agent name `quote-preparation-agent`. Exact RG/subscription/ACR literal values are env-var-driven, not repo constants -- Quick facts section should describe the naming *pattern*, not print secrets/exact subscription IDs.
* `Home.md` "Useful commands" section: mirror sibling's `azd provision`/`azd deploy`/`azd ai agent invoke|show|monitor quote-preparation-agent` block -- confirmed applicable (see above).
