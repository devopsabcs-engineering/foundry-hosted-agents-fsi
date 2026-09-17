<!-- markdownlint-disable-file -->
# Release Changes: Semantic Versioning + CI/CD Docker Tagging

**Related Plan**: semantic-versioning-ci-tagging-plan.instructions.md
**Implementation Date**: 2026-09-17

## Summary

Added an independently-tracked semantic version (starting `1.0.0`) to `apps/web-chat`
and `apps/reviewer-app`, a `scripts/bump_version.py` CLI to auto-increment it (default:
patch), a version badge in each app's frontend topbar, Dockerfile/`.dockerignore`
wiring so the `VERSION` file ships in each image, and a new `release` job in each app's
GitHub Actions build workflow that bumps the version, commits + tags the change in git,
and builds/pushes a matching `pilot/<app>:vX.Y.Z` (+ `:latest`) image to ACR on every
push to `main`.

## Changes

### Added

* apps/web-chat/VERSION - seed version file, `1.0.0`.
* apps/reviewer-app/VERSION - seed version file, `1.0.0`.
* scripts/bump_version.py - CLI to bump an app's `VERSION` file (`--app`, `--part`, default patch); exposes a pure `bump()` function.
* scripts/tests/test_bump_version.py - unit tests for patch/minor/major bumps and malformed-input errors.

### Modified

* apps/web-chat/app.py - added `_read_version()` helper, `version` field on `Settings`, wired into `from_env()` and `/api/config`.
* apps/web-chat/tests/test_app.py - config-response key-set assertion now includes `"version"`.
* apps/reviewer-app/app.py - same `_read_version()`/`Settings.version`/`from_env()`/`/api/config` wiring.
* apps/reviewer-app/tests/test_app.py - added assertion for `config["version"]`.
* apps/web-chat/frontend/src/main.jsx - added `version-badge` span next to the environment badge.
* apps/web-chat/frontend/src/style.css - added `.version-badge` CSS rule.
* apps/reviewer-app/frontend/src/main.jsx - added `version-badge` span next to the environment badge.
* apps/reviewer-app/frontend/src/style.css - added `.version-badge` CSS rule.
* apps/web-chat/Dockerfile - `COPY` instruction now includes `VERSION`.
* apps/web-chat/.dockerignore - added `!VERSION` allowlist entry.
* apps/reviewer-app/Dockerfile - `COPY` instruction now includes `apps/reviewer-app/VERSION`.
* .github/workflows/web-chat-build.yml - added `release` job (push-to-main only): version bump, git commit+tag `[skip ci]`, Azure OIDC login (`environment: staging`), `az acr build` → `pilot/web-chat:vX.Y.Z` + `:latest`.
* .github/workflows/reviewer-app-build.yml - added equivalent `release` job → `pilot/reviewer-app:vX.Y.Z` + `:latest`.

### Removed

* None.

## Additional or Deviating Changes

* reviewer-app's test suite asserts `config["version"] == "0.0.0"` (the dataclass
  default), not `"1.0.0"`, because its test fixture constructs `Settings` directly
  with positional args rather than through `from_env()`/`_read_version()` — this is
  correct behavior for that test, not a defect.
* A pre-existing, unrelated pytest collection quirk was discovered during Phase 6
  validation: running `pytest apps/web-chat/tests apps/reviewer-app/tests scripts/tests`
  together in one invocation fails with an `import file mismatch` because both app test
  directories lack `__init__.py` and share module basenames (e.g. `test_app.py`). CI
  never runs these combined (each workflow runs its own app's tests in its own job), so
  this was left unfixed as out of scope for this feature — validation was instead run
  as three separate `pytest` invocations, matching the actual CI pattern.
* Docker validation of the two updated Dockerfiles could not be run locally (Docker
  Desktop daemon was not running on the implementation machine); this is expected to
  work per a static review of the `COPY` instructions and will be exercised for real by
  the new CI `release` jobs on the next push to `main`.

## Post-Implementation Rollout (2026-09-17, same day)

Committed (`bd45f7d`), pushed to `main`, and monitored the resulting CI runs:

* First push-triggered run of both `release` jobs surfaced two CI bugs (lightweight
  tag silently dropped by `--follow-tags`; concurrent release jobs racing on
  `git push origin HEAD:main`). Fixed in follow-up commits `d88c268`/`714dd20`
  (see Discrepancy Log DD-02). Re-run succeeded for both apps.
* Confirmed on `origin`: git tags `web-chat-v1.0.1` and `reviewer-app-v1.0.2`
  (reviewer-app bumped twice due to the race); ACR tags `pilot/web-chat:v1.0.1`
  and `pilot/reviewer-app:v1.0.2` (+ `:latest` for both) in `acrdesjqp7651`.
* Redeployed production `foundry-quote-chat` (web-chat) via the established
  out-of-band recipe (`az deployment group create --template-file infra/web-chat.bicep`,
  reusing all prior parameters, only the `image` digest changed to
  `pilot/web-chat@sha256:f1d87d1a...`). Validated live: `GET /api/config` on
  `https://foundry-quote-chat.lemonwave-09491729.eastus2.azurecontainerapps.io`
  now returns `"version": "1.0.1"`; new revision `foundry-quote-chat--0000003`
  holds 100% traffic.
* Reviewer-app's production Container App (`foundry-quote-reviewer`) was **not**
  redeployed. It pulls from `staging/reviewer-app`, a repo path only the
  evaluation-gated `deploy-and-evaluate.yml` pipeline writes to — the new
  `pilot/reviewer-app` stream is not wired into production for this app (see
  Planning Log WI-01/ID-03). Redeploying it the sanctioned way requires running
  that full pipeline (including its manual production-approval gate), which
  was deferred pending user confirmation rather than done ad hoc.
* `/memories/repo/deployment-gotchas.md` updated with the CI bug findings and the
  reviewer-app production image-stream mismatch, for future sessions.

## Release Summary

**Total files affected**: 15 (4 added, 11 modified, 0 removed) plus 2 follow-up CI
bug-fix commits (`.github/workflows/web-chat-build.yml`,
`.github/workflows/reviewer-app-build.yml`) and one production infrastructure
redeploy (web-chat Container App, no source files changed).

* **Added**: `apps/web-chat/VERSION`, `apps/reviewer-app/VERSION`, `scripts/bump_version.py`, `scripts/tests/test_bump_version.py`.
* **Modified**: `apps/web-chat/app.py`, `apps/web-chat/tests/test_app.py`, `apps/reviewer-app/app.py`, `apps/reviewer-app/tests/test_app.py`, `apps/web-chat/frontend/src/main.jsx`, `apps/web-chat/frontend/src/style.css`, `apps/reviewer-app/frontend/src/main.jsx`, `apps/reviewer-app/frontend/src/style.css`, `apps/web-chat/Dockerfile`, `apps/web-chat/.dockerignore`, `apps/reviewer-app/Dockerfile`, `.github/workflows/web-chat-build.yml`, `.github/workflows/reviewer-app-build.yml`.
* **Dependency/infrastructure changes**: no new dependencies added. CI/CD now performs its first-ever automated Docker build+push for web-chat and a new versioned/tagged parallel build stream for reviewer-app, both gated to `push` on `main` and using the existing Azure OIDC federated credential under `environment: staging`.
* **Deployment notes**: the new `release` jobs push directly to `main` (version bump commit + tag) and to ACR (`acrdesjqp7651`, `pilot/<app>:vX.Y.Z` + `:latest`). No changes were made to `deploy-and-evaluate.yml`'s existing staging/production promotion pipeline — the two systems are independent. Before the first real push-triggered run, confirm the GitHub `staging` Environment has no required-reviewer protection rule that would block an unattended job (tracked as WI-03 in the Planning Log).
* **Validation status**: all backend tests (169 passed across 3 suites), both frontend test suites (18 passed) and builds, and both workflow YAML files (valid) passed. Docker builds were not exercised locally (daemon unavailable) but the file-level changes were verified consistent by a full read-through.
