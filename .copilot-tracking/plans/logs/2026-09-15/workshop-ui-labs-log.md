<!-- markdownlint-disable-file -->
# Planning Log: Reviewer redirect URIs and bilingual UI labs

**Related Plan**: ad hoc (user request in Task Implementor session)

## Discrepancy Log

Gaps and deviations identified during implementation.

### Unaddressed Research Items

* DR-01: `AGENT_PRINCIPAL_ID` remains unset in the deployment configuration
  * Source: `infra/main.bicep` parameter documentation
  * Reason: the Foundry data plane reports zero deployed agents, so the per-agent Entra identity does not exist. The account and project system-assigned identities are explicitly not valid substitutes.
  * Impact: medium. The hosted agent cannot write cases to Cosmos until it is supplied, but nothing can supply it before the gated deploy runs.

### Implementation Deviations

* DD-01: Web chat conversation screenshots were not captured
  * Plan intent: illustrate the full applicant experience
  * Implementation differs: only the pre-authentication gate is shown
  * Rationale: the conversation view needs a deployed agent endpoint and a chat app registration, neither of which exists. Lab 11 documents the boundary rather than fabricating a transcript.

* DD-02: Web chat test command required `PYTHONPATH`
  * Plan intent: document `python -m pytest apps/web-chat/tests`
  * Implementation differs: the labs set `PYTHONPATH=apps/web-chat` first
  * Rationale: found by executing the drafted command. The chat tests import `app` and `auth` as top-level modules with no `sys.path` insertion, unlike the reviewer tests. The workflow sets the same variable.

## Suggested Follow-On Work

Items identified during implementation that fall outside current scope.

* WI-30: Make the web chat test suite runnable without an external `PYTHONPATH` (low)
  * Source: Lab 11 validation
  * Dependency: none. Adding the same `sys.path.insert` header the reviewer tests use would make both suites consistent and remove a footgun for workshop attendees.

* WI-31: Have `scripts/setup-reviewer-identity.ps1` publish `REVIEWER_CLIENT_ID` and optionally create the reviewer group (medium)
  * Source: Lab 12 authoring
  * Dependency: none. Both gaps required manual follow-up steps that are now documented in the lab but could be automated.

* WI-32: Capture an authenticated web chat conversation screenshot (low)
  * Source: Lab 11, Exercise 11.7
  * Dependency: G2, G3 and G6 gate clearance, followed by an agent deployment.

* WI-33: Revisit Lab 14's `actionlint` expectation if the linter adds `concurrency.queue` to its schema (low)
  * Source: Lab 14, Exercise 14.5
  * Dependency: an upstream actionlint release.

## User Decisions

Decisions recorded from Implementation Decision prompts.

* ID-06: Reviewer screenshot capture method - interactive sign-in selected
  * Rationale: the user chose to authenticate in the automated browser rather than stubbing the API and seeding an MSAL cache. This produced screenshots backed by a real token, including a genuine Entra object ID in the audit trail.

* ID-07: New lab scope - all five labs (10 through 14) selected
  * Rationale: the user accepted the full proposal covering the Azure foundation, both user interfaces, reviewer identity, and pilot operations.
