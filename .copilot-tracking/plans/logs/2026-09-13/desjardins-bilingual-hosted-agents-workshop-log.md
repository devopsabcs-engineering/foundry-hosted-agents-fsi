<!-- markdownlint-disable-file -->
# Planning Log: Desjardins Bilingual Hosted Agents Workshop

## Discrepancy Log

Gaps and differences identified between research findings and the implementation plan.

### Unaddressed Research Items

* DR-01: Gate-numbering mismatch between the primary research document and the platform-and-scenario-decision subagent report.
  * Source: .copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md (Lines 32-41), and .copilot-tracking/research/subagents/2026-09-13/platform-and-scenario-decision-research.md (its own Implementation Gates table, G1-G8).
  * Reason: The primary document's Gates G1-G6 (added during the adversarial review pass) consolidate and relabel the original five unlabeled research items plus a new regulatory item; the subagent report's G1-G8 predate that relabeling and use a different eight-way split. The plan treats the primary document's G1-G6 as canonical because it is the newer, adversarially reviewed synthesis, but the subagent report's G1-G8 was never edited to match.
  * Impact: Low — the plan and its Success Criteria reference only the primary document's G1-G6 labels; no plan content depends on the subagent report's G1-G8 labels. Recommend reconciling or retiring the subagent report's gate table in a future research pass so only one gate numbering exists repo-wide.

* DR-02: Unresolved timing and figure conflicts from the source PDF (lab minutes, judging minutes, coaching minutes) remain undecided.
  * Source: .copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md — Risk Register RR8 (Lines 288-308).
  * Reason: These are evidence conflicts in the PDF itself (305 vs 290 lab minutes; 25 vs 30 technical-judging minutes; 10 vs 15 coaching minutes) that only the workshop organizer can resolve (Gate G1).
  * Impact: Low — the plan's lab curriculum (Phase 6) does not hard-code any of the conflicting minute figures; labs describe exercises and expected outputs, not wall-clock timing, so this conflict does not block Phase 1-9 implementation.

* DR-03: LIDIA and PDM acronyms from the source PDF remain unexpanded and unconfirmed.
  * Source: .copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md — Customer and Historical Constraints (Lines 102-113); Risk Register RR13.
  * Reason: The PDF does not define these terms and no other source was available during research.
  * Impact: Low — the plan does not reference LIDIA or PDM in any file path, module name, or lab content; the terms are not load-bearing for any Phase 1-9 deliverable.

### Plan Deviations from Research

* DD-01: The plan implements ten EN/FR labs (00 through 09, including a new teardown/cost-cleanup lab) instead of the nine labs recommended in the research's Selected Recommendation and Bilingual Workshop Adaptation table.
  * Research recommends: Nine labs (research Bilingual Workshop Adaptation table, Lines 242-252), mirroring the sibling repository's structure as it existed when the research was written.
  * Plan implements: Ten labs, matching the sibling repository's CURRENT state, which was found during planning (live `list_dir` on C:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents\docs\labs and docs\fr\labs) to already include lab-09-teardown.md in both languages.
  * Rationale: The sibling repository evolved after the research was completed (a known, explicitly flagged risk in the research itself — Risk Register RR14, circular self-validation / working-tree drift). A tenth teardown lab directly strengthens the mitigation of Risk Register RR5 (cost/quota exhaustion at up-to-75-participant scale) by giving every learner an explicit resource-cleanup exercise. Matching the sibling's current ten-lab structure keeps the adapted curriculum consistent with its stated source of structural reuse (research Selective Reuse, Lines 256-266) rather than an outdated nine-lab snapshot.

## Implementation Paths Considered

### Selected: Nine-plus-one bilingual hosted-agent labs, synthetic Ontario quote-preparation, LangGraph plus a separate SQLite approval backend

* Approach: Adapt the sibling's LangGraph supervisor/specialist topology and ten-lab structure (see DD-01) into a Desjardins-specific synthetic Ontario auto-insurance quote-preparation scenario with a deterministic calculator and a mandatory, separately persisted employee-approval gate before any applicant-facing preview.
* Rationale: Matches the user's explicit requirements (Foundry hosted agents, bilingual, FSI-appropriate use case) while keeping the riskiest business logic (arithmetic, approval authorization) offline-testable and framework-agnostic, per the research's own risk-driven design.
* Evidence: .copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md (Lines 26-31, Selected Recommendation; Lines 339 area, Research Handoff).

### IP-01: Claims-intake or first-notice-of-loss scenario instead of quote preparation

* Approach: Build the workshop around a claims-intake or FNOL (first notice of loss) flow instead of a new-quote flow.
* Trade-offs: Also FSI-relevant and arguably higher business stakes, but the PDF evidence more directly supports a quote/application-preparation framing (pp. 8-9, 12-13) and claims data carries materially higher sensitivity and regulatory exposure than a synthetic quote scenario.
* Rejection rationale: Higher privacy/regulatory exposure for the same illustrative teaching value; quote preparation lets the deterministic-calculator and approval-gate patterns shine without implying claims-adjudication authority. Documented in research Considered Alternatives (Lines 267-278).

### IP-02: Card-dispute or fraud-review scenario instead of quote preparation

* Approach: Adapt a payment-card dispute or fraud-review workflow as the FSI use case.
* Trade-offs: Strong FSI fit but weaker grounding in the specific PDF evidence, and higher risk of implying investigative/fraud-determination authority the workshop cannot support.
* Rejection rationale: Same category of rejection as IP-01 — greater implied-authority risk for no material teaching benefit over quote preparation. Documented in research Considered Alternatives (Lines 267-278).

### IP-03: Keep the airline/threat-assessment theme and only re-skin terminology

* Approach: Minimal-diff adaptation — keep the sibling's threat-assessment domain and vocabulary, renaming surface terms to sound FSI-adjacent.
* Trade-offs: Fastest to build, but does not satisfy the user's explicit requirement for a different, FSI-fitting use case grounded in the Desjardins PDF.
* Rejection rationale: Fails the user's stated requirement directly; documented in research Considered Alternatives (Lines 267-278).

### IP-04: Ship only the short (single-session) workshop variant, omitting the full ten-lab arc

* Approach: Build a condensed, single-session version instead of the full multi-lab curriculum.
* Trade-offs: Faster to deliver and lower scope risk, but does not exercise the full architecture (MCP services, evaluation gate, CI/CD, teardown) the sibling repository demonstrates, and does not match the user's "similar to the sibling repository" requirement.
* Rejection rationale: Documented in research Considered Alternatives (Lines 267-278); rejected because it under-delivers relative to the explicit "similar to the sibling repository" requirement.

### IP-05: Model-written or conversation-only approval instead of a persisted approval repository

* Approach: Let the agent's conversation transcript itself serve as the approval record (for example, the model states "approved" in a message) rather than a separate, transactional data store.
* Trade-offs: Simpler to build; no separate persistence layer needed.
* Rejection rationale: Directly enables self-approval and is not tamper-evident or queryable; rejected per research Implementation Patterns and Risk Register RR4 (model self-approval / spoofed reviewer). Documented in research Considered Alternatives (Lines 267-278).

### IP-06: Use the Foundry-managed conversation/session store as the approval database

* Approach: Reuse the hosted agent's own session/conversation state store (Foundry's durable state store, public preview) as the system of record for approval state, instead of a separate SQLite-backed ApprovalRepository.
* Trade-offs: Fewer moving parts, no separate database to operate; but the durable state store's 30-day session deletion and preview status make it unsuitable as an audit-grade, long-lived approval record.
* Rejection rationale: Documented in research Considered Alternatives (Lines 267-278) and Risk Register RR11 (approval-store durability mistaken for a production-grade control); rejected in favor of an explicit, independently durable ApprovalRepository.

### IP-07: Migrate now to Microsoft Agent Framework or another hosted-agent SDK

* Approach: Adopt a newer, Foundry-native unified agent SDK instead of continuing with LangGraph.
* Trade-offs: Potentially less long-term platform drift, but adds an unverified migration on top of an already-unverified toolchain, with no current evidence base (sibling reuse and all current research are LangGraph-based).
* Rejection rationale: Documented in research Considered Alternatives (Lines 267-278) and Risk Register RR6 (framework/version drift); deferred until after Gate G3 (reproducible compatibility) and, if available, dedicated Azure AI best-practices guidance. Not revisited in this plan.

## Suggested Follow-On Work

Items identified during planning that fall outside the current implementation plan's scope.

* WI-01: Clear Gate G1 (organizer policy and delivery confirmation) — confirm PDF pp. 8-9/12-13 scenario framing, resolve the RR8 timing conflicts (305 vs 290 lab minutes; 25 vs 30 judging minutes; 10 vs 15 coaching minutes), and confirm delivery format with the workshop organizer. (Priority: High)
  * Source: research Potential Next Research (Lines 32-41); Planning Log DR-02.
  * Dependency: None; can start immediately, independent of Phases 1-9.

* WI-02: Clear Gate G2 (approved platform, security, and capacity) — confirm the approved Foundry project/subscription, quota and cost ceiling for up to 75 concurrent participants across up to 15 teams, and the required private-networking/ingress posture before any Phase 5/8 hosted deployment. (Priority: High)
  * Source: research Potential Next Research (Lines 32-41); Risk Register RR5, RR7 (Lines 288-308).
  * Dependency: Should be resolved before attempting Phase 5 hosted deployment or Phase 8 `azd provision`/`azd deploy`.

* WI-03: Clear Gate G3 (reproducible compatibility) — pin and verify exact LangGraph/Azure OpenAI/LangChain adapter versions against the target Foundry runtime, and formally decide whether IP-07 (framework migration) should be revisited. (Priority: Medium)
  * Source: research Potential Next Research (Lines 32-41); Risk Register RR6.
  * Dependency: Should be resolved before Phase 5's hosted deployment (not required for the local-only Phase 5 work in this plan) and before Phase 8's infrastructure apply.

* WI-04: Clear Gate G4 (domain and approval review) — obtain domain-expert review of the calculator's illustrative rate tables and independent verification of the actor-authorization implementation (Phase 3) beyond automated tests. (Priority: Medium)
  * Source: research Potential Next Research (Lines 32-41); Risk Register RR4.
  * Dependency: Depends on Phase 2 and Phase 3 completion.

* WI-05: Clear Gate G5 (bilingual pilot) — run a live bilingual pilot session to verify EN/FR runtime parity (not just structural file-name parity) and gather learner/coach feedback. (Priority: Medium)
  * Source: research Potential Next Research (Lines 32-41); Risk Register RR9.
  * Dependency: Depends on Phase 6 and Phase 7 completion; also depends on WI-02 if the pilot uses a hosted deployment rather than local-only demonstration.

* WI-06: Clear Gate G6 (regulatory and privacy sign-off) — obtain Legal/Privacy review for Quebec Law 25, PIPEDA, AMF, and FSRA considerations before any real-jurisdiction or public-facing use of the workshop materials, even though all data remains synthetic. (Priority: High)
  * Source: research Regulatory and Privacy Boundary (Lines 114-118); Risk Register RR2, RR3.
  * Dependency: Must complete before any public release or delivery beyond an internal/coach-only pilot; independent of Phases 1-9's code authoring.

* WI-07: Reconcile the two gate-numbering schemes (primary research document's G1-G6 versus the platform subagent report's G1-G8) into a single canonical list. (Priority: Low)
  * Source: Planning Log DR-01.
  * Dependency: None; a documentation-only follow-up.
