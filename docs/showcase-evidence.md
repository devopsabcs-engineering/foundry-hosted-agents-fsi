---
layout: default
title: Native showcase evidence
description: Recorded native generation recovery, running demo versions and authentic application screenshots.
---

[Français](fr/showcase-evidence.md) | [Native runbook](native-showcase.md) | [Labs](labs/index.md)

## Release status

Evidence collected on 2026-10-20 UTC. Both environments remain deployed.
[Release 39356610865](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/runs/39356610865)
successfully deployed approved runtime source
`25f3e54037a4063fa5bba1781af8e5b4b20ce1c8` through staging and production.
Direct SDK queries against the two explicit project endpoints confirm
`quote-preparation-agent:3` in staging and `quote-preparation-agent:4` in
production. Production passed its existing required-reviewer gate; no
protection setting was changed. Subsequent evidence-only documentation
commits do not represent another runtime deployment.

| Runtime | Running image digest | Ready revision |
| --- | --- | --- |
| Staging chat | `sha256:f036a1622e77ee1920a7d7530a9c0e67bf35d789c68c2c6d9a027acb0f95fc34` | `foundry-quote-chat-staging--0000002` |
| Production chat | Same chat digest | `foundry-quote-chat--0000001` |
| Staging reviewer | `sha256:3fc629e2ddc44604a23fa3f08603cea0dcf1a6aa3177c9e47dd40ec51dc8e132` | `foundry-quote-reviewer-staging--0000004` |
| Production reviewer | Same reviewer digest | `foundry-quote-reviewer--0000001` |

The application MCP digest is
`sha256:019360cb0c87d69328ef0e0b7595130d4f706d00462a0040db3a5e1be19c8fac`;
the rulebook MCP digest is
`sha256:5ff4d4f5693944d2ae36b232eccf89664717aea83b8c3045f2dc7ee3bacaa0de`.
Each production MCP image matches its staging-tested digest. Both MCP services
report their latest revision ready in each environment.

The workflow passed offline tests, Bicep validation/what-if, staging deployment,
the deterministic release gate and production deployment, including each
agent's live Cosmos readiness check. That check restores the actual deployed
agent's Cosmos data grant only when the live request proves it missing.
Native azd authentication is explicitly reselected before each OIDC login.
No new credential secret, authentication bypass, Search service, embedding
deployment or teardown was needed.

### Independent live regression

Fresh native Responses requests passed in both environments, independently of
the workflow result. Every answer had exactly the nonempty `en-CA` and `fr-CA`
template fields, with no applicant-facing numeric or monetary disclosure.

| Synthetic input | Expected and observed outcome in both environments |
| --- | --- |
| `CASE-SYN-001` | `READY` employee-review submission |
| `CASE-SYN-003` | `UNSUPPORTED` employee-review submission |
| `CASE-SYN-005` | `INCOMPLETE` employee-review submission |
| `NOT-A-CASE-ID` | `REJECTED_INTAKE` before lookup |

All four applications passed `/healthz` and `/api/config`. Anonymous chat
conversation creation and reviewer case-list requests returned HTTP 401.
These checks do not claim a newly authenticated browser conversation or a
human reviewer decision.
An independent operator Cosmos read was denied by data-plane RBAC (HTTP 403);
no extra operator grant was added. Authenticated reviewer persistence readback
is retained in [follow-up #17](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/issues/17),
separately from the successful agent-side Cosmos readiness checks.

The deterministic evaluation artifact passed all 13 records. The separate
advisory LLM judge completed as
`evalrun_e2bfaa11b8bb4994a5d89e12c9c9bc7c` with 0/10 passing items and no
service errors. Its coherence, groundedness and task-adherence results failed
their criteria. The workflow deliberately treats this judge as advisory;
release success must not be presented as a passing semantic-quality judge.

### Successful release screenshot

Captured from the actual GitHub Actions release summary at
`2026-10-20T02:46Z`, not a locally rendered mockup.

![Successful staging-to-production release for approved source 25f3e54](assets/evidence/release-39356610865.png)

Previous native agent versions remain listed in both projects, including
staging v2 and production v3 from
[the restored baseline](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/runs/39293980605).
No rollback was executed against the retained demo. Use the existing gated
deployment workflow and an approved previous artifact if rollback is needed.
The previous chat digest
`sha256:ccfab1bc368463602c5b5f85cc6b93cde242e9a03c7b3000a6cf8cee007fce70`
was independently confirmed retained and readable in ACR. This is artifact
availability, not a tested traffic rollback or a retained old Container Apps
revision.

## Two failed generation jobs recovered

Historical failures remain visible as historical failures. They are not mutable
datasets that can be marked successful. New native jobs replace them with an
expanded, self-contained teaching reference containing 26 technical lessons.
The uploaded reference is 19,881 bytes, not just a short JSON fixture.

| Original job | Actual failure | Successful replacement | Downloaded rows |
| --- | --- | --- | --- |
| `datagen-4e74a27bd5f24a87a08ea35ad788c8cb` | Reference smaller than 1 KB | `datagen-a866fd3be0104ae4b6ec4808b76cbec2` | 6 |
| `datagen-af8399a33bd7477b8279591b5a408c7a` | Insufficient standalone context | `datagen-afe38ec64fb744a09e845119139e4064` | 5 |

The replacement names in Foundry Data generation are
`showcase-synthetic-dataset-recovered-v3` and
`showcase-synthetic-dataset-v2-recovered-v3`. Both reached `succeeded`.
Their shared input file is `file-21aee188caff46979b16bf3abc40beb1`.
The requested 15 is a maximum, not a guaranteed output count.
Retrying the earlier reference also failed, so increasing file size alone
was not accepted as the fix.

| Output file | Downloaded SHA-256 |
| --- | --- |
| `file-b9923ced057f450eaa8347bf7e68dfae-dg` | `82efe086958d8756bfa5612573b5e1c02d7cebaf5948bfed0457d97bd91f07d4` |
| `file-9c7c0515bfea4f73a12deb4a6de40142-dg` | `0f99391d6ce77d2a5e0b1e25e6fbf9bd55e1eeebdfc310ebf2a3a30364b1ea69` |

The CLI downloaded the service outputs and checked their job/file provenance.
The examples still require human review. No fine-tuning was submitted.
Use the [native generation lab](labs/lab-15-native-files-generation.md) to
reproduce the process and retain your own job IDs.

## Authentic application screenshots

These refreshed captures show the signed-out application boundaries after the
verified release, not an authenticated conversation or reviewer action.
Runtime source provenance is established by the workflow, SDK and image checks
above, not by a screenshot alone. They contain no applicant data or tokens.

### Staging applicant chat

Captured at `2026-10-20T02:55Z` from the
[live staging chat](https://foundry-quote-chat-staging.victorioussand-be863134.eastus2.azurecontainerapps.io).

![Deployed staging chat requires Microsoft sign-in and disables message input before authentication](assets/evidence/staging-chat-en.png)

### Production employee reviewer

Captured at `2026-10-20T02:50Z` from the
[live production reviewer](https://foundry-quote-reviewer.gentleplant-e170129b.eastus2.azurecontainerapps.io).

![Deployed production reviewer requires Microsoft sign-in before employee actions](assets/evidence/production-reviewer-en.png)

### Foundry portal screenshots still pending

The integrated browser is signed out of Foundry. API evidence above is genuine,
but it must not be presented as a portal screenshot. Share an authenticated
project tab to capture generation jobs, indexed files, skill versions,
evaluation runs and traces without exposing account details.
The explicit interactive-only follow-up is
[#17](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/issues/17).

## Native quality boundaries

The native File Search demonstration verified six cited answers and two exact
`OUT_OF_CORPUS` refusals. It uses the reviewed EN/FR corpus, not Foundry IQ and
not a new hosted-agent attachment. The runtime skill was actually consumed by
an isolated operator runtime in both language orders.

The retrieval evaluator distinguished relevant and irrelevant controls, 5/1.
Groundedness v18 and groundedness_pro v8 accepted a known bad scope/authorization
answer; their negative-control comparison gates therefore failed. These are
documented judge limitations, not an optimization success. Local trace publishing received HTTP 403; exporter flush was not treated as
ingestion evidence. This differs from the deployed hosted invocation traces
verified below.

### Native hosted trace ingestion

Exact-operation Log Analytics queries found one successful `invoke_agent` span
for each independently invoked hosted agent:

| Environment | Actual operation ID | Observed spans |
| --- | --- | --- |
| Staging | `715c5c7da66449cba2faf91432945904` | One successful hosted invocation |
| Production | `c76f5a78438e42aa8546bb9f2405260d` | One successful hosted invocation |

The production span was recorded at `2026-10-20T02:42:26.5330371Z`.
The custom stage, case ID, policy hash and execution-kind fields were empty.
This proves hosted invocation ingestion, not deterministic stage-level
visibility or trace-to-dataset replay. Those deeper acceptance checks remain
open; no case lineage or replay dataset was fabricated. The native inventory
also still lists zero memory stores, so no live native-memory demonstration
is claimed.

See the [native runbook](native-showcase.md) and
[Microsoft Foundry documentation](https://learn.microsoft.com/azure/ai-foundry/)
for the capability boundaries and reproducible commands.
