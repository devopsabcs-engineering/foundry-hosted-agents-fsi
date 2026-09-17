<!-- markdownlint-disable-file -->
# Planning Log: Semantic Versioning + CI/CD Docker Tagging

**Related Plan**: semantic-versioning-ci-tagging-plan.instructions.md

## Discrepancy Log

### Unaddressed Research Items

* None — research scope was fully consumed by the plan.

### Implementation Deviations

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
