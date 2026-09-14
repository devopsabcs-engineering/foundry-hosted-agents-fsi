<!-- markdownlint-disable-file -->
# Planning Log: Bring foundry-hosted-agents-fsi to parity with sibling foundry-hosted-agents

## Discrepancy Log

### Unaddressed Research Items

* DR-01: Sibling's `Web-Chat-Pilot.md`, `RBAC-401-Investigation.md`, and `Manual-Agent-Workaround.md` wiki pages are not ported.
  * Source: .copilot-tracking/research/subagents/2026-09-14/wiki-and-pages-research.md (Sibling Wiki Page Contents section)
  * Reason: All three describe a deployed-and-reachable web-chat pilot with a real URL, or sibling-specific historical incidents. This plan explicitly does not deploy the web-chat app to Azure (see DD-01), so there is no live pilot to document, and the other two have no FSI analog.
  * Impact: low -- these become natural follow-on work once the app is actually deployed by an operator.
* DR-02: Sibling's `Continuous-Test-Trends.md` wiki page is not ported.
  * Source: .copilot-tracking/research/subagents/2026-09-14/wiki-and-pages-research.md (Home.md / Workflows.md Diff section)
  * Reason: Requires extending `publish-test-trends.yml` to push results to the wiki, which local's `Workflows.md` explicitly documents as NOT happening today. Out of scope for a parity pass that doesn't change trend-publishing behavior.
  * Impact: low -- logged as follow-on (WI-02).
* DR-03: `scripts/build-release-evidence.js` and its screenshot companion behavior are not ported.
  * Source: .copilot-tracking/research/subagents/2026-09-14/web-chat-app-research.md (Summary for Planner)
  * Reason: Hardcoded to one specific historical sibling run/metric set (`coherence`/`groundedness`/`task_adherence`), belongs to the agent-release-evidence concern rather than the web-chat/workflow-count/wiki gaps the user asked about. Porting well requires a from-scratch rewrite against this repo's actual eval metrics.
  * Impact: medium -- `scripts/capture-release-evidence.ps1` is ported but has nothing to screenshot without this; noted as a paired follow-on item (WI-03).
* DR-04: Sibling's "Monitoring and recovery" wiki content (Kusto exception-count query, manual recovery steps) is not ported into `Workflows.md`.
  * Source: .copilot-tracking/research/subagents/2026-09-14/wiki-and-pages-research.md (Home.md / Workflows.md Diff section)
  * Reason: Confirmed local `deploy-and-evaluate.yml` has no equivalent monitoring/exception-check step to document; writing this section now would fabricate non-existent pipeline behavior.
  * Impact: low -- logged as follow-on (WI-04), tied to adding a monitoring step to the pipeline first.

### Plan Deviations from Research

* DD-01: Plan ports `apps/web-chat/`, `infra/web-chat.bicep`, and `scripts/setup-web-chat-identity.ps1` as code only; it does NOT run `az acr build`, `az deployment group create`, or `./scripts/setup-web-chat-identity.ps1` against any real Azure subscription.
  * Research recommends: The sibling's own wiki documents an operator runbook that ends with an actually-deployed, reachable Container App URL.
  * Plan implements: Code/templates ready for a human operator to run manually, matching this repo's existing `azure.yaml` "AUTHOR-ONLY / NOT DEPLOYED" gate (G2/G3/G6) already in place for the hosted agent itself.
  * Rationale: Executing real Azure deployment commands is a destructive/hard-to-reverse, credential-requiring, cost-incurring action outside a code-authoring plan, and would bypass the same gating discipline already applied to the rest of this repo's infrastructure. The user's three stated symptoms (workflow count, wiki content, "web app not deployed") are about the app/tooling existing and being deployable, not about this plan personally standing up a live pilot.

## Implementation Paths Considered

### Selected: Code-only port + GitHub Pages source-config fix + adapted wiki authoring

* Approach: Port `apps/web-chat` (adapted for Desjardins), its supporting scripts (ported/adapted per file), `infra/web-chat.bicep` (parameterized, not executed), and `.github/workflows/web-chat-build.yml`; fix the local repo's GitHub Pages source configuration to `legacy` + `/docs` (repo settings API call, reversible); author new/updated wiki pages using the sibling's structural patterns with FSI-accurate content only.
* Rationale: Directly resolves the three symptoms the user reported (4-vs-6 workflows, web app not deployed [code exists and is deployable], wiki missing content) while respecting this repo's existing deployment-gating conventions and avoiding fabricated documentation.
* Evidence: .copilot-tracking/research/2026-09-14/foundry-hosted-agents-parity-research.md (Consolidated Findings section)

### IP-01: Fully automate the web-chat deployment as part of this plan (run `az acr build` + `az deployment group create` + identity script against the real Desjardins subscription)

* Approach: Have the implementation phase actually stand up the Container App, matching the sibling's live, reachable pilot.
* Trade-offs: Would fully close the "web app not deployed" gap (a real URL would exist), but requires real Entra tenant/pilot-group IDs that don't exist yet for this repo (per web-chat-app-research.md blocking question #3), requires credentials/subscription access this planning session doesn't have, and bypasses the same G2/G3/G6 gating already enforced on the rest of the repo's infra.
* Rejection rationale: Too high-risk/irreversible for an unattended plan; no Entra app-registration values are available; inconsistent with the repo's existing "AUTHOR-ONLY / NOT DEPLOYED" convention. Left as an explicit, clearly-flagged manual follow-on step (WI-01) for a human operator with the right access.

### IP-02: Skip the web-chat app port entirely and only fix workflows/Pages/wiki text

* Approach: Treat "web app not deployed" as out of scope; only close the workflow-count and wiki-content gaps.
* Trade-offs: Much smaller, lower-risk change; but leaves the single largest and most concrete symptom (no `apps/web-chat` at all) completely unaddressed, and the ported `web-chat-build.yml` (needed for true workflow-count parity) would have nothing to build.
* Rejection rationale: The user explicitly named "web app not deployed" as one of the three gaps to close; a workflow file with no app to build it against would not be genuine parity, just a hollow file.

## Suggested Follow-On Work

* WI-01: Deploy the ported web-chat app to a real staging Container App -- run the operator runbook (`az acr build`, `az deployment group create --template-file infra/web-chat.bicep`, `./scripts/setup-web-chat-identity.ps1`) once real Entra tenant/client/pilot-group IDs exist for the Desjardins tenant, and add a `Web-Chat-Pilot.md` wiki page documenting the live URL. (medium priority)
  * Source: DD-01, DR-01
  * Dependency: Entra app-registration values for the Desjardins tenant; sign-off consistent with the repo's existing gating model.
* WI-02: Extend `publish-test-trends.yml` to push a `Continuous-Test-Trends.md` wiki page, matching the sibling's trend-publishing behavior. (low priority)
  * Source: DR-02
  * Dependency: Decision on whether wiki-push trend publishing is desired for this repo at all.
* WI-03: Port and rewrite `scripts/build-release-evidence.js` against this repo's actual eval metrics/dataset, pairing it with the already-ported `scripts/capture-release-evidence.ps1`. (medium priority)
  * Source: DR-03
  * Dependency: A completed, evidence-worthy staging-to-production release run to capture.
* WI-04: Add a "Monitoring and recovery" section to `Workflows.md` once `deploy-and-evaluate.yml` gains an actual post-deploy monitoring/exception-check step. (low priority)
  * Source: DR-04
  * Dependency: A monitoring step must be added to `deploy-and-evaluate.yml` first (separate piece of work, not part of this plan).
