<!-- markdownlint-disable-file -->
# Implementation Details: Semantic Versioning + CI/CD Docker Tagging

## Context Reference

Sources: .copilot-tracking/research/2026-09-17/semantic-versioning-ci-tagging-research.md

## Implementation Phase 1: Version bump tooling

<!-- parallelizable: true -->

### Step 1.1: Create VERSION files

* File operations:
  * Create `apps/web-chat/VERSION` with exact content `1.0.0\n`.
  * Create `apps/reviewer-app/VERSION` with exact content `1.0.0\n`.
* Success criteria: both files exist, contain only a bare semver string plus trailing
  newline (no leading `v`, no extra whitespace).

### Step 1.2: Create scripts/bump_version.py

* Context: no existing version-bump script in `scripts/`; mirror the style of
  `scripts/ci_results.py` / `scripts/deployment_summary.py` (plain argparse CLI,
  `pathlib.Path`, no external dependencies beyond stdlib).
* File operations: create `scripts/bump_version.py` with:
  * `argparse` CLI: `--app` (required, `choices=["web-chat", "reviewer-app"]`),
    `--part` (`choices=["major", "minor", "patch"]`, `default="patch"`).
  * A `VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")` to validate/parse the current
    file content (`.strip()` first). Raise a clear `SystemExit(f"...invalid semver...")`
    on mismatch.
  * Bump logic: `patch` → `z+1`; `minor` → `y+1, z=0`; `major` → `x+1, y=0, z=0`.
  * Resolve the VERSION path as `Path(__file__).resolve().parent.parent / "apps" / app / "VERSION"`
    (repo root is `scripts/..`).
  * Write back `f"{new_version}\n"` and `print(new_version)` (stdout only, no extra
    text, so CI can capture it with `NEW_VERSION=$(python scripts/bump_version.py --app web-chat)`).
* Success criteria: running `python scripts/bump_version.py --app web-chat` bumps
  `apps/web-chat/VERSION` from `1.0.0` to `1.0.1` and prints `1.0.1`.

### Step 1.3: Create scripts/tests/test_bump_version.py

* Context: `scripts/tests/` already exists (sibling tests for other scripts).
* File operations: create `scripts/tests/test_bump_version.py` using `tmp_path` /
  monkeypatching the resolved VERSION path (or invoke the script's functions directly
  with an explicit path parameter — prefer refactoring `bump_version.py` to expose a
  pure `bump(version: str, part: str) -> str` function plus a thin `main()` so tests
  don't need filesystem tricks).
* Test cases:
  * `bump("1.0.0", "patch") == "1.0.1"`
  * `bump("1.2.3", "minor") == "1.3.0"`
  * `bump("1.2.3", "major") == "2.0.0"`
  * `bump("1.2.3", "patch")` default when `--part` omitted at the CLI layer.
  * Malformed input (e.g. `"1.0"`, `"v1.0.0"`, `"abc"`) raises a clear error.
* Success criteria: `python -m pytest scripts/tests/test_bump_version.py -q` passes.

## Implementation Phase 2: Backend version endpoint wiring

<!-- parallelizable: true -->

### Step 2.1: apps/web-chat/app.py

* File: apps/web-chat/app.py
* `pathlib.Path` is already imported (line 9) — no new import needed.
* Add a module-level helper near `logger = logging.getLogger("web_chat")` (line 22):
  ```python
  def _read_version() -> str:
      path = Path(__file__).resolve().parent / "VERSION"
      try:
          return path.read_text(encoding="utf-8").strip() or "0.0.0"
      except FileNotFoundError:
          return "0.0.0"
  ```
* In the `Settings` dataclass (lines 25-35), add a new field after `environment`:
  `version: str = "0.0.0"`.
* In `from_env()` (lines 37-50), add `version=_read_version()` to the `cls(...)` call
  (after `environment=os.environ.get("ENVIRONMENT", "staging"),`).
* In the `/api/config` handler (lines 212-215), add `"version": settings.version` to
  the returned dict.
* Update `apps/web-chat/tests/test_app.py` line 167's assertion:
  `assert set(response.json()) == {"tenantId", "clientId", "scope", "environment", "version"}`.
* Discrepancy references: none.
* Success criteria: `python -m pytest apps/web-chat/tests -q` passes; `GET /api/config`
  includes `"version"`.

### Step 2.2: apps/reviewer-app/app.py

* File: apps/reviewer-app/app.py
* `pathlib.Path` is already imported (line 25) — no new import needed.
* Add the same `_read_version()` helper near `logger = logging.getLogger("reviewer_app")`.
* In the `Settings` dataclass (lines 72-80), add `version: str = "0.0.0"` after
  `queue_limit: int = 100`.
* In `from_env()` (lines 81-95), add `version=_read_version()` to the returned `cls(...)`.
* In the `/api/config` handler (line 250 onward), add `"version": settings.version` to
  the returned dict.
* Update `apps/reviewer-app/tests/test_app.py` (~lines 99-101) to assert
  `config["version"] == "0.0.0"` (tests construct `Settings` directly without a real
  VERSION file on disk, so the default applies) or adjust per actual test fixture
  behavior discovered during implementation.
* Success criteria: `python -m pytest apps/reviewer-app/tests -q` passes.

## Implementation Phase 3: Frontend version display

<!-- parallelizable: true -->

### Step 3.1: apps/web-chat/frontend/src/main.jsx

* File: apps/web-chat/frontend/src/main.jsx, line 161 (the `<header className="topbar">`
  line containing the `.environment` span).
* Add a sibling span immediately after the existing
  `<span className="environment">...</span>`:
  `<span className="version-badge">v{config.version}</span>`.
* File: apps/web-chat/frontend/src/style.css — add near the existing `.environment`
  rule: `.version-badge{font-size:11px;color:var(--muted)}`.
* Success criteria: rendered topbar shows both the environment badge and `v1.0.0` (or
  current version) next to it.

### Step 3.2: apps/reviewer-app/frontend/src/main.jsx

* File: apps/reviewer-app/frontend/src/main.jsx, line 291 (the `<span className="environment">`
  line inside `<header className="topbar">`).
* Add a sibling span immediately after it:
  `<span className="version-badge">v{config.version}</span>`.
* File: apps/reviewer-app/frontend/src/style.css — add near the existing `.environment`
  rule (line 11): `.version-badge{font-size:11px;color:var(--muted)}`.
* Success criteria: rendered topbar shows both badges.

### Step 3.3: Update frontend tests referencing config shape

* Grep `apps/web-chat/frontend/tests/*.test.js` and
  `apps/reviewer-app/frontend/tests/*.test.js` for `config.environment`,
  `topbar.pilotBadge`, or asserted config object keys; add `version` to any mocked
  config fixtures and update snapshot/text assertions that would break from the new
  badge markup.
* Success criteria: no frontend test references a config fixture missing `version`.

## Implementation Phase 4: Docker build changes

<!-- parallelizable: true -->

### Step 4.1: apps/web-chat

* File: apps/web-chat/Dockerfile — change
  `COPY app.py auth.py messages.py ./` to
  `COPY app.py auth.py messages.py VERSION ./`.
* File: apps/web-chat/.dockerignore — add a new line `!VERSION` (allowlist entry,
  anywhere among the existing `!file` lines).
* Success criteria: `docker build -f apps/web-chat/Dockerfile apps/web-chat` (or the
  CI `az acr build` step in Phase 5) succeeds and the running container's `/app/VERSION`
  file is present.

### Step 4.2: apps/reviewer-app

* File: apps/reviewer-app/Dockerfile — change
  `COPY apps/reviewer-app/app.py apps/reviewer-app/auth.py apps/reviewer-app/messages.py ./`
  to
  `COPY apps/reviewer-app/app.py apps/reviewer-app/auth.py apps/reviewer-app/messages.py apps/reviewer-app/VERSION ./`.
* Check whether a repository-root `.dockerignore` exists and would exclude
  `apps/reviewer-app/VERSION` from the build context; if one exists and excludes it,
  add an allowlist/negation entry. (Research did not find one during planning; confirm
  at implementation time.)
* Success criteria: `az acr build --file apps/reviewer-app/Dockerfile .` succeeds and
  the container's `/app/VERSION` file is present.

## Implementation Phase 5: CI/CD release automation

<!-- parallelizable: false -->

### Step 5.1: .github/workflows/web-chat-build.yml

* Add a second job `release` after the existing `build` job:
  ```yaml
  release:
    name: Bump version, tag, and publish image
    needs: build
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: staging
    permissions:
      contents: write
      id-token: write
    concurrency:
      group: release-web-chat-${{ github.ref }}
      cancel-in-progress: false
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: '3.13'
      - name: Configure git identity
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
      - name: Bump patch version
        id: bump
        run: |
          set -euo pipefail
          NEW_VERSION=$(python scripts/bump_version.py --app web-chat)
          echo "version=$NEW_VERSION" >> "$GITHUB_OUTPUT"
      - name: Commit and tag
        run: |
          set -euo pipefail
          git add apps/web-chat/VERSION
          git commit -m "chore(web-chat): bump version to ${{ steps.bump.outputs.version }} [skip ci]"
          git tag "web-chat-v${{ steps.bump.outputs.version }}"
          git push origin HEAD:main --follow-tags
      - name: Azure login (OIDC)
        uses: azure/login@v3
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
      - name: Build and push versioned image
        env:
          MCP_ACR_NAME: ${{ vars.MCP_ACR_NAME }}
          VERSION: ${{ steps.bump.outputs.version }}
        run: |
          set -euo pipefail
          az acr build --registry "$MCP_ACR_NAME" \
            --image "pilot/web-chat:v${VERSION}" \
            --image "pilot/web-chat:latest" \
            --file apps/web-chat/Dockerfile apps/web-chat
  ```
* `if: github.event_name == 'push' && github.ref == 'refs/heads/main'` guards against
  running on `pull_request` (never has push/write credentials exposed to fork PRs) and
  against non-main pushes.
* `environment: staging` satisfies the OIDC federated credential subject
  (`repo:...:environment:staging`) confirmed in research.
* `[skip ci]` in the commit message prevents the pushed commit from re-triggering
  `web-chat-build.yml` (and any other path-filtered workflow) — GitHub Actions built-in
  behavior — avoiding an infinite bump loop.
* Success criteria: on a push to `main` touching `apps/web-chat/**`, the workflow bumps
  `apps/web-chat/VERSION`, pushes a commit + `web-chat-vX.Y.Z` tag, and pushes
  `pilot/web-chat:vX.Y.Z` + `pilot/web-chat:latest` to ACR.

### Step 5.2: .github/workflows/reviewer-app-build.yml

* Add the equivalent `release` job, differing only in:
  * `--app reviewer-app` in the bump step.
  * Tag name `reviewer-app-v${{ steps.bump.outputs.version }}`.
  * Commit message prefix `chore(reviewer-app): ...`.
  * `concurrency.group: release-reviewer-app-${{ github.ref }}`.
  * `az acr build --image "pilot/reviewer-app:v${VERSION}" --image "pilot/reviewer-app:latest" --file apps/reviewer-app/Dockerfile .`
    (build context is repo root `.`, matching the existing reviewer-app build pattern
    in `deploy-and-evaluate.yml`).
* Discrepancy references: none.
* Success criteria: equivalent to Step 5.1 for `reviewer-app`.

## Success Criteria

* All VERSION files, script, backend/frontend changes, Dockerfile changes, and CI jobs
  described above exist and pass the validation commands listed per phase in the
  implementation plan.
