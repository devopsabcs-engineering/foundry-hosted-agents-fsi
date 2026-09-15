<!-- markdownlint-disable-file -->
# Implementation Details: Reviewer App (Option C)

**Related Plan**: reviewer-app-plan.instructions.md

## Phase 1: Shared case store and calculation persistence

### Step 1.1: Extract a `CaseStore` protocol

Create `src/quote-preparation-agent/case_store.py` defining a `typing.Protocol` named `CaseStore` that captures the exact public surface of the existing `ApprovalRepository`: `create_draft`, `submit_for_review`, `approve`, `reject`, `revise`, `get_case`, `get_audit_trail` (verify the real name while reading the file), plus the new `list_cases_by_state` from step 1.3.

Re-export the existing exception types unchanged. Do not move or rename them. `SelfApprovalError` must remain a sibling of `InvalidTransitionError`, not a subclass, because the HTTP layer maps them to different status codes.

`ApprovalRepository` must satisfy the protocol without modification to its method signatures.

### Step 1.2: Extend the case record with persisted calculation fields

Add optional fields to `CaseRecord`: `amount_cents: int | None`, `currency: str | None`, `period: str | None`, `calculation_status: str | None`, `rule_ids: tuple[str, ...]`, `issues: tuple[str, ...]`, `rulebook_version: str | None`.

All must default such that existing constructor call sites and tests keep working. Add the matching nullable columns to the SQLite `CREATE TABLE`, and guard with a lightweight migration so an existing database file does not fail to open. Read the current `CREATE TABLE` statement verbatim before editing.

Critical: `amount_cents` must accept null. `composition_node` submits for review regardless of calculation status, so `CASE-SYN-003` (UNSUPPORTED) and `CASE-SYN-005` (MISSING_PLAN) legitimately reach `PENDING_REVIEW` with no amount. The reviewer UI must render that state rather than assume a number exists.

### Step 1.3: Add a state-filtered listing method

Add `list_cases_by_state(state: str, limit: int = 100) -> tuple[CaseRecord, ...]` ordered by `updated_at` descending. Validate `state` against the existing state constants and raise `ValueError` for anything else. Do not build the SQL by string concatenation of caller input.

### Step 1.4: Implement `CosmosCaseStore`

Create `src/quote-preparation-agent/cosmos_case_store.py` using `azure-cosmos` with `DefaultAzureCredential`. The repository has no Key Vault convention and the account is provisioned with local auth disabled, so authenticate with managed identity only. Never accept an account key parameter.

Preserve these four semantics exactly. They are the traps that a naive port breaks silently:

1. Compare-and-swap. The SQLite implementation guards with `UPDATE ... WHERE state = ? AND revision = ?` and checks `changes()`. The Cosmos equivalent is `replace_item` with `etag` and `match_condition=MatchConditions.IfNotModified`. A read-modify-write without the precondition passes single-threaded tests and still lets a second reviewer overwrite the first decision. On precondition failure, raise `InvalidTransitionError`.
2. Atomic case plus audit write. SQLite writes both in one transaction. Use a transactional batch with the case id as the partition key, or embed the audit events as an array on the case document. Choose one and state it in the module docstring.
3. Check order in the decision path. Self-approval, then idempotent replay, then state guard, then compare-and-swap. The replay branch returns before any write. An upsert-shaped port appends a duplicate audit event on every replay.
4. `revise` reassigns `preparer_id` to the acting reviewer and carries no optimistic guard in the SQLite version, relying on a process-local lock that gives zero protection across replicas. The Cosmos implementation must add the ETag precondition here. Record this as a deliberate strengthening in the changes log.

Partition key: `/caseId`. Container id: `cases`. Database id: `quote-preparation`.

### Step 1.5: Store factory and graph wiring

Add `build_case_store()` to `case_store.py` returning `CosmosCaseStore` when `COSMOS_ENDPOINT` is set and `ApprovalRepository` otherwise. Change `graph.py` line 179 to call the factory instead of constructing `toolbox.ApprovalRepository()` directly. Keep the injected-repository parameter so the existing spy stub in `tests/test_graph.py` still works untouched.

### Step 1.6: Persist the calculation at submission

In `composition_node`, after `toolbox.calculate_quote` returns and before or during `submit_for_review`, persist the calculation onto the case. Extend `submit_for_review` to accept the calculation payload rather than adding a second write, so the case and its amount become visible to reviewers atomically.

Do not alter `applicant_message` construction, `_STATUS_TEMPLATES`, or `_bounded_message`. The applicant response must be byte-identical before and after this change, and step 7.1 asserts that.

Record `rulebook_version` from the loaded rulebook so the persisted amount is traceable to the rules that produced it.

### Step 1.7: Backend-agnostic contract tests

Create `src/quote-preparation-agent/tests/test_case_store_contract.py` with a single suite parameterised over both backends. Cover the full state machine, revision invalidation, self-approval rejection, idempotent replay producing no additional audit event, concurrent decision where the loser raises, listing by state, and null-amount cases.

There is no `pytest-asyncio` and no `conftest.py` in this repository. Do not introduce async tests. Follow the existing in-file `sys.path.insert` plus `# noqa: E402` import convention.

For the Cosmos backend, prefer the Cosmos DB emulator when reachable and skip with a clear reason when it is not. A hand-written fake is acceptable only if it enforces ETag preconditions, otherwise it defeats the purpose of the suite.

## Phase 2: Reviewer API service

### Step 2.1: Scaffold

Create `apps/reviewer-app/` mirroring `apps/web-chat/`: `app.py`, `auth.py`, `requirements.txt`, `Dockerfile`, `tests/`, `frontend/`. Copy the structural conventions from `apps/web-chat/app.py`, specifically the frozen `Settings` dataclass with `from_env`, `create_app(settings=None, verifier=None, store=None)` injection seams, the `security_headers` middleware, and the static mount of `frontend/dist`.

Drop everything chat-specific: `SessionStore`, `Conversation`, `FoundryClient`, SSE streaming, the semaphore, and the keepalive loop.

### Step 2.2: Endpoints

* `GET /healthz`
* `GET /api/config` returning tenant id, client id, and the reviewer scope
* `GET /api/me` returning the object id and reviewer role
* `GET /api/cases` returning the `PENDING_REVIEW` queue including `amountCents`, `currency`, `calculationStatus`, and `issues`
* `GET /api/cases/{case_id}` returning the case plus its audit trail
* `POST /api/cases/{case_id}/approve`
* `POST /api/cases/{case_id}/reject` accepting an optional `reasonCode`
* `POST /api/cases/{case_id}/revise` accepting an optional `reasonCode`

Decision bodies take a `revision` field. Pass it through to the store so a reviewer acting on a stale page loses the compare-and-swap rather than overwriting a newer decision.

Use Pydantic models with `ConfigDict(extra="forbid")` and explicit length bounds, matching the existing `Message` model.

### Step 2.3: Exception mapping

`CaseNotFoundError` to 404. `SelfApprovalError` to 403. `InvalidTransitionError` and `CaseAlreadyExistsError` to 409. Any other `ApprovalRepositoryError` to 500 with a generic body.

`SelfApprovalError` does not inherit from `InvalidTransitionError`. Handling only the latter lets self-approval escape as an unhandled 500.

### Step 2.4: Idempotency

Accept an `Idempotency-Key` header on decision endpoints and rely on the store's existing replay behaviour rather than adding a second caching layer.

### Step 2.5: Tests

Create `apps/reviewer-app/tests/test_app.py`. Fake auth with a small duck-typed class passed to `create_app`, following the existing convention. Do not use `dependency_overrides` or `unittest.mock`. Use `TestClient` as a context manager so lifespan fires. Cover: unauthorized, wrong role, empty queue, populated queue including a null-amount case, approve, self-approval forbidden, stale revision conflict, and replay.

## Phase 3: Reviewer identity and Entra automation

### Step 3.1: Reviewer auth module

Copy `apps/web-chat/auth.py` to `apps/reviewer-app/auth.py` and change the authorization check from group membership to app role membership: `if self.required_role not in claims.get("roles", [])`.

`roles` carries role value strings, not GUIDs. Remove the `uuid.UUID()` normalization that `Settings.from_env` applies to the group id, or the app will fail to start. Keep tenant, audience, scope, and non-empty `oid` validation. The scope becomes `Review.Access`. The role value is `Reviewer`.

### Step 3.2: Registration script

Create `scripts/setup-reviewer-identity.ps1` modelled on the existing `scripts/setup-web-chat-identity.ps1`, which uses `az rest` against Microsoft Graph v1.0. Generate new GUIDs for the `Review.Access` scope and the `Reviewer` app role. Do not reuse the web-chat GUIDs.

The script must be idempotent: look the application up by display name first, patch when it exists, create when it does not, and exit zero on a repeat run with no changes. Emit the resulting client id in a form the deploy workflow can consume.

This script requires Microsoft Graph `Application.ReadWrite.All`. It runs identically in CI or on an administrator workstation, so the path is not blocked if the CI identity lacks Graph rights. Fail with an explicit, actionable message when the permission is missing rather than a raw Graph error.

### Step 3.3: Identity teardown script

Create `scripts/remove-reviewer-identity.ps1`. Delete the application registration and its service principal by display name. Support `-WhatIf`. Exit zero when the objects are already absent.

### Step 3.4: Auth tests

Create `apps/reviewer-app/tests/test_auth.py`. Build claim dictionaries directly and assert accept or reject. Cover: missing bearer prefix, wrong tenant, wrong audience, missing scope, missing role, empty `oid`, and the success path.

## Phase 4: Reviewer frontend

### Step 4.1: Scaffold

Read `apps/web-chat/frontend/package.json` and its build config, then mirror the same framework version, bundler, and script names in `apps/reviewer-app/frontend/`. Match the existing toolchain rather than introducing a different one.

### Step 4.2: Views

A queue list showing case id, state, revision, preparer, submitted timestamp, and the formatted premium. Render cases with no amount as an explicit unpriced state showing the issue codes, never as a zero or a blank.

A detail view showing the full calculation, rule ids, rulebook version, and audit trail, with approve, reject, and revise actions. Reject and revise prompt for an optional reason code.

Format currency from `amountCents` using the stored currency. Do not hardcode a dollar sign.

Carry the training-simulation notice on every view, consistent with the applicant surface.

### Step 4.3: MSAL

Copy the MSAL configuration approach from the web-chat frontend, changing the requested scope to the reviewer app's `Review.Access`. Attach the token as a bearer header. There is no SSE here, so use plain fetch.

### Step 4.4: Lockfile and container build

Commit the lockfile for the reviewer frontend. The web-chat frontend has none, which breaks `npm ci` in a container build. Verify the Dockerfile builds the SPA and copies `dist` into the image, matching the web-chat Dockerfile structure.

## Phase 5: Infrastructure as code

### Step 5.1: Cosmos module

Create `infra/modules/cosmos-db.bicep`: a `Microsoft.DocumentDB/databaseAccounts` resource with the `EnableServerless` capability, `disableLocalAuth: true`, a SQL database, and a `cases` container partitioned on `/caseId`.

Follow the repository's plain interpolation naming, for example `'cosmos-${environmentName}'`. There is no `uniqueString` or resource token convention here, and no azd resource tagging. Do not introduce one.

Note that a Cosmos account name is globally unique and lowercase-constrained. Validate the derived name.

### Step 5.2: Reviewer Container App module

Create `infra/modules/reviewer-app.bicep`. Read `infra/web-chat.bicep` for the Container App shape, but take the parameters and wiring style from the modules under `infra/modules/`, since the reviewer app is a module rather than a standalone template.

Be careful: `environmentName` is overloaded in this repository. In `main.bicep` it is the azd base name; in `web-chat.bicep` it is the Container Apps managed environment name. Pass the managed environment explicitly and do not copy the ambiguous parameter.

The image must be digest-pinned through a parameter, matching how CI resolves and passes image digests today.

### Step 5.3: Wire into main.bicep

Add both modules to `infra/main.bicep`, which is `targetScope = 'resourceGroup'`. Add parameters and outputs following the existing style. Output the Cosmos endpoint and the reviewer app FQDN.

### Step 5.4: Cosmos data-plane RBAC

This is the highest-risk step. Every other role assignment in this repository uses `Microsoft.Authorization/roleAssignments` with `subscriptionResourceId`. Cosmos data-plane access does not work that way. Use `Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments` referencing a built-in `sqlRoleDefinitions` id, with the data-plane scope supplied as a string property. Using the ARM pattern deploys successfully and then fails at runtime with a 403.

Assign the built-in Cosmos DB Built-in Data Contributor role to the reviewer Container App identity and to the agent identity. Resolve the agent principal id before writing this step; the hosted agent is deployed by azd rather than by Bicep, so confirm which identity actually runs it instead of assuming the Foundry account or project identity. Report back if it cannot be resolved.

Use `guid()` over the scope and principal for deterministic assignment names so redeployment is idempotent.

### Step 5.5: CI what-if parameters

The `bicep-validate` job hand-maintains its `--parameters` list. Any new required parameter on `main.bicep` breaks it. Update both occurrences in `deploy-and-evaluate.yml`, or give the new parameters defaults so the list stays valid.

## Phase 6: Delivery and teardown workflows

### Step 6.1: Build workflow

Create `.github/workflows/reviewer-app-build.yml` modelled on `web-chat-build.yml`: Python 3.13, Node 22, pytest from the repository root with `-v --junitxml`, and `PYTHONPATH: apps/reviewer-app`.

### Step 6.2: Deploy path

Follow the established mechanics exactly: authenticate with `azure/login@v3` using `vars.AZURE_CLIENT_ID`, `vars.AZURE_TENANT_ID`, and `vars.AZURE_SUBSCRIPTION_ID` with workflow-level `permissions: id-token: write`. This repository uses OIDC and repository variables, not secrets.

Build with `az acr build`, never Docker. Tag as `${GITHUB_SHA}-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}`, resolve to a digest, validate it against `^sha256:[a-f0-9]{64}$`, and deploy by digest. Update the Container App through the Bicep parameter and `azd provision`, not `az containerapp update`.

### Step 6.3: Teardown workflow

Create `.github/workflows/reviewer-app-teardown.yml`, triggered by `workflow_dispatch` only.

Never call `az group delete`. Staging and production share a resource group, so deleting it is a production outage.

Inputs: an environment selector, and a confirmation string the operator must type to match the target environment name. Refuse to proceed on mismatch.

Default to a dry run that lists what would be deleted. Require an explicit flag to perform deletion.

Delete, in order, and idempotently so a rerun after partial failure succeeds: the reviewer Container App, the Cosmos SQL container and database, the Cosmos account, then the Entra objects by invoking `scripts/remove-reviewer-identity.ps1`.

Handle Cosmos soft delete. A deleted account name can remain reserved and block recreation. Document the behaviour observed and purge where the API supports it.

Do not delete shared resources: the ACR, the Container Apps environment, Log Analytics, Application Insights, the Foundry account, or anything declared `existing` in Bicep.

### Step 6.4: Test trends

`publish-test-trends.yml` hard-codes an allow-list of source workflow paths and artifact names. Add the reviewer app workflow in both places or its results are invisible.

## Phase 7: Validation

### Step 7.1: Applicant guardrail regression

Add a test asserting that for every fixture, the `applicant_message` produced after the Phase 1 changes is identical to the current output and contains no digits from `amountCents`. Confirm `no_invented_amount` in `eval/deterministic-tests/checks.py` still passes. This is the guarantee that persisting the premium did not leak it to applicants.

### Step 7.2: Bicep idempotency

Add a validation step proving redeployment is a no-op: run `az deployment group what-if` against the already-deployed template and assert no resource shows as modified or deleted. Deterministic `guid()` role assignment names and fixed resource names are what make this hold.

### Step 7.3: Full suite

Run every test suite in the repository from the root, plus the new contract, API, and auth suites. Record pass and fail counts in the changes log. Report any pre-existing failure separately from regressions introduced here.
