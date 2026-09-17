---
applyTo: '.copilot-tracking/changes/2026-09-17/semantic-versioning-ci-tagging-changes.md'
---
<!-- markdownlint-disable-file -->
# Implementation Plan: Semantic Versioning + CI/CD Docker Tagging

## Overview

Add a visible, independently-tracked semantic version to `apps/web-chat` and
`apps/reviewer-app`, a script to auto-increment it (default patch), and CI automation
that bumps the version, tags the commit in git, and builds/pushes a matching Docker
image on every push to `main`.

## Objectives

### User Requirements

* Display a version, starting at `1.0.0`, in each UI app's frontend — Source:
  user request "add versions visible for each ui app starting with 1.0.0 use semantic
  versioning".
* Auto-increment the version, defaulting to patch +1, with a git tag created
  automatically — Source: user request "tools to automatically increment version and
  add appropriate git tag as well automatically increment patch by 1 by default with
  each commit".
* Tag the Docker images automatically in the CI/CD pipeline — Source: user request
  "also tag the docker images as well as such and automatically in ci/cd pipeline".
* Automate a first-time Docker build+push for web-chat (previously manual-only), and
  add the version-bump job as a new push-only job inside the existing build workflows —
  Source: user decisions recorded in Planning Log (ID-01, ID-02).

### Derived Objectives

* Add `version` to each app's `/api/config` response so the frontend can render it
  without a second endpoint — Derived from: both apps already expose `environment`
  this way; consistent, minimal-surface-area pattern.
* Gate the new CI release job to `push` on `main` only (never `pull_request`) and
  declare `environment: staging` — Derived from: research findings on OIDC federated
  credential scoping (environment-scoped, not branch-scoped) and the need to avoid
  exposing write-back/Azure credentials to fork PR runs.

## Context Summary

### Project Files

* apps/web-chat/VERSION (new) - semantic version for web-chat, starts `1.0.0`.
* apps/reviewer-app/VERSION (new) - semantic version for reviewer-app, starts `1.0.0`.
* scripts/bump_version.py (new) - CLI to bump an app's VERSION file (default: patch).
* scripts/tests/test_bump_version.py (new) - unit tests for the bump script.
* apps/web-chat/app.py - Settings dataclass, `from_env`, `/api/config` endpoint.
* apps/reviewer-app/app.py - Settings dataclass, `from_env`, `/api/config` endpoint.
* apps/web-chat/tests/test_app.py - config-endpoint key assertion to update.
* apps/reviewer-app/tests/test_app.py - config-endpoint assertions to extend.
* apps/web-chat/frontend/src/main.jsx - topbar badge to extend with version.
* apps/reviewer-app/frontend/src/main.jsx - topbar badge to extend with version.
* apps/web-chat/frontend/src/style.css - `.environment` rule to mirror for `.version-badge`.
* apps/reviewer-app/frontend/src/style.css - `.environment` rule to mirror for `.version-badge`.
* apps/web-chat/Dockerfile - add `COPY VERSION`.
* apps/web-chat/.dockerignore - allowlist `!VERSION`.
* apps/reviewer-app/Dockerfile - add `COPY apps/reviewer-app/VERSION`.
* .github/workflows/web-chat-build.yml - new `release` job.
* .github/workflows/reviewer-app-build.yml - new `release` job.

### References

* .copilot-tracking/research/2026-09-17/semantic-versioning-ci-tagging-research.md - full research findings.

### Standards References

* None of the applicable `.github/instructions/**` files govern Python/JS app code or
  GitHub Actions YAML in this repository; existing sibling files were used as the
  style/convention reference instead (see research doc).

## Implementation Checklist

### [x] Implementation Phase 1: Version bump tooling

<!-- parallelizable: true -->

* [x] Step 1.1: Create `apps/web-chat/VERSION` and `apps/reviewer-app/VERSION`, each
  containing `1.0.0\n`.
  * Details: .copilot-tracking/details/2026-09-17/semantic-versioning-ci-tagging-details.md (Lines 1-20)
* [x] Step 1.2: Create `scripts/bump_version.py` (bump patch/minor/major, validate
  semver, write back, print new version).
  * Details: .copilot-tracking/details/2026-09-17/semantic-versioning-ci-tagging-details.md (Lines 21-55)
* [x] Step 1.3: Create `scripts/tests/test_bump_version.py` covering default patch
  bump, minor/major bump, and malformed-VERSION-file error handling.
  * Details: .copilot-tracking/details/2026-09-17/semantic-versioning-ci-tagging-details.md (Lines 56-75)
* [x] Step 1.4: Validate phase changes
  * Run `python -m pytest scripts/tests/test_bump_version.py -q`

### [x] Implementation Phase 2: Backend version endpoint wiring

<!-- parallelizable: true -->

* [x] Step 2.1: Add `version` field, `_read_version()` helper, and `/api/config` wiring
  to `apps/web-chat/app.py`; update `apps/web-chat/tests/test_app.py`.
  * Details: .copilot-tracking/details/2026-09-17/semantic-versioning-ci-tagging-details.md (Lines 76-105)
* [x] Step 2.2: Add `version` field, `_read_version()` helper, and `/api/config` wiring
  to `apps/reviewer-app/app.py`; update `apps/reviewer-app/tests/test_app.py`.
  * Details: .copilot-tracking/details/2026-09-17/semantic-versioning-ci-tagging-details.md (Lines 106-135)
* [x] Step 2.3: Validate phase changes
  * Run `python -m pytest apps/web-chat/tests -q` and `python -m pytest apps/reviewer-app/tests -q`

### [x] Implementation Phase 3: Frontend version display

<!-- parallelizable: true -->

* [x] Step 3.1: Render a `version-badge` span next to the environment badge in
  `apps/web-chat/frontend/src/main.jsx`; add `.version-badge` CSS rule.
  * Details: .copilot-tracking/details/2026-09-17/semantic-versioning-ci-tagging-details.md (Lines 136-155)
* [x] Step 3.2: Render a `version-badge` span next to the environment badge in
  `apps/reviewer-app/frontend/src/main.jsx`; add `.version-badge` CSS rule.
  * Details: .copilot-tracking/details/2026-09-17/semantic-versioning-ci-tagging-details.md (Lines 156-175)
* [x] Step 3.3: Grep both frontend `tests/` directories for assertions on `config`
  shape or rendered topbar markup and update any that would now fail.
  * Details: .copilot-tracking/details/2026-09-17/semantic-versioning-ci-tagging-details.md (Lines 176-185)
* [x] Step 3.4: Validate phase changes
  * Run each frontend's `npm test` and `npm run build`

### [x] Implementation Phase 4: Docker build changes

<!-- parallelizable: true -->

* [x] Step 4.1: Add `VERSION` to `apps/web-chat/Dockerfile`'s `COPY` step and to
  `apps/web-chat/.dockerignore`'s allowlist.
  * Details: .copilot-tracking/details/2026-09-17/semantic-versioning-ci-tagging-details.md (Lines 186-200)
* [x] Step 4.2: Add `apps/reviewer-app/VERSION` to `apps/reviewer-app/Dockerfile`'s
  `COPY` step; confirm no repository-root `.dockerignore` excludes it.
  * Details: .copilot-tracking/details/2026-09-17/semantic-versioning-ci-tagging-details.md (Lines 201-215)
* [x] Step 4.3: Validate phase changes
  * Run `docker build -f apps/web-chat/Dockerfile apps/web-chat` and
    `docker build -f apps/reviewer-app/Dockerfile .` locally if Docker is available;
    otherwise defer to Phase 5's CI validation.

### [x] Implementation Phase 5: CI/CD release automation

<!-- parallelizable: false -->

* [x] Step 5.1: Add a `release` job to `.github/workflows/web-chat-build.yml`: bump
  version, commit `[skip ci]`, tag `web-chat-vX.Y.Z`, push, `azure/login@v3` (OIDC,
  `environment: staging`), `az acr build` tagging `pilot/web-chat:vX.Y.Z` and `:latest`.
  * Details: .copilot-tracking/details/2026-09-17/semantic-versioning-ci-tagging-details.md (Lines 216-260)
* [x] Step 5.2: Add the equivalent `release` job to
  `.github/workflows/reviewer-app-build.yml` tagging `reviewer-app-vX.Y.Z` and
  `pilot/reviewer-app:vX.Y.Z` / `:latest`.
  * Details: .copilot-tracking/details/2026-09-17/semantic-versioning-ci-tagging-details.md (Lines 261-290)
* [x] Step 5.3: Validate phase changes
  * Run `python -m pip install pyyaml && python -c "import yaml; yaml.safe_load(open('.github/workflows/web-chat-build.yml'))"`
    (and the same for reviewer-app-build.yml) to confirm valid YAML.

### [x] Implementation Phase 6: Validation

<!-- parallelizable: false -->

* [x] Step 6.1: Run full project validation
  * `python -m pytest apps/web-chat/tests apps/reviewer-app/tests scripts/tests -q`
  * `npm test` and `npm run build` in both `apps/web-chat/frontend` and
    `apps/reviewer-app/frontend`
* [x] Step 6.2: Fix minor validation issues
  * Iterate on any lint/test failures surfaced above
* [x] Step 6.3: Report blocking issues
  * Document anything requiring additional research (e.g., GitHub Environment
    protection rules on `staging` blocking unattended job runs) and provide next steps

## Planning Log

See `.copilot-tracking/plans/logs/2026-09-17/semantic-versioning-ci-tagging-log.md`
for discrepancy tracking, implementation paths considered, and suggested follow-on work.

## Dependencies

* Python 3.13, pytest (already project dependencies)
* Node 22, npm (already project dependencies)
* Azure CLI + `azure/login@v3` OIDC via existing `AZURE_CLIENT_ID` /
  `AZURE_TENANT_ID` / `AZURE_SUBSCRIPTION_ID` / `MCP_ACR_NAME` repo variables
* GitHub Actions `staging` Environment (must not require manual approval for
  unattended push-triggered runs to succeed)

## Success Criteria

* `apps/web-chat/VERSION` and `apps/reviewer-app/VERSION` exist starting at `1.0.0` —
  Traces to: user requirement (visible version, semver, starting 1.0.0).
* `GET /api/config` on both apps returns a `version` field and the frontend renders it —
  Traces to: user requirement (visible version in each UI app).
* `scripts/bump_version.py` bumps patch by default and is covered by passing tests —
  Traces to: user requirement (auto-increment tooling, default patch +1).
* A push to `main` touching either app automatically commits a version bump, creates a
  `*-vX.Y.Z` git tag, and builds/pushes a matching `pilot/<app>:vX.Y.Z` image to ACR —
  Traces to: user requirement (automatic git tag + automatic Docker image tagging in CI/CD).
* All existing and new tests pass; workflow YAML is valid — Traces to: Phase 6
  validation.
