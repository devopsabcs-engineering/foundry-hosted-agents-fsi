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

At `2026-10-27T23:53:37Z`, a guest-local Playwright capture also verified the
desktop sign-in, desktop sign-up, and mobile sign-in pages. The actual screenshots
were transferred through authenticated Azure management, checked against their
VM-generated SHA256 values, and visually inspected. This establishes rendered
UI existence without claiming a working operator SSH tunnel.

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

A fresh [raw runtime response](assets/langfuse-pilot/2026-10-27/runtime-response.json)
at `2026-10-28T00:03:21Z` confirmed the same six running containers, zero restarts,
five passing health checks, the worker without a configured health check,
loopback-only publication, protected environment file permissions, healthy
application version, and unchanged Compose SHA256. Disk usage was then 11%
with approximately 111 GiB available; available memory was 12,887 MiB.
The dated asset directory groups this evidence session, including its checks
after midnight; timestamps inside each response remain authoritative.

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

A temporary Playwright 1.61.1 / Chromium 149.0.7827.55 browser ran inside the VM
against `http://127.0.0.1:3000`. The
[capture manifest](assets/langfuse-pilot/2026-10-27/ui-evidence.json) records
timestamps, URLs, HTTP status, branded page titles, viewport sizes, image sizes,
SHA256 values, observed form fields, and nonblank pixel measurements.

All three pages returned HTTP 200. No page errors, failed requests, or HTTP error
responses were observed during this capture. The application health request also
returned HTTP 200 with `{"status":"OK","version":"4.70.1"}`.

| View | Viewport | Image size | Captured UTC |
| --- | --- | --- | --- |
| Desktop sign-in | 1440 x 1000 | 8,158 bytes | `23:53:39.182` |
| Desktop sign-up | 1440 x 1000 | 8,230 bytes | `23:53:40.534` |
| Mobile sign-in | 390 x 844 | 6,282 bytes | `23:53:41.553` |

### Desktop sign-in

![Langfuse desktop sign-in page with email and password fields](assets/langfuse-pilot/2026-10-27/sign-in-desktop.webp)

### Desktop sign-up

![Langfuse desktop sign-up page with name, email, and password fields](assets/langfuse-pilot/2026-10-27/sign-up-desktop.webp)

### Mobile sign-in

![Langfuse mobile sign-in page with readable form fields and no overlapping controls](assets/langfuse-pilot/2026-10-27/sign-in-mobile.webp)

### Provenance and scope

The 19,696-byte transfer archive contained only these three images and their
manifest. Its locally verified SHA256 matched the VM-generated value:

```text
2522e259f8680d62aaa755e31b568acc6d88f60b300a8f77151c3395baf40abd
```

Each extracted image's size and SHA256 also matched its manifest entry, and all
three images were visually inspected. The browser container used image digest
`sha256:5b8f294aff9041b7191c34a4bab3ac270157a28774d4b0660e9743297b697e48`.
Only empty forms and their built-in example placeholders were captured; no
credentials were entered or account-creation forms submitted.

Management-channel browser evidence proves guest-local UI rendering. It does
not prove a functioning workstation SSH tunnel. Visiting the sign-up page does
not create an account or project.

## Diagnostic cleanup

The [guest cleanup response](assets/langfuse-pilot/2026-10-27/cleanup-response.json)
at `2026-10-28T00:04:44Z` confirmed removal of the temporary browser image and
the task-owned guest evidence directory after verified local transfer. The
bounded capture removed its browser container. All six application containers
remained running, and the post-cleanup health response remained
`{"status":"OK","version":"4.70.1"}`.

The completed `langfuse-evidence-inspect` and `langfuse-evidence-recover` managed
Run Command resources were deleted; the subsequent command-resource listing
was empty. The VM, application containers, data volumes, protected environment
file, network rules, and SSH keys were retained. No public ingress or identity
permissions were added for evidence capture.

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
