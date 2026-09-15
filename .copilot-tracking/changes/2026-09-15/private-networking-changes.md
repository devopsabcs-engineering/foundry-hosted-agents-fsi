<!-- markdownlint-disable-file -->
# Release Changes: Private Networking Remediation

**Related Plan**: none (reactive remediation from a production defect)
**Implementation Date**: 2026-09-15

## Summary

A tenant-root Azure Policy applies a `modify` effect that forces
`publicNetworkAccess: 'Disabled'` on every Cosmos DB account. The templates
declared `Enabled`, so every deployment produced permanent drift and both the
reviewer app and the agent lost their path to the case store. The reviewer app
surfaced this as HTTP 500 on every request.

The remediation routes Cosmos traffic over a private endpoint, moves the
Container Apps environments and Foundry accounts onto a shared virtual network,
and adds a teardown workflow for the resources whose network configuration is
immutable. The labs and the infra README were rewritten to describe the
deployed system rather than the earlier author-only posture.

## Changes

### Added

* infra/network.bicep - shared VNet, five subnets, Cosmos private DNS zone and link
* infra/network.json - compiled artifact
* .github/workflows/network-rebuild-teardown.yml - dispatch-only teardown for immutable network configuration
* .copilot-tracking/research/2026-09-15/private-networking-research.md - policy findings and the network injection probe result

### Modified

* infra/main.bicep - references the existing VNet, subnets, and DNS zone; passes them to the modules
* infra/main.json - compiled artifact
* infra/modules/cosmos-db.bicep - declares the policy-enforced Disabled state and adds the SQL private endpoint with its DNS zone group
* infra/modules/mcp-container-apps.bicep - VNet-integrated managed environment with a Consumption workload profile
* infra/modules/ai-foundry.bicep - agent network injection into a dedicated subnet
* infra/modules/monitoring.bicep - banner corrected
* infra/modules/rbac.bicep - banner corrected
* infra/modules/cosmos-rbac.bicep - banner corrected
* infra/modules/reviewer-app.bicep - banner corrected
* infra/web-chat.bicep - deploymentLabel parameter drives the reported environment
* infra/web-chat.json - compiled artifact
* .github/workflows/deploy-and-evaluate.yml - deploys the network foundation idempotently in both jobs; banner corrected
* apps/web-chat/app.py - environment is configurable rather than a hardcoded literal
* apps/reviewer-app/frontend/src/main.jsx - distinguishes a failed queue load from an empty queue
* infra/README.md - rewritten around the deployed architecture and the network split
* docs/labs/index.md, docs/fr/labs/index.md - Lab 10 summary
* docs/labs/lab-10-azure-foundation.md, docs/fr/labs/lab-10-azure-foundation.md - network foundation and Cosmos private endpoint exercises replace the gate narrative
* docs/labs/lab-11-web-chat.md, docs/fr/labs/lab-11-web-chat.md - points at the deployed chat origin
* docs/labs/lab-14-pilot-operations.md, docs/fr/labs/lab-14-pilot-operations.md - eighth workflow, four lint findings, network rebuild teardown exercise

### Removed

* none

## Additional or Deviating Changes

* The virtual network is deliberately not part of `infra/main.bicep`
  * `main.bicep` deploys twice into one resource group, and an ARM write that
    omits `subnets` deletes the ones it does not name, so each environment
    would delete the other's subnets
* The Foundry accounts keep `publicNetworkAccess: 'Enabled'` alongside
  `networkInjections`
  * Documentation ties injection to Standard Agent Setup with private
    networking, which mandates BYO Storage, AI Search, and provisioned Cosmos
  * A probe deployment proved the combination is accepted on Basic Agent
    Setup, avoiding roughly $250/month of mandatory AI Search
* A probe Foundry account held a service association link on its subnet for
  over an hour after deletion
  * `az rest` force-release of the link is rejected for the CLI client ID, so
    the only remedy is to wait for the purge to complete
  * The teardown workflow polls the purge for this reason

## Release Summary

Pending completion of the staging and production rebuilds.
