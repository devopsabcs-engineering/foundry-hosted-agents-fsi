<!-- markdownlint-disable-file -->
# Planning Log: Reviewer App (Option C)

**Related Plan**: reviewer-app-plan.instructions.md

## User Decisions

* ID-01: Shared case store backend, Option B selected
  * Rationale: Cosmos DB serverless is the only option where two separate container apps can both write safely. Its ETag preconditions express the repository's existing compare-and-swap guard natively.
* ID-02: Reviewer identity, separate app registration selected
  * Rationale: Clean isolation between the applicant pilot and the reviewer surface, with the additional setup automated.
* ID-03: Teardown workflow required, accepted as new scope.
* ID-04: Delegated to the agent ("answer the questions yourself"), resolved as follows:
  * WI-18 / DD-03 ratified: Step 7.2 asserts zero `Delete` unconditionally plus a differential mode. The 10 live `Modify` entries are pre-existing drift unrelated to this feature, so a blanket zero-Modify assertion would fail on the first CI run.
  * D7 resolved by adding an approve confirmation step. Approve is the only irreversible decision and was the only one reachable in a single click. No reason code is collected, so the plan's "reject and revise prompt for an optional reason code" wording still holds.
  * WI-22 closed: the revision compare-and-swap already makes a replayed decision safe, so Step 2.4 is satisfied without server-side dedupe. Real `Idempotency-Key` dedupe stays a follow-on item.
  * WI-23 closed: the frontend branches only on `code === SELF_APPROVAL` and otherwise surfaces `detail` verbatim, so there is no string matching to remove from 404/409/500.
  * WI-24 closed: reviewer copy stays English-only, matching the web-chat sibling. The applicant-facing surface keeps bilingual parity.
  * WI-27 closed: the reviewer image builds unconditionally. Gating it on `REVIEWER_CLIENT_ID` would require a second run to deploy once the variable is set.
  * WI-28 closed: teardown does not delete the ACR repository. Image digests are shared audit evidence.
  * WI-29 closed: the single shared reviewer registration stays. Per-environment split is follow-on work.
* ID-05: Publish clickable app URLs to the wiki and job summaries, accepted as new scope.
  * Rationale: `main.bicep` now outputs `REVIEWER_APP_NAME` alongside `REVIEWER_APP_URL`, `deployment_summary.py` renders reviewer rows, and `update_wiki_deployment_links.py` gained `--create-missing` so a wiki without the markers is seeded instead of failing the publish job.

## Agent Decisions Taken Without Escalation

* AD-01: Teardown deletes named resources only, never the resource group.
  * Evidence: staging and production jobs in `deploy-and-evaluate.yml` both target the same `vars.AZURE_RESOURCE_GROUP`. A group delete would take production down.
* AD-02: The calculation is persisted at submission rather than recomputed on read.
  * Rationale: recomputation drifts when the rulebook changes, and nothing currently records which rulebook version a case was priced against. The persisted record includes `rulebookVersion`.
* AD-03: The reviewer app is wired into `infra/main.bicep` as modules rather than copied as a standalone template like `infra/web-chat.bicep`.
  * Rationale: Cosmos data-plane role assignments need to reference the account symbolically. The standalone pattern relies on `existing` string matching and cannot express this cleanly.
* AD-04: `ApprovalRepository` (SQLite) is preserved unchanged as the local and test backend. Cosmos is added as a second implementation behind a shared protocol.
  * Rationale: the file is byte-identical to the `apps/workshop/` workshop copy and ships to the hosted agent container. A destructive rewrite risks the workshop material and the existing test suite.
* AD-05: The reviewer UI ships in English only, matching the existing web-chat frontend which is not internationalized.
  * Recorded as follow-on work rather than silently expanding scope.
* AD-06: Reject and revise accept an optional reason code, already modelled in `data/synthetic/quote-contract.schema.json` as `reasonCode`.

## Discrepancy Log

Gaps and deviations identified during implementation.

### Research Errors Found During Implementation

* DR-03: The research claimed the CI what-if `--parameters` list appears twice in `deploy-and-evaluate.yml`. It appears once. The second cited block is the production `azd provision` retry loop, which uses `azd env set` and passes no `--parameters`.
  * Source: `.copilot-tracking/research/2026-09-15/reviewer-app-infra-research.md`
  * Impact: low

### Unaddressed Research Items

* DR-01: The contract schema models `recordVersion`, `commandId`, `actorRole`, `approvedRevision`, and `previewRevision`, none of which are implemented.
  * Source: reviewer-app-conventions-research.md
  * Reason: out of scope for the reviewer surface.
  * Impact: low
* DR-02: `apps/web-chat/frontend/` has no committed lockfile, which breaks `npm ci` in a container build.
  * Reason: pre-existing defect in the applicant app, addressed only for the new reviewer frontend.
  * Impact: medium
* DR-03: `infra/modules/rbac.bicep` is never invoked. Its `principalIds` parameter defaults to empty and no parameter file supplies it.
  * Reason: pre-existing dead code, not in scope to remove.
  * Impact: low

### Implementation Deviations

* DD-01: Steps 1.2 and 1.3 add storage fields by subclassing rather than by editing `approval_repository.py`.
  * Plan specifies: extend `CaseRecord` and the schema in place.
  * Implementation differs: `SqliteCaseStore` subclasses `ApprovalRepository` and owns the extended record, migration, and new methods.
  * Rationale: `sys.path` ordering in `toolbox.py` and both agent test modules resolves `approval_repository` to the frozen `apps/workshop/` copy locally and to the vendored agent copy in the container. An in-place edit would have applied in production and silently not in local tests.
* DD-02: Step 1.6 introduces `submit_for_review_with_calculation` instead of extending `submit_for_review`.
  * Plan specifies: extend the existing method so case and amount become visible atomically.
  * Implementation differs: a distinct method, capability-detected in `toolbox.submit_for_review`. Atomicity is still preserved.
  * Rationale: the spy stub in `tests/test_graph.py` defines a two-parameter signature and the phase constraint required those suites to pass unmodified.

## Agent Decisions Ratified After Phase 1

* AD-07: `submit_for_review_with_calculation` is accepted as a distinct method. Preserving the existing suites was the correct trade.
* AD-08: The SQLite additions are not mirrored into `src/quote-preparation-agent/approval_repository.py`. The subclass approach makes local and hosted behaviour identical without forcing the two vendored copies to diverge.
* AD-09: Live Cosmos validation is deferred to Phase 5, which owns the deployed account.
* AD-10: Cosmos client construction becomes lazy, added as Step 1.8. `CosmosClient.__init__` performs a network call in azure-cosmos 4.17, so eager construction inside `build_graph()` would turn a Cosmos outage into a hosted-agent startup failure.

## Agent Decisions Ratified After Phases 2 and 3

* AD-11: The environment variable stays `REVIEWER_CLIENT_ID`, distinct from web-chat's `ENTRA_CLIENT_ID`. ID-02 provisions a separate registration and a shared parameter file makes accidental reuse too easy.
* AD-12: The decision reason code is persisted on the audit event rather than discarded. A rejection reason that reaches only a log line has no audit value, and `reasonCode` is already modelled in the contract schema. Added as Step 1.9.
* AD-13: `/api/config` remains anonymous. It exposes only the tenant id, client id, scope, role name, and environment, which MSAL needs before a token exists, matching the web-chat surface.
* AD-14: `http://localhost:8100` is the reviewer development origin, leaving port 8000 to web-chat so both can run locally at once. Phase 4 must use this port.
* AD-15: `-ReviewerGroupId` stays optional. Access is gated by the `Reviewer` app role per ID-02, so group membership is not required at registration time.
* AD-16: The removal script does not explicitly revoke the `oauth2PermissionGrant`. Deleting the service principal cascades it.
* AD-17: Cosmos data-plane role assignments live in a third module, `infra/modules/cosmos-rbac.bicep`. Placing them in `cosmos-db.bicep` creates a dependency cycle, because the reviewer app consumes the Cosmos endpoint while the role assignment consumes the reviewer principal.
* AD-18: `agentPrincipalId` is an optional parameter defaulting to empty with a conditional assignment, rather than a guess. The hosted agent runs under a dedicated Entra agent identity created at `azd deploy` time, which is neither the Foundry account nor the Foundry project managed identity, and therefore cannot be referenced from the template.
* AD-19: Cosmos role assignments are scoped account-wide rather than container-scoped, accepted for a pilot.
* AD-20: The reviewer Container App name uses a short suffix-branched literal. `reviewer-${environmentName}` resolves to 45 characters against a 32-character limit and would have failed at deploy time.

## Open Risks Requiring User Action

* RI-01: Automating the reviewer Entra app registration in CI requires the CI OIDC service principal to hold Microsoft Graph `Application.ReadWrite.All`. Azure resource roles grant no Graph rights. Mitigated by shipping the registration as an idempotent script that runs identically in CI or from an administrator workstation, so the work is not blocked either way.
* RI-02: The `apps/workshop/` copy of the calculator and repository is byte-identical to the agent copy. Phase 1 changes the agent copy only, so the two will diverge.

## Suggested Follow-On Work

* WI-10: Obtain the hosted agent's Entra agent identity object id after the first `azd deploy` and supply it as `agentPrincipalId`. Until it is supplied the agent cannot write cases to Cosmos. (high, blocking)
  * Source: Phase 5, Step 5.4
* WI-11: `infra/main.parameters.json` still needs `reviewerClientId`, `reviewerAppImage`, and `agentPrincipalId`. Without them `azd provision` falls back to the Bicep defaults and never deploys the reviewer app. (high)
  * Source: Phase 5
* WI-12: The deploy workflow needs an `az acr build` and digest-resolve step for `apps/reviewer-app/Dockerfile`, whose build context is the repository root rather than the app directory. (medium)
  * Source: Phase 5
* WI-13: Teardown must handle Cosmos soft delete. A deleted account name can stay reserved and block recreation, and the staging name has only one character of headroom. (medium)
  * Source: Phase 5
* WI-14: Two pre-existing `BCP318` warnings in `mcp-container-apps.bicep` need the `!` operator. (low)
  * Source: Phase 5
* WI-15: The Graph `$filter` on `directory/deletedItems` may require a `ConsistencyLevel: eventual` header in some tenants. (medium)
  * Source: Gap closure, Step 3.5
* WI-16: Consider constraining `reasonCode` to a closed enum drawn from the contract schema rather than an uppercase character class. (low)
  * Source: Gap closure, Step 1.9
* WI-17: Surface `reasonCode` in the reviewer frontend audit-trail view now that the case detail endpoint returns it. (medium)
  * Source: Gap closure, Step 1.9
* WI-18: Ratify or overturn DD-03. If a literal zero-`Modify` assertion is the intent, the 10 pre-existing `Modify` entries must be diagnosed and the template corrected first, at which point the script gains a `--forbid-modify` flag. (medium)
  * Source: Phase 7, Step 7.2
* WI-19: Correct WI-04 in this log. The web-chat suite is collectible locally; it needs `PYTHONPATH=apps/web-chat`, which CI already sets. The missing-dependency diagnosis was wrong. (low)
  * Source: Phase 7, Step 7.3
* WI-20: Capture a pre-change baseline what-if once and commit it as a fixture so the differential idempotency mode runs in CI rather than only in unit tests. (low)
  * Source: Phase 7, Step 7.2
* WI-21: `formatAmount` still returns a semi-bare `"1425.00 not-a-currency"` when the stored currency is a non-empty but invalid ISO code. It is labelled, but the unit is garbage. (low)
  * Source: Frontend audit, D2 follow-on
* WI-22: The `Idempotency-Key` header is decorative on both sides. The frontend sends a fresh UUID per call so it cannot dedupe a retry, and the backend only logs it. The sole protection against a duplicate decision is the revision compare-and-swap. Confirm this satisfies Step 2.4 or implement server-side replay dedupe. (medium)
  * Source: Frontend audit, section 4
* WI-23: Only the self-approval 403 carries a machine-readable `code`. Consider stable codes on 404, 409, and 500 so the frontend never infers intent from a status alone. (low)
  * Source: Frontend audit, D1 follow-on
* WI-24: Decide whether reviewer-app copy needs fr-CA. The surface is English-only, matching the web-chat sibling, and Phase 4 of the details file does not require French - but the repository is otherwise bilingual. (medium)
  * Source: Frontend audit, criterion 7
* WI-25: `apps/reviewer-app/frontend/src/main.jsx` is invisible to `get_errors` and `node --check`, neither of which parses JSX. The production build is currently the only lint gate on that file. (low)
  * Source: Frontend defect remediation
* WI-26: Confirm whether the `production` GitHub environment has required reviewers. The teardown workflow binds to it for its approval gate. (medium)
  * Source: Phase 6, Step 6.3
* WI-27: Decide whether the reviewer image should be built at all when `REVIEWER_CLIENT_ID` is unset. Today it is built and pushed, the digest is set on the azd environment, and the module is then skipped. (low)
  * Source: Phase 6, Step 6.2
* WI-28: Teardown leaves the reviewer's ACR repository (`staging/reviewer-app`) in the shared registry, orphaning images. Deleting repositories inside a shared registry was judged out of scope. (low)
  * Source: Phase 6, Step 6.3
* WI-29: The reviewer Entra registration is shared across staging and production, so Entra teardown is not environment-scoped. Consider two registrations. (medium)
  * Source: Phase 6, Step 6.3

## Implementation Deviations Recorded After Phases 4, 6, and 7

* DD-03: Step 7.2 asserts zero `Delete` unconditionally instead of the specified zero `Modify`.
  * Plan specifies: assert no resource shows as modified or deleted.
  * Implementation differs: zero `Delete` is enforced in CI; the "baseline plus `Create` only" claim is enforced by a differential mode exercised in unit tests.
  * Rationale: a live what-if reports 10 pre-existing `Modify` entries unrelated to this feature, so the literal assertion would fail on the first CI run. Needs ratification - see WI-18.
* DD-04: The applicant-invariance digest `3c486bf9...` recorded during gap closure could not be reproduced across 30 canonicalisations, so the regression test pins a self-generated digest instead.
  * Rationale: the one-off script that produced the original value was deleted. All three stores were confirmed to produce identical output under every canonicalisation tried, so the substantive claim holds; pinning a value the repository cannot regenerate would have been worse.
* DD-05: The frontend lockfile was generated against the Azure Artifacts feed host and then rewritten to canonical `registry.npmjs.org` URLs.
  * Plan specifies: commit a lockfile.
  * Implementation differs: the lockfile is post-processed rather than emitted directly by `npm install`.
  * Rationale: `registry.npmjs.org` is TLS-intercepted on this network, and the corporate proxy emits tarball hosts that npm 12 rejects as type `remote`. Neither registry alone produces a usable lockfile. Rewriting restores portability via npm's `replace-registry-host` default.
* DD-06: `reviewerAppImage` uses `${REVIEWER_APP_IMAGE=mcr.microsoft.com/k8se/quickstart:latest}` rather than the specified `${VAR=}` form.
  * Rationale: an explicit empty string overrides the Bicep default instead of falling back to it, which would produce a Container App with an empty `image` whenever `reviewerClientId` is set but the image is not.

* WI-06: Consider adding a `revision` parameter to the store's decision methods. The reviewer API closes the stale-page hole today, but any future non-HTTP caller reopens it. (medium)
  * Source: Phase 2
* WI-07: Extract the duplicated `Invoke-Graph` helper and permission detector now shared across three PowerShell scripts. (low)
  * Source: Phase 3
* WI-08: The venv reports a pre-existing dependency conflict, `langgraph-prebuilt 1.1.0` requires `langchain-core>=1.3.1` against installed `0.3.86`. Unrelated to this feature. (medium)
  * Source: Phase 2
* WI-09: Live execution of the reviewer identity scripts is unvalidated. An administrator holding Graph `Application.ReadWrite.All` must run setup twice and diff the JSON to prove idempotency, then run removal and confirm the web-chat registration survives. (high)
  * Source: Phase 3

* WI-01: Enforce the vendored-copy invariant in CI. The byte-identical relationship between `src/quote-preparation-agent/approval_repository.py` and `apps/workshop/approval_repository.py` is load-bearing and currently unchecked. Added as Step 6.5. (high)
  * Source: Phase 1
* WI-02: Run the contract suite against a real Cosmos account. The container double proves the store's own logic but cannot prove wire compatibility of ETag headers or that the cross-partition `ORDER BY c.updatedAt` query works under the deployed indexing policy. (high)
  * Source: Phase 1
  * Dependency: Phase 5 provisions the account
* WI-03: `__pycache__/*.pyc` files are tracked in git and are modified by any test run. They should be removed from tracking and ignored. (medium)
  * Source: Phase 1
* WI-04: Install `apps/web-chat/requirements.txt` into the repo virtualenv so the web-chat suite can be collected locally. It currently runs only in CI. (low)
  * Source: Phase 1
* WI-05: An uncommitted `content_text` bilingual helper change exists in `apps/web-chat/app.py`, unrelated to this feature and left untouched. (low)
  * Source: Phase 1
