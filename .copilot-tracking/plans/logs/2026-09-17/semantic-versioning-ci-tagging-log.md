<!-- markdownlint-disable-file -->
# Planning Log: Semantic Versioning + CI/CD Docker Tagging

**Related Plan**: semantic-versioning-ci-tagging-plan.instructions.md

## Discrepancy Log

### Unaddressed Research Items

* None — research scope was fully consumed by the plan.

### Implementation Deviations

* DD-02: First real push-triggered run of both `release` jobs (2026-09-17) failed/misbehaved and
  required a follow-up fix commit before either app's redeploy could proceed.
  * Issue 1: `git tag "<name>"` creates a lightweight tag; `git push ... --follow-tags`
    only pushes annotated tags, so `web-chat-v1.0.1`/`reviewer-app-v1.0.1` were created
    locally on the runner but never reached `origin` on the first run.
  * Issue 2: both apps changed in the same commit, so both release jobs fired
    concurrently and both ran `git push origin HEAD:main` at nearly the same time;
    reviewer-app's push won the race, web-chat's was rejected (`! [rejected] (fetch first)`).
  * Fix: pushed a follow-up commit (`d88c268`/`714dd20`) changing both workflows to
    (a) push the tag ref explicitly (`git push origin "<tag>"`) instead of relying on
    `--follow-tags`, and (b) retry the branch push up to 5x with `git fetch` +
    `git rebase origin/main` between attempts. Re-run succeeded: `web-chat-v1.0.1` and
    `reviewer-app-v1.0.2` (reviewer-app bumped twice due to the race) both landed on
    `origin` with matching ACR tags `pilot/web-chat:v1.0.1` and `pilot/reviewer-app:v1.0.2`.
* DD-03: `azure.yaml`'s `rulebook-conn`/`application-conn` connection services used
  invalid `endpoint`/`type: remote-tool` fields (do not exist in azd's
  `azure.ai.connection` extension schema). Fixed to `target`/`category: RemoteTool`
  per the live schema at `Azure/azure-dev` on GitHub; commit `bdf4931`.
* DD-04: The AI Foundry project's own managed identity was never granted the
  `Foundry User` role, causing the hosted-evaluation step to fail with
  `PermissionDenied` on `.../assets/write` and `.../assets/read`.
  * Root cause: `infra/modules/rbac.bicep` already had the correct role
    assignments, but `infra/main.bicep`'s `rbac` module only ran when the external
    `principalIds` parameter was set (never true in practice).
  * Fix: always include `aiFoundry.outputs.projectPrincipalId` in `principalIds`,
    additive to any externally supplied ones; commit `3e6520b`. Verified via job
    logs on a fresh run (`35238867109`) that the PermissionDenied error is gone.
* DD-01: The plan adds Docker build+push to `web-chat-build.yml` and
  `reviewer-app-build.yml` rather than reusing `deploy-and-evaluate.yml`'s existing
  `az acr build` steps.
  * Plan specifies: new `release` job per app-build workflow, tagging `pilot/<app>:vX.Y.Z`.
  * Implementation differs from the pre-existing pattern: `deploy-and-evaluate.yml`
    tags images `staging/<name>:<sha>-<run>-<attempt>` and pins by digest for its
    manual staging→production promotion flow.
  * Rationale: user explicitly chose "automate build+push for both apps" as a new,
    parallel, commit-triggered artifact stream (`pilot/<app>:vX.Y.Z`), leaving the
    existing manual-dispatch staging/production pipeline untouched.

## Implementation Paths Considered

* Path A (chosen): add version-bump + git-tag + Docker build/push as a new job inside
  the existing `web-chat-build.yml` / `reviewer-app-build.yml`, gated to `push` on
  `main`, using `environment: staging` to satisfy the existing OIDC federated
  credential scoping.
  * Trade-off: couples release automation to the same workflow file as tests, but
    avoids creating and wiring a brand-new workflow + new federated credential.
* Path B (rejected): create a standalone new workflow file for release automation.
  * Trade-off: cleaner separation of concerns, but doubles the checkout/setup steps
    and requires duplicating the same `paths:` filters to trigger correctly — user
    explicitly chose Path A.
* Path C (rejected): limit Docker image tagging to reviewer-app only (leave web-chat's
  build manual, as today).
  * Trade-off: smaller/lower-risk change, but leaves web-chat permanently without any
    CI-driven image build — user explicitly chose to automate both apps instead.

## Suggested Follow-On Work

* WI-01: Consider whether the `deploy-and-evaluate.yml` production-promotion step
  should also re-tag the promoted digest with the same semver tag, so the version
  visible in the UI always matches what is actually running in production.
  * Source: Phase 5 design discussion.
  * Dependency: none blocking; purely an enhancement.
  * CONFIRMED 2026-09-17 (post-implementation redeploy attempt): production
    `foundry-quote-reviewer` pulls `acrdesjqp7651.azurecr.io/staging/reviewer-app@sha256:...`,
    a repo path only `deploy-and-evaluate.yml` writes to. The new `pilot/reviewer-app`
    stream this feature added is not consumed by production at all today. Web-chat's
    production Container App, by contrast, already tracks `pilot/web-chat` directly, so
    only reviewer-app has this gap. Redeployed and validated web-chat in production
    (`v1.0.1`, confirmed live via `/api/config`); reviewer-app's production redeploy is
    deferred pending a user decision (see ID-03) since the only way to update it without
    bypassing the evaluation-gated pipeline is to run `deploy-and-evaluate.yml` in full.
  * RESOLVED 2026-09-17: user selected Option A (see ID-03). Ran
    `deploy-and-evaluate.yml` twice (`35235911956` for the azd-schema fix,
    `35238867109` for the RBAC fix); both completed `promote-production`
    successfully. Reviewer-app v1.0.2 is now live in production via the sanctioned
    pipeline, on the `pilot/reviewer-app`-derived staging digest that pipeline
    evaluated and promoted.
* WI-02: Reviewer-app has no Application Insights wiring at all (confirmed during the
  prior review-queue investigation, recorded in `/memories/repo/deployment-gotchas.md`).
  Out of scope for this feature but worth a dedicated follow-up.
  * Source: carried over from prior session's investigation, not from this plan.
* WI-03: Confirm the GitHub `staging` Environment has no required-reviewer protection
  rule that would block the new push-triggered `release` jobs from running
  unattended; if it does, either relax it for this job or request a separate
  environment/federated credential scoped differently.
  * Source: Phase 5, OIDC environment-scoping research finding.
  * Dependency: GitHub repository environment settings (outside code, needs a repo
    admin to confirm/adjust if the blocking case is hit).
* WI-04: `apps/web-chat/tests` and `apps/reviewer-app/tests` cannot be collected by a
  single combined `pytest` invocation (missing `__init__.py`, duplicate module
  basenames like `test_app.py` across the two directories). Pre-existing repo
  structure, discovered during Phase 6 validation, not introduced by this feature.
  * Source: Phase 6 validation report.
  * Dependency: none blocking (CI already runs each app's tests as separate
    invocations); would need `__init__.py` files or a root `pytest.ini` with
    `--import-mode=importlib` if a combined local run is ever desired.

## User Decisions

* ID-01: Docker image build scope — Option "Automate build+push for both apps" selected.
  * Rationale: user chose to give web-chat its first CI-driven Docker build rather than
    leaving it manual-only.
* ID-02: Where version bump runs — Option "Add push-only job to existing build
  workflows" selected.
  * Rationale: user preferred extending `web-chat-build.yml` / `reviewer-app-build.yml`
    over creating a new standalone workflow file.
* ID-03: Reviewer-app production redeploy path — Option A ("use the sanctioned
  `deploy-and-evaluate.yml` gated pipeline") selected over an ad hoc Bicep deploy.
  * Rationale: production's reviewer-app image source (`staging/reviewer-app`)
    differs from the new CI stream (`pilot/reviewer-app`); the evaluation-gated
    pipeline is the only sanctioned way to promote a new digest to that path.
* ID-04: When the pipeline's first run failed on the unrelated `azure.yaml`/azd
  schema bug, user selected "always the more durable fix" over a workaround —
  applied throughout: the azd schema fix (DD-03) and the Foundry RBAC fix (DD-04)
  were both root-caused and fixed in Bicep/azure.yaml rather than patched around
  with manual `az role assignment create`/config edits.
* ID-05: User explicitly authorized approving both runs' `production` environment
  gates via the GitHub API on their behalf (run `35235911956` commit `bdf4931`,
  and run `35238867109` commit `3e6520b`), rather than clicking "Review
  deployments" themselves in the browser.
