# Infrastructure Scaffolding (Phase 8) — Author-Only, Gated

Status: **authored, not deployed, not reviewed.**

Everything in this directory is Bicep source only. No file here has been
applied against an Azure subscription, and none should be until the
following gates are explicitly cleared by their owners:

* **Gate G2 — platform/security sign-off** (network topology, ingress
  posture, identity/RBAC model).
* **Gate G3 — reproducible compatibility** (pinned model name/version, SDK
  and package version compatibility).
* **Gate G6 — regulatory/privacy sign-off** (synthetic-data-only boundary,
  no real customer/PII flow into any provisioned resource).

## What exists here

* `main.bicep` / `main.parameters.json` — orchestrating template that wires
  the four modules together (mirrors the sibling `foundry-hosted-agents`
  repository's `infra/main.bicep` composition, renamed for this project).
* `modules/monitoring.bicep` — Log Analytics workspace + Application
  Insights component.
* `modules/ai-foundry.bicep` — Foundry account, project, model deployment,
  and MCP toolbox connections (`application-conn`, `rulebook-conn`) for the
  `quote-preparation-agent`.
* `modules/mcp-container-apps.bicep` — Container Apps environment and two
  apps (`*-application-server`, `*-rulebook-server`) hosting the read-only
  MCP services defined in `mcp/application-server` and `mcp/rulebook-server`.
* `modules/rbac.bicep` — Foundry role assignments (User, Project Manager,
  Agent Consumer) for a list of principal IDs.

All resource names, tags, and parameters were renamed from the sibling
Air Canada threat-assessment reference (`defender-server`/`anomaly-server`
→ `application-server`/`rulebook-server`; `threat-assessment-agent` →
`quote-preparation-agent`). Model name/version/SKU defaults are placeholders
carried over from the reference for structural completeness only — they are
**not** an approved model selection and must be revisited once Gate G2/G3
discovery completes. No tenant ID, subscription ID, credential, or
production endpoint is hard-coded anywhere in these templates.

## What was validated in this phase

* `bicep build` (via `az bicep build`) lint/compile check on every `.bicep`
  file listed above — see the Phase 8 completion report for exact
  pass/fail results.
* No `azd provision`, `azd deploy`, `azd up`, `az deployment group create`,
  or any other apply/provision command was executed against these
  templates or the root `azure.yaml`.

## Before any deploy is attempted

1. Confirm Gate G2, G3, and G6 sign-off is on record.
2. Replace placeholder model name/version/SKU with the approved selection.
3. Confirm the target resource group, subscription, and region with the
   platform owner; none are assumed or hard-coded here.
4. Re-run `bicep build` / `az bicep build` after any edits, before running
   `azd provision` for the first time.
