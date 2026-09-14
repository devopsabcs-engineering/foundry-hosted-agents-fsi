---
applyTo: '.copilot-tracking/changes/2026-09-14/hosted-agents-sibling-parity-changes.md'
---
<!-- markdownlint-disable-file -->
# Implementation Plan: Bring foundry-hosted-agents-fsi to parity with sibling foundry-hosted-agents

## Overview

Close the three parity gaps the user identified against the sibling repo `foundry-hosted-agents` -- missing wiki content (including test trends), the web-chat app not existing/deployable, and only 4 of 6 Actions workflows -- by porting an adapted `apps/web-chat` application and its supporting scripts/infra template (code only, not deployed), fixing the local repo's misconfigured GitHub Pages source, and authoring FSI-accurate wiki pages.

## Objectives

### User Requirements

* Bring wiki content up to parity with the sibling -- Source: user's parity request ("wiki missing stuff including test trends"). Note: the "test trends" sub-ask is explicitly deferred to follow-on work (WI-02, see Planning Log DR-02) since closing it requires extending `publish-test-trends.yml` to push wiki updates, which is out of scope for this parity pass; this plan delivers `Architecture`, `Operations`, and `Release-Evidence` wiki pages plus `Home.md`/`Workflows.md`/`_Sidebar.md` updates.
* Get the web app deployed/deployable -- Source: user's parity request ("web app not deployed")
* Have 6 workflows instead of 4, matching the sibling -- Source: user's parity request ("only have 4 instead of 6 workflows --- due to lab not published")

### Derived Objectives

* Fix the root cause of the workflow-count gap (misconfigured GitHub Pages source) rather than fabricating a 6th workflow file -- Derived from: research confirming the sibling's 6th "workflow" is the auto-registered `pages-build-deployment`, not a repo-authored file
* Port `apps/web-chat` as code only, without executing any real Azure deployment command -- Derived from: this repo's existing `azure.yaml` "AUTHOR-ONLY / NOT DEPLOYED" gate (G2/G3/G6), and the absence of real Desjardins-tenant Entra IDs needed for a genuine deployment
* Adapt all sibling-domain content (Air Canada threat-assessment) to the Desjardins insurance quote-preparation domain rather than porting verbatim where domain-specific -- Derived from: this is a different product/customer context, verbatim sibling copy would be factually wrong here
* Do not fabricate wiki content describing pipeline behavior that does not exist locally (e.g. monitoring/recovery steps, a live web-chat URL, historical release runs) -- Derived from: documentation accuracy; research confirmed several sibling wiki sections have no current local equivalent

## Context Summary

### Project Files

* azure.yaml - defines the local `quote-preparation-agent` hosted-agent service (`kind: hosted`), the "AUTHOR-ONLY / NOT DEPLOYED" gate, and confirms `azd ai agent` commands are applicable
* infra/main.bicep - defines `accountName`/`projectName`/`environmentName` naming conventions (`aif-${environmentName}`, `proj-${environmentName}`) to mirror in the ported `web-chat.bicep`
* infra/modules/mcp-container-apps.bicep - defines the `${namePrefix}-mcp-env` Container Apps environment naming convention to reuse
* docs/_config.yml, docs/index.md, docs/Gemfile - existing, already-complete Jekyll scaffolding; only the Pages source configuration and one include file are missing
* .github/workflows/{continuous-validation.yml,deploy-and-evaluate.yml,hosted-agent-cd.yml,publish-test-trends.yml} - existing 4 workflows; confirmed to have zero web-chat or Pages-deploy references
* eval/evaluation_gate.py - must be checked for `METRICS`/`validate_results` compatibility before porting `scripts/ci_results.py`
* data/synthetic/fixtures/ - source material for rewriting `apps/web-chat/frontend/src/samples.js` with realistic quote-preparation sample queries

### References

* .copilot-tracking/research/2026-09-14/foundry-hosted-agents-parity-research.md - primary research document with Consolidated Findings synthesizing both subagent reports
* .copilot-tracking/research/subagents/2026-09-14/web-chat-app-research.md - full sibling `apps/web-chat/` source, scripts, and Azure deployment mechanism
* .copilot-tracking/research/subagents/2026-09-14/wiki-and-pages-research.md - full sibling wiki page contents and GitHub Pages configuration diff

### Standards References

* None discovered in `.github/copilot-instructions.md` specific to this repo's wiki/docs/workflow conventions beyond what research already captured

## Implementation Checklist

Note on `<!-- parallelizable: true -->` markers below: this means the *phase as a whole* has no file overlap with other parallelizable phases and can be worked concurrently with them. Steps *within* a phase may still have their own internal ordering (noted per-step in the details file's Dependencies subsections) -- parallelizability is a phase-to-phase property, not a claim that every step inside the phase is independently orderable.

### [ ] Implementation Phase 1: Fix GitHub Pages configuration and add bilingual nav include

<!-- parallelizable: true -->

* [ ] Step 1.1: Switch the repo's GitHub Pages source to `legacy` + `/docs` (live repo-settings change -- confirm with user before running)
  * Details: .copilot-tracking/details/2026-09-14/hosted-agents-sibling-parity-details.md (Lines 16-42)
* [ ] Step 1.2: Add the bilingual nav-hiding Jekyll include (`docs/_includes/head_custom.html`)
  * Details: .copilot-tracking/details/2026-09-14/hosted-agents-sibling-parity-details.md (Lines 43-89)
* [ ] Step 1.3: Update `docs/_config.yml` url placeholder once Pages has built (depends on Step 1.1)
  * Details: .copilot-tracking/details/2026-09-14/hosted-agents-sibling-parity-details.md (Lines 90-106)

### [ ] Implementation Phase 2: Port `apps/web-chat` application, adapted for Desjardins

<!-- parallelizable: true -->

* [ ] Step 2.1: Create backend files (verbatim port: `app.py`, `auth.py`, `Dockerfile`, `.dockerignore`, `requirements.txt`)
  * Details: .copilot-tracking/details/2026-09-14/hosted-agents-sibling-parity-details.md (Lines 111-132)
* [ ] Step 2.2: Create backend tests (verbatim port: `tests/test_app.py`, `tests/test_auth.py`) (depends on Step 2.1)
  * Details: .copilot-tracking/details/2026-09-14/hosted-agents-sibling-parity-details.md (Lines 133-150)
* [ ] Step 2.3: Create frontend scaffolding and generic modules (verbatim port)
  * Details: .copilot-tracking/details/2026-09-14/hosted-agents-sibling-parity-details.md (Lines 151-175)
* [ ] Step 2.4: Rewrite domain-specific frontend files for Desjardins (`package.json`, `index.html`, `main.jsx`, `samples.js`, regenerate `package-lock.json`) (depends on Step 2.3)
  * Details: .copilot-tracking/details/2026-09-14/hosted-agents-sibling-parity-details.md (Lines 176-198)
* [ ] Step 2.5: Validate phase changes
  * Run `python -m py_compile apps/web-chat/app.py apps/web-chat/auth.py`
  * Run `python -m pytest apps/web-chat/tests -q`
  * Run `node --test apps/web-chat/frontend/tests/*.test.js` and `npm run build` from `apps/web-chat/frontend/`

### [ ] Implementation Phase 3: Port supporting scripts, infra template, and the build workflow

<!-- parallelizable: false -->

* [ ] Step 3.1: Port generic scripts verbatim (`validate-agent-response.jq`, `test-agent-response.sh`, `record-production-version.sh`, `test-production-version.sh`, `capture-release-evidence.ps1`)
  * Details: .copilot-tracking/details/2026-09-14/hosted-agents-sibling-parity-details.md (Lines 203-225)
* [ ] Step 3.2: Adapt `setup-web-chat-identity.ps1` and rewrite `deployment_summary.py`
  * Details: .copilot-tracking/details/2026-09-14/hosted-agents-sibling-parity-details.md (Lines 226-244)
* [ ] Step 3.3: Verify `eval/evaluation_gate.py` compatibility and port `ci_results.py` (depends on Phase 2 for evidence file names)
  * Details: .copilot-tracking/details/2026-09-14/hosted-agents-sibling-parity-details.md (Lines 245-266)
* [ ] Step 3.4: Port `infra/web-chat.bicep`, parameterized for local naming conventions
  * Details: .copilot-tracking/details/2026-09-14/hosted-agents-sibling-parity-details.md (Lines 267-294)
* [ ] Step 3.5: Port `.github/workflows/web-chat-build.yml` (depends on Phase 2 and Steps 3.2/3.3)
  * Details: .copilot-tracking/details/2026-09-14/hosted-agents-sibling-parity-details.md (Lines 295-313)
* [ ] Step 3.6: Validate phase changes
  * Run `az bicep build --file infra/web-chat.bicep` (or `mcp_azure_bicep_m_build_bicep`)
  * Run `python -c "import yaml; yaml.safe_load(open('.github/workflows/web-chat-build.yml'))"`
  * Run `bash scripts/test-agent-response.sh` and `bash scripts/test-production-version.sh`

### [ ] Implementation Phase 4: Update wiki content

<!-- parallelizable: false -->

* [ ] Step 4.1: Update `Home.md` with Quick facts and Useful commands sections -- confirm `azure.yaml`/`hosted-agent-cd.yml` gate status with the user before wording the "Useful commands" section (see plan Objectives note)
  * Details: .copilot-tracking/details/2026-09-14/hosted-agents-sibling-parity-details.md (Lines 320-342)
* [ ] Step 4.2: Author `Architecture.md`
  * Details: .copilot-tracking/details/2026-09-14/hosted-agents-sibling-parity-details.md (Lines 343-360)
* [ ] Step 4.3: Author `Operations.md` (omitting fabricated monitoring content, depends on Phase 3 for an accurate workflow list)
  * Details: .copilot-tracking/details/2026-09-14/hosted-agents-sibling-parity-details.md (Lines 361-377)
* [ ] Step 4.4: Author `Release-Evidence.md`
  * Details: .copilot-tracking/details/2026-09-14/hosted-agents-sibling-parity-details.md (Lines 378-394)
* [ ] Step 4.5: Update `_Sidebar.md` and `Workflows.md` (depends on Steps 1.1, 3.5, 4.2-4.4)
  * Details: .copilot-tracking/details/2026-09-14/hosted-agents-sibling-parity-details.md (Lines 395-413)
* [ ] Step 4.6: Commit and push wiki changes
  * Details: .copilot-tracking/details/2026-09-14/hosted-agents-sibling-parity-details.md (Lines 414-425)

### [ ] Implementation Phase 5: Validation

<!-- parallelizable: false -->

* [ ] Step 5.1: Run full project validation
  * Details: .copilot-tracking/details/2026-09-14/hosted-agents-sibling-parity-details.md (Lines 430-439)
* [ ] Step 5.2: Fix minor validation issues
  * Details: .copilot-tracking/details/2026-09-14/hosted-agents-sibling-parity-details.md (Lines 440-443)
* [ ] Step 5.3: Report blocking issues
  * Details: .copilot-tracking/details/2026-09-14/hosted-agents-sibling-parity-details.md (Lines 444-447)

## Planning Log

See .copilot-tracking/plans/logs/2026-09-14/hosted-agents-sibling-parity-log.md for discrepancy tracking (DR-01..DR-04, DD-01), implementation paths considered (IP-01, IP-02), and suggested follow-on work (WI-01..WI-04).

## Dependencies

* `gh` CLI authenticated with repo-admin scope (GitHub Pages settings change)
* Python 3.13 and Node.js 22 (matching `web-chat-build.yml`'s toolchain)
* Azure CLI + Bicep CLI (or `mcp_azure_bicep_m_build_bicep` tool) for template validation only -- no deployment
* Git access to the wiki remote `https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi.wiki.git`

## Success Criteria

* Local repo shows 6 registered Actions workflows (4 existing + `Web Chat Build` + auto-registered `pages-build-deployment`) -- Traces to: user requirement "6 workflows"
* GitHub Pages builds successfully and publishes the labs from `docs/` -- Traces to: user requirement "lab not published"
* `apps/web-chat/` exists, is fully adapted to the Desjardins domain, builds, and its tests pass -- Traces to: user requirement "web app not deployed" (deployable, not yet deployed per DD-01)
* `infra/web-chat.bicep` validates via `az bicep build` but is not executed against Azure by this plan -- Traces to: DD-01 (deployment gating discipline)
* Wiki has `_Sidebar`, `Home`, `Workflows`, `Architecture`, `Operations`, `Release-Evidence` pages, all with FSI-accurate (non-fabricated) content -- Traces to: user requirement "wiki missing stuff"
