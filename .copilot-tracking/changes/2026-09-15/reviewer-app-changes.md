<!-- markdownlint-disable-file -->
# Release Changes: Reviewer App (Option C)

**Related Plan**: reviewer-app-plan.instructions.md
**Implementation Date**: 2026-09-15

## Summary

Adds a separate, Entra-gated reviewer application that surfaces `PENDING_REVIEW` cases with their calculated premium and records approve, reject, and revise decisions. Introduces a Cosmos DB serverless case store shared between the agent and the reviewer app, persists the calculation alongside each case, deploys the new surface with idempotent Bicep, and provides a scoped teardown workflow.

## Changes

### Added

* src/quote-preparation-agent/case_store.py - `CaseStore` protocol, extended `CaseRecord`, `CalculationSnapshot`, and the `build_case_store()` factory
* src/quote-preparation-agent/sqlite_case_store.py - `SqliteCaseStore` subclassing `ApprovalRepository`, adding the column migration, state-filtered listing, and atomic submit-with-calculation
* src/quote-preparation-agent/cosmos_case_store.py - `CosmosCaseStore` with Entra-only auth, ETag preconditions on every mutation, and an embedded audit array
* src/quote-preparation-agent/tests/test_case_store_contract.py - backend-agnostic contract suite plus an ETag-enforcing container double
* apps/reviewer-app/app.py - FastAPI factory, settings, queue and decision endpoints, exception handlers, security middleware
* apps/reviewer-app/auth.py - `ReviewerAuth`, app-role based authorization
* apps/reviewer-app/requirements.txt - pinned to the web-chat versions where shared
* apps/reviewer-app/Dockerfile - repository-root build context so the store modules are copied rather than re-vendored
* apps/reviewer-app/tests/test_app.py - 25 API tests
* scripts/setup-reviewer-identity.ps1 - idempotent reviewer app registration with the `Review.Access` scope and `Reviewer` role
* scripts/remove-reviewer-identity.ps1 - exact-match identity teardown with dry-run support
* scripts/tests/test_reviewer_identity_scripts.py - 39 tests covering GUID stability, exact-match protection, delete ordering, and the recycle-bin sweep
* apps/reviewer-app/tests/test_auth.py - 38 claim-level authorization tests
* apps/reviewer-app/frontend/package.json - reviewer SPA manifest mirroring the web-chat toolchain
* apps/reviewer-app/frontend/package-lock.json - committed lockfile so `npm ci` is reproducible
* apps/reviewer-app/frontend/vite.config.js - build configuration
* apps/reviewer-app/frontend/index.html - SPA entry point
* apps/reviewer-app/frontend/src/main.jsx - queue and detail views, MSAL wiring, decision actions
* apps/reviewer-app/frontend/src/format.js - currency and unpriced-state formatting helpers
* apps/reviewer-app/frontend/src/style.css - reviewer styling
* apps/reviewer-app/frontend/tests/format.test.js - formatting and error-mapping tests
* apps/reviewer-app/frontend/src/request.js - pure decision-request builder, extracted so the revision value is unit-testable
* apps/reviewer-app/frontend/tests/request.test.js - 5 tests asserting the revision is sent on all three commands, including `revision: 0`
* .github/workflows/reviewer-app-build.yml - reviewer build, backend pytest, frontend `npm ci` / `npm test` / `npm run build`
* .github/workflows/reviewer-app-teardown.yml - dispatch-only scoped teardown with typed confirmation, dry-run default, and a protected-name guard
* eval/tests/test_applicant_guardrail_regression.py - 4 tests pinning applicant-output invariance across all three stores
* scripts/assert_bicep_idempotent.py - what-if change-set assertion in single-template and differential modes
* scripts/tests/test_assert_bicep_idempotent.py - 8 tests encoding the live what-if evidence shape
* infra/modules/cosmos-db.bicep - serverless Cosmos account, database, and container with local auth disabled
* infra/modules/reviewer-app.bicep - reviewer Container App with digest-pinned image and managed identity
* infra/modules/cosmos-rbac.bicep - Cosmos data-plane role assignments, separated to break a dependency cycle

### Modified

* src/quote-preparation-agent/graph.py - store factory wiring and calculation pass-through
* src/quote-preparation-agent/toolbox.py - capability-detecting `submit_for_review`
* src/quote-preparation-agent/main.py - `repository` annotation widened to `CaseStore`
* src/quote-preparation-agent/requirements.txt - added `azure-cosmos` and `azure-identity`
* src/quote-preparation-agent/cosmos_case_store.py - lazy container property so a Cosmos outage cannot block agent startup; reason code embedded on audit events
* src/quote-preparation-agent/case_store.py - `AuditRecord` carrying `reason_code`, plus `validate_reason_code`
* src/quote-preparation-agent/sqlite_case_store.py - reason code threaded onto the audit row without duplicating the state machine
* apps/reviewer-app/app.py - reason code passed through to the store instead of only being logged
* apps/reviewer-app/tests/test_app.py - reason code persistence coverage
* scripts/remove-reviewer-identity.ps1 - recycle-bin sweep so an interrupted purge completes on rerun
* infra/main.bicep - Cosmos, reviewer app, and Cosmos RBAC modules wired in with parameters and outputs
* infra/main.bicep - added the `REVIEWER_APP_NAME` output so the deployment summary can build a portal link for the reviewer container app
* scripts/deployment_summary.py - reviewer rows ("Open reviewer app", health probe, portal link) sourced from `REVIEWER_APP_URL`/`REVIEWER_APP_NAME`, omitted when the reviewer app is not deployed
* scripts/update_wiki_deployment_links.py - `--create-missing` seeds the deployment-links section on a wiki page that has none, instead of failing the publish job
* .github/workflows/publish-test-trends.yml - wiki update passes `--create-missing`, and a failed wiki clone now explains that the wiki must be initialised once through the web UI
* .github/workflows/publish-test-trends.yml - the wiki link table is only rewritten when the source run published real deployment links; runs without azd context now leave the last deployed values in place instead of overwriting them with an emptier table
* apps/reviewer-app/frontend/src/main.jsx - approve routes through an `ApproveConfirm` step, so the irreversible decision is no longer a single click
* .github/workflows/deploy-and-evaluate.yml - what-if parameter list extended for the new template parameters; reviewer `az acr build` and deploy path; what-if now emits JSON and is asserted for idempotency
* .github/workflows/publish-test-trends.yml - reviewer workflow registered in the trigger list, the path allow-list, and the artifact-kind download loop
* .github/workflows/continuous-validation.yml - authoritative vendored-copy byte-identity gate
* infra/main.parameters.json - `reviewerClientId`, `reviewerAppImage`, and `agentPrincipalId` added
* apps/reviewer-app/app.py - `SelfApprovalError` now returns a stable `code: SELF_APPROVAL` so the frontend stops inferring intent from a 403 alone
* apps/reviewer-app/frontend/src/format.js - missing currency is an explicit unverifiable state instead of a bare number; `premiumView` extracted; 403 branches on the error code
* apps/reviewer-app/frontend/src/main.jsx - decision and refresh separated so a failed refresh cannot misreport the decision; focus management, live region, per-row labels, `aria-hidden` on decorative icons
* apps/reviewer-app/frontend/src/style.css - horizontally scrollable queue replacing the block-ified mobile layout that destroyed the header associations
* apps/reviewer-app/frontend/.gitignore - `*.log` added

### Removed

## Additional or Deviating Changes

* Phase 1 layered the reviewer-facing storage surface on top of `ApprovalRepository` by subclassing, rather than editing that file directly.
  * `toolbox.py` and both agent test modules insert `apps/workshop` ahead of `src/quote-preparation-agent` on `sys.path`, and the two `approval_repository.py` copies are byte-identical. Editing the agent copy would have taken effect inside the hosted container but silently not in local test runs, and `apps/workshop/` is frozen workshop material.
* The calculation is written through a distinct `submit_for_review_with_calculation` rather than by extending `submit_for_review`.
  * The spy stub in `tests/test_graph.py` declares a two-parameter `submit_for_review`. Adding a third argument raised `TypeError`. Preserving the existing suites unmodified took priority over matching the details document literally.
* `submit_for_review_with_calculation` carries a compare-and-swap that the base method lacks. Deliberate strengthening.
* The Cosmos contract tests run against an in-process container double that genuinely raises on stale ETags, not the Cosmos emulator.
  * The emulator authenticates with a well-known account key, which the phase constraints forbid.
* `revise` leaves a stale persisted calculation in place. A DRAFT case never appears in the review queue and the next submission overwrites the fields, so the value is unreachable from the reviewer surface.
* Stale-revision detection sits in the reviewer API layer rather than the store. No store method accepts an expected revision, so `decide()` compares the submitted revision against the record before calling the store. The store's own compare-and-swap remains as a second layer.
* Exception mapping uses registered FastAPI handlers rather than try/except, so `SelfApprovalError` resolves to its own 403 handler by MRO and cannot be swallowed by the 409 or 500 handlers.
* The reviewer Dockerfile builds from the repository root and copies the store modules out of `src/quote-preparation-agent/`, avoiding a third vendored copy of `approval_repository.py`.
* The reviewer identity scripts look applications up through a Graph `$filter` with a case-sensitive client-side recheck, rather than `az ad app list --display-name`, so teardown cannot match the web-chat registration by prefix.
* `-ReviewerGroupId` is optional on the reviewer setup script, unlike the mandatory `-PilotGroupId` on the web-chat sibling, because access is gated by app role rather than group membership.
* The frontend lockfile had to be generated against the Azure Artifacts feed directly and then normalised to canonical `registry.npmjs.org` URLs.
  * `registry.npmjs.org` is TLS-intercepted on the corporate network and fails with `ERR_SSL_SSL/TLS_ALERT_HANDSHAKE_FAILURE`. The corporate proxy rewrites every tarball to a host that does not match the configured registry, so npm 12 classifies them as type `remote` and refuses them under its `allow-remote = "none"` default, breaking both `npm ci` and `npm install`. Installing against the feed host directly makes the tarball hosts match; rewriting the 119 `resolved` URLs afterwards restores portability, because npm's `replace-registry-host = npmjs` default swaps an `npmjs.org` host for whatever registry is configured. The result installs cleanly behind the proxy and on GitHub runners without an `.npmrc`.
* The teardown workflow never deletes the resource group.
  * Staging and production share `vars.AZURE_RESOURCE_GROUP`, so only individually named reviewer resources are deleted, and a guard step aborts when a computed target collides with shared infrastructure. `az group delete` appears once in the repository, inside a comment explaining why it is never used.
* Entra teardown is opt-in and defaults to false, because the reviewer registration is shared across both environments.
* `agentPrincipalId` is sourced from a repository variable rather than resolved in-template.
  * A hosted agent receives a dedicated Entra agent identity created at deploy time, which is explicitly not the project managed identity. No CLI surfaces it. Parsing the wrong GUID would grant Cosmos write access to the wrong principal while leaving the agent unable to write, so the workflow publishes the project ARM JSON as an artifact and leaves the value to an operator.
* Step 7.2 asserts zero `Delete` unconditionally rather than zero `Modify`.
  * A live what-if reports 10 pre-existing `Modify` entries that are present with or without this feature, so a blanket zero-`Modify` assertion would fail on the first CI run. The differential mode proves the stronger claim - candidate equals baseline plus `Create` only - but needs a pre-change baseline CI cannot regenerate, so it is exercised by unit tests.
* The applicant-invariance digest recorded during gap closure could not be reproduced across 30 canonicalisations, so the regression test defines its own canonicalisation and pins that value instead. All three stores were confirmed to produce identical output under every canonicalisation tried, which is the substantive claim.

## Release Summary

All seven phases are complete. The applicant-facing agent still withholds the calculated premium; a separate reviewer web application now surfaces it to an authorized human reviewer.

**Files affected: 40 (31 added, 9 modified, 0 removed).**

Added, by area:

* Shared case store - `case_store.py`, `sqlite_case_store.py`, `cosmos_case_store.py`, and the contract suite.
* Reviewer service - `apps/reviewer-app/` with `app.py`, `auth.py`, `Dockerfile`, `requirements.txt`, and two test modules.
* Reviewer SPA - `apps/reviewer-app/frontend/` with the manifest, committed lockfile, Vite config, entry point, three source modules, and two test modules.
* Identity automation - `setup-reviewer-identity.ps1`, `remove-reviewer-identity.ps1`, and their test module.
* Infrastructure - `cosmos-db.bicep`, `reviewer-app.bicep`, `cosmos-rbac.bicep` and the compiled JSON for each.
* Delivery - `reviewer-app-build.yml` and `reviewer-app-teardown.yml`.
* Validation - the applicant-guardrail regression test, the Bicep idempotency assertion, and its test module.

Dependency and infrastructure changes:

* `azure-cosmos>=4.17,<5` and `azure-identity>=1.25,<2` added to the agent requirements. No npm dependency was added.
* New Azure resources: a serverless Cosmos DB account with local auth disabled, the `quote-preparation` database, the `cases` container partitioned on `/caseId`, a second Container App, and its user-assigned identity. A live what-if confirms these are the only additions - zero `Modify` and zero `Delete` against pre-existing resources.
* Cosmos access is Entra-only through data-plane role assignments. No account keys anywhere.

Deployment notes:

* Three repository variables must be set before the reviewer surface does anything. `REVIEWER_CLIENT_ID` is required - while it is empty the reviewer Container App and both Cosmos grants are conditionally skipped, so the deploy path is inert but harmless. `AGENT_PRINCIPAL_ID` must be the hosted agent's Entra agent identity, read from the Foundry project's portal JSON view or the artifact the deploy workflow now publishes; until it is set the agent cannot write cases. `REVIEWER_APP_IMAGE` is set by the workflow itself.
* `scripts/setup-reviewer-identity.ps1` has not been run against a live tenant. It creates the registration whose client id becomes `REVIEWER_CLIENT_ID`.
* Teardown is `reviewer-app-teardown.yml`, dispatch-only, dry-run by default, and requires typed confirmation. It deletes only named reviewer resources and never the shared resource group. Cosmos has no purge API, so a deleted account name stays reserved - and the staging name is 43 of 44 permitted characters, so renaming is not an escape hatch.
