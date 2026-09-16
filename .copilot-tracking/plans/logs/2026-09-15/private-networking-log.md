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

* WI-43: Neither agent persists cases to Cosmos (high) — RESOLVED
  * Root cause found while closing this item: `azure.yaml` never passed
    `COSMOS_ENDPOINT` to the hosted agent. `build_case_store()` therefore
    returned an in-memory SQLite store in both environments, so submitted
    cases were discarded and never reached the reviewer queue. Confirmed
    against the live production agent definition, whose environment variables
    contained no `COSMOS_ENDPOINT`
  * The original symptom (production cannot write) understated the defect:
    staging did not persist either, it simply had a valid grant sitting unused
  * Fix part 1: `azure.yaml` now passes `${COSMOS_ENDPOINT}` to the hosted
    agent, alongside the existing MCP URLs
  * Fix part 2: the old production identity was unregistered in Entra, so the
    agent was deleted with `force=true` and recreated by the pipeline. The
    fresh identity `171dca8a-bda3-46ec-8121-a235ecee6e30` accepted the Cosmos
    grant, which is itself proof of registration because Cosmos rejects
    grants to principals it cannot resolve
  * Verified end to end: a case submitted to the production agent now appears
    in Cosmos, read from inside the VNet through the reviewer app container.
    The pre-fix submissions are absent, confirming they were discarded
  * Cleanup done: the orphaned production grant for dead principal
    `3984e2d5-374e-44ee-b83e-3837f7aeb6f0` was deleted, and
    `AGENT_PRINCIPAL_ID` was reset for both environments

* WI-44: The staging account is not registered with the agent gateway (high)
  * Invoking the staging responses endpoint returns
    `ResourceNotFound: Subdomain does not map to a resource`, from CI and
    from a workstation alike. Recreating the staging agent did not help, so
    this is account-level rather than agent-level
  * Isolated with a nonexistent-agent probe against both accounts. Production
    answers `Agent 'no-such-agent' not found`, which means the request
    reached the agent gateway. Staging answers with the subdomain error,
    which means it never got that far
  * Everything comparable is symmetric: kind, SKU, provisioning state,
    `publicNetworkAccess`, `allowProjectManagement`, the exposed endpoint
    list, `networkInjections`, the injection subnets, and the one-project
    layout. DNS resolves both hosts to the same address
  * The staging agent kept its version history through the network rebuild
    (5 then 6) while production restarted at 1, so the production account was
    recreated and the staging account was not. The working environment is the
    recreated one
  * This was masked because the LLM-judge step is `continue-on-error`, so a
    hard transport 404 surfaced as a green run. The workflow now fails when
    the judge produces no evidence
  * Next step: rebuild the staging Foundry account through
    `network-rebuild-teardown.yml`, then rerun the pipeline and re-grant the
    new staging agent identity
  * Dependency: none

* WI-31 (carried forward): Should `setup-reviewer-identity.ps1` publish
  `REVIEWER_CLIENT_ID` and create the reviewer group itself? (low)

## User Decisions

* ID-01: Remediation approach — Option A selected
  * Rationale: the user chose full private networking plus a lab rewrite over
    narrower alternatives, and accepted teardown and redeployment as the cost
