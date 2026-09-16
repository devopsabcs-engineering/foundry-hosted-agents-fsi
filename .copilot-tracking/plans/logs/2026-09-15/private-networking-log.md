<!-- markdownlint-disable-file -->
# Planning Log: Private Networking Remediation

**Related Plan**: none (reactive remediation from a production defect)

## Discrepancy Log

### Implementation Deviations

* DD-01: The virtual network is a separate template rather than part of `main.bicep`
  * Plan specifies: nothing, this was discovered during implementation
  * Implementation differs: `infra/network.bicep` is deployed once per resource
    group under the fixed name `network-foundation`
  * Rationale: `main.bicep` deploys twice into one resource group, and an ARM
    write that omits `subnets` deletes the ones it does not name

* DD-02: Foundry accounts keep `publicNetworkAccess: 'Enabled'` alongside `networkInjections`
  * Documentation ties injection to Standard Agent Setup with private
    networking, which mandates BYO Storage, AI Search, and provisioned Cosmos
  * A probe deployment proved the combination is accepted on Basic Agent Setup
  * Verified in production: the agent reaches Cosmos over the private endpoint
    without any of the Standard Setup dependencies

## Suggested Follow-On Work

* WI-40: Prune dead redirect URIs in the identity scripts (medium)
  * `setup-reviewer-identity.ps1` and `setup-web-chat-identity.ps1` merge
    redirect URIs with `Sort-Object -Unique` and never remove them, so every
    network rebuild leaves a URI pointing at a hostname that no longer exists
  * This session pruned the reviewer registration by hand through Graph
  * Dependency: none

* WI-41: Make the deploy workflow tolerate a long-running promotion (medium)
  * `azd deploy` failed once with
    `AzureDeveloperCLICredential: please run "azd auth login"` after the
    production teardown and provision had consumed most of the token lifetime
  * A rerun of the failed job succeeded with no code change
  * Dependency: none

* WI-42: Decide whether the chat apps should join the main deployment graph (low)
  * `infra/web-chat.bicep` is applied out of band, so a network rebuild deletes
    both chat apps and nothing redeploys them automatically
  * Dependency: none

* WI-43: Neither agent persists cases to Cosmos (high)
  * Root cause found while closing this item: `azure.yaml` never passed
    `COSMOS_ENDPOINT` to the hosted agent. `build_case_store()` therefore
    returned an in-memory SQLite store in both environments, so submitted
    cases were discarded and never reached the reviewer queue. Confirmed
    against the live production agent definition, whose environment variables
    contain no `COSMOS_ENDPOINT`
  * The original symptom (production cannot write) understated the defect:
    staging did not persist either, it simply had a valid grant sitting unused
  * Fix part 1 (applied): `azure.yaml` now passes `${COSMOS_ENDPOINT}` to the
    hosted agent, alongside the existing MCP URLs
  * Fix part 2 (blocked): the agents API reports an
    `instance_identity.principal_id` for the production agent that does not
    resolve in Entra, so the Cosmos data-plane grant cannot be applied and
    `AGENT_PRINCIPAL_ID` is deliberately unset. Deploying fix part 1 before
    this is resolved would turn a silent no-op into a visible production
    failure, so the change is held
  * The staging identity resolves and predates the teardown, which shows these
    identities are tenant-level and survive account deletion. Production's was
    never registered or was removed independently
  * Next step: delete and redeploy the production agent so Foundry mints a
    fresh identity, confirm it resolves with `az ad sp show`, set
    `AGENT_PRINCIPAL_ID`, then deploy both fixes together
  * Also pending: delete the orphaned production Cosmos grant for dead
    principal `3984e2d5-374e-44ee-b83e-3837f7aeb6f0`, mirroring the staging
    cleanup
  * Dependency: none

* WI-31 (carried forward): Should `setup-reviewer-identity.ps1` publish
  `REVIEWER_CLIENT_ID` and create the reviewer group itself? (low)

## User Decisions

* ID-01: Remediation approach — Option A selected
  * Rationale: the user chose full private networking plus a lab rewrite over
    narrower alternatives, and accepted teardown and redeployment as the cost
