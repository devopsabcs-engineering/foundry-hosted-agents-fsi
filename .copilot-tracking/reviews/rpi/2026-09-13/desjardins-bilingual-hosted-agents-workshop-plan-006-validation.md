<!-- markdownlint-disable-file -->
# RPI Validation: Desjardins Bilingual Hosted Agents Workshop — Phase 6

**Plan**: .copilot-tracking/plans/2026-09-13/desjardins-bilingual-hosted-agents-workshop-plan.instructions.md
**Phase Validated**: Implementation Phase 6: Bilingual Lab Curriculum and Shared Deck
**Changes Log**: .copilot-tracking/changes/2026-09-13/desjardins-bilingual-hosted-agents-workshop-changes.md
**Research Document**: .copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md
**Details File**: .copilot-tracking/details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md
**Planning Log**: .copilot-tracking/plans/logs/2026-09-13/desjardins-bilingual-hosted-agents-workshop-log.md
**Validation Date**: 2026-09-13

## Scope

Phase 6 checklist items validated (plan lines 115-125):

* Step 6.1: Author the ten English labs (00 through 09).
* Step 6.2: Author the ten paired French labs.
* Step 6.3: Adapt the shared bilingual deck generator script.
* Step 6.4: Validate phase changes (EN/FR parity, markdown lint, deck smoke check).

## Plan-Item-to-Changes Comparison

| Plan item | Changes log evidence | Status |
| --- | --- | --- |
| Step 6.1 — ten EN labs | `docs/labs/index.md, docs/labs/lab-00-setup.md through lab-09-teardown.md (10 files) - Phase 6` | Files exist (count correct); **content/topic mapping differs from the plan's named files** (see Finding F1) |
| Step 6.2 — ten paired FR labs | `docs/fr/labs/index.md, docs/fr/labs/lab-00-setup.md through lab-09-teardown.md (10 files) - Phase 6` | Files exist; filenames and exercise counts match EN 1:1 |
| Step 6.3 — deck generator | `scripts/build-workshop-deck.js, package.json - Phase 6` | File exists; PPTX build unverified (disclosed); license-check success criterion undocumented (see Finding F3) |
| Step 6.4 — validate phase | Not a file-producing step; validated via "Additional or Deviating Changes" narrative | Partially evidenced (see Finding F2) |

## Evidence Verified

### File inventory (10 EN + 10 FR + 2 indexes)

* `docs/labs/` contains exactly 11 files: `index.md`, `lab-00-setup.md` … `lab-09-teardown.md` (verified via directory listing).
* `docs/fr/labs/` contains exactly 11 files, identical filenames to the EN set (verified via directory listing).
* Requirement "10 EN labs + 10 FR labs + 2 indexes" is **satisfied** on a pure file-count/filename basis.

### Disclaimer spot-check (10 files checked, exceeding the 6-file minimum)

Confirmed the required synthetic/non-binding disclaimer is present, in the correct language, in every file checked:

* [docs/labs/index.md](../../../../docs/labs/index.md#L9) (EN) — "Every fixture, rulebook, and calculator output across these labs is synthetic and non-binding..."
* [docs/fr/labs/index.md](../../../../docs/fr/labs/index.md#L9) (FR) — "Chaque donnée, règle et résultat de calcul de ces ateliers est synthétique et non contraignant..."
* [docs/labs/lab-00-setup.md](../../../../docs/labs/lab-00-setup.md#L9) (EN)
* [docs/fr/labs/lab-00-setup.md](../../../../docs/fr/labs/lab-00-setup.md#L9) (FR)
* [docs/labs/lab-03-approval-repository.md](../../../../docs/labs/lab-03-approval-repository.md#L9) (EN)
* [docs/fr/labs/lab-03-approval-repository.md](../../../../docs/fr/labs/lab-03-approval-repository.md#L9) (FR)
* [docs/labs/lab-08-evaluations.md](../../../../docs/labs/lab-08-evaluations.md#L9) (EN)
* [docs/fr/labs/lab-08-evaluations.md](../../../../docs/fr/labs/lab-08-evaluations.md#L9) (FR)
* [docs/labs/lab-09-teardown.md](../../../../docs/labs/lab-09-teardown.md#L9) (EN)
* [docs/fr/labs/lab-09-teardown.md](../../../../docs/fr/labs/lab-09-teardown.md#L9) (FR)

Wording is consistent across all EN files and consistent across all FR files (correct translation, not literal machine artifacts). No discrepancy found. This also corroborates the changes log's Phase 9 note that "all 24 learner-facing Markdown files carry the full disclaimer verbatim" (10 EN labs + 10 FR labs + 2 indexes + root README.md + the two docs/index.md pages referenced from Phase 1 = 24).

### EN/FR structural parity (Step 6.4 claim)

* Filenames: identical across `docs/labs/` and `docs/fr/labs/` (11/11 match).
* Exercise counts: verified per-file via heading search (`### Exercise` vs `### Exercice`) — 37 exercises total in each language set, with an identical per-lab distribution (4/4/4/4/3/3/4/4/3/4 across labs 00–09). **Parity claim is fully supported by evidence.**
* Every EN and FR file carries a reciprocal-language link (`🇫🇷 Version française` / `🇬🇧 English version`) and a `## Knowledge Check` section, satisfying the details file's structural requirement (objectives, numbered exercises, expected outputs, knowledge checks).

### Deck generator and pptxgenjs limitation (Planning Log / DD-flagged item)

* [scripts/build-workshop-deck.js](../../../../scripts/build-workshop-deck.js#L1-L12) and [package.json](../../../../package.json#L10-L12) exist; the script's internal `SLIDES` array (lines 74-238) enumerates labs 00-09 with titles that match the **actual** (not originally planned) lab topics, so the deck generator is internally self-consistent with what was actually authored.
* Changes log lines 56 and 60 and Planning Log WI-08/WI-12 consistently and accurately disclose: (a) `pptxgenjs` could not be installed (internal-feed-restricted npm registry), so only `node --check` syntax validation ran, not an actual PPTX build; (b) `npx markdownlint-cli2` fails with `EALLOWREMOTE` in this sandbox, so markdown lint was skipped in Phases 1, 6, and 9. Both limitations are **correctly and consistently disclosed** in the changes log and cross-referenced with matching Planning Log follow-up items (WI-08, WI-12). No discrepancy found on these two specific items — this is a correctly-handled known limitation, not a defect.

### Cross-check against research curriculum guidance

Research document lines 242-252 (Bilingual Workshop Adaptation table) specify a **nine**-lab curriculum: 00 Setup, 01 Architecture, 02 MCP tools, 03 Hosted deployment, 04 Invocation and review, 05 Evaluations, 06 CI/CD, 07 Troubleshooting and RBAC, 08 Readiness and demo. Planning Log DD-01 (lines 27-34) documents and justifies the plan's addition of a tenth lab (teardown), matching the sibling repository's current state. That specific deviation (count 9→10) is **properly disclosed**.

## Findings

### Critical

None.

### Major

**F1 — Undisclosed restructuring of lab topics/filenames (Step 6.1/6.2)**

The plan's Step 6.1 (details file lines 292-306) names ten specific files with specific topics, directly derived from the research curriculum table (research lines 242-252):

* `lab-01-architecture.md`, `lab-02-mcp-servers.md`, `lab-03-deploy-agent.md`, `lab-04-invoke-agent.md`, `lab-05-evaluations.md`, `lab-06-cicd.md`, `lab-07-troubleshooting-rbac.md`, `lab-08-production-readiness.md`.

The files actually created under [docs/labs/](../../../../docs/labs/) use entirely different filenames and topics for labs 01-08:

* `lab-01-fixtures-schema.md`, `lab-02-calculator.md`, `lab-03-approval-repository.md`, `lab-04-application-server.md`, `lab-05-rulebook-server.md`, `lab-06-agent-graph.md`, `lab-07-run-agent.md`, `lab-08-evaluations.md`.

Only `lab-00-setup.md` and `lab-09-teardown.md` match the plan's filenames. Confirmed by grep across `docs/labs/**` and `docs/fr/labs/**`: there is no lab content anywhere covering CI/CD (`lab-06-cicd`), troubleshooting/RBAC (`lab-07-troubleshooting-rbac`), hosted deployment (`lab-03-deploy-agent`), or production-readiness/demo (`lab-08-production-readiness`) topics — no "CI/CD", "RBAC", "troubleshoot", "production readiness", "one-pager", or "demo script" strings appear anywhere in the ten EN or ten FR lab files. The actual curriculum instead walks the real Phase 2/3/4/5/7 codebase directly (fixtures/schema, calculator, approval repository, application server, rulebook server, agent graph, run-the-agent, evaluations), which is arguably a reasonable adaptation of the details file's own Step 6.1 success criterion ("technical claims... match the actual Phase 2-5 implementation, not aspirational claims" — a real CI/CD or hosted-deployment lab would have been aspirational given Phase 8/9 gates remain uncleared) — but this substantial scope/topic change is **not recorded anywhere**: not in the changes log's "Additional or Deviating Changes" section (which for Phase 6 only mentions the `pptxgenjs`/markdown-lint limitations), and not in the Planning Log's Discrepancy Log (DD-01 addresses only the lab **count**, 9→10, not the topic remap for labs 01-08). A reviewer relying on the plan or details file to locate `lab-03-deploy-agent.md` or `lab-06-cicd.md` will not find them and has no pointer explaining why.

* Evidence: [details file lines 292-306](../../../../.copilot-tracking/details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md#L292-L306) (planned files) vs. [docs/labs/index.md lines 18-27](../../../../docs/labs/index.md#L18-L27) (actual files); changes log "Additional or Deviating Changes" section (no Phase 6 entry addresses this); Planning Log DD-01 (count only).
* Recommendation: Add a Planning Log discrepancy entry (e.g., DD-02) and a changes-log "Additional or Deviating Changes" bullet for Phase 6 documenting the topic-mapping change and its rationale (avoiding aspirational deployment/CI-CD/RBAC content while Gates G2/G3/G6 remain open), or restore the originally planned topics if this coverage is still required before Gate G5 (bilingual pilot, WI-05).

**F2 — Step 6.3 license-check success criterion not documented as completed or skipped**

The details file's Step 6.3 success criteria (lines 355-356) and the plan's Risk Register cross-reference (line 186) both require: "The PptxGenJS package license has been checked and permits this reuse" (addressing Risk Register RR12, unlicensed vendored dependencies). No evidence of this check — its outcome, or an explicit note that it was skipped — appears in the changes log, the Planning Log, or in [scripts/build-workshop-deck.js](../../../../scripts/build-workshop-deck.js) comments. The changes log documents the *install* failure (`pptxgenjs` could not be installed) but does not address the separate, explicitly required *license* check.

* Evidence: [details file lines 355-356](../../../../.copilot-tracking/details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md#L355-L356); changes log line 56 (addresses install failure only, not license check); no "license" string found anywhere in the changes log or the deck script.
* Recommendation: Record the PptxGenJS license (MIT, per public package metadata) and its compatibility with this repository's reuse in the changes log or Planning Log, closing out RR12 for this dependency, or explicitly note it as deferred alongside WI-08.

### Minor

**F3 — Markdownlint-cli2 sandbox limitation: correctly disclosed, no action needed**

Requested specifically for this validation: the markdownlint-cli2 `EALLOWREMOTE` sandbox limitation is consistently and accurately disclosed across the changes log ("Additional or Deviating Changes," lines mentioning Phases 1, 6, 9) and the Planning Log (WI-12). No discrepancy found; recorded here only to confirm the specific item requested was checked and found compliant.

## Coverage Assessment

* File-existence and naming-count requirements (10 EN + 10 FR + 2 indexes): **fully met**.
* Disclaimer presence/language correctness (spot-checked 10 of 22 lab/index files): **fully met**, no defects.
* EN/FR structural and exercise-count parity: **fully met**, verified with exact counts.
* Deck generator and known tooling limitations (pptxgenjs install, markdownlint-cli2): **correctly disclosed**, no defects beyond the license-check gap (F2).
* Fidelity to the plan's/research's originally specified lab **topics** for Step 6.1/6.2 (labs 01-08): **not met**, and the deviation is undisclosed (F1). The delivered curriculum is coherent and defensible on its own terms but diverges materially from what the plan and details file describe, without a discrepancy-log or changes-log record.

Overall Phase 6 completion is substantively real (all files exist, are bilingual, disclaimed, and internally consistent with the actual codebase) but the changes log's implicit claim that Step 6.1/6.2 followed the plan's specified file/topic list is inaccurate and undocumented.

## Clarifying Questions

* Was the topic restructuring (codebase-walkthrough curriculum instead of architecture/deploy/CI-CD/troubleshooting/readiness) an intentional design decision made during Phase 6 execution, or an oversight where the details file's Step 6.1 file list was not consulted? This determines whether the fix is "add a discrepancy-log entry" or "add the missing CI/CD, RBAC, deployment, and readiness lab content."
* Should the PptxGenJS license check (RR12) be performed now as a quick follow-up, or is it intentionally deferred alongside WI-08 (pptxgenjs install/PPTX generation)?
