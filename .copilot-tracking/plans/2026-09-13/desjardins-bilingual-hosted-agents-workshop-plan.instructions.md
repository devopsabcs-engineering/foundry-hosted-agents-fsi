---
applyTo: '.copilot-tracking/changes/2026-09-13/desjardins-bilingual-hosted-agents-workshop-changes.md'
---
<!-- markdownlint-disable-file -->
# Implementation Plan: Desjardins Bilingual Hosted Agents Workshop

## Overview

Build a bilingual (English/French) hands-on workshop, adapted from the sibling `foundry-hosted-agents` Air Canada threat-assessment labs, around a synthetic Ontario auto-insurance quote-preparation scenario with a deterministic calculator and a mandatory, separately persisted employee-approval gate before any applicant-facing preview.

## Objectives

### User Requirements

* Do something similar to the sibling `foundry-hosted-agents` repository, adapted to Desjardins, using hosted agents and Microsoft Foundry — Source: original user request in conversation.
* Deliver a bilingual (English/French) workshop, as with the sibling repository — Source: original user request in conversation.
* Use a different, more FSI-fitting use case specific to Desjardins, grounded in `assets/Hackathon - Rencontre prep des coachs.pdf` — Source: original user request in conversation.

### Derived Objectives

* Select the synthetic Ontario auto-insurance quote-preparation scenario with mandatory employee approval — Derived from: research .copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md, Selected Recommendation (lines 26-31), grounded in PDF pp. 8-9.
* Keep the sibling's LangGraph orchestration pattern and lab arc conceptually, rewriting all domain content, prompts, fixtures, and tests — Derived from: research, Implementation Patterns (lines 130-145) and Selective Reuse (lines 256-266).
* Add a tenth lab (teardown/cost-cleanup) beyond the nine originally researched, because the sibling repository now ships `lab-09-teardown.md` (EN and FR) that did not exist when the research was written — Derived from: live repository inspection during planning (see Planning Log DD-01).
* Treat MCP deployment, hosted-agent deployment, and infrastructure apply as gated, author-only work until Gates G2 (platform/security), G3 (reproducible compatibility), and G6 (regulatory/privacy sign-off) are cleared by their owners — Derived from: research, Potential Next Research (lines 32-41) and Risk Register (lines 288-308).
* Build and validate an offline vertical slice (fixtures, calculator, approval repository, state machine) before any MCP or hosted-agent code, so the riskiest business logic (arithmetic, self-approval prevention, revision invalidation) is testable without any Azure dependency — Derived from: research, Actionable Implementation Sequence step 3 (lines 282).

## Context Summary

### Project Files

* .copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md - Primary, adversarially reviewed research document; authoritative source for scope, architecture, curriculum, and risk register.
* .copilot-tracking/research/subagents/2026-09-13/air-canada-workshop-research.md - Line-cited analysis of the sibling repository's reusable architecture and lab structure.
* .copilot-tracking/research/subagents/2026-09-13/desjardins-customer-evidence-research.md - Page-cited extraction of the Desjardins PDF (scenario evidence, judging criteria, constraints).
* .copilot-tracking/research/subagents/2026-09-13/platform-and-scenario-decision-research.md - Full JSON Schema, fixture, state machine, and 21 acceptance examples for the quote-preparation contract.
* README.md - Current repository README; a one-line placeholder title, to be expanded.
* assets/Hackathon - Rencontre prep des coachs.pdf - Source customer evidence document (16 pages).

### Reference Files (sibling repository, for adaptation only, not to be copied wholesale)

* C:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents\docs\labs\lab-00-setup.md through lab-09-teardown.md - Ten English labs to adapt (structure, not content).
* C:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents\docs\fr\labs\lab-00-setup.md through lab-09-teardown.md - Ten French labs, structurally paired with the English set.
* C:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents\src\threat-assessment-agent\graph.py, state.py, toolbox.py, main.py, runtime_evidence.py - LangGraph supervisor/specialist pattern to adapt for the quote-preparation agent.
* C:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents\mcp\defender-server, anomaly-server - Reference pattern for building the application-server and rulebook-server as read-only FastMCP services.
* C:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents\infra\modules\ai-foundry.bicep, mcp-container-apps.bicep, rbac.bicep, monitoring.bicep - Bicep modules to adapt (author only; do not deploy until gates clear).
* C:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents\eval\golden-dataset.jsonl, evaluation_gate.py, deterministic-tests\checks.py - Evaluation harness pattern to adapt for arithmetic, approval, injection, and bilingual-parity checks.
* C:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents\scripts\build-workshop-deck.js - Shared bilingual deck generator to adapt.

### Standards References

* c:\Users\emknafo\.vscode\extensions\ise-hve-essentials.hve-core-3.2.2\.github\instructions\hve-core\markdown.instructions.md — Applies to all new/edited Markdown labs, README, and index files.
* c:\Users\emknafo\.vscode\extensions\ise-hve-essentials.hve-core-3.2.2\.github\instructions\hve-core\writing-style.instructions.md — Applies to all Markdown learner-facing content (voice, tone, language).

## Implementation Checklist

Note on `parallelizable`: the marker describes whether a phase's files can be authored alongside sibling phases without shared-file or shared-state conflicts once that phase's own upstream prerequisite phase has completed. It does not imply that steps within a phase are unordered; steps inside a phase may still be sequential (see each step's Dependencies in the details file).

### [ ] Implementation Phase 1: Repository and Bilingual Site Scaffold

<!-- parallelizable: true -->

* [ ] Step 1.1: Create the top-level directory structure and expand the root README
  * Details: .copilot-tracking/details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md (Lines 12-42)
* [ ] Step 1.2: Create the bilingual Jekyll site skeleton (docs/index.md, docs/fr/index.md, shared config)
  * Details: .copilot-tracking/details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md (Lines 43-67)
* [ ] Step 1.3: Validate phase changes
  * Run markdown lint on all new Markdown files; confirm docs/ and docs/fr/ are structurally paired (same file names)
  * Skip build/test commands here; no code exists yet in this phase

### [ ] Implementation Phase 2: Synthetic Fixtures, JSON Schema, and Deterministic Calculator

<!-- parallelizable: true -->

* [ ] Step 2.1: Author the synthetic fixture set and JSON Schema (draft-07) for the quote-preparation contract
  * Details: .copilot-tracking/details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md (Lines 79-101)
* [ ] Step 2.2: Implement the pure deterministic calculator and its unit tests
  * Details: .copilot-tracking/details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md (Lines 102-122)
* [ ] Step 2.3: Validate phase changes
  * Run the calculator unit tests (pytest)
  * Validate every fixture against the JSON Schema

### [ ] Implementation Phase 3: Approval Repository and State Machine

<!-- parallelizable: false -->

* [ ] Step 3.1: Implement the SQLite-backed ApprovalRepository with the full state machine
  * Details: .copilot-tracking/details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md (Lines 133-154)
* [ ] Step 3.2: Implement concurrency, idempotency, and actor-authorization tests
  * Details: .copilot-tracking/details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md (Lines 155-176)
* [ ] Step 3.3: Validate phase changes
  * Run the approval-repository unit and concurrency tests (pytest)
  * Confirm self-approval and forged-actor attempts fail (traces to research V09, V11)

### [ ] Implementation Phase 4: Read-Only MCP Services

<!-- parallelizable: true -->

* [ ] Step 4.1: Implement application-server (get_application) as a read-only FastMCP service
  * Details: .copilot-tracking/details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md (Lines 186-207)
* [ ] Step 4.2: Implement rulebook-server (get_rulebook) as a read-only FastMCP service
  * Details: .copilot-tracking/details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md (Lines 208-228)
* [ ] Step 4.3: Validate phase changes
  * Run MCP server unit/smoke tests locally (no hosted deployment); confirm no write tools are exposed and unknown fixture/rulebook IDs are rejected

### [ ] Implementation Phase 5: Hosted LangGraph Quote-Preparation Agent (local, unhosted)

<!-- parallelizable: false -->

* [ ] Step 5.1: Adapt the supervisor/specialist LangGraph topology for intake, reference lookup, and composition
  * Details: .copilot-tracking/details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md (Lines 238-262)
* [ ] Step 5.2: Wire the agent to the Phase 4 MCP tools and the Phase 2/3 calculator and approval repository, with bounded applicant-facing output
  * Details: .copilot-tracking/details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md (Lines 263-282)
* [ ] Step 5.3: Validate phase changes
  * Run the local agent test harness against synthetic fixtures (no Azure calls); do not attempt hosted deployment in this phase (Gate G2/G3/G6 not cleared)

### [ ] Implementation Phase 6: Bilingual Lab Curriculum and Shared Deck

<!-- parallelizable: true -->

* [ ] Step 6.1: Author the ten English labs (00 through 09) adapted from the sibling structure
  * Details: .copilot-tracking/details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md (Lines 292-321)
* [ ] Step 6.2: Author the ten paired French labs with reviewed, natural French and matching filenames
  * Details: .copilot-tracking/details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md (Lines 322-341)
* [ ] Step 6.3: Adapt the shared bilingual deck generator script
  * Details: .copilot-tracking/details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md (Lines 342-362)
* [ ] Step 6.4: Validate phase changes
  * Confirm EN/FR lab file-name and exercise-count parity; run markdown lint

### [ ] Implementation Phase 7: Evaluation Suite

<!-- parallelizable: true -->

* [ ] Step 7.1: Author the paired EN/FR golden dataset (minimum six business fixtures plus fault cases)
  * Details: .copilot-tracking/details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md (Lines 373-391)
* [ ] Step 7.2: Adapt the deterministic checks and evaluation gate script
  * Details: .copilot-tracking/details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md (Lines 392-411)
* [ ] Step 7.3: Validate phase changes
  * Run the deterministic checks and evaluation gate locally against Phase 2/3/4/5 code

### [ ] Implementation Phase 8: Infrastructure Scaffolding (author only, gated)

<!-- parallelizable: false -->

* [ ] Step 8.1: Adapt Bicep modules for the read-only MCP services and hosted agent, without deploying
  * Details: .copilot-tracking/details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md (Lines 421-443)
* [ ] Step 8.2: Validate phase changes
  * Run `bicep build` (or `az bicep build`) for lint/compile checking only; do not run `azd provision`, `azd deploy`, or any apply command until Gates G2, G3, and G6 are explicitly cleared by their owners

### [ ] Implementation Phase 9: Final Validation

<!-- parallelizable: false -->

* [ ] Step 9.1: Run full project validation
  * Execute all Python test suites (pytest) across calculator, approval repository, MCP servers, and agent test harness
  * Execute `bicep build` across all modified Bicep modules
  * Execute markdown lint across all new/edited Markdown files
  * Search docs/, docs/fr/, and any applicant/reviewer templates for the required synthetic-only/non-binding/no-regulatory-endorsement disclaimer string in both languages; fail this check if any applicant-facing or reviewer-facing file is missing it
* [ ] Step 9.2: Fix minor validation issues
  * Iterate on lint errors, type errors, and test failures directly when corrections are straightforward
* [ ] Step 9.3: Report blocking issues
  * Document any issue requiring additional research or an unresolved gate (G1-G6)
  * Provide next steps and recommended follow-up planning instead of attempting large-scale fixes here

## Planning Log

See .copilot-tracking/plans/logs/2026-09-13/desjardins-bilingual-hosted-agents-workshop-log.md for discrepancy tracking, implementation paths considered, and suggested follow-on work.

## Dependencies

* Python 3.11+ with pytest, for the calculator, approval repository, MCP servers, and evaluation suite
* Node.js, for the shared bilingual deck generator script (PptxGenJS-based, adapted from the sibling)
* LangGraph and the Azure OpenAI/LangChain adapters used by the sibling agent, subject to the version-pin verification required by Gate G3
* Bicep CLI, for lint/compile-only validation of infrastructure modules in Phase 8
* Jekyll (Ruby, Bundler) with the Just the Docs remote theme, matching the sibling's docs/ site, for local site preview (optional, not required for file authoring)
* Approved Foundry project, model deployment, and network topology (Gate G2), required only before any hosted deployment or infrastructure apply, not for Phases 1-7 or the author-only, no-deploy work in Phase 8

## Success Criteria

* Offline vertical slice (fixtures, calculator, approval repository, state machine) passes all unit tests with no Azure dependency — Traces to: research Actionable Implementation Sequence step 3 (line 282).
* Calculator arithmetic is exact and provenance-traceable; missing/unsupported/unavailable evidence never yields an invented amount — Traces to: research Validation section (lines 317-327).
* Self-approval, forged-actor, and unauthorized-preview attempts fail in tests — Traces to: research Risk Register RR2 and RR4 (lines 288-308).
* MCP services expose only get_application and get_rulebook, reject unknown IDs, and contain no write tools — Traces to: research Implementation Patterns (lines 130-145).
* Ten EN and ten FR labs exist with matching filenames and exercise counts, reflecting the sibling repository's current (post-teardown-lab) structure — Traces to: Planning Log DD-01.
* At least six paired EN/FR business fixtures plus reusable fault cases pass the deterministic evaluation gate — Traces to: research Validation section (lines 317-327).
* No infrastructure apply/deploy command is executed before Gates G2, G3, and G6 are explicitly cleared — Traces to: research Risk Register (lines 288-308) and Potential Next Research (lines 32-41).
* Every applicant-facing and reviewer-facing artifact carries an explicit non-binding, non-regulatory, synthetic-only disclaimer in both languages, verified by the Phase 9 disclaimer search — Traces to: research Regulatory and Privacy Boundary (lines 114-118) and Risk Register RR2/RR3.
* Reused vendored build tooling (Jekyll "Just the Docs" theme, PptxGenJS) passes a license check before reuse, and no sibling-specific branding, screenshots, or run evidence are carried over — Traces to: research Risk Register RR12 (lines 288-308).
* The default learner path is Copilot-free, with any authoring-assistance tooling disclosed rather than implied as learner-facing — Traces to: research Risk Register RR10 (lines 288-308).
