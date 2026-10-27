---
layout: default
title: Langfuse pilot runtime evidence
description: Timestamped Azure inventory, guest runtime observations, and access limitations for the synthetic Langfuse pilot.
nav_order: 24
---

[Integration guide](langfuse-integration.md) | [Workshop home](index.md)

## Verified outcome

Langfuse 4.70.1 is deployed on the isolated Azure VM
`langfuse-synthetic-pilot` in `rg-langfuse-synthetic-pilot`, East US 2.
At `2026-10-27T23:15:53Z`, a guest script executed through authenticated Azure
Run Command returned a healthy application and six running containers.
This establishes runtime existence, not successful operator SSH, UI onboarding,
or end-to-end OpenTelemetry ingestion.

The implementation was merged in [PR 63](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/pull/63)
at commit `42c627cddba2cc14743f8120322634227d1f7366`.
The [protected release](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/runs/40567253202)
promoted production agent version 8. This pilot evidence follow-up is tracked in
[issue 64](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/issues/64).
The production agent's optional Langfuse export remains disabled.

## Azure inventory

The saved [VM response](assets/langfuse-pilot/2026-10-27/azure-vm.json) reports
`VM running`, SKU `Standard_D4s_v6` (4 vCPU, 16 GiB), Trusted Launch, Secure Boot,
vTPM, and password authentication disabled. The public/private addresses are
`20.96.32.65` and `10.90.0.4`. Its provisioning state was `Updating` while guest
evidence collection was in progress; that inventory is not a claim that the
evidence job finished successfully.

## Guest runtime observations

The bounded runtime collector returned the following at `23:15:53 UTC`.
These are observations from its output, not a substitute for a fresh health check.

| Check | Observed result |
| --- | --- |
| Cloud-init | `status: done` |
| Docker and SSH system services | Both active |
| Docker server | `29.1.3` |
| Docker Compose | `2.40.3+ds1-0ubuntu1~24.04.1` |
| Langfuse web | Running, healthy, zero restarts |
| Langfuse worker | Running, no health check configured, zero restarts |
| PostgreSQL, Redis, ClickHouse, MinIO | Each running, healthy, zero restarts |
| Application health response | `{"status":"OK","version":"4.70.1"}` |
| Published host ports | Web only, `127.0.0.1:3000`; no published database/object-storage ports |
| Protected environment file | `600 root:root /opt/langfuse-pilot/.env` |
| Disk | 8% used, approximately 114 GiB available |
| Memory | Approximately 12,973 MiB available; no swap |

The deployed Compose file's SHA256 matched the
[released source](../infra/langfuse-pilot/docker-compose.yml):

```text
ea0fca82d6ce775c14e62e99c2b6e86d92388366a72818860785f44e9d9156ab
```

Container image IDs matched the six digest-pinned images in that source.
The worker's running state must not be described as a passing worker health check.
No secrets, expanded container environments, or private SSH keys were captured.

## SSH access blocker

Operator attempts using the existing private key and strict verification against
an Azure-authenticated Ed25519 host key failed before the SSH server banner:

```text
kex_exchange_identification: read: Connection reset
Connection reset by 20.96.32.65 port 22
```

Guest checks confirmed listening SSH services and successful key scans on
loopback and the private interface. External attempts produced no SSH service
journal entries. Bounded packet captures showed reset packets rather than a
normal external SSH exchange; their source alone does not identify the cause.

The [NSG activity history](assets/langfuse-pilot/2026-10-27/nsg-activity.json)
records successful NSG writes by caller
`da847d8c-ee71-44de-b462-6775e7d649a7` at `19:28:55 UTC` and `23:27:51 UTC`.
Between those writes, the operator explicitly approved restoring only the
original TCP 22 rule from `76.65.61.229/32`, successfully written at
`23:10:54 UTC`. SSH still failed after restoration. The later
[NSG response](assets/langfuse-pilot/2026-10-27/azure-nsg.json) again has no
custom rules. The controller's identity and intent remain unverified.

Further rule restoration stopped as agreed. No broader CIDR, public web port,
alternative SSH port, or security-policy override was introduced. The subscription
owner must identify the external writer and agree a supported operator access
path. Restoring the rule alone is not proven to resolve the connection reset.

## UI proof status

A temporary Playwright browser capture was launched inside the VM against
`http://127.0.0.1:3000`. Completion and screenshot transfer are not yet verified.
No screenshot is presented as proof until its actual bytes, SHA256, nonblank
pixels, and visible Langfuse content have been checked.

Management-channel browser evidence, when available, proves guest-local UI
rendering. It does not prove a functioning workstation SSH tunnel. Visiting the
sign-up page does not create an account or project.

## Remaining limitations

* Operator SSH and tunnel access remain blocked.
* No account, organization, synthetic project, or project API keys have been verified.
* No real Langfuse OTLP ingestion or matching Azure/Langfuse trace has been verified.
* A remote Foundry hosted agent cannot reach the workstation's loopback tunnel.
* Remote export needs separately approved routing, TLS, and secret injection.
* This single-VM synthetic pilot has no HA, validated backup/restore, automatic expiry, or production-readiness approval.

The saved JSON responses are point-in-time Azure CLI evidence, not signed
attestations. VM power state, HTTP health, rendered UI, user onboarding, and
telemetry ingestion are separate verification criteria.
