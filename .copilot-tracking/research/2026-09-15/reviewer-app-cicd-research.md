<!-- markdownlint-disable-file -->
# Research: Existing CI/CD, Azure Auth, Deploy Mechanics, and Teardown/Entra Gaps

Date: 2026-09-15
Scope: RESEARCH ONLY. No files were modified.
Repository root: c:\src\GitHub\devopsabcs-engineering\foundry-hosted-agents-fsi

## Research Topics and Questions

1. Workflow inventory (name, triggers, jobs, runner, permissions, concurrency, end-to-end behavior).
2. Azure authentication mechanism (OIDC vs secrets, action version, vars/secrets, GitHub Environments).
3. Deploy mechanics (azd vs az deployment, image build/push, Container App update).
4. Python/test conventions in CI (version, installs, pytest invocation, PYTHONPATH, artifacts).
5. Frontend build in CI (node version, package manager, build command, dist packaging).
6. Existing teardown/cleanup/destroy — definitive yes/no.
7. Entra ID automation (app registration, app roles, scopes, groups, admin consent).
8. Gaps and conventions for the new reviewer-app build/deploy workflow, teardown workflow, and reviewer app registration automation.

## Files Read In Full

* .github/workflows/continuous-validation.yml (150 lines)
* .github/workflows/deploy-and-evaluate.yml (529 lines)
* .github/workflows/hosted-agent-cd.yml (23 lines)
* .github/workflows/publish-test-trends.yml (~172 lines)
* .github/workflows/web-chat-build.yml (~70 lines)
* azure.yaml
* scripts/setup-web-chat-identity.ps1
* scripts/capture-release-evidence.ps1
* scripts/deployment_summary.py (first 120 lines; remainder is link rendering)
* infra/main.bicep (lines 1-140)
* infra/web-chat.bicep
* infra/modules/mcp-container-apps.bicep (lines 1-130)
* infra/README.md
* README.md
* apps/web-chat/Dockerfile
* apps/web-chat/frontend/package.json

---

## 1. WORKFLOW INVENTORY

There are exactly **five** workflow files. Confirmed via glob `.github/workflows/*.yml` — five results, no `.yaml` variants.

### 1.1 Continuous Validation — .github/workflows/continuous-validation.yml

| Attribute | Value | Evidence |
|---|---|---|
| `name` | `Continuous Validation` | continuous-validation.yml line 1 |
| Triggers | `push` on `branches: [main]`; `pull_request` (no path filter); `workflow_dispatch` | lines 12-16 |
| Permissions | `contents: read` ONLY — no `id-token` | lines 18-19 |
| Concurrency | **None declared** | (absent) |
| Jobs | `offline` (line 22), `bicep-lint` (line 120) | lines 22, 120 |
| Runner | `ubuntu-latest` both jobs | lines 24, 122 |
| Timeouts | `offline` 20 min; `bicep-lint` 10 min | lines 25, 123 |

End-to-end behavior:

* `offline`: checkout (`actions/checkout@v6`, `persist-credentials: false`, lines 27-29) → `actions/setup-python@v6` with `python-version: "3.13"` (lines 31-33) → install four requirements files (lines 35-43) → three pytest sweeps writing JUnit XML into `evidence/` (lines 45-56) → `python eval/evaluation_gate.py` gate (lines 58-60) → inline heredoc Python step summary (lines 62-95) → `python scripts/ci_results.py --junit evidence` (lines 97-99) → `python scripts/deployment_summary.py` (lines 101-103) → copy `eval/results.json` into `evidence/` (lines 105-107) → upload artifact `offline-test-evidence-${{ github.run_attempt }}` (lines 109-118).
* `bicep-lint`: `az bicep install` (lines 129-130), then a loop compiling `infra/main.bicep` and every `infra/modules/*.bicep` with `az bicep build --file` under `set -euo pipefail` (lines 132-140). **No Azure login** — compile-only. Followed by a summary block (lines 142-150).

This workflow is deliberately credential-free; see the top-of-file comment block, lines 3-10.

### 1.2 Deploy and Evaluate (Staging -> Production) — .github/workflows/deploy-and-evaluate.yml

| Attribute | Value | Evidence |
|---|---|---|
| `name` | `Deploy and Evaluate (Staging -> Production)` | line 1 |
| Triggers | `workflow_call` (input `golden_dataset_path`, default `eval/golden-dataset.jsonl`) and `workflow_dispatch` (same input) | lines 36-50 |
| Permissions | `id-token: write`, `contents: read` | lines 52-55 |
| Concurrency | `group: desjardins-quote-preparation-shared-environments`, `queue: max` | lines 56-58 |
| Env (workflow level) | `AGENT_PROJECT_DIR: .`, `AGENT_NAME: quote-preparation-agent`, `GOLDEN_DATASET_PATH`, `STAGING_AZD_ENV_NAME: desjardins-quote-preparation-staging`, `PRODUCTION_AZD_ENV_NAME: desjardins-quote-preparation-poc` | lines 60-65 |
| Jobs | `lint` (73), `bicep-validate` (123), `deploy-staging` (161), `evaluate` (299), `promote-production` (430) | as listed |
| Runners | all `ubuntu-latest` | lines 75, 126, 164, 302, 433 |
| GitHub Environments | `bicep-validate`, `deploy-staging`, `evaluate` → `staging`; `promote-production` → `production` | lines 127, 165, 303, 434 |

Job dependency chain: `lint` → `bicep-validate` → `deploy-staging` → `evaluate` → `promote-production` (`needs: [evaluate, deploy-staging]`, line 432).

`deploy-staging` job outputs (lines 166-170): `agent_version`, `project_endpoint`, `application_mcp_image`, `rulebook_mcp_image`.

The manual production approval gate is implemented purely by the `production` GitHub Environment + required reviewers — there is no separate approval job. Documented at lines 421-429.

> Caveat recorded in session memory (/memories/session/hosted-agent-cicd-fix.md, lines 41-43): the `production` GitHub Environment had **no required-reviewer protection configured**, so `promote-production` may run with no human approval. Flagged, not yet remediated.

### 1.3 Hosted Agent CI/CD — .github/workflows/hosted-agent-cd.yml

Entire file is 23 lines. Thin dispatch wrapper:

```yaml
name: Hosted Agent CI/CD
on:
  workflow_dispatch:
permissions:
  id-token: write
  contents: read
jobs:
  release:
    uses: ./.github/workflows/deploy-and-evaluate.yml
    secrets: inherit
```

Evidence: hosted-agent-cd.yml lines 1, 14-15, 17-19, 21-23. No concurrency block of its own (inherits the called workflow's).

### 1.4 Web Chat Build — .github/workflows/web-chat-build.yml

| Attribute | Value | Evidence |
|---|---|---|
| `name` | `Web Chat Build` | line 1 |
| Triggers | `workflow_dispatch`; `push` on `main` with paths `['apps/web-chat/**', '.github/workflows/web-chat-build.yml', 'scripts/deployment_summary.py']`; `pull_request` with the same path filter | lines 3-9 |
| Permissions | `contents: read` ONLY | lines 11-12 |
| Concurrency | **None** | (absent) |
| Jobs | single `build` job | line 15 |
| Runner / timeout | `ubuntu-latest`, 15 min | lines 17-18 |

End to end: checkout → `actions/setup-node@v6` node 22 → `actions/setup-python@v6` 3.13 → pip install backend deps → backend pytest → `npm ci`/`npm install` → frontend `node --test` → `npm run build` → upload `dist/` + lockfile → upload test evidence → summary. **Build-and-test only — it never logs into Azure and never deploys.** Confirmed by absence of any `azure/login` or `az` step in the file and by README.md lines 129-140.

### 1.5 Publish Test Trends — .github/workflows/publish-test-trends.yml

| Attribute | Value | Evidence |
|---|---|---|
| `name` | `Publish Test Trends` | line 1 |
| Triggers | `workflow_run` on workflows `[Continuous Validation, 'Deploy and Evaluate (Staging -> Production)', Hosted Agent CI/CD]`, `types: [completed]`, `branches: [main]`; plus `workflow_dispatch` with `run_id` (required) and `run_attempt` (optional) | lines 28-41 |
| Permissions | `contents: read`, `actions: read` | lines 42-44 |
| Concurrency | `group: desjardins-quote-preparation-test-trends`, `queue: max` | lines 46-48 |
| Job | `publish`, `ubuntu-latest`, 10 min | lines 51-54 |
| Job-level `if` | dispatch, or same-repo non-PR workflow_run | line 52 |

Notable: an explicit allow-list of source workflow paths is enforced in the provenance check (lines 75-89), asserting `.path` is one of `continuous-validation.yml`, `deploy-and-evaluate.yml`, `hosted-agent-cd.yml`. **A new deploy workflow whose evidence should reach the wiki must be added to BOTH the `workflows:` trigger list (line 30) and this `jq -e` path allow-list.** Evidence artifact kinds are also hard-coded: `offline-test-evidence`, `evaluation-evidence` (line 95), and `deployment-links-production` / `deployment-links-staging` (line 118).

Wiki push uses `secrets.WIKI_PUSH_TOKEN` with `git -c "http.https://github.com/.extraheader=$AUTH_HEADER"` basic auth (lines 136-152) and fails loudly (exit 1) when the secret is absent (lines 139-149).

---

## 2. AZURE AUTH

**Mechanism: OIDC federated credentials via `azure/login@v3`. No client secrets are stored or referenced anywhere.**

Only `deploy-and-evaluate.yml` authenticates to Azure. It does so in three jobs, using an identical verbatim step:

```yaml
      - name: Azure login with OIDC
        uses: azure/login@v3
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
```

Occurrences: deploy-and-evaluate.yml lines 132-138 (`bicep-validate`), lines 183-189 (`deploy-staging`), lines 308-314 (`evaluate`), lines 447-453 (`promote-production`).

Key facts:

* All three identity values come from **`vars.*` (GitHub Actions variables), NOT `secrets.*`**: `vars.AZURE_CLIENT_ID`, `vars.AZURE_TENANT_ID`, `vars.AZURE_SUBSCRIPTION_ID`.
* `permissions: id-token: write` is declared at the **workflow level** (lines 52-55), and re-declared in the wrapper hosted-agent-cd.yml (lines 17-19).
* GitHub Environments **are** used and carry the environment-scoped variables: `staging` and `production` (lines 127, 165, 303, 434).
* Additional `vars.*` referenced: `AZURE_RESOURCE_GROUP`, `AZURE_LOCATION`, `MCP_ACR_NAME`, `APPLICATION_MCP_IMAGE`, `RULEBOOK_MCP_IMAGE` (lines 144-149, 200-205, 209, 466-470).
* Only ONE repository secret is used anywhere: `secrets.WIKI_PUSH_TOKEN` (publish-test-trends.yml line 137). `hosted-agent-cd.yml` line 23 uses `secrets: inherit`.
* `azd` is bridged to the `az` CLI login rather than performing its own auth:

```yaml
      - name: Configure azd authentication
        run: |
          azd config set auth.useAzCliAuth true
          azd config set defaults.subscription "${{ vars.AZURE_SUBSCRIPTION_ID }}"
```

(deploy-and-evaluate.yml lines 190-194; equivalent at lines 454-476 for production.)

The comment at lines 51-52 states the intent explicitly: "Secretless OIDC federation (no stored client secrets) for every job that talks to Azure".

---

## 3. DEPLOY MECHANICS

### 3.1 Infrastructure

Two distinct mechanisms coexist:

**(a) `azd provision` / `azd deploy` — the main path (infra/main.bicep + azure.yaml).**

```yaml
      - name: Install Azure Developer CLI
        uses: Azure/setup-azd@v2

      - name: Install azd extensions (auto-install is disabled in CI)
        run: |
          azd extension install azure.ai.agents --source azd
          azd extension install azure.ai.connections --source azd
```

(deploy-and-evaluate.yml lines 175-182; repeated at 439-446.)

Environment selection and variable seeding (lines 195-206):

```yaml
      - name: Configure staging deployment environment
        working-directory: ${{ env.AGENT_PROJECT_DIR }}
        run: |
          set -euo pipefail
          azd env select "$STAGING_AZD_ENV_NAME" || azd env new "$STAGING_AZD_ENV_NAME" --no-prompt

          azd env set AZURE_SUBSCRIPTION_ID "${{ vars.AZURE_SUBSCRIPTION_ID }}"
          azd env set AZURE_TENANT_ID "${{ vars.AZURE_TENANT_ID }}"
          azd env set AZURE_LOCATION "${{ vars.AZURE_LOCATION }}"
          azd env set AZURE_RESOURCE_GROUP "${{ vars.AZURE_RESOURCE_GROUP }}"
          azd env set MCP_ACR_NAME "${{ vars.MCP_ACR_NAME }}"
```

Provision with a 3-attempt retry loop (lines 224-234, identical block at 477-487):

```yaml
      - name: Provision staging infrastructure (idempotent)
        working-directory: ${{ env.AGENT_PROJECT_DIR }}
        run: |
          set -euo pipefail
          for ATTEMPT in 1 2 3; do
            azd provision --no-prompt && exit 0
            [[ "$ATTEMPT" -lt 3 ]] || { echo "::error::azd provision failed after 3 attempts"; exit 1; }
            echo "::warning::azd provision failed (attempt $ATTEMPT/3); a prior ARM operation may still be settling -- retrying in 60s"
            sleep 60
          done
```

Deploy + verification (lines 235-248):

```yaml
      - name: Deploy candidate to staging
        id: deploy
        working-directory: ${{ env.AGENT_PROJECT_DIR }}
        run: |
          set -euo pipefail
          azd deploy --no-prompt
          PROJECT_ENDPOINT=$(azd env get-values --output json | jq -er '.FOUNDRY_PROJECT_ENDPOINT')
          echo "project_endpoint=$PROJECT_ENDPOINT" >> "$GITHUB_OUTPUT"
          azd ai agent show "$AGENT_NAME" --output json > /tmp/agent-show.json
          AGENT_VERSION=$(jq -er '.version | select(type == "string" and test("^[0-9]+$"))' /tmp/agent-show.json)
          jq -e '.status == "active"' /tmp/agent-show.json
          echo "Deployed candidate version: $AGENT_VERSION"
          echo "agent_version=$AGENT_VERSION" >> "$GITHUB_OUTPUT"
```

**(b) `az deployment group what-if` — preview only, never an apply.** (lines 142-159):

```yaml
      - name: az deployment group what-if (staging resource group; preview only, no apply)
        env:
          AZURE_RESOURCE_GROUP: ${{ vars.AZURE_RESOURCE_GROUP }}
          AZURE_LOCATION: ${{ vars.AZURE_LOCATION }}
          MCP_ACR_NAME: ${{ vars.MCP_ACR_NAME }}
          APPLICATION_MCP_IMAGE: ${{ vars.APPLICATION_MCP_IMAGE }}
          RULEBOOK_MCP_IMAGE: ${{ vars.RULEBOOK_MCP_IMAGE }}
        run: |
          set -euo pipefail
          az deployment group what-if \
            --resource-group "$AZURE_RESOURCE_GROUP" \
            --template-file infra/main.bicep \
            --parameters environmentName="$STAGING_AZD_ENV_NAME" location="$AZURE_LOCATION" \
              mcpAcrName="$MCP_ACR_NAME" applicationMcpImage="$APPLICATION_MCP_IMAGE" \
              rulebookMcpImage="$RULEBOOK_MCP_IMAGE"
```

Note: parameters are passed as **space-separated `key=value` pairs after a single `--parameters`**, not as a parameters file. `infra/main.parameters.json` exists but is not referenced by any workflow.

`infra/main.bicep` line 11 sets `targetScope = 'resourceGroup'` — there is no subscription-scoped deployment anywhere.

**(c) `infra/web-chat.bicep` is deliberately NOT wired into `main.bicep` or `azure.yaml`** and has no workflow that deploys it. Its header (web-chat.bicep lines 10-17) states it "is deployed out-of-band via a manual `az deployment group create` against this file, into the *existing* Container Apps environment, ACR, and Foundry project that infra/main.bicep already provisions."

### 3.2 Container image build and push

Images are built with **`az acr build` (remote ACR build — no Docker daemon, no `docker buildx`, no `docker login`, no registry-login action)**, then pinned by digest (lines 207-223):

```yaml
      - name: Build immutable staging MCP images
        id: build-mcp
        env:
          MCP_ACR_NAME: ${{ vars.MCP_ACR_NAME }}
        run: |
          set -euo pipefail
          REGISTRY=$(az acr show --name "$MCP_ACR_NAME" --query loginServer -o tsv)
          TAG="${GITHUB_SHA}-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
          for SERVER in application rulebook; do
            IMAGE="staging/${SERVER}-mcp:${TAG}"
            az acr build --registry "$MCP_ACR_NAME" --image "$IMAGE" --file "mcp/${SERVER}-server/Dockerfile" .
            DIGEST=$(az acr repository show --name "$MCP_ACR_NAME" --image "$IMAGE" --query digest -o tsv)
            [[ "$DIGEST" =~ ^sha256:[a-f0-9]{64}$ ]] || { echo "::error::Invalid image digest"; exit 1; }
            azd env set "${SERVER^^}_MCP_IMAGE" "${REGISTRY}/staging/${SERVER}-mcp@${DIGEST}"
            echo "${SERVER}_mcp_image=${REGISTRY}/staging/${SERVER}-mcp@${DIGEST}" >> "$GITHUB_OUTPUT"
          done
```

Conventions encoded here and reused at promotion time (lines 466-475):

* Build context is the **repository root (`.`)** with `--file <path>/Dockerfile`.
* Tag format: `${GITHUB_SHA}-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}`.
* The tag is then **resolved to a digest and only the `@sha256:` reference is propagated** — floating tags are never deployed.
* Digest shape is validated with a regex guard, and promotion re-validates it: `[[ "$IMAGE" =~ @sha256:[a-f0-9]{64}$ ]] || { echo "::error::Missing evaluated MCP image digest"; exit 1; }` (lines 471-473).
* Staging images live under the `staging/` repository prefix; production reuses the **same digest** that staging evaluated (no rebuild), passed via job outputs.

### 3.3 How the Container App is updated

**There is no `az containerapp update` anywhere.** The container app image is a Bicep parameter (`applicationMcpImage` / `rulebookMcpImage`, infra/main.bicep lines 63-67), so the update path is: set the `azd` env var to the digest → `azd provision` re-applies `infra/main.bicep` → ARM updates `Microsoft.App/containerApps` (infra/modules/mcp-container-apps.bicep line 98 onward). The same pattern is implied for web-chat, whose `image` parameter is described as "Fully digest-pinned image reference ... never a floating tag" (infra/web-chat.bicep line 32).

---

## 4. PYTHON / TEST CONVENTIONS IN CI

* **Python version: `3.13` everywhere**, always via `actions/setup-python@v6`. Evidence: continuous-validation.yml lines 31-33; deploy-and-evaluate.yml lines 80-83 and 315-318; web-chat-build.yml lines 27-29; publish-test-trends.yml lines 64-66. Quoting varies (`"3.13"` vs `'3.13'`) but the value never does.
* **Dependency install (main suite)** — one pip invocation, four requirements files, identical in both places:

```yaml
        run: |
          python -m pip install --upgrade pip
          python -m pip install \
            -r requirements.txt \
            -r mcp/application-server/requirements.txt \
            -r mcp/rulebook-server/requirements.txt \
            -r src/quote-preparation-agent/requirements.txt
```

(continuous-validation.yml lines 35-43; deploy-and-evaluate.yml lines 85-93 and 320-328.)

* **Web-chat backend install is different** — single line, requirements plus an explicit `pytest`: `python -m pip install -r apps/web-chat/requirements.txt pytest` (web-chat-build.yml lines 30-31). `apps/web-chat/requirements.txt` is a separate file not included in the four-file list above.
* **Judge SDKs are pinned inline, not in a requirements file**: `python -m pip install azure-ai-projects==2.6.0 openai==3.6.0 azure-identity==1.25.3` (deploy-and-evaluate.yml lines 367-368).

### Exact pytest invocation patterns

Three sweeps, always from the **repository root** (no `working-directory`), always `-v`, always `--junitxml`:

```yaml
pytest src/quote-preparation-agent/tests -v --junitxml=evidence/agent.xml
pytest eval -v --junitxml=evidence/deterministic.xml
pytest apps/workshop/tests mcp/application-server/tests mcp/rulebook-server/tests \
  -v --junitxml=evidence/reporting.xml
```

(continuous-validation.yml lines 45-56; deploy-and-evaluate.yml lines 94-107 uses the same three commands but writes into `offline-evidence/` instead of `evidence/`, and creates the directory inline with `mkdir -p offline-evidence` at line 96.)

The web-chat sweep is the only one that differs in style and is the **only place `PYTHONPATH` is manipulated**:

```yaml
      - name: Backend authorization and session tests
        env:
          PYTHONPATH: apps/web-chat
        run: python -m pytest apps/web-chat/tests -q --junitxml=web-chat-evidence/backend.xml
```

(web-chat-build.yml lines 32-35.) Note: `python -m pytest`, `-q` not `-v`, and `PYTHONPATH: apps/web-chat` so `app`/`auth` import as top-level modules. This is documented as an intentional convention in pyrightconfig.json per session memory notes.

### Artifacts / evidence publishing

* Always `actions/upload-artifact@v6`.
* Naming conventions that downstream tooling depends on:
  * `offline-test-evidence-${{ github.run_attempt }}` (continuous-validation.yml line 113; deploy-and-evaluate.yml line 115)
  * `evaluation-evidence-${{ github.run_attempt }}` (deploy-and-evaluate.yml line 417)
  * `deployment-links-staging` / `deployment-links-production` (lines 283, 527)
  * `azd-env-staging` — uploads `${{ github.workspace }}/.azure/` with `include-hidden-files: true`, `retention-days: 1`, `if-no-files-found: error` (lines 249-257)
  * `web-chat-frontend-${{ github.sha }}`, `web-chat-tests-${{ github.run_attempt }}` (web-chat-build.yml lines 50-64)
  * `production-version-evidence` (lines 499-506)
* Retention: 30 days for test/eval evidence, 14 days for deployment links and web-chat artifacts, 1 day for azd env state.
* `if: always()` on every evidence-upload and summary step; `if-no-files-found: warn` except where a missing file is a real failure.
* Every workflow ends by writing to `$GITHUB_STEP_SUMMARY`, frequently via `python scripts/ci_results.py --junit <dir>` and `python scripts/deployment_summary.py` (continuous-validation.yml lines 97-103; web-chat-build.yml lines 66-70).

---

## 5. FRONTEND BUILD

CI build (web-chat-build.yml lines 23-49):

```yaml
      - uses: actions/setup-node@v6
        with:
          node-version: '22'
          registry-url: https://registry.npmjs.org
...
      - name: Resolve frontend dependencies on the hosted runner
        working-directory: apps/web-chat/frontend
        run: |
          if [ -f package-lock.json ]; then
            npm ci
          else
            npm install
          fi
      - name: Frontend stream contract tests
        working-directory: apps/web-chat/frontend
        run: node --test --test-reporter=spec --test-reporter=junit --test-reporter-destination=stdout --test-reporter-destination=../../../web-chat-evidence/frontend.xml tests/*.test.js
      - name: Compile frontend
        working-directory: apps/web-chat/frontend
        run: npm run build
```

* Node **22**, npm (`npm ci` preferred, `npm install` fallback — the lockfile is not committed, hence the conditional; the workflow uploads the generated lockfile as an artifact, line 55).
* Build tool is **Vite**: `"build": "vite build"` (apps/web-chat/frontend/package.json line 8), React 19 + `@azure/msal-browser` ^4 (lines 12-21).
* Output dir is `apps/web-chat/frontend/dist/` (uploaded at web-chat-build.yml lines 53-56).
* Tests use the **Node built-in test runner** (`node --test`), not Jest/Vitest, and emit JUnit XML.

Container packaging is a **two-stage Dockerfile** (apps/web-chat/Dockerfile):

```dockerfile
FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/index.html frontend/vite.config.js ./
COPY frontend/src ./src
COPY frontend/tests/request.test.js frontend/tests/stream.test.js ./tests/
RUN npm test && npm run build

FROM python:3.13-slim-bookworm
...
COPY --from=frontend /build/dist ./frontend/dist
USER 10001
EXPOSE 8000
CMD ["uvicorn", "app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
```

(Dockerfile lines 1-19.) Important: stage 1 requires `frontend/package-lock.json` to exist in the build context (`COPY` of it is unconditional, line 3) — but the lockfile is **not committed** (that is exactly why CI has the `npm ci`/`npm install` conditional). **An `az acr build` of this Dockerfile from a clean checkout will fail on that COPY.** The container serves the FastAPI app on port 8000 with a `/healthz` probe endpoint (infra/web-chat.bicep lines 128-131) as a non-root uid 10001 user.

---

## 6. EXISTING TEARDOWN

**Definitive answer: NO. There is no teardown, cleanup, destroy, or purge workflow or script of any kind in this repository.**

Evidence — a repo-wide regex grep for `az group delete|azd down|az containerapp delete|az ad app delete|--purge|deletedItems|Remove-Az` returned **exactly 2 matches, both in prose inside a slide-deck generator**:

* scripts/build-workshop-deck.js line 243: `'Confirm there is nothing to azd down or delete in a subscription'`
* scripts/build-workshop-deck.js line 249: the French translation of the same bullet.

What exists that is *named* teardown but is not an implementation:

* docs/labs/lab-09-teardown.md and docs/fr/labs/lab-09-teardown.md — a **learner** lab whose stated objective (lab-09-teardown.md line 22) is "Confirm this workshop provisioned no Azure resources, so there is no cloud teardown to run", with an exercise titled "Confirm There Is No Cloud Teardown" (line 57). It teaches stopping local processes only.
* docs/labs/index.md line 27 and docs/fr/labs/index.md line 28 index that lab as "Stop local processes and confirm there is no cloud teardown to run".

Complete script inventory (glob `**/*.{ps1,sh}` — 5 files, none destructive):

* scripts/setup-web-chat-identity.ps1 (Entra — see §7)
* scripts/capture-release-evidence.ps1 (headless Edge screenshots into assets/release-evidence)
* scripts/test-agent-response.sh
* scripts/test-production-version.sh
* scripts/record-production-version.sh

Note the important contradiction: the repo's own documentation asserts nothing has been deployed (infra/README.md lines 1-9, 44-48; README.md lines 129-140; banners on every `.bicep` and on azure.yaml lines 3-9), but session memory (/memories/session/hosted-agent-cicd-fix.md lines 34-43) records a **real live deployment**: resource group `rg-desjardins-quote-preparation`, region `eastus2`, subscription `64c3d212-40ed-4c6d-a825-6adfbdf25dad`, ACR `acrdesjqp7651`, azd envs `desjardins-quote-preparation-staging` and `desjardins-quote-preparation-poc`. A teardown workflow must be designed against reality, not the banners.

---

## 7. ENTRA AUTOMATION

**Yes — exactly one artifact automates Entra ID, and it is a manually-run PowerShell script, NOT wired into any workflow.**

File: scripts/setup-web-chat-identity.ps1 (107 lines). No workflow references it (grepped; zero hits outside docs/research/tracking prose). README.md lines 136-139 describe it as an operator prerequisite.

Structure and exact behavior:

* **Parameters** (lines 1-7): `-RedirectUri` (default `http://localhost:8000`), mandatory `-TenantId`, mandatory `-PilotGroupId`.
* **Hard-coded identifiers** (lines 10-12) — this is the key convention for a second app:

```powershell
$displayName = 'Foundry Quote Preparation Web Chat'
$scopeId = 'e14a1f2b-6c3d-4a91-9b7e-2f8d3c5a6b10'
$roleId = 'b7d4e912-3f6a-4c88-9e21-5a0d8f4b6c33'
```

* **Graph access is via `az rest`, not the Graph PowerShell SDK** (lines 14-30). The `Invoke-Graph` helper writes the body to a temp file and passes `--body "@$temporary"` to avoid shell quoting problems, targets `https://graph.microsoft.com/v1.0/$Path`, throws on non-zero `$LASTEXITCODE`, and cleans up the temp file in a `finally`.
* **Guard rails before any write** (lines 32-39): asserts `az account show` tenant equals `-TenantId` ("Sign in to the approved tenant first."), asserts the pilot group is `securityEnabled`, and rejects any redirect URI that is neither HTTPS nor the approved `http://localhost:8000`.
* **Idempotent create-or-update** (lines 41-47): `az ad app list --display-name $displayName`; throws if more than one match ("Cannot uniquely resolve the web-chat application."); POSTs `applications` with `signInAudience = 'AzureADMyOrg'` only when zero matches.
* **App configuration PATCH** (lines 49-78) sets `identifierUris = @("api://$($application.appId)")`, `groupMembershipClaims = 'SecurityGroup'`, merged+deduped SPA `redirectUris`, `api.requestedAccessTokenVersion = 2`, one `oauth2PermissionScopes` entry `value = 'Chat.Access'` / `type = 'Admin'` with the fixed `$scopeId`, a self-referential `requiredResourceAccess` (`resourceAppId = $application.appId`), and one `appRoles` entry:

```powershell
    appRoles = @(@{
        id = $roleId
        value = 'Pilot.User'
        displayName = 'Pilot user'
        description = 'Assigned member of the web-chat pilot.'
        allowedMemberTypes = @('User')
        isEnabled = $true
    })
```

* **Service principal** (lines 80-86): `az ad sp list --filter "appId eq '...'"`, create if missing with `appRoleAssignmentRequired = $true`, then PATCH to re-assert that flag (line 89).
* **Group role assignment** (lines 90-95): reads `servicePrincipals/{id}/appRoleAssignedTo`, POSTs `{ principalId = $PilotGroupId; resourceId = $principal.id; appRoleId = $roleId }` only if not already present.
* **Admin consent is granted programmatically**, not via `az ad app permission admin-consent` (lines 96-101):

```powershell
$grants = Invoke-Graph GET "servicePrincipals/$($principal.id)/oauth2PermissionGrants" $null
if (-not ($grants.value | Where-Object { $_.resourceId -eq $principal.id -and $_.scope -eq 'Chat.Access' -and $_.consentType -eq 'AllPrincipals' })) {
    Invoke-Graph POST 'oauth2PermissionGrants' @{
        clientId = $principal.id; resourceId = $principal.id; consentType = 'AllPrincipals'; scope = 'Chat.Access'
    } | Out-Null
}
```

* **Post-write verification then structured stdout** (lines 102-107): re-GETs the application, throws unless `requestedAccessTokenVersion -eq 2` and `groupMembershipClaims -eq 'SecurityGroup'`, then emits an ordered JSON object of `tenantId`, `clientId`, `applicationObjectId`, `servicePrincipalId`, `pilotGroupId`, `redirectUris`.

What is **NOT** automated today, anywhere:

* Security **group creation** — `-PilotGroupId` must already exist and is validated, never created.
* Any **federated credential / OIDC app registration** for GitHub Actions itself (the `vars.AZURE_CLIENT_ID` identity was created out of band).
* Any **deletion/rollback** of the app registration or service principal.
* Any invocation of this script from CI.

---

## 8. GAPS FOR THE NEW WORK

### 8.a Reviewer-app build + deploy workflow

Best template to copy: **web-chat-build.yml for the build/test half, and the `deploy-staging` job of deploy-and-evaluate.yml for the deploy half.** There is no existing workflow that both builds a container and deploys it, so this is genuinely new composition — web-chat-build.yml stops at `dist/` and never touches Azure.

Conventions it must follow:

| Convention | Value | Source |
|---|---|---|
| Action versions | `actions/checkout@v6`, `actions/setup-python@v6`, `actions/setup-node@v6`, `actions/upload-artifact@v6`, `azure/login@v3`, `Azure/setup-azd@v2` | all workflows |
| Checkout hardening | `persist-credentials: false` on non-deploy jobs | continuous-validation.yml line 29, web-chat-build.yml line 22 |
| Python / Node | 3.13 / 22 | §4, §5 |
| Permissions | `contents: read` + `id-token: write` only on Azure-touching jobs | deploy-and-evaluate.yml lines 52-55 |
| Auth | `azure/login@v3` with `vars.AZURE_CLIENT_ID`/`AZURE_TENANT_ID`/`AZURE_SUBSCRIPTION_ID` | §2 |
| Environment | `environment: staging` / `environment: production` | lines 165, 434 |
| Concurrency | reuse `group: desjardins-quote-preparation-shared-environments`, `queue: max` if it touches the shared RG | lines 56-58 |
| Image build | `az acr build --registry "$MCP_ACR_NAME" --image "<prefix>/<name>:${GITHUB_SHA}-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}" --file <path>/Dockerfile .` then resolve digest, regex-validate `^sha256:[a-f0-9]{64}$`, deploy by digest only | lines 207-223 |
| Shell | `set -euo pipefail` at the top of every multi-line `run` that matters | throughout |
| Failure signalling | `echo "::error::..."` / `echo "::warning::..."` annotations | lines 214, 228-229 |
| Evidence | upload artifact `<kind>-${{ github.run_attempt }}`, `if: always()`, `if-no-files-found: warn` | §4 |
| Summary | append to `$GITHUB_STEP_SUMMARY`; call `python scripts/deployment_summary.py --out ...` if it produces deployable links | lines 271-278 |

Constraints and traps:

1. A reviewer app deployed from a standalone Bicep file will need a decision the repo has not yet made: either follow web-chat.bicep's **out-of-band `az deployment group create`** pattern (currently 100% manual, never automated) or wire the resource into `infra/main.bicep` so `azd provision` owns it. Mixing the two would let `azd provision` delete or drift resources it does not know about.
2. `deployment_summary.py` already reserves keys for a web app: `WEB_CHAT_APP_NAME`, `WEB_CHAT_URL` (scripts/deployment_summary.py lines 67-68, 87-101). A reviewer app should add sibling keys the same way rather than hardcoding a URL — README.md lines 100-127 commit to "no hardcoded live demo URL".
3. To get the new workflow's evidence onto the wiki, it must be added to publish-test-trends.yml's `workflows:` list (line 30) **and** the `jq -e '.path == ...'` allow-list (lines 84-88), otherwise the provenance check fails the publish job.
4. If the reviewer app's Dockerfile mirrors apps/web-chat/Dockerfile, the missing committed `package-lock.json` will break `npm ci` in the container build (see §5).

### 8.b Teardown workflow

There is **no template in this repository** — this is fully greenfield. Closest structural analogue is hosted-agent-cd.yml (a `workflow_dispatch`-only, `id-token: write` entry point) plus the `bicep-validate` job's login-and-run-az-command shape.

Resources the feature provisions that a teardown must handle (enumerated from the templates):

From infra/main.bicep (`targetScope = 'resourceGroup'`, line 11) and its modules:

* `Microsoft.OperationalInsights/workspaces` — `log-${environmentName}` (line 56) **and** a second one `${namePrefix}-mcp-logs` inside the MCP module (mcp-container-apps.bicep line 74)
* `Microsoft.Insights/components` — `appi-${environmentName}` (line 59)
* `Microsoft.CognitiveServices/accounts` — `aif-${environmentName}` (line 21) with child project `proj-${environmentName}` (line 23) and a model deployment
* `Microsoft.App/managedEnvironments` — `${namePrefix}-mcp-env` (mcp-container-apps.bicep line 75)
* `Microsoft.App/containerApps` — `${namePrefix}-application-server` (line 98) and `${namePrefix}-rulebook-server`
* `Microsoft.ManagedIdentity/userAssignedIdentities` — `${namePrefix}-image-pull` (line 58)
* `Microsoft.Authorization/roleAssignments` — AcrPull on the ACR (line 63); Foundry roles via modules/rbac.bicep

From infra/web-chat.bicep (standalone): `${appName}-identity` user-assigned identity (line 69), two role assignments (AcrPull line 73, Foundry User line 82), and the `foundry-quote-chat-staging` container app (line 92).

From scripts/setup-web-chat-identity.ps1: one application, one service principal, one appRoleAssignedTo grant, one oauth2PermissionGrant.

New for this feature: **Cosmos DB** — note that *no Cosmos DB resource exists in this repository today*. Grepping for `cosmos` returns only src/quote-preparation-agent/state.py line 11 ("no equivalent to the sibling's optional Cosmos DB checkpointer here") and prose in tracking docs. So the teardown must delete something the Bicep does not yet declare; whoever adds Cosmos must add it to a template first or the teardown will have nothing authoritative to enumerate.

Constraints the implementer must plan for:

1. **Soft-delete / purge.** `Microsoft.CognitiveServices/accounts` soft-deletes: a plain resource-group delete leaves the account name reserved, and re-provisioning the same `aif-<env>` name fails until it is purged (`az cognitiveservices account purge --name <n> --resource-group <rg> --location <loc>`). Azure Cosmos DB accounts likewise support soft-delete/restore semantics. Log Analytics workspaces soft-delete for 14 days (`az monitor log-analytics workspace delete --force` needed to bypass). An ACR is *shared infrastructure that main.bicep only references as `existing`* (mcp-container-apps.bicep lines 53-55, `acrName` param) — **the teardown must NOT delete the ACR** unless it is explicitly in scope, and the same applies to anything else declared `existing`.
2. **Blast radius.** `AZURE_RESOURCE_GROUP` is a single shared RG (`rg-desjardins-quote-preparation` per session memory) used by BOTH the staging and production azd environments (deploy-and-evaluate.yml lines 200-205 and 466-470 set the same `vars.AZURE_RESOURCE_GROUP` for both). A naive `az group delete` would destroy production while tearing down staging. Scope teardown by resource name prefix / azd env name, or require an explicit typed confirmation input.
3. **Concurrency.** Must join `group: desjardins-quote-preparation-shared-environments` with `queue: max` (lines 56-58) so a teardown cannot interleave with an in-flight `azd provision`.
4. **Permissions the CI identity needs that it may not have today.** Deleting resources requires Contributor-or-better on the RG; deleting **role assignments** requires `Microsoft.Authorization/roleAssignments/delete` (User Access Administrator or RBAC Administrator) — Contributor alone cannot remove the AcrPull/Foundry role assignments the templates create. Purging a Cognitive Services account requires the purge action on the *subscription/location* scope, not just the RG.
5. **Entra deletion needs Graph application permissions, not Azure RBAC.** Deleting an application/service principal requires `Application.ReadWrite.All` (or `Application.ReadWrite.OwnedBy` if the CI SP created it) granted to the **OIDC app registration itself** as a Microsoft Graph application permission with admin consent. Azure `Contributor`/`Owner` grants exactly zero Graph rights. Also note Entra applications soft-delete for 30 days and must be hard-removed via `directory/deletedItems/{id}` if the name must be reusable immediately.
6. **Guard rails.** The existing PowerShell precedent is to *refuse* rather than guess: assert the signed-in tenant matches (setup-web-chat-identity.ps1 lines 32-33) and throw when a lookup is ambiguous (lines 42, 81). A teardown should mirror that — verify subscription/tenant/RG before any delete, and `workflow_dispatch`-only with a required confirmation input, matching the AUTHOR-ONLY posture of hosted-agent-cd.yml lines 2-12.

### 8.c Reviewer app registration automation

Best template: **copy scripts/setup-web-chat-identity.ps1 wholesale** — it is the only Entra automation and it establishes every convention.

Must-match conventions:

* PowerShell 5+/7 compatible, `$ErrorActionPreference = 'Stop'` (line 9).
* `az rest` + the `Invoke-Graph` temp-file body helper against Graph **v1.0** (lines 14-30) — do not introduce `Microsoft.Graph` PowerShell modules; nothing in CI installs them.
* **New, distinct, hard-coded GUIDs** for the reviewer scope and the reviewer app role. Reusing `e14a1f2b-...` or `b7d4e912-...` across two applications would be a correctness bug. The role for the new work is described as a "Reviewer" app role — follow the existing shape: `value = '<Something>.Reviewer'`-style string, `allowedMemberTypes = @('User')`, `isEnabled = $true` (lines 73-80).
* A distinct `$displayName` (the lookup is `az ad app list --display-name` and throws on ambiguity, lines 41-42) — it must not collide with `'Foundry Quote Preparation Web Chat'`.
* `signInAudience = 'AzureADMyOrg'`, `requestedAccessTokenVersion = 2`, `groupMembershipClaims = 'SecurityGroup'`, `appRoleAssignmentRequired = $true` (lines 51-57, 86-89).
* Idempotent everywhere: list-then-create, merge-and-dedupe redirect URIs, check-before-POST for both `appRoleAssignedTo` and `oauth2PermissionGrants`.
* End with post-write verification and ordered-JSON stdout (lines 102-107) so a caller can capture `clientId` for Bicep parameters.

Open constraint: if this script is to run **in CI** (it never has), the OIDC identity needs Graph `Application.ReadWrite.All` + `AppRoleAssignment.ReadWrite.All` + `DelegatedPermissionGrant.ReadWrite.All` with admin consent, and PowerShell must be invoked explicitly (`shell: pwsh`) since every existing `run:` block is bash on `ubuntu-latest`.

---

## Key Discoveries (ranked by risk of getting wrong)

1. **Identity comes from `vars.*`, not `secrets.*`.** Using `secrets.AZURE_CLIENT_ID` will silently resolve to empty and fail at login.
2. **Digest-only deployment.** Never deploy a floating tag; build → resolve digest → regex-validate → pass the `@sha256:` reference.
3. **`az acr build`, never `docker build`.** No Docker daemon, no registry login step exists or is needed.
4. **Container App updates happen through Bicep parameters + `azd provision`**, not `az containerapp update`.
5. **The shared resource group hosts staging AND production.** Teardown by RG deletion is a production outage.
6. **Zero teardown exists.** Also zero Cosmos DB exists. Both are greenfield.
7. **Entra automation is one manual `.ps1`, never run by CI**, and the CI OIDC identity almost certainly lacks Graph permissions today.
8. **publish-test-trends.yml has a hard-coded allow-list** of source workflow paths and artifact names; a new workflow is invisible to the wiki until added in two places.
9. **AUTHOR-ONLY banners are stale.** Every `.bicep`, `azure.yaml`, and infra/README.md claim nothing is deployed; session memory records a live deployment in `rg-desjardins-quote-preparation`. Do not treat the banners as ground truth, and decide deliberately whether new files carry the same banner.

## Recommended Next Research (not completed this session)

- [ ] Confirm the current Azure role assignments held by the `vars.AZURE_CLIENT_ID` OIDC service principal (is it Owner, Contributor, or User Access Administrator on `rg-desjardins-quote-preparation`?) — determines whether it can delete role assignments.
- [ ] Confirm which Microsoft Graph **application** permissions, if any, are already consented for that same app registration.
- [ ] Confirm whether the `production` GitHub Environment now has required reviewers configured (session memory says it did not).
- [ ] Enumerate the live resource group contents (`az group resource list`) to compare actual deployed resources against what the Bicep declares, since the templates and reality have diverged before.
- [ ] Read the remaining ~70 lines of scripts/deployment_summary.py and scripts/ci_results.py to confirm the exact env-var keys a reviewer app should export.
- [ ] Review scripts/test-agent-response.sh, scripts/test-production-version.sh, scripts/record-production-version.sh (not read in full; grep showed no deployment or Entra content).
- [ ] Determine the intended Cosmos DB usage (container/database names, throughput mode, whether it replaces the SQLite approval repository) — required before a teardown can enumerate it.

## Clarifying Questions

1. **Is the reviewer app a second Container App, or a second route/container inside the existing web-chat app?** The teardown scope and the Bicep composition differ substantially.
2. **Should the reviewer app be wired into `infra/main.bicep` (azd-owned) or kept standalone like `infra/web-chat.bicep` (manual `az deployment group create`)?** The repo currently has one of each and no stated preference.
3. **Is teardown scoped to one azd environment (staging only) or to everything in the shared resource group?** The RG is shared by staging and production.
4. **Should teardown delete the shared ACR (`acrdesjqp7651`) and any pre-existing resources referenced as `existing` in Bicep?** Current templates treat the ACR as external input.
5. **Is the CI OIDC identity permitted to be granted Microsoft Graph `Application.ReadWrite.All`?** Without it, reviewer app registration and Entra teardown cannot run in CI and must stay operator-run.
6. **Do the AUTHOR-ONLY / G2-G3-G6 gate banners still apply** to newly added infra and workflows, given a deployment demonstrably exists?
7. **Should `apps/web-chat/frontend/package-lock.json` be committed?** Its absence will break any `az acr build` of the existing Dockerfile, which a reviewer-app deploy workflow would likely mirror.
