---
description: "Implementation plan for the reviewer-facing approval surface (Option C), Cosmos-backed shared case store, Bicep deployment, and teardown automation"
applyTo: ".copilot-tracking/**"
---

<!-- markdownlint-disable-file -->

# Implementation Plan: Reviewer App (Option C)

**Date**: 2026-09-15
**Details**: `.copilot-tracking/details/2026-09-15/reviewer-app-details.md`
**Research**:

* `.copilot-tracking/research/2026-09-15/reviewer-app-infra-research.md`
* `.copilot-tracking/research/2026-09-15/reviewer-app-cicd-research.md`
* `.copilot-tracking/research/2026-09-15/reviewer-app-conventions-research.md`

## Objective

Build the missing reviewer half of the quote-preparation workflow: a separate, Entra-gated web application where an authorized reviewer sees `PENDING_REVIEW` cases together with their calculated premium and can approve, reject, or request revision. Deploy it with idempotent Bicep, automate its identity and delivery, and provide a scoped teardown that removes everything this feature provisions.

## Non-Negotiable Constraints

* The applicant-facing surface must not change behaviour. The five bilingual templates in `_STATUS_TEMPLATES` and the `no_invented_amount` guardrail in `eval/deterministic-tests/checks.py` stay intact. The premium may appear only on the reviewer surface.
* The reviewer app imports the case store directly. It must not route decisions through `toolbox.py`, which deliberately refuses to wrap `approve`, `reject`, and `revise`.
* Every state transition preserves the existing semantics: self-approval prevention, revision invalidation, idempotent decision replay, and append-only audit.
* Teardown never issues `az group delete`. The resource group is shared with production.

## Phases

### Phase 1: Shared case store and calculation persistence

* [x] Step 1.1: Extract a `CaseStore` protocol capturing the full `ApprovalRepository` contract
* [x] Step 1.2: Extend the case record with persisted calculation fields
* [x] Step 1.3: Add a state-filtered listing method for the review queue
* [x] Step 1.4: Implement `CosmosCaseStore` with ETag concurrency and batched audit writes
* [x] Step 1.5: Add a store factory and wire `graph.py` to it
* [x] Step 1.6: Persist the calculation at submission time in `composition_node`
* [x] Step 1.7: Write a backend-agnostic contract test suite and run it against both backends
* [x] Step 1.8: Make Cosmos client construction lazy so a Cosmos outage cannot block agent startup
* [x] Step 1.9: Persist the decision reason code on the audit event

### Phase 2: Reviewer API service

* [x] Step 2.1: Scaffold `apps/reviewer-app` following the web-chat app layout
* [x] Step 2.2: Implement the queue, detail, and decision endpoints
* [x] Step 2.3: Map repository exceptions to correct HTTP status codes
* [x] Step 2.4: Add idempotency-key handling for decision replay
* [x] Step 2.5: Write API tests using the duck-typed auth fake convention

### Phase 3: Reviewer identity and Entra automation

* [x] Step 3.1: Implement role-based `auth.py` for the reviewer app
* [x] Step 3.2: Write an idempotent reviewer app registration script
* [x] Step 3.3: Write the matching identity teardown script
* [x] Step 3.4: Test the auth module against crafted claim sets
* [x] Step 3.5: Add a recycle-bin sweep so an interrupted purge completes on rerun

### Phase 4: Reviewer frontend

* [x] Step 4.1: Scaffold the SPA from the web-chat frontend toolchain
* [x] Step 4.2: Build the queue, case detail, and decision views
* [x] Step 4.3: Wire MSAL acquisition of the reviewer scope
* [x] Step 4.4: Commit a lockfile and verify a clean container build

### Phase 5: Infrastructure as code

* [x] Step 5.1: Author `infra/modules/cosmos-db.bicep` with serverless capacity and data-plane RBAC
* [x] Step 5.2: Author `infra/modules/reviewer-app.bicep` for the second Container App
* [x] Step 5.3: Wire both modules into `infra/main.bicep` with parameters and outputs
* [x] Step 5.4: Grant the agent and reviewer identities Cosmos data-plane roles
* [x] Step 5.5: Update the CI what-if parameter list

### Phase 6: Delivery and teardown workflows

* [x] Step 6.1: Add the reviewer app build and test workflow
* [x] Step 6.2: Add the reviewer app deploy path
* [x] Step 6.3: Add the scoped teardown workflow
* [x] Step 6.4: Register the new workflow with the test-trends publisher
* [x] Step 6.5: Add a CI check asserting the vendored repository copies stay byte-identical

### Phase 7: Validation

* [x] Step 7.1: Add an applicant-guardrail regression test
* [x] Step 7.2: Add a Bicep idempotency check
* [x] Step 7.3: Run the full test suite and record results

## Dependencies

Phase 1 gates Phases 2, 5, and 7. Phase 3 gates Phase 4 step 4.3 and Phase 6 step 6.2. Phases 2 and 3 may run in parallel once Phase 1 completes. Phase 5 may run in parallel with Phases 2 through 4.
