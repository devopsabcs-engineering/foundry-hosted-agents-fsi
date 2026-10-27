---
layout: default
title: Langfuse and Foundry
description: Optional metadata-only OTLP integration, an Azure single-VM synthetic pilot, and a native-first observability capability comparison.
nav_order: 23
---

[Workshop home](index.md) | [Evaluation guide](evaluation-guide.md) | [Root README](../README.md)

## Recommendation

Keep Foundry, Application Insights, Azure Monitor, and the existing evaluation
gates as the default. Add Langfuse when a concrete prompt-management,
cross-provider experiment, or human-annotation workflow warrants another system.
Langfuse complements those services; it is not required to obtain traces,
datasets, judges, production evaluation, or regression gates in Azure.

Capability overlap does not mean identical interfaces, evaluator semantics,
availability, or operational responsibility. Foundry also supports third-party
frameworks through OpenTelemetry; cross-provider tracing is not exclusive to
Langfuse. Check the selected region, agent type, SDK version, permissions,
network policy, preview status, and Langfuse edition before adopting a feature.

## Capability comparison

| Need | Foundry and Azure-native path | Where Langfuse can complement it |
| --- | --- | --- |
| Traces and spans | Foundry tracing with Application Insights and OpenTelemetry | A second LLM-oriented trace view across applications and providers |
| OTEL ingestion | Azure Monitor OpenTelemetry export into Application Insights | OTLP/HTTP ingestion into a separately operated backend; not the same ingestion endpoint |
| LLM, agent, and tool calls | Framework instrumentation and Foundry agent traces | Shared observation conventions across a heterogeneous application estate |
| Latency and exceptions | Application Insights requests, dependencies, exceptions, and Foundry traces | LLM-focused debugging alongside prompts, scores, and experiments |
| Trace exploration | Foundry Traces UI, Application Insights, and Log Analytics/KQL | An LLM-engineering workspace alongside annotation and experiment workflows |
| Production monitoring | Azure Monitor alerts and Foundry operational and quality dashboards | LLM score trends and application-specific quality workflows; not a replacement for infrastructure monitoring |
| Evaluation datasets | Foundry versioned datasets and existing synthetic JSONL fixtures | A dataset/experiment workspace shared by teams using several providers |
| LLM-as-judge | Foundry built-in and custom prompt-based evaluators | Alternative judge definitions and calibration/score workflows |
| Custom scoring | Foundry code-, prompt-, and endpoint-based evaluators plus repository tests | Human annotations, external scores, and custom checks in one workspace |
| Offline evaluation | Foundry evaluation SDK/service and this repository's evaluation gates | Side-by-side prompt, model, and code experiments |
| Production evaluation | Foundry trace-based and continuous evaluation workflows | Langfuse online evaluation and annotation workflows when separately configured |
| Regression testing | Versioned datasets and evaluators integrated into CI/CD | Langfuse experiments in CI; both approaches require explicit thresholds and failure handling |
| Trace-to-dataset | Native Foundry trace selection and dataset-generation workflows | Curation within an existing Langfuse dataset/experiment workflow |
| Prompt lifecycle | Version-controlled application/agent artifacts and governed releases | A prompt registry with versions, labels, caching, and links to observations, if the application explicitly uses it |

Azure-native is sufficient when your team can complete its debugging,
evaluation, operations, and release decisions in the native tools and existing
CI gates. Choose Langfuse for a demonstrated workflow improvement, not because
Application Insights supposedly cannot collect LLM traces or Foundry lacks evals.
Neither stack makes an uncalibrated judge or a passing average score a regulatory
approval. Deterministic calculation and employee-approval gates remain mandatory.

### Native trace-to-dataset qualifications

[Foundry's native workflow](https://learn.microsoft.com/azure/foundry/observability/how-to/traces-to-dataset)
supports manual trace selection and generated, versioned datasets. The documented
SDK path requires `azure-ai-projects>=2.8.0`; this repository currently pins
`2.6.0`. Availability in the platform is not evidence that the pinned SDK or
this project's configuration already implements it. Review an SDK upgrade as
separate work rather than silently changing the evaluation contract here.

The workflow requires supported regions, project access, and permissions for
the project identity to query the connected Application Insights resource.
The current guide also requires public query access to Application Insights
and, for bring-your-own storage, public storage access. Do not relax this
repository's private-network controls to make that workflow succeed without
platform/security approval. Continue using curated synthetic fixtures instead
when those requirements conflict with your boundary. Sampling and private-content
redaction are separate controls.

## What this integration implements

The hosted adapter initializes the existing SDK-owned provider first.
[The optional exporter](../src/quote-preparation-agent/langfuse_telemetry.py)
then adds one bounded asynchronous processor per provider:

```text
Hosted agent / LangGraph / deterministic workflow
                    |
           Existing OTel provider
              /             \
     Existing Azure      Selected scopes, sanitized copies
       exporter                     |
           |                  OTLP/HTTP + project credentials
  Application Insights              |
    / Foundry traces            Langfuse
```

* Export is disabled unless `LANGFUSE_TRACING_ENABLED=true`.
* `LANGFUSE_HOST` is an HTTPS origin without a path, query, or credentials.
  Plain HTTP is permitted only for `localhost`, `127.0.0.1`, or `::1` tunnels.
* Project keys are supplied through `LANGFUSE_PUBLIC_KEY` and
  `LANGFUSE_SECRET_KEY`. Dedicated exporter headers do not overwrite Azure's
  authentication or generic `OTEL_EXPORTER_OTLP_*` settings.
* The exporter targets `/api/public/otel/v1/traces`, uses Basic project-key
  authentication and the v4 ingestion header, and does not use OTLP/gRPC.
* Only the workflow, SDK server, and configured LangGraph callback scopes are
  forwarded. Unknown HTTP/database instrumentation scopes are excluded.
* Trace/span IDs, parent IDs, timestamps, kind, and status code are preserved.
  Span names are normalized. Attributes are allowlisted and format-checked.
* Only approved stage names, policy hashes, synthetic case references, bounded
  revision numbers, and already-hashed preparation references can be included.
  Events, links, exception descriptions, arbitrary attributes, trace state,
  and original resource metadata are removed from the Langfuse copy.
* Azure receives its original spans. Missing/invalid optional settings disable
  Langfuse export with a generic warning. Export errors do not fail agent work.
* The queue is bounded to 512 spans, batches to 64, and the HTTP timeout to
  five seconds. Host/provider shutdown owns flushing; there is no per-request
  network flush. Outages can drop optional telemetry; delivery is not guaranteed.

This process emits real deterministic `INTAKE`, `REFERENCE_LOOKUP`, and
`COMPOSITION` stages, not invented LLM generations or token/cost measurements.
Unknown or remote ancestors may not be present in Langfuse. Shared IDs enable
correlation; they do not copy Foundry's server-side traces into this process.
Review scope and parent relationships whenever instrumentation changes.

No prompts, responses, tool arguments, customer identities, or arbitrary payloads
are intentionally forwarded. This is data minimization, not a compliance
certification. Metadata-only observations cannot provide content-based semantic
judging, prompt replay, or complete query/response evaluation datasets.

OTLP export does not synchronize prompt versions, datasets, human labels,
evaluation results, or scores. This change does not install a second LangGraph
callback, fetch prompts from Langfuse, alter release gates, or enable online
judges. Those integrations need explicit schema, ownership, privacy, and cost
decisions. Use approved synthetic evaluation data for any later experiments.

## Single-VM Azure pilot

> [!WARNING]
> The separately approved synthetic pilot is deployed and its guest-local health
> was verified. [Runtime evidence and access limitations](langfuse-pilot-evidence.md)
> distinguish those checks from operator SSH, UI onboarding, and OTLP ingestion.
> Do not modify retained staging/production resources or bypass deployment gates.

The standalone [Bicep template](../infra/langfuse-pilot.bicep) creates a VM,
network, NSG, NIC, and static public IPv4 in a separate resource group. It is not
included in the main infrastructure or agent deployment manifest. The default
VM is `Standard_D4s_v5` (4 vCPU, 16 GiB) with a 128-GiB Premium managed OS disk,
SSH-key-only access, Trusted Launch, and platform patching. The Ubuntu image is
resolved from `latest` at deployment; container images, not the OS image, are
digest-pinned.

[Cloud-init](../infra/langfuse-pilot/cloud-init.yaml) installs Docker/Compose and
creates random credentials locally in `/opt/langfuse-pilot/.env` with mode `0600`.
No passwords or project keys are placed in Bicep parameters, deployment outputs,
or VM custom data. Root and Docker administrators can still read container
configuration and secrets; this is not a production secret-store design.

The [Compose stack](../infra/langfuse-pilot/docker-compose.yml) runs Langfuse
web/worker 4.70.1, PostgreSQL, Redis, ClickHouse, and MinIO on that VM. Its service
selection follows the upstream 4.70.1 Compose configuration, with immutable
registry digests, no sample passwords, health checks, bounded container logs,
and persistent named volumes. Only the web service publishes a host port,
bound to `127.0.0.1:3000`. Databases and object storage are not published.
Multimodal uploads, batch exports, in-app AI features, and vendor telemetry are
not configured/enabled for this pilot.

### Approval and deployment

1. Approve an isolated resource group, Azure subscription/region, owner, expiry
   date, budget, operator public IPv4, and SSH public key. Never provide a private
   SSH key or project secret in chat.
2. Price the selected VM's running hours, 128-GiB Premium disk, static IPv4,
   egress, and any backups in the
   [Azure pricing calculator](https://azure.microsoft.com/pricing/calculator/).
   No region-specific cost estimate is approved here. Deallocation stops compute
   billing, not disk or allocated-IP charges; OS shutdown alone is insufficient.
3. Use your approved Bicep deployment workflow or VS Code's **Deploy Bicep File**
   command for the standalone template, targeting only the isolated group.
   Supply `operatorIpv4Address` without `/32`, `sshPublicKey`, and any approved
   overrides. Review an ARM what-if before approving deployment. No Foundry,
   Cosmos, retained application, role assignment, or peering is required.
4. After the separately approved deployment, SSH to the output IPv4 and run
   `sudo cloud-init status --wait`, then
   `sudo docker compose --project-directory /opt/langfuse-pilot ps`.
   ARM deployment success does not prove that cloud-init or migrations succeeded.
5. In another terminal, run the deployment's `sshTunnelCommand`, or use:

   ```powershell
   ssh -N -o ExitOnForwardFailure=yes -L 3000:127.0.0.1:3000 pilotadmin@<pilot-public-ip>
   ```

6. Open <http://localhost:3000>, create the first user, organization, and a
   synthetic-only project, then generate project API keys. There is no default
   administrator login. Disable further signups by setting
   `AUTH_DISABLE_SIGNUP=true` in the VM's protected environment file and rerunning
   `sudo /opt/langfuse-pilot/start.sh`.

Use the tunnel only on a trusted workstation. Anyone with local access to its
forwarded port can reach Langfuse's login/API. The network permits inbound SSH
only from the supplied IPv4 as `/32`; there is no public web/OTLP ingress.
Outbound access is needed for Ubuntu packages, image registries, and any later
explicitly configured judge/model connection.

### Activation and synthetic smoke check

Use a dedicated local agent terminal and the existing workshop virtual
environment. Remove inherited Cosmos/MCP settings in that terminal if they
would direct the smoke check into retained environments. Install the agent's
updated requirements, then set the optional exporter before starting the host:

```powershell
python -m pip install -r src/quote-preparation-agent/requirements.txt
$env:LANGFUSE_HOST = 'http://localhost:3000'
$env:LANGFUSE_PUBLIC_KEY = Read-Host 'Synthetic Langfuse project public key'
$env:LANGFUSE_SECRET_KEY = [System.Net.NetworkCredential]::new('', (Read-Host 'Synthetic Langfuse project secret key' -AsSecureString)).Password
$env:LANGFUSE_TRACING_ENABLED = 'true'
python src/quote-preparation-agent/main.py
```

Keep the SSH tunnel open. In a separate terminal, check the local Responses
server and submit only a known synthetic case:

```powershell
Invoke-RestMethod http://localhost:8088/readiness
Invoke-RestMethod -Method Post -Uri http://localhost:8088/responses -ContentType application/json -Body '{"input":"CASE-SYN-001","stream":false}'
```

Use hosted/server mode with **no** case argument. The one-shot CLI path
`main.py CASE-SYN-001` intentionally does not initialize hosted tracing.
For a dual-destination check, retain the approved existing Application Insights
configuration and its required Entra credentials/RBAC. Do not replace it with
Langfuse's endpoint or credentials. A local Langfuse observation alone does not
prove Azure ingestion.

Verify the three stages under a request in Langfuse, absence of payloads and
invented token/cost data, and the same 32-hex trace ID in Application Insights.
For a workspace-based resource, query its Log Analytics workspace:

```kusto
union AppRequests, AppDependencies, AppTraces
| where OperationId == '<trace-id-from-langfuse>'
| project TimeGenerated, Name, OperationId, ParentId
| order by TimeGenerated asc
```

Allow for ingestion delay. Trigger a controlled exporter outage and confirm
that the agent still responds and Azure spans still arrive. Restart the host
with `LANGFUSE_TRACING_ENABLED=false` to roll back; a processor already attached
to a running provider is not removed by changing an environment variable.
Remove project-key variables from the terminal afterward. Do not print them,
put them in history as literals, or commit them in an environment file.

A deployed Foundry hosted agent **cannot reach your workstation's localhost
tunnel**. The pilot demonstrates the same hosted adapter running locally.
Deploying the exporter in Foundry requires a separately approved reachable TLS
endpoint, DNS/routing/egress, private connectivity or controlled ingress, and
runtime secret injection. The deployment manifest is deliberately unchanged;
this pilot is not a shortcut to a public or production telemetry endpoint.

### Ownership and cleanup

There is no HA, automated backup, SSO integration, validated disaster recovery,
or managed data-retention policy in this single-VM stack. Named volumes survive
container replacement and VM stop/start, but not deletion of their underlying
disk. The OS disk is detached when deleting only the VM, so disk charges and data
can remain. Deleting the isolated resource group destroys the pilot and data.
Do not delete the workshop's retained resource groups.

Set a short owner-approved retention/cleanup window. Container log rotation does
not limit ClickHouse tables, raw event objects, or database growth. Monitor disk
usage and decommission the disposable pilot on schedule. A backup must include
the databases, object storage, and protected encryption/authentication material;
a named volume alone is not a backup. Review image pins for security updates.

For production, evaluate the
[official Azure Terraform module](https://github.com/langfuse/langfuse-terraform-azure)
or an independently reviewed supported architecture. The official path uses
AKS, managed PostgreSQL/Redis, and stateful ClickHouse and is not cost-equivalent
to this VM. Azure Blob Storage is natively supported by Langfuse; the documented
integration currently uses a static account key, not an assumed managed-identity
flow. Review secret rotation, networking, retention, recovery, Entra/SSO setup,
edition/license requirements, and on-call ownership before production approval.

## Verification

Run the focused agent tests without Azure or Langfuse credentials:

```powershell
python -m pytest src/quote-preparation-agent/tests/test_case_telemetry.py src/quote-preparation-agent/tests/test_hosted_telemetry.py src/quote-preparation-agent/tests/test_langfuse_telemetry.py -q
```

The tests cover SDK provider reuse, enabled/disabled export, identical IDs,
idempotency, privacy projection, invalid configuration, exporter failures,
and a real local HTTP/protobuf receiver. They do not prove a live Langfuse server
accepted data, Azure ingested it, the VM booted, or a judge/dataset workflow ran.
Continuous Validation also checks Compose interpolation using dummy credentials
and compiles the standalone Bicep template without deployment.

## References

* [Microsoft Foundry observability](https://learn.microsoft.com/azure/foundry/concepts/observability)
* [Foundry cloud evaluations](https://learn.microsoft.com/azure/foundry/observability/how-to/cloud-evaluation)
* [Foundry dataset evaluations](https://learn.microsoft.com/azure/foundry/observability/how-to/cloud-evaluation-datasets)
* [Foundry custom evaluators](https://learn.microsoft.com/azure/foundry/concepts/evaluation-evaluators/custom-evaluators)
* [Langfuse OTEL ingestion](https://langfuse.com/integrations/native/opentelemetry)
* [Langfuse with an existing OTEL provider](https://langfuse.com/faq/all/existing-otel-setup)
* [Langfuse evaluation workflows](https://langfuse.com/docs/evaluation/overview)
* [Langfuse prompt management](https://langfuse.com/docs/prompt-management/overview)
* [Upstream 4.70.1 Compose source](https://github.com/langfuse/langfuse/blob/v4.70.1/docker-compose.yml)
* [Langfuse Docker Compose guidance](https://langfuse.com/self-hosting/deployment/docker-compose)
* [Langfuse Azure Blob Storage configuration](https://langfuse.com/self-hosting/infrastructure/blobstorage#azure-blob-storage)
