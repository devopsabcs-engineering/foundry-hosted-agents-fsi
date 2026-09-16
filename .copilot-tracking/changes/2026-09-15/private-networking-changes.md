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
* The first real teardown run failed with `CannotDeleteResource`
  * A Foundry account refuses deletion while any nested project exists, and the
    probe account had no project, so the probe did not surface this
  * The workflow now enumerates and deletes the account's projects first
* The second teardown run reported a successful purge that had not happened
  * A purge issued while the account is still settling is accepted and then
    does nothing, and the account lands in the soft-deleted list afterwards
  * The next provision failed preflight with a soft-deleted name collision
  * The loop now exits only when the account is absent from the resource group
    and absent from the soft-deleted list
* The production teardown reported success and still left a soft-deleted account
  * The soft-deleted list is eventually consistent and read empty moments
    before the account appeared in it
  * The loop now requires three consecutive clean readings before exiting
* Production could not be provisioned in place
  * `ManagedEnvironmentV1SubnetDelegationNotAllowed` on the existing
    consumption-only environment confirmed the immutability assumption
  * Staging, which had already been deleted, provisioned cleanly on the first
    attempt with a workload profile and a delegated subnet
* Both configured agent principals were dead
  * `cosmos-rbac.bicep` grants Cosmos data-plane access to the agent's own
    identity, supplied through the `AGENT_PRINCIPAL_ID` environment variable
  * Neither configured value resolved in Entra, so the grants were applied to
    principals that do not exist and both provisions reported success
  * Staging was corrected to the live identity and the orphaned grant removed
* The production agent identity does not resolve in Entra at all
  * The agents API reports `4fcc9b60-d117-4d6c-912a-a3e206270403`, which
    `az ad sp show` cannot find and Cosmos rejects with
    `BadRequest: The provided principal ID ... was not found in the AAD tenant`
  * azd surfaces that as `A resource with this name already exists or is in a
    conflicting state`, which points in the wrong direction entirely
  * `AGENT_PRINCIPAL_ID` is unset for production, so the grant is skipped. The
    production agent serves requests correctly but cannot write cases
  * These identities are tenant-level and survive account deletion: the staging
    identity predates the teardown by a day

## Release Summary

Both environments run on the shared virtual network, and Cosmos is reachable
only over its private endpoint. Verified from inside each Container Apps
environment:

| Environment | Managed environment subnet | Cosmos resolves to |
| --- | --- | --- |
| Staging | `snet-aca-staging` | `10.20.6.4` |
| Production | `snet-aca-production` | `10.20.6.6` |

All four application surfaces return HTTP 200, and each chat reports its own
environment through `/api/config` rather than a hardcoded label, which closes
the defect that started this work.

The network rebuild required deleting and recreating both Container Apps
environments and both Foundry accounts, which changed every application
hostname. Both Entra registrations were updated and pruned to exactly the live
origins plus localhost.

Three defects in the new teardown workflow were found by running it and fixed:
nested project deletion, a purge that races the delete, and an eventually
consistent soft-deleted list. One gap in the deploy workflow was closed: the
agent identity behind the Cosmos grant is now read live and validated against
Entra, so a stale or unresolvable principal is reported on the run rather than
discovered through a failed write or a misleading ARM error.

Outstanding: the production agent cannot write cases until its identity
resolves in Entra. Tracked as WI-43 in the planning log.
