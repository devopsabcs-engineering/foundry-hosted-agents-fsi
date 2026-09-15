<!-- markdownlint-disable-file -->
# Release Changes: Bring foundry-hosted-agents-fsi to parity with sibling foundry-hosted-agents

**Related Plan**: hosted-agents-sibling-parity-plan.instructions.md
**Implementation Date**: 2026-09-14

## Summary

Ports an adapted `apps/web-chat` application (Desjardins quote-preparation domain) plus supporting scripts and an `infra/web-chat.bicep` template, code-only per DD-01; fixes the local repo's misconfigured GitHub Pages source so the labs publish and the auto-registered `pages-build-deployment` workflow appears; and authors FSI-accurate wiki pages (`Architecture`, `Operations`, `Release-Evidence`, plus `Home`/`Workflows`/`_Sidebar` updates).

## Changes

### Added

* docs/_includes/head_custom.html - bilingual nav-hiding Jekyll include (Phase 1, Step 1.2)
* apps/web-chat/requirements.txt - backend dependencies (Phase 2, Step 2.1)
* apps/web-chat/app.py - FastAPI chat backend (Phase 2, Step 2.1)
* apps/web-chat/auth.py - MSAL/Entra auth module (Phase 2, Step 2.1)
* apps/web-chat/Dockerfile - backend container build (Phase 2, Step 2.1)
* apps/web-chat/.dockerignore (Phase 2, Step 2.1)
* apps/web-chat/tests/test_app.py - backend tests (Phase 2, Step 2.2)
* apps/web-chat/tests/test_auth.py - auth tests (Phase 2, Step 2.2)
* apps/web-chat/frontend/vite.config.js (Phase 2, Step 2.3)
* apps/web-chat/frontend/.gitignore (Phase 2, Step 2.3)
* apps/web-chat/frontend/src/request.js (Phase 2, Step 2.3)
* apps/web-chat/frontend/src/stream.js (Phase 2, Step 2.3)
* apps/web-chat/frontend/tests/request.test.js (Phase 2, Step 2.3)
* apps/web-chat/frontend/tests/stream.test.js (Phase 2, Step 2.3)
* apps/web-chat/frontend/src/style.css - reconstructed, not byte-for-byte (Phase 2, Step 2.3; see Additional/Deviating Changes)
* apps/web-chat/frontend/package.json - Desjardins-domain rename (Phase 2, Step 2.4)
* apps/web-chat/frontend/index.html - Desjardins-domain retitle (Phase 2, Step 2.4)
* apps/web-chat/frontend/src/main.jsx - Desjardins quote-preparation UI copy (Phase 2, Step 2.4)
* apps/web-chat/frontend/src/samples.js - sample queries grounded in local `data/synthetic/fixtures/case-syn-*.json` (Phase 2, Step 2.4)
* apps/web-chat/frontend/tests/samples.test.js - adapted to validate against local fixture files (Phase 2, Step 2.4)
* scripts/validate-agent-response.jq (Phase 3, Step 3.1)
* scripts/test-agent-response.sh (Phase 3, Step 3.1)
* scripts/record-production-version.sh - `quote-preparation-agent` naming (Phase 3, Step 3.1)
* scripts/test-production-version.sh - `quote-preparation-agent` naming (Phase 3, Step 3.1)
* scripts/capture-release-evidence.ps1 (Phase 3, Step 3.1)
* scripts/setup-web-chat-identity.ps1 - adapted, mandatory tenant/pilot-group params (Phase 3, Step 3.2)
* scripts/deployment_summary.py - rewritten to source values from `azd env get-values`/env vars (Phase 3, Step 3.2)
* scripts/ci_results.py - ported with adapted eval-gate import (Phase 3, Step 3.3; see Additional/Deviating Changes)
* infra/web-chat.bicep - parameterized standalone template (Phase 3, Step 3.4)
* infra/web-chat.json - compiled Bicep output, matching repo convention (Phase 3, Step 3.4)
* .github/workflows/web-chat-build.yml (Phase 3, Step 3.5)
* [wiki repo, C:\temp\fsi-wiki] Architecture.md - LangGraph topology, azd services, MCP servers (Phase 4, Step 4.2)
* [wiki repo, C:\temp\fsi-wiki] Operations.md - release path, identity prerequisites, image promotion (Phase 4, Step 4.3)
* [wiki repo, C:\temp\fsi-wiki] Release-Evidence.md - evidence reproduction guide (Phase 4, Step 4.4)

### Modified

* docs/_config.yml - `url` field set from the repo's already-assigned GitHub Pages `html_url` (Phase 1, Step 1.3)
* [wiki repo, C:\temp\fsi-wiki] Home.md - Quick facts + gated Useful commands (Phase 4, Step 4.1)
* [wiki repo, C:\temp\fsi-wiki] Workflows.md, _Sidebar.md - added web-chat-build.yml row, linked new pages (Phase 4, Step 4.5)
* scripts/capture-release-evidence.ps1 - `$profile` renamed to `$edgeProfile` to avoid shadowing PowerShell's automatic variable (Phase 5, Step 5.2)

### Removed

## Additional or Deviating Changes

* Step 1.1 (GitHub Pages source switch to `legacy` + `/docs`) was executed after explicit user confirmation on 2026-09-14. Verified live: `build_type: legacy`, `source: {branch: main, path: /docs}` (Planning Log DD-03, now resolved).
  * Reason it was held for confirmation: operational-safety rule for live/shared-infrastructure changes; the plan itself flagged this step as requiring confirmation.
* `apps/web-chat/frontend/src/style.css` was reconstructed rather than ported byte-for-byte (Planning Log DD-02).
  * Reason: the sibling source captured in research was truncated mid-rule; a re-fetch attempt did not recover the missing lines. Reconstructed to cover every class referenced by `main.jsx`, keeping confirmed tokens/media query verbatim.
* `apps/web-chat/frontend/package-lock.json` was not generated; `node --test tests/stream.test.js` and `npm run build` were not run (Planning Log DR-05, WI-05).
  * Reason: `npm install` is blocked by the implementation environment's npm registry policy (remote fetches rejected / hangs against the public registry). Not a code defect -- backend tests (25 passed) and dependency-free frontend tests (2 passed) all passed.
* `scripts/ci_results.py`'s `eval.evaluation_gate` import was adapted (not verbatim) with a defensive fallback (Planning Log DD-04, WI-06).
  * Reason: this repo's `eval/evaluation_gate.py` is architecturally different (deterministic golden-dataset gate) from the sibling's evaluation-judge gate `ci_results.py` expects; a verbatim import would break at import time. Current workflow usage (`--junit` only) is unaffected.
* Wiki changes (Phase 4) were committed locally in the separate wiki clone (`C:\temp\fsi-wiki`, commit `fa9ac2e`) and pushed to `https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi.wiki.git` after explicit user confirmation on 2026-09-14 (`769b519..fa9ac2e`, Planning Log DD-05, now resolved).
  * Reason it was held for confirmation: pushing publishes content to a shared, externally-visible wiki, consistent with how Step 1.1 (GitHub Pages settings) was handled.

## Release Summary

All 5 phases executed; 4 of 5 fully complete, 1 partial (npm-registry-blocked frontend tooling). Both previously-pending confirmations were approved by the user on 2026-09-14 and executed:

* **DD-03**: GitHub Pages source switched to `legacy` + `/docs` -- verified live via follow-up GET.
* **DD-05**: Wiki changes pushed to `origin/master` (`769b519..fa9ac2e`).

**Files changed in the main repo**: 30 added, 3 modified, 0 removed (see Added/Modified above) across `docs/`, `apps/web-chat/` (backend + frontend), `scripts/`, `infra/`, and `.github/workflows/`.

**Wiki repo changed** (separate clone at `C:\temp\fsi-wiki`, pushed to `origin/master`): 3 pages added (`Architecture.md`, `Operations.md`, `Release-Evidence.md`), 3 pages modified (`Home.md`, `Workflows.md`, `_Sidebar.md`).

**Dependency/infrastructure changes**: `infra/web-chat.bicep` + compiled `infra/web-chat.json` added as a standalone, non-`azd`-driven template (validates via `az bicep build`, never deployed by this plan per DD-01). No changes to `azure.yaml` or `infra/main.bicep`.

**Deployment notes**: The web-chat app code was not deployed to Azure. `apps/web-chat` is code-complete and unit-tested on the backend (25/25 tests passing); frontend `package-lock.json`/build/full test suite are blocked by an environment npm-registry policy (DR-05/WI-05), not a code defect. GitHub Pages will rebuild from `docs/` shortly; allow a few minutes for the live site to reflect the new source. See Planning Log for the full discrepancy/deviation/follow-on-work ledger (DR-01..DR-05, DD-01..DD-05, WI-01..WI-06).

## Follow-On Changes (2026-09-15): Deployment link visibility (partial WI-01/WI-02 groundwork)

User request: ensure the Foundry project, hosted-agent, and web app/chatbot URLs are visible and clickable (README, wiki), matching the sibling repo's pattern. Investigation found `apps/web-chat` and `scripts/deployment_summary.py` already existed from the port above, but two real bugs/gaps prevented any links from actually appearing anywhere the user would see them. Fixed the bugs; did not deploy web-chat (still blocked on WI-01's real Entra tenant/pilot-group IDs and explicit gate sign-off -- see below).

### Modified (2026-09-15)

* scripts/deployment_summary.py - fixed the Foundry account/project name lookup: `infra/main.bicep`'s azd outputs land as the literal `accountName`/`projectName` keys, not `AZURE_AI_ACCOUNT_NAME`/`AZURE_AI_PROJECT_NAME`, so the "Foundry project" link always fell through to a wrong hardcoded staging-only guess. Now checks the real key names first, then derives `aif-<env>`/`proj-<env>` from `AZURE_ENV_NAME` (matching `main.bicep`'s own naming formula) so it resolves correctly for staging AND production; omits the row entirely if neither is available, per the file's existing "omit rather than guess" design. Also fixed the "Web app in Azure" portal link, which was previously added whenever a resource group was known (regardless of whether web-chat was actually deployed) -- now gated on `WEB_CHAT_URL` too, alongside the chatbot link it describes. Added an `--out <path>` mode so a job with real azd/Azure context can persist the rendered table to a file for a later, credential-less job to reuse.
* scripts/update_wiki_deployment_links.py - added an optional `--from-file <path>` argument so the wiki-publish job can splice in a pre-rendered deployment-links file (produced by a job that had real deployment context) instead of calling `render()` locally with no azd/Azure context (which always produced an almost-empty table).
* .github/workflows/deploy-and-evaluate.yml - `deploy-staging` and `promote-production` jobs' existing "Deployment links summary" steps now also write to `deployment-links.md` (via the new `--out` flag) and upload it as `deployment-links-staging`/`deployment-links-production` artifacts (14-day retention) for `publish-test-trends.yml` to consume.
* .github/workflows/publish-test-trends.yml - added a "Download deployment links from the source run" step (prefers `deployment-links-production`, falls back to `deployment-links-staging`); the "Deployment links summary" step now republishes that downloaded file to `$GITHUB_STEP_SUMMARY` when present, falling back to the previous local `deployment_summary.py` render otherwise; the final wiki-push step passes `--from-file` to `update_wiki_deployment_links.py` when a downloaded file exists. Also corrected a stale top-of-file comment that claimed "this repository has no apps/web-chat" (it exists, code-only, gated).
* README.md - added `apps/web-chat/` to the Repository layout list (previously omitted); added a new "Deployment links" section pointing to the wiki's always-current Deployment Links table and Continuous Test Trends page, and transparently documenting the web-chat pilot's current authored-but-not-deployed, gated status (no fabricated live chatbot URL).

### Additional or Deviating Changes (2026-09-15)

* Did not execute `scripts/setup-web-chat-identity.ps1` or deploy `infra/web-chat.bicep`, which would be required to produce a real, live chatbot URL (WI-01). Both require a real Entra tenant ID and an existing security-enabled pilot group ID that were not supplied, and constitute a hard-to-reverse, shared-system, new-public-surface change (new Entra app registration + new Container App) that this repo's own gate language ("gated behind G2/G3/G6 sign-off... by their owners") and this session's operational-safety rules require explicit user authorization for before proceeding. Flagged to the user as the next decision point rather than assumed.
* Noted, but did not resolve, an apparent contradiction between `deploy-and-evaluate.yml`'s top-of-file banner ("This repository has never been deployed to Azure. Do not dispatch it... until all three gates are explicitly cleared") and this session's and the prior session's confirmed real, successful dispatches of that exact workflow against real Azure infrastructure. Not changed pending user clarification on whether the banner is simply stale or reflects an unresolved process gap.
