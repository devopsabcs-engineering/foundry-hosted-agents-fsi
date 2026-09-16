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

* WI-43: Production agent cannot write cases (high)
  * The agents API reports an `instance_identity.principal_id` for the
    production agent that does not resolve in Entra, so the Cosmos data-plane
    grant cannot be applied and `AGENT_PRINCIPAL_ID` is deliberately unset
  * The agent itself is healthy and returns the correct bounded bilingual
    message, so this affects case persistence only
  * The staging identity resolves and predates the teardown, which shows these
    identities are tenant-level and survive account deletion. Production's was
    never registered or was removed independently
  * Next step: redeploy the production agent to mint a fresh identity, confirm
    it resolves with `az ad sp show`, then set the variable and rerun
  * Dependency: none

* WI-31 (carried forward): Should `setup-reviewer-identity.ps1` publish
  `REVIEWER_CLIENT_ID` and create the reviewer group itself? (low)

## User Decisions

* ID-01: Remediation approach — Option A selected
  * Rationale: the user chose full private networking plus a lab rewrite over
    narrower alternatives, and accepted teardown and redeployment as the cost
