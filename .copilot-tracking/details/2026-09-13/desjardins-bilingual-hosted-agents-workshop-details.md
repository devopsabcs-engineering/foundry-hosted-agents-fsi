<!-- markdownlint-disable-file -->
# Implementation Details: Desjardins Bilingual Hosted Agents Workshop

## Context Reference

Sources: .copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md; .copilot-tracking/research/subagents/2026-09-13/air-canada-workshop-research.md; .copilot-tracking/research/subagents/2026-09-13/desjardins-customer-evidence-research.md; .copilot-tracking/research/subagents/2026-09-13/platform-and-scenario-decision-research.md; live inspection of C:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents during planning.

## Implementation Phase 1: Repository and Bilingual Site Scaffold

<!-- parallelizable: true -->

### Step 1.1: Create the top-level directory structure and expand the root README

Create the directories proposed in the research's Configuration Examples (research lines 184-206): src/quote-preparation-agent/, mcp/application-server/, mcp/rulebook-server/, apps/workshop/, data/synthetic/, eval/, infra/, scripts/, docs/, docs/fr/. Expand README.md from its current one-line placeholder to describe the workshop's scope, the synthetic-only/non-binding boundary, and links to docs/index.md and docs/fr/index.md.

Files:
* README.md - Expand from a one-line title to a short project overview, explicitly stating synthetic-only data, no regulatory endorsement, and a default Copilot-free learner path (with any authoring-assistance tooling disclosed rather than implied as learner-facing, per Risk Register RR10).
* src/quote-preparation-agent/ (new directory) - Placeholder for the Phase 5 agent.
* mcp/application-server/ (new directory) - Placeholder for the Phase 4 read-only application MCP service.
* mcp/rulebook-server/ (new directory) - Placeholder for the Phase 4 read-only rulebook MCP service.
* apps/workshop/ (new directory) - Placeholder for the Phase 2/3 calculator, approval repository, and applicant/reviewer views.
* data/synthetic/ (new directory) - Placeholder for the Phase 2 fixtures.
* eval/ (new directory) - Placeholder for the Phase 7 evaluation suite.
* infra/ (new directory) - Placeholder for the Phase 8 Bicep modules.
* scripts/ (new directory) - Placeholder for the Phase 6 deck generator and any shared helpers.

Discrepancy references:
* Directory list matches research Configuration Examples (research lines 184-206) exactly; no deviation.
* Addresses research Risk Register RR10 (Copilot-prohibition scope misapplication, lines 288-308) via the README's disclosed-tooling statement.

Success criteria:
* All nine directories exist.
* README.md states the synthetic-only, non-binding, no-regulatory-endorsement boundary in at least one sentence.
* README.md states the default Copilot-free learner path with disclosed authoring assistance.

Context references:
* .copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md (Lines 184-206) - Configuration Examples (proposed organization).
* .copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md (Lines 114-118) - Regulatory and Privacy Boundary, for the README disclaimer wording.

Dependencies:
* None; this is the first step.

### Step 1.2: Create the bilingual Jekyll site skeleton

Mirror the sibling's docs/ site structure: docs/index.md (English landing page), docs/fr/index.md (French landing page), and a shared Jekyll config (docs/_config.yml) using the same remote theme (Just the Docs) as the sibling, adapted for Desjardins branding-neutral content (no airline branding, no Desjardins trademark assets without approval). Before reuse, confirm the Just the Docs theme's license permits this redistribution (Risk Register RR12). Do not create docs/labs/ content yet; that is Phase 6.

Files:
* docs/index.md - English landing page, linking to (not-yet-created) docs/labs/.
* docs/fr/index.md - French landing page, structurally paired with docs/index.md.
* docs/_config.yml - Jekyll site configuration, adapted from C:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents\docs\_config.yml.
* docs/Gemfile - Ruby/Jekyll dependency manifest, adapted from C:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents\docs\Gemfile.

Discrepancy references:
* Addresses research Risk Register RR12 (reused sibling assets carrying forward branding/screenshots/unlicensed tooling, lines 288-308) via the license check and Selective Reuse exclusions.

Success criteria:
* docs/index.md and docs/fr/index.md exist with reciprocal language-navigation links.
* No airline branding, screenshots, or run evidence copied from the sibling (per Selective Reuse, research lines 256-266).
* The Just the Docs theme license has been checked and permits this reuse before docs/_config.yml references it.

Context references:
* C:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents\docs\index.md - Structural reference only, content must not be copied verbatim.
* .copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md (Lines 256-266) - Selective Reuse table (what to exclude).

Dependencies:
* Step 1.1 completion (directories exist).

### Step 1.3: Validate phase changes

Run markdown lint on all new Markdown files. Confirm docs/ and docs/fr/ contain the same file names (structural parity check applies from this phase forward).

Validation commands:
* markdownlint docs/index.md docs/fr/index.md README.md - Markdown lint scope for this phase.

## Implementation Phase 2: Synthetic Fixtures, JSON Schema, and Deterministic Calculator

<!-- parallelizable: true -->

### Step 2.1: Author the synthetic fixture set and JSON Schema (draft-07)

Port the illustrative fixture and full draft-07 JSON Schema from the platform supporting report into data/synthetic/. Use `dataClass: SYNTHETIC_ONLY` on every fixture. Include the CASE-SYN-001 fixture (COMPACT + TRAINING_EXTENDED = 100000 CAD cents, state PENDING_REVIEW) plus additional fixtures covering SEDAN, TRAINING_BASIC, an out-of-dataset (UNSUPPORTED) case, and a revision-invalidation case. Reuse the schema's `if/then/else` conditional logic tying state to required fields (for example, APPROVED requires a non-null approvedRevision).

Files:
* data/synthetic/fixtures.json (or one file per fixture) - Fixture set, at minimum mirroring the research's CASE-SYN-001 example plus 4-5 additional cases for schema/calculator coverage.
* data/synthetic/quote-contract.schema.json - Full draft-07 JSON Schema, ported from the platform supporting report.

Discrepancy references:
* None; directly implements research Complete Examples (research lines 146-179) and the platform report's Illustrative JSON Contract.

Success criteria:
* Every fixture validates against quote-contract.schema.json.
* CASE-SYN-001 arithmetic equals exactly 100000 cents (80000 base + 20000 add-on), matching the research's verified value.
* At least one fixture exercises the UNSUPPORTED (out-of-dataset input) path and one exercises revision invalidation.

Context references:
* .copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md (Lines 146-179) - Complete Examples (fixture and schema summary).
* .copilot-tracking/research/subagents/2026-09-13/platform-and-scenario-decision-research.md - Full JSON Schema and 21 acceptance examples (V01-V21).

Dependencies:
* Step 1.1 completion (data/synthetic/ directory exists).

### Step 2.2: Implement the pure deterministic calculator and its unit tests

Implement a pure function (no LLM, no I/O) taking a confirmed input, an active rulebook, and returning amountCents plus currency/period, or a specific unsupported/missing-evidence issue code, never an invented amount. Base rates and plan add-ons come only from the bound rulebook's baseCents/planAddOnCents tables (research lines 146-163).

Files:
* apps/workshop/calculator.py - Pure calculator function and issue-code definitions.
* apps/workshop/tests/test_calculator.py - Unit tests covering every fixture from Step 2.1, including the exact 100000-cent case and the unsupported-input case.

Discrepancy references:
* Addresses research Implementation Patterns constraint: "The pure calculator uses invented tables and integer CAD cents... The model cannot infer rates" (research lines 130-145).

Success criteria:
* test_calculator.py passes for every fixture in data/synthetic/.
* The calculator never returns an amount for a fixture lacking a matching rulebook entry; it returns the specific issue code instead.

Context references:
* .copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md (Lines 130-145) - Implementation Patterns, calculator constraints.

Dependencies:
* Step 2.1 completion (fixtures and schema exist).

### Step 2.3: Validate phase changes

Validation commands:
* pytest apps/workshop/tests/test_calculator.py - Calculator unit tests.
* A JSON Schema validation pass (for example, PowerShell Test-Json or a Python jsonschema script) over every file in data/synthetic/ against quote-contract.schema.json.

## Implementation Phase 3: Approval Repository and State Machine

<!-- parallelizable: false -->

### Step 3.1: Implement the SQLite-backed ApprovalRepository with the full state machine

Implement the state machine exactly as described in research (Mermaid diagram, research lines 221-232): INCOMPLETE -> DRAFT -> PENDING_REVIEW -> APPROVED/REJECTED, DRAFT -> UNSUPPORTED for out-of-dataset input, and APPROVED/REJECTED -> DRAFT (new revision) on any input or rule change, which invalidates the prior approval. Persist immutable revisions, record versions, actor context, transitions, and receipts transactionally in SQLite.

Files:
* apps/workshop/approval_repository.py - ApprovalRepository class: create draft, submit, approve, reject, revise, get status; enforces the state machine and immutable revisions.
* apps/workshop/db/schema.sql - SQLite schema for cases, revisions, approvals, and command receipts.

Discrepancy references:
* Implements research Implementation Patterns ApprovalRepository description (research lines 130-145) and the state machine diagram (research lines 221-232).

Success criteria:
* Every transition in the Mermaid state diagram (research lines 221-232) has a corresponding code path and at least one test.
* A revision created after APPROVED or REJECTED correctly resets state to DRAFT and clears any prior approval.

Context references:
* .copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md (Lines 209-232) - Technical Scenarios, architecture and state-machine Mermaid diagrams.
* .copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md (Lines 130-145) - Implementation Patterns, ApprovalRepository constraints.

Dependencies:
* Step 2.1 completion (fixture/schema shapes inform the repository's data model).

### Step 3.2: Implement concurrency, idempotency, and actor-authorization tests

Implement and test: identical command replays return the original receipt (idempotency by commandId); changed payloads with the same commandId conflict; concurrent approve/reject commands on the same case/revision permit exactly one winner; only a server-authenticated reviewer actor may approve/reject (no client-supplied actor/role override is trusted); the applicant/model cannot approve its own draft.

Files:
* apps/workshop/tests/test_approval_repository.py - State machine, revision-invalidation, and transactional-binding tests.
* apps/workshop/tests/test_concurrency.py - Idempotent replay, conflicting-payload, and concurrent-race tests.
* apps/workshop/tests/test_authorization.py - Self-approval and forged-actor rejection tests (traces to research V09, V11).

Discrepancy references:
* Directly implements research Validation section requirements (research lines 317-327) and Risk Register RR4 mitigation (research lines 288-308).

Success criteria:
* All listed test files pass.
* A test asserts that a command with a stale recordVersion is rejected as a conflict, not silently applied.

Context references:
* .copilot-tracking/research/subagents/2026-09-13/platform-and-scenario-decision-research.md - State Machine and Atomic Commands table; Validation Acceptance Examples V01-V21.

Dependencies:
* Step 3.1 completion.

### Step 3.3: Validate phase changes

Validation commands:
* pytest apps/workshop/tests/test_approval_repository.py apps/workshop/tests/test_concurrency.py apps/workshop/tests/test_authorization.py

## Implementation Phase 4: Read-Only MCP Services

<!-- parallelizable: true -->

### Step 4.1: Implement application-server (get_application)

Adapt the sibling's FastMCP pattern (C:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents\mcp\defender-server, anomaly-server) into a read-only service exposing a single tool, get_application(fixtureId), that returns only data present in data/synthetic/ fixtures. Reject unknown fixtureId values explicitly; expose no write, SQL, URL, or path-based tools.

Files:
* mcp/application-server/server.py - FastMCP server exposing get_application(fixtureId) only.
* mcp/application-server/tests/test_application_server.py - Tests for a known fixture, an unknown fixtureId (expected rejection), and absence of any write-capable tool.

Discrepancy references:
* Implements research Implementation Patterns MCP constraint: "Expose only get_application(fixtureId) and get_rulebook(rulebookId). No arbitrary SQL, URLs, paths, write tools..." (research lines 130-145).

Success criteria:
* get_application returns the exact fixture content for a known fixtureId and a clear rejection for an unknown one.
* No additional tools are registered on the server.

Context references:
* C:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents\mcp\defender-server - Structural FastMCP pattern reference.
* .copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md (Lines 130-145) - Implementation Patterns, MCP tool exposure constraints.

Dependencies:
* Step 2.1 completion (fixtures exist to serve).

### Step 4.2: Implement rulebook-server (get_rulebook)

Same pattern as Step 4.1, serving only the pinned rulebook definitions (baseCents, planAddOnCents, authority: WORKSHOP_AUTHORS_ONLY) used by the Phase 2 calculator. Reject unknown rulebookId values.

Files:
* mcp/rulebook-server/server.py - FastMCP server exposing get_rulebook(rulebookId) only.
* mcp/rulebook-server/tests/test_rulebook_server.py - Tests mirroring Step 4.1's coverage for rulebook lookups.

Discrepancy references:
* Same as Step 4.1.

Success criteria:
* get_rulebook returns the exact pinned rulebook for a known rulebookId and a clear rejection for an unknown one.
* No additional tools are registered on the server.

Context references:
* C:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents\mcp\anomaly-server - Structural FastMCP pattern reference.

Dependencies:
* Step 2.1 completion (rulebook fixtures exist to serve).

### Step 4.3: Validate phase changes

Validation commands:
* pytest mcp/application-server/tests mcp/rulebook-server/tests - MCP service unit/smoke tests, run locally without any hosted deployment.

## Implementation Phase 5: Hosted LangGraph Quote-Preparation Agent (local, unhosted)

<!-- parallelizable: false -->

### Step 5.1: Adapt the supervisor/specialist LangGraph topology

Adapt C:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents\src\threat-assessment-agent\graph.py and state.py into src/quote-preparation-agent/, replacing the evidence_investigator/risk_analyst/report_composer specialist trio with an intake specialist (confirms structured input), a reference specialist (calls the Phase 4 MCP tools), and a tool-free composer that only assembles bounded applicant/reviewer templates. Keep the supervisor-routes-until-both-specialists-complete pattern.

Files:
* src/quote-preparation-agent/graph.py - Adapted LangGraph supervisor/specialist topology.
* src/quote-preparation-agent/state.py - Adapted state definitions (no checkpointer requirement change without a version-specific test, per research Platform Findings).
* src/quote-preparation-agent/toolbox.py - Adapted tool bindings to the Phase 4 MCP servers.
* src/quote-preparation-agent/main.py - Adapted entry point.

Discrepancy references:
* Implements research Implementation Patterns: "Select one hosted LangGraph orchestrator containing logical intake/reference specialists and a tool-free composer" (research lines 130-145).
* Retains the framework per Risk Register RR6 mitigation (research lines 288-308): framework choice is reversible, no migration performed without a demonstrated need.

Success criteria:
* The graph compiles and runs locally against Phase 4 MCP servers and Phase 2 fixtures without any hosted Foundry call.
* No node infers rates, discounts, or coverage outside the Phase 2 calculator's pure computation.

Context references:
* C:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents\src\threat-assessment-agent\graph.py (Lines 1-40 read during planning) - Supervisor/specialist topology pattern.
* .copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md (Lines 209-220) - Technical Scenarios architecture Mermaid diagram.

Dependencies:
* Step 4.1 and 4.2 completion (MCP tools exist to bind).

### Step 5.2: Wire the agent to the calculator, approval repository, and bounded output rules

Ensure the agent never stores approval state itself (no shared approval in an applicant's hosted session, no inference from model text); it calls into apps/workshop/approval_repository.py for all state transitions. Ensure applicant-facing output uses bounded intake/status templates only; amount-bearing drafts stay with the reviewer until approval; approved previews use only authoritative fields.

Files:
* src/quote-preparation-agent/tests/test_agent_local.py - Local end-to-end test running the graph against synthetic fixtures, asserting no self-approval, no invented amounts, and correct applicant/reviewer output separation.

Discrepancy references:
* Implements research Implementation Patterns: "Applicant output uses bounded intake/status templates, never raw employee-facing composer output" (research lines 130-145).

Success criteria:
* test_agent_local.py passes for at least the CASE-SYN-001 fixture and one UNSUPPORTED fixture.
* No test path allows the agent itself to transition a case to APPROVED.

Context references:
* .copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md (Lines 130-145) - Applicant/reviewer output separation rules.

Dependencies:
* Step 3.1, 3.2, 5.1 completion.

### Step 5.3: Validate phase changes

Validation commands:
* pytest src/quote-preparation-agent/tests/test_agent_local.py - Local-only agent test; explicitly do not attempt `azd deploy` or any hosted Foundry call in this phase.

## Implementation Phase 6: Bilingual Lab Curriculum and Shared Deck

<!-- parallelizable: true -->

### Step 6.1: Author the ten English labs (00 through 09)

Adapt each sibling lab's structure (objectives, numbered exercises, expected outputs, knowledge checks) into the Desjardins scenario, per the Bilingual Workshop Adaptation table (research lines 242-252), plus a new lab-09 (teardown/cost-cleanup) mirroring C:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents\docs\labs\lab-09-teardown.md, addressing Risk Register RR5 (cost/quota exhaustion at scale).

Files:
* docs/labs/lab-00-setup.md - Synthetic boundaries, calculator oracle, language choice, policy, approved access.
* docs/labs/lab-01-architecture.md - Trace who can read, calculate, persist, and approve.
* docs/labs/lab-02-mcp-servers.md - Two read-only services; transport/failure cases.
* docs/labs/lab-03-deploy-agent.md - Approved isolated sandbox and one verified protocol/toolchain (explicitly gated behind G2/G3; lab content describes the gate, does not assume it is cleared).
* docs/labs/lab-04-invoke-agent.md - EN/FR intake, correction, approval/rejection, revision invalidation, gated preview.
* docs/labs/lab-05-evaluations.md - Arithmetic, evidence, approval, injection, missing data, isolation, language parity.
* docs/labs/lab-06-cicd.md - Evidence gates and protected promotion; CI approval vs business approval distinction.
* docs/labs/lab-07-troubleshooting-rbac.md - Auth/network/evidence/storage failures, concurrent commands, positive telemetry.
* docs/labs/lab-08-production-readiness.md - Happy/blocked paths; README, one-pager, slides, demo with evidence limits.
* docs/labs/lab-09-teardown.md - New lab (beyond the original nine researched): resource cleanup, cost/quota hygiene, addressing the PDF's up-to-75-participant scale (Risk Register RR5).

Discrepancy references:
* DD-01 (Planning Log): research recommended nine labs; this plan implements ten, matching the sibling repository's current state.

Success criteria:
* All ten lab files exist with objectives, numbered exercises, expected outputs, and knowledge checks.
* Every lab's technical claims (deployment, tools, approval) match the actual Phase 2-5 implementation, not aspirational claims.

Context references:
* .copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md (Lines 242-252) - Nine-lab curriculum table (base structure).
* C:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents\docs\labs\lab-09-teardown.md - Structural reference for the new tenth lab.

Dependencies:
* Phases 2-5 substantially complete, so lab content accurately describes working code, not aspirational behavior.

### Step 6.2: Author the ten paired French labs

Publish natural, reviewed French with accents, stable executable identifiers (matching the English fixtures/commands), and localized speaker notes. Maintain the same file names as the English set under docs/fr/labs/.

Files:
* docs/fr/labs/lab-00-setup.md through docs/fr/labs/lab-09-teardown.md - Ten French labs, one per English lab from Step 6.1.

Discrepancy references:
* Same as Step 6.1 (DD-01); also addresses Risk Register RR9 (bilingual parity is structural only until runtime-tested).

Success criteria:
* Every English lab from Step 6.1 has a matching French file name.
* At least one bilingual reviewer (human, out of this plan's automation) signs off on natural French phrasing before publication (Gate G5).

Context references:
* .copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md (Lines 242-252) - Curriculum requirements (EN/FR parity).

Dependencies:
* Step 6.1 completion.

### Step 6.3: Adapt the shared bilingual deck generator script

Adapt C:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents\scripts\build-workshop-deck.js to generate EN and FR decks from the Step 6.1/6.2 lab content, keeping the shared deck-generation model and evidence-status legend described in the sibling analysis. Before reuse, confirm the PptxGenJS package license permits this redistribution (Risk Register RR12).

Files:
* scripts/build-workshop-deck.js - Adapted deck generator (Node.js, PptxGenJS-based).

Discrepancy references:
* Implements Selective Reuse guidance: "Shared deck model and evidence-status legend" retained conceptually (research lines 256-266).
* Addresses research Risk Register RR12 (unlicensed vendored dependencies, lines 288-308) via the PptxGenJS license check.

Success criteria:
* Running the script produces both an EN and an FR deck output without runtime errors, from the Step 6.1/6.2 content.
* The PptxGenJS package license has been checked and permits this reuse.

Context references:
* C:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents\scripts\build-workshop-deck.js - Structural reference.

Dependencies:
* Step 6.1, 6.2 completion.

### Step 6.4: Validate phase changes

Validation commands:
* markdownlint docs/labs docs/fr/labs - Markdown lint scope for this phase.
* node scripts/build-workshop-deck.js --check (or equivalent dry-run flag) - Deck generation smoke check, if supported by the adapted script.

## Implementation Phase 7: Evaluation Suite

<!-- parallelizable: true -->

### Step 7.1: Author the paired EN/FR golden dataset

Adapt C:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents\eval\golden-dataset.jsonl into a Desjardins-specific dataset with at least six paired EN/FR business fixtures (matching canonical IDs, amounts, references, tools, and states across languages) plus reusable fault cases (missing data, out-of-dataset input, unauthorized approval attempt, injection attempt).

Files:
* eval/golden-dataset.jsonl - Paired EN/FR golden dataset for the quote-preparation scenario.

Discrepancy references:
* Implements research Validation section requirement: "At least six paired EN/FR business fixtures plus reusable fault cases" (research lines 317-327).

Success criteria:
* Golden dataset contains at least six paired EN/FR business cases with identical canonical fields, plus fault cases.

Context references:
* .copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md (Lines 317-327) - Validation section, bilingual fixture requirements.

Dependencies:
* Step 2.1, 6.1, 6.2 completion (fixtures and lab language conventions established).

### Step 7.2: Adapt the deterministic checks and evaluation gate script

Adapt C:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents\eval\deterministic-tests\checks.py and evaluation_gate.py to check: exact arithmetic, evidence/provenance, approval-state correctness, injection resistance, missing-data handling, case isolation, and EN/FR language parity. The gate must fail on any missing/skipped required case and must not let quality judges override arithmetic or approval failures.

Files:
* eval/deterministic-tests/checks.py - Adapted deterministic check functions.
* eval/evaluation_gate.py - Adapted evaluation gate script.

Discrepancy references:
* Implements research Validation section requirement: "Strict terminal SSE success and complete required evaluator results... quality judges cannot override arithmetic or approval failures" (research lines 317-327).

Success criteria:
* Running the evaluation gate against the Step 7.1 dataset and the Phase 2-5 implementation passes all required deterministic checks.

Context references:
* C:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents\eval\deterministic-tests\checks.py - Structural reference.

Dependencies:
* Step 7.1 completion; Phases 2-5 implemented.

### Step 7.3: Validate phase changes

Validation commands:
* python eval/evaluation_gate.py --dataset eval/golden-dataset.jsonl (or the adapted equivalent invocation) - Full evaluation gate run against local implementation.

## Implementation Phase 8: Infrastructure Scaffolding (author only, gated)

<!-- parallelizable: false -->

### Step 8.1: Adapt Bicep modules for the read-only MCP services and hosted agent

Adapt C:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents\infra\modules\ai-foundry.bicep, mcp-container-apps.bicep, and rbac.bicep for the Desjardins MCP services and quote-preparation agent. Do not prescribe tenant/subscription identifiers, credentials, endpoints, model deployment names, or package versions before Gate G2/G3 discovery, per research Configuration Examples (research lines 184-206). Explicitly comment in each module that it is author-only until gates clear.

Files:
* infra/modules/ai-foundry.bicep - Adapted hosted-agent infrastructure module (author only).
* infra/modules/mcp-container-apps.bicep - Adapted MCP container infrastructure module (author only).
* infra/modules/rbac.bicep - Adapted RBAC module (author only).

Discrepancy references:
* Addresses Risk Register RR7 (private networking/ingress ambiguity, Gate G2) and RR6 (framework/version drift, Gate G3) by deferring any apply/deploy action.

Success criteria:
* Each module builds/compiles cleanly (`bicep build`) without being deployed.
* No hard-coded tenant, subscription, credential, or endpoint values exist in any module.

Context references:
* .copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md (Lines 184-206) - Configuration Examples, explicit "no tenant/subscription identifiers... before approved discovery" constraint.
* .copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md (Lines 288-308) - Risk Register, RR6 and RR7.

Dependencies:
* Phase 4 and 5 completion (module inputs reflect the actual MCP services and agent).

### Step 8.2: Validate phase changes

Validation commands:
* bicep build infra/modules/ai-foundry.bicep - Lint/compile only.
* bicep build infra/modules/mcp-container-apps.bicep - Lint/compile only.
* bicep build infra/modules/rbac.bicep - Lint/compile only.
* Do not run azd provision, azd deploy, az deployment group create, or any apply command in this phase.

## Implementation Phase 9: Final Validation

<!-- parallelizable: false -->

### Step 9.1: Run full project validation

Execute all validation commands for the project:
* pytest apps/workshop/tests mcp/application-server/tests mcp/rulebook-server/tests src/quote-preparation-agent/tests eval - Full Python test sweep.
* bicep build infra/modules/*.bicep - Full Bicep lint/compile sweep.
* markdownlint README.md docs docs/fr - Full Markdown lint sweep.

### Step 9.2: Fix minor validation issues

Iterate on lint errors, type errors, and straightforward test failures. Apply fixes directly when corrections are isolated and low-risk.

### Step 9.3: Report blocking issues

When validation failures require changes beyond minor fixes, or when they surface an unresolved gate (G1-G6):
* Document the issue and affected files.
* Provide the user with next steps and recommend additional research/planning rather than a large-scale fix in this phase.

## Dependencies

* Python 3.11+, pytest, jsonschema (or equivalent) for Phases 2, 3, 4, 5, 7, 9.
* Node.js and the sibling's PptxGenJS-based tooling for Phase 6.
* LangGraph, azure-openai/langchain adapters (exact versions pending Gate G3) for Phase 5.
* Bicep CLI for Phase 8 and Phase 9 lint/compile checks only.
* Jekyll/Ruby/Bundler (optional, for local site preview) for Phase 1 and Phase 6.

## Success Criteria

* All nine implementation phases (1-9, excluding gated deployment) produce locally testable, passing artifacts with no Azure dependency beyond lint/compile checks.
* No infrastructure apply/deploy command runs before Gates G2, G3, and G6 are cleared by their owners.
* Ten EN and ten FR labs exist with matching structure, reflecting the sibling repository's current state (DD-01).
