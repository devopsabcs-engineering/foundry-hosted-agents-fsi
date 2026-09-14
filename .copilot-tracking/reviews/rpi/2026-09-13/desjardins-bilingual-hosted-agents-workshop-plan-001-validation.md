<!-- markdownlint-disable-file -->
# RPI Validation: Desjardins Bilingual Hosted Agents Workshop — Phase 1

**Phase validated**: Implementation Phase 1: Repository and Bilingual Site Scaffold
**Plan file**: .copilot-tracking/plans/2026-09-13/desjardins-bilingual-hosted-agents-workshop-plan.instructions.md (heading `### [x] Implementation Phase 1: Repository and Bilingual Site Scaffold`, plan lines 57-68)
**Changes log**: .copilot-tracking/changes/2026-09-13/desjardins-bilingual-hosted-agents-workshop-changes.md
**Research document**: .copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md
**Details file**: .copilot-tracking/details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md (Lines 12-67)
**Planning log**: .copilot-tracking/plans/logs/2026-09-13/desjardins-bilingual-hosted-agents-workshop-log.md
**Validation date**: 2026-09-13

## Scope

Phase 1 has three claimed-complete steps:

* Step 1.1: Create the top-level directory structure and expand the root README.
* Step 1.2: Create the bilingual Jekyll site skeleton (docs/index.md, docs/fr/index.md, shared config).
* Step 1.3: Validate phase changes (markdown lint, structural EN/FR parity).

## Step 1.1: Directory structure and README

### Evidence checked

* Directory existence verified directly on disk (not just claimed in the changes log): [src/quote-preparation-agent](../../../../src/quote-preparation-agent), [mcp/application-server](../../../../mcp/application-server), [mcp/rulebook-server](../../../../mcp/rulebook-server), [apps/workshop](../../../../apps/workshop), [data/synthetic](../../../../data/synthetic), [eval](../../../../eval), [infra](../../../../infra), [scripts](../../../../scripts), [docs/fr](../../../../docs/fr) — all 9 directory paths named in the details file (Lines 16-24) exist.
* [README.md](../../../../README.md) (lines 1-58): expanded from the prior one-line placeholder into a project overview.
  * Lines 16-19: states the synthetic-only/non-binding/no-regulatory-endorsement boundary — satisfies the details file's Step 1.1 success criterion (details Lines 32-34).
  * Lines 21-26 ("Learner path"): states the default Copilot-free learner path with disclosed authoring assistance — satisfies details Lines 35 and addresses Risk Register RR10 as claimed.

### Finding: Directory-count wording (already self-disclosed, no new issue)

* Severity: **None (informational only)**
* The plan's Step 1.1 success criterion says "All nine directories exist" (details Lines 32), while the Files list under Step 1.1 (details Lines 18-26) enumerates 8 new directories plus the pre-existing `docs/`. The changes log's "Additional or Deviating Changes" section (Changes log, "Phase 1 created 8 new top-level directories...") already discloses this exact wording gap and correctly notes it is not a functional deviation. Verified consistent with the actual repository state (9 directory paths total, 8 newly created, `docs/` pre-existing). No further action needed.

## Step 1.2: Bilingual Jekyll site skeleton

### Evidence checked

* [docs/index.md](../../../../docs/index.md) (lines 1-58) and [docs/fr/index.md](../../../../docs/fr/index.md) (lines 1-37): both exist, are structurally paired (same filename `index.md` in `docs/` and `docs/fr/`), and contain reciprocal navigation — `docs/index.md` line 15 links `🇫🇷 [Version française](fr/)`, `docs/fr/index.md` line 9 links `🇬🇧 [English version](../)`. Satisfies the details file's Step 1.2 success criteria (details Lines 71-74).
* [docs/_config.yml](../../../../docs/_config.yml) (lines 1-24) and [docs/Gemfile](../../../../docs/Gemfile) (lines 1-3): adapted Jekyll config and Ruby/Jekyll dependency manifest, present and structurally consistent with the sibling repository's pattern per the details file (Lines 47-48).
* No airline branding, screenshots, or Air Canada-specific content found in any of the four Phase 1 docs files — consistent with the Selective Reuse exclusions cited in research (research Lines 256-266, "Exclude or defer": airline branding, screenshots, historical run evidence).

### Finding 1 (Major): Just the Docs theme license check not evidenced anywhere

* Severity: **Major**
* The details file's Step 1.2 description explicitly requires: "Before reuse, confirm the Just the Docs theme's license permits this redistribution (Risk Register RR12)" (details, Step 1.2 body, line 45), and lists as an explicit success criterion: "The Just the Docs theme license has been checked and permits this reuse before docs/_config.yml references it" (details line 59). The Discrepancy references for this step explicitly tie this check to closing Risk Register RR12 (details line 54).
* [docs/_config.yml](../../../../docs/_config.yml) line 3 does reference `remote_theme: just-the-docs/just-the-docs`, meaning the precondition step (the license check) was required before this file could be authored as written.
* No evidence of this check exists anywhere in the available artifacts:
  * The changes log's "Additional or Deviating Changes" section for Phase 1 (three bullets) does not mention a license check or its outcome.
  * The planning log's Discrepancy Log (DR-01, DR-02, DR-03) and Plan Deviations (DD-01) do not reference this item at all — RR12 is only echoed generically as a research risk (research Lines 305), never resolved or dismissed in the planning log.
  * No other file in `.copilot-tracking/` records this check having been performed.
* Impact: In fact, the "Just the Docs" Jekyll theme is publicly known to be MIT-licensed, which would satisfy the redistribution requirement in practice — so the real-world risk is low. However, the plan's own success criterion and its explicit risk-traceability requirement (RR12) were not verifiably satisfied or documented, unlike every other Phase 1 deviation, which the implementer did document. This is a process gap: an explicit, risk-tied verification step appears to have been silently skipped rather than performed-and-recorded or explicitly deferred.
* Recommendation: Add a one-line note to the changes log or planning log confirming the Just the Docs MIT license was checked and permits this reuse, closing RR12 for Phase 1 (or, if not actually checked, perform and record the check).

## Step 1.3: Validate phase changes

### Evidence checked

* The plan's Step 1.3 calls for two actions: (a) run markdown lint on all new Markdown files, (b) confirm `docs/` and `docs/fr/` are structurally paired.
* (a) Markdown lint: **explicitly skipped**, and this is transparently disclosed — changes log "Additional or Deviating Changes": "Markdown lint (Step 1.3) was skipped: no markdownlint tool is installed locally and the environment has remote npm package fetches disabled. Directory/file structure and reciprocal links were confirmed manually instead." Corroborated by Planning Log WI-12, which tracks re-running markdownlint as a follow-up once registry access is available.
* (b) Structural parity: verified directly — `docs/` and `docs/fr/` both contain `index.md` (confirmed by direct listing); the later-populated `labs/` subdirectories (Phase 6) also pair correctly, though that is outside Phase 1's own scope.

### Finding 2 (Minor): Markdown lint never executed for Phase 1's Markdown files

* Severity: **Minor**
* Because the lint step could not run (tooling/registry constraint), no automated verification exists that `README.md`, `docs/index.md`, `docs/fr/index.md` conform to the required [markdown.instructions.md](../../../../../.vscode/extensions/ise-hve-essentials.hve-core-3.2.2/.github/instructions/hve-core/markdown.instructions.md) standard referenced in the plan's Standards References section (plan, Standards References). This is a known, already-disclosed, and tracked limitation (Planning Log WI-12) rather than a hidden gap, so it is graded Minor rather than Major. A quick manual read of the three files did not surface obvious markdownlint violations (heading structure, single H1 via front matter title, reasonable line content), but this was not exhaustively verified against every markdownlint rule.

## Additional Cross-Check: Stale `.gitkeep` artifacts / changes-log completeness

### Finding 3 (Minor): `.gitkeep` placeholders from Phase 1 are inconsistently tracked and two remain stale

* Severity: **Minor**
* The changes log's "Added" section for Phase 1 lists only 5 `.gitkeep` placeholders (`src/quote-preparation-agent/.gitkeep`, `mcp/application-server/.gitkeep`, `mcp/rulebook-server/.gitkeep`, `infra/.gitkeep`, `scripts/.gitkeep`), but the "Removed" section later references removing `apps/workshop/.gitkeep`, `data/synthetic/.gitkeep`, and `eval/.gitkeep` (Phases 2 and 7) — three placeholders that were evidently created in Phase 1 (since Phase 1 created those directories) but were never listed under Phase 1's "Added" section. This is a minor changes-log completeness gap, not a functional defect.
* More materially: direct directory listings confirm `infra/.gitkeep` and `scripts/.gitkeep` **still exist on disk** alongside the real content added in later phases (`infra/main.bicep`, `infra/modules/`, `infra/README.md` from Phase 8; `scripts/build-workshop-deck.js` from Phase 6), whereas every other directory's placeholder (`apps/workshop`, `data/synthetic`, `mcp/application-server`, `mcp/rulebook-server`, `src/quote-preparation-agent`, `eval`) was correctly removed once populated. The changes log's "Removed" section does not account for these two, so this is both an undisclosed cleanup gap and a minor changes-log accuracy issue.
* Impact: cosmetic only — the stray `.gitkeep` files do not affect functionality, tests, or builds. Recommended cleanup: delete `infra/.gitkeep` and `scripts/.gitkeep` and update the changes log's Removed section accordingly.

## Planning Log Cross-Check

* DD-01 (ten labs vs. nine labs) is scoped to Phase 6 (lab curriculum), not Phase 1; no conflict with Phase 1 evidence.
* DR-01, DR-02, DR-03 (gate numbering, PDF timing conflicts, LIDIA/PDM acronyms) are not Phase-1-relevant; no conflict with Phase 1 evidence.
* No DD-*/DR-* entry addresses the Just the Docs license-check gap (Finding 1) or the stale `.gitkeep` files (Finding 3) — both are net-new observations from this validation, not previously captured discrepancies.

## Coverage Assessment

All three Phase 1 checkboxes have corresponding, verifiable evidence in the changes log and on disk:

* Step 1.1 (directories + README): **Fully implemented**, one already-disclosed wording nuance (directory count), no new issue.
* Step 1.2 (bilingual site skeleton): **Implemented**, but one explicit success criterion (theme license check) has no evidence of having been performed or recorded — Major finding.
* Step 1.3 (validation): **Partially implemented** — structural parity confirmed manually and correctly; markdown lint was skipped, transparently disclosed and tracked as follow-up work (WI-12) — Minor finding.

Overall Phase 1 completion is substantively real (all files/directories exist and match plan intent) but has one unresolved Major documentation/process gap (license check) and two Minor gaps (lint skip already tracked; stale `.gitkeep` cleanup untracked).

## Severity Summary

| Severity | Count | Finding(s) |
| --- | --- | --- |
| Critical | 0 | — |
| Major | 1 | Finding 1: Just the Docs theme license check not evidenced |
| Minor | 2 | Finding 2: Markdown lint skipped (already disclosed/tracked); Finding 3: stale `.gitkeep` files in `infra/` and `scripts/` plus incomplete changes-log Added/Removed accounting |

## Clarifying Questions

* Was the Just the Docs theme license actually checked out-of-band (for example, verbally confirmed or checked in a prior session) and simply not recorded, or was this step genuinely skipped? If skipped, should it be performed now before any further public/pilot use of the docs site (relevant to Gate G5/WI-09)?
* Should `infra/.gitkeep` and `scripts/.gitkeep` be deleted now as trivial cleanup, or is there a reason (for example, guaranteeing the directories survive an empty git state in some tooling path) they were intentionally left in place?

## Recommended Next Validations

* [ ] Validate Phase 2 (Synthetic Fixtures, JSON Schema, and Deterministic Calculator) against its changes log entries and the platform-and-scenario-decision subagent research.
* [ ] Validate Phase 3 (Approval Repository and State Machine), including the self-approval/forged-actor test evidence referenced in the plan (traces to research V09, V11).
* [ ] Independently confirm the Just the Docs theme's actual license terms (MIT) against the redistribution use in this repository, and record the outcome in the planning log to close RR12 for Phase 1.
