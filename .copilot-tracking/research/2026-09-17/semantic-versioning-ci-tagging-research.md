<!-- markdownlint-disable-file -->
# Research: Semantic Versioning + CI/CD Docker Tagging

## Scope

Add a visible semantic version (starting `1.0.0`) to both UI apps (`apps/web-chat`,
`apps/reviewer-app`), tooling to auto-increment it (default: patch +1), automatic git
tags per release, and automatic Docker image tagging in CI/CD.

## Key Findings

### No existing versioning conventions for these apps

* Root `package.json` has `"version": "1.0.0"` but is unrelated (workshop deck build
  script package), not consumed by either app.
* `git tag --list` returns nothing — no existing tags, no naming convention to
  conflict with.
* `scripts/record-production-version.sh` / `scripts/test-production-version.sh` track
  the Foundry **hosted agent's** own numeric version (`agent_version`, e.g. `"33"`),
  an unrelated concept scoped to the agent's deployment, not the UI apps.

### CI workflow landscape

* `.github/workflows/web-chat-build.yml` and `.github/workflows/reviewer-app-build.yml`
  both run on `push` (branches: `[main]`, path-filtered to their app) and `pull_request`
  (same path filters). They run tests + frontend build only — **no Docker build/push,
  no Azure login**, `permissions: contents: read`.
* `.github/workflows/deploy-and-evaluate.yml` is `workflow_dispatch`-only (manual). Its
  `deploy-staging` job builds Docker images via `az acr build` for the MCP servers and
  reviewer-app, tagged `staging/<name>:${GITHUB_SHA}-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}`,
  then resolves and pins by digest. This is a separate, unaffected pipeline (staging →
  production promotion via a manual GitHub Environment approval).
* **web-chat has no Docker build anywhere in CI** — its image is built manually via
  `az acr build` per the out-of-band recipe in `/memories/repo/deployment-gotchas.md`.

### OIDC / Azure login constraint (critical)

* GitHub Actions federated credentials on the `AZURE_CLIENT_ID` app registration
  (`7fbd7713-95ea-438a-91e2-9998fef6c9ca`) are scoped by **GitHub Environment**, not by
  branch ref:
  * `repo:devopsabcs-engineering/foundry-hosted-agents-fsi:environment:staging`
  * `repo:devopsabcs-engineering/foundry-hosted-agents-fsi:environment:production`
  (plus two legacy variants under a renamed-repo slug).
* Any new workflow job that calls `azure/login@v3` with this same client ID **must**
  declare `environment: staging` (or `production`) to satisfy the OIDC subject claim,
  otherwise login fails with "no matching federated identity record found."
* `MCP_ACR_NAME` repo variable = `acrdesjqp7651` (same registry as manual builds).

### Backend config endpoint pattern (both apps)

* Both `apps/web-chat/app.py` and `apps/reviewer-app/app.py` define a frozen `Settings`
  dataclass with `environment: str = "staging"`, populated in `from_env()` from
  `os.environ.get("ENVIRONMENT", "staging")`, and exposed via `GET /api/config`.
* `pathlib.Path` is already imported in both `app.py` files.
* Existing tests assert the exact config key set:
  * `apps/web-chat/tests/test_app.py:167` — `{"tenantId", "clientId", "scope", "environment"}`.
  * `apps/reviewer-app/tests/test_app.py:99-101` — asserts `scope` and `role` present.

### Frontend badge pattern (both apps)

* Both `main.jsx` files render an `<span className="environment">` badge using the
  i18n key `topbar.pilotBadge` with `{env: config.environment}` interpolation.
* `apps/web-chat/frontend/src/main.jsx:161` and
  `apps/reviewer-app/frontend/src/main.jsx:291`.
* Matching `.environment` CSS rules exist in each app's `style.css` (minified,
  single-line stylesheets).

### Docker build context differs per app

* `apps/web-chat/Dockerfile` uses **`apps/web-chat/` as build context** (relative
  `COPY app.py auth.py messages.py ./`, etc.). `apps/web-chat/.dockerignore` is an
  **allowlist** (`**` then explicit `!file` unignores) — a new `VERSION` file must be
  explicitly unignored or it never reaches the build context.
* `apps/reviewer-app/Dockerfile` uses the **repository root as build context**
  (`az acr build --file apps/reviewer-app/Dockerfile .`), with fully-qualified `COPY`
  paths. It has no `.dockerignore` of its own.

## Constraints / Decisions Confirmed With User

* Docker image build+push will be **automated for both apps** (this is a first-time
  automated build for web-chat; it previously had none).
* Version bump + git tag creation will be added as a **new job inside the existing**
  `web-chat-build.yml` / `reviewer-app-build.yml` workflows, gated to `push` on `main`
  only (never `pull_request`, to avoid exposing write-back/Azure credentials to
  fork-originated PR runs).

## Open Follow-Ons (not in scope now)

* `deploy-and-evaluate.yml`'s staging/production promotion pipeline is left untouched;
  the new `pilot/<app>:vX.Y.Z` images are a separate, parallel artifact stream matching
  the existing manual `pilot/web-chat` ACR naming convention.
* Reviewer-app has no Application Insights wiring at all (unrelated pre-existing gap,
  already recorded in `/memories/repo/deployment-gotchas.md`).
