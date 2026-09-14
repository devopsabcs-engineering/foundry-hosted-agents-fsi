<!-- markdownlint-disable-file -->
# RPI Validation: Desjardins Bilingual Hosted Agents Workshop — Implementation Phase 8: Infrastructure Scaffolding (author only, gated)

**Plan file**: [.copilot-tracking/plans/2026-09-13/desjardins-bilingual-hosted-agents-workshop-plan.instructions.md](../../../plans/2026-09-13/desjardins-bilingual-hosted-agents-workshop-plan.instructions.md) (Lines 139-146)
**Changes log**: [.copilot-tracking/changes/2026-09-13/desjardins-bilingual-hosted-agents-workshop-changes.md](../../../changes/2026-09-13/desjardins-bilingual-hosted-agents-workshop-changes.md)
**Research document**: [.copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md](../../../research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md)
**Details file**: [.copilot-tracking/details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md](../../../details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md) (Lines 417-460)
**Planning log**: [.copilot-tracking/plans/logs/2026-09-13/desjardins-bilingual-hosted-agents-workshop-log.md](../../../plans/logs/2026-09-13/desjardins-bilingual-hosted-agents-workshop-log.md)
**Validation date**: 2026-09-13

## Scope

Phase 8 has two checklist steps, both marked `[x]`:

* Step 8.1 (plan line 143; details lines 421-443): Adapt Bicep modules for the read-only MCP services and hosted agent, without deploying.
* Step 8.2 (plan lines 145-146; details lines 444-450): Validate phase changes — `bicep build`/`az bicep build` lint/compile only; explicitly forbids `azd provision`, `azd deploy`, or any apply command until Gates G2, G3, G6 clear.

## Plan Item → Changes Log Mapping

| Plan/Details item | Changes log evidence | Status |
| --- | --- | --- |
| Adapt `infra/modules/ai-foundry.bicep`, `mcp-container-apps.bicep`, `rbac.bicep` (details lines 423, 428-430) | Changes log line 33: "infra/modules/ai-foundry.bicep, mcp-container-apps.bicep, rbac.bicep, monitoring.bicep, infra/main.bicep, infra/main.parameters.json, infra/README.md, azure.yaml - Phase 8: author-only, undeployed Bicep modules and azd manifest..." | Met (and exceeded — `monitoring.bicep`, `main.bicep`, `main.parameters.json`, `infra/README.md`, `azure.yaml` were also added, consistent with the orchestrating `main.bicep` step 8.1 implies but the plan checklist text does not itemize) |
| Explicit author-only banner in each module (details "Explicitly comment in each module that it is author-only until gates clear") | Changes log line 33 references the banner; independently confirmed present in all four `infra/modules/*.bicep` files (`AUTHOR-ONLY / NOT DEPLOYED` banner, line 2 of each file), plus `infra/main.bicep` (lines 1-9), `azure.yaml` (lines 2-9), and `infra/README.md` | Met |
| No hard-coded tenant/subscription/credential/endpoint values (details success criteria) | Independently grepped `infra/**` for `tenantId`, `subscriptionId`, `clientSecret`, `password`, `ApiKey`, and GUID patterns. Matches found are all Azure built-in RBAC role-definition GUIDs (`rbac.bicep` lines 27-29, `mcp-container-apps.bicep` line 61 — AcrPull role) and the connection `authType: 'ApiKey'` enum literal in `ai-foundry.bicep` line 115 (a schema discriminator, paired with a parameterized `applicationInsightsConnectionString`, not a literal secret). No tenant ID, subscription ID, or literal credential found. | Met |
| Step 8.2 — `bicep build` lint/compile only, no apply command (plan line 146; details lines 444-450) | Changes log line 58: "No deploy/provision/apply command was run; only `az bicep build` (offline compile) was used for validation." Release Summary (unnumbered, near end of file): "`az bicep build` → **5/5 files compiled** (2 non-blocking carried-over warnings in mcp-container-apps.bicep/main.bicep)." | Met |

## Independent Re-Verification

Ran `az bicep build --file infra/main.bicep --outfile <temp>` from the repo root:

```text
WARNING: C:\src\...\infra\modules\mcp-container-apps.bicep(118,26) : Warning BCP318: ... may be null ...
WARNING: C:\src\...\infra\modules\mcp-container-apps.bicep(172,26) : Warning BCP318: ... may be null ...
EXITCODE:0
```

This independently confirms: (a) compile succeeds (exit code 0), and (b) exactly two non-blocking `BCP318` nullable warnings in `mcp-container-apps.bicep`, matching the changes log's claim of "two non-blocking BCP318 nullable-warning lint messages in mcp-container-apps.bicep/main.bicep verbatim from the sibling reference module" (changes log line 58) and the Release Summary's "2 non-blocking carried-over warnings in mcp-container-apps.bicep/main.bicep" almost exactly (the warnings physically live in `mcp-container-apps.bicep`; `main.bicep` is where the module is referenced/composed, which is a reasonable way to describe where the diagnostic surfaces during a full-graph `main.bicep` build).

## Deploy/Provision/Apply Command Check (hard requirement)

Searched the changes log for `azd provision`, `azd deploy`, `az deployment group create`, `deploy(`, `provision` (regex, case-insensitive):

* Line 58: "No deploy/provision/apply command was run; only `az bicep build` (offline compile) was used for validation." — a negation, not an execution record.
* Release Summary (near line 62-64): "...was built and validated with no live Azure dependency and no deploy/provision/apply command ever executed." — a negation.

No terminal transcript, command log, or narrative text anywhere in the changes log records an actual `azd provision`, `azd deploy`, `azd up`, or `az deployment group create` invocation. All infra `.bicep`/`.json`/`.yaml` files carry explicit `AUTHOR-ONLY / NOT DEPLOYED` banners at their top (verified directly in `infra/main.bicep` lines 1-9, `azure.yaml` lines 2-9, and all four `infra/modules/*.bicep` files, line 2). `infra/README.md` (lines 1-3, 44-48) independently states: "Status: **authored, not deployed, not reviewed.**" and "No `azd provision`, `azd deploy`, `azd up`, `az deployment group create`, or any other apply/provision command was executed against these templates or the root `azure.yaml`."

**Conclusion: No evidence of any actual deployment/provision/apply attempt was found. The hard requirement is satisfied.**

## Gate Documentation Check (G2/G3/G6)

* Plan line 146 explicitly names all three gates as blocking Step 8.2's apply commands.
* Details lines 423, 444-450 repeat the same three gates for both steps.
* `infra/main.bicep` lines 2-6, `azure.yaml` lines 3-8, and all four `infra/modules/*.bicep` banners (line 2-6 pattern) cite G2 (platform/security), G3 (reproducible compatibility), and G6 (regulatory/privacy) by name.
* `infra/README.md` lines 5-15 spells out each gate's meaning (network/ingress/identity for G2; pinned model/SDK versions for G3; synthetic-data-only/no-PII for G6) and lines 44-48 restate the pre-deploy checklist gating on all three.
* Changes log line 33 also cites "Gates G2/G3/G6" for the Phase 8 artifact set.

**Gates G2, G3, and G6 are explicitly and consistently documented as blocking across the plan, details, changes log, and the infra source/README themselves.**

## Cross-Check Against Research Document

* Research "Configuration Examples" (research lines ~201, `infra/ (approved isolated sandbox)`) and the surrounding constraint "No tenant/subscription identifiers, credentials, endpoints, model deployment names, or package versions are prescribed before approved discovery and compatibility checks" — matches the implementation: `main.bicep` params for `modelDeploymentName`, `modelName`, `modelVersion` are explicitly commented `Placeholder pending Gate G2/G3 sign-off` (main.bicep lines 24-33), and no subscription/tenant/credential literal exists anywhere in `infra/`.
* Risk Register RR6 (framework/dependency version drift, gate G3) and RR7 (private networking/ingress ambiguity, gate G2) — details file "Discrepancy references" (line ~436-438, inside Step 8.1) explicitly cites both RR6 and RR7 as addressed by deferring apply/deploy. Confirmed consistent.
* Risk Register RR5 (cost/quota exhaustion at up-to-75-participant scale, tracked under G2) — `main.bicep` includes an `endsWith(environmentName, '-staging')` branch adjusting `modelSkuCapacity` and `mcpNamePrefix` (lines 39, 71) to keep staging/production tool apps distinct, a reasonable partial mitigation, though full resolution remains correctly deferred to G2.
* Planning log DR-01 (gate-numbering mismatch between the primary research document's G1-G6 and the platform-and-scenario-decision subagent's G1-G8) is rated Low impact and explicitly scoped as not affecting any plan content, since the plan only ever references the primary document's G1-G6 labels — consistent with what Phase 8 actually cites (G2/G3/G6 only, matching the primary document's numbering). No discrepancy specific to Phase 8's infrastructure content was found in DD-01, DR-02, or DR-03 (all three log entries concern lab count, PDF timing conflicts, and unexpanded acronyms — unrelated to infra scaffolding).

No discrepancy between the research document's infrastructure guidance and the Phase 8 implementation was found.

## Findings

### Critical

None found.

### Major

None found.

### Minor

* **M1 — Changes log Phase 8 narrative bullet (line 58) attributes both BCP318 warnings to "mcp-container-apps.bicep/main.bicep," but the independent `az bicep build` re-run shows both warnings physically reported at `mcp-container-apps.bicep(118,26)` and `mcp-container-apps.bicep(172,26)` — neither warning's file/line locator names `main.bicep` directly.** This is a benign imprecision (the diagnostics do surface while compiling through `main.bicep`'s module graph, and the Release Summary's phrasing is the same), not a functional defect — the warning count (2) and non-blocking nature match exactly. No action required beyond this note.
* **M2 — Step 8.1's plan checklist text ("Adapt Bicep modules... without deploying") only names three files (`ai-foundry.bicep`, `mcp-container-apps.bicep`, `rbac.bicep`), while the changes log and repository show five additional artifacts (`monitoring.bicep`, `main.bicep`, `main.parameters.json`, `infra/README.md`, `azure.yaml`).** This is additive scope beyond the literal checklist wording, but it is consistent with the details file's own file list expectations for an orchestrating template (`main.bicep` necessarily references `monitoring.bicep` and needs `main.parameters.json`) and does not contradict any success criterion. Documented as a deviation, not a gap.

## Coverage Assessment

Phase 8 is **fully implemented and verifiable**:

* Both checklist steps (8.1, 8.2) have direct, verifiable evidence in the changes log.
* All four required Bicep modules plus the orchestrating `main.bicep`, parameters file, README, and `azure.yaml` exist on disk with `AUTHOR-ONLY / NOT DEPLOYED` banners naming G2/G3/G6.
* Independent `az bicep build` re-run confirms compile success (exit code 0) with exactly the two non-blocking warnings the changes log claims — no undisclosed errors.
* No hard-coded tenant/subscription/credential/endpoint values were found in any infra file.
* No evidence anywhere in the changes log, infra source, or README of an actual `azd provision`/`azd deploy`/`az deployment group create` execution — the hard "no deploy" requirement is satisfied.
* Gates G2/G3/G6 are consistently and explicitly documented as blocking across every artifact touched by this phase.
* No planning-log discrepancy (DD-01, DR-01, DR-02, DR-03) surfaces a Phase-8-specific infrastructure gap; DR-01 (gate-numbering mismatch) is explicitly scoped as not affecting the plan's G1-G6 usage, which Phase 8 follows correctly.

**Overall phase status: Passed**, with two Minor, non-blocking documentation-precision notes (M1, M2).

## Recommended Next Validations (not performed in this session)

* Validate Phase 9 (Final Validation) directly, since its Step 9.1 depends on Phase 8's `bicep build` sweep and the Release Summary's aggregate test/lint counts (49 pytest, 5/5 bicep, 12/12 eval, 24/24 disclaimer sweep) were only spot-checked for the Bicep portion in this session.
* Independently re-run the full `pytest` sweep and `python eval/evaluation_gate.py` referenced in the Release Summary, since this validation session only re-ran `az bicep build`.
* Confirm with a markdown linter (once registry access is restored, per the changes log's repeated "Markdown lint was skipped" notes) that no lint errors exist in the Phase 6/9 authored Markdown, since this was never run in-repo.

## Clarifying Questions

None — all evidence needed to validate Phase 8 was available in the plan, details, changes log, research document, planning log, and the live repository/CLI re-check.
