---
layout: default
title: Native showcase evidence
description: Recorded native generation recovery, running demo versions and authentic application screenshots.
---

[Français](fr/showcase-evidence.md) | [Native runbook](native-showcase.md) | [Labs](labs/index.md)

## Release status

Evidence collected on 2026-10-20 UTC. Both environments remain deployed.
[Release 39411002808](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/runs/39411002808)
successfully deployed approved runtime source
`b0778c7d33460591dfe4056403b8c6674ed57e4b` through staging and production.
Direct SDK queries against the two explicit project endpoints confirm
`quote-preparation-agent:4` in staging and `quote-preparation-agent:5` in
production. Production passed its existing required-reviewer gate; no
protection setting was changed. Subsequent evidence-only documentation
commits do not represent another runtime deployment.

| Runtime | Running image digest | Ready revision |
| --- | --- | --- |
| Staging chat | `sha256:f036a1622e77ee1920a7d7530a9c0e67bf35d789c68c2c6d9a027acb0f95fc34` | `foundry-quote-chat-staging--0000002` |
| Production chat | Same chat digest | `foundry-quote-chat--0000001` |
| Staging reviewer | `sha256:ed04abc06ce750d61bd04e2a5a8b8f451458c15abfd28b870b4de598ce15f630` | `foundry-quote-reviewer-staging--0000005` |
| Production reviewer | Same reviewer digest | `foundry-quote-reviewer--0000002` |

The application MCP digest is
`sha256:a8235a2e88a707e3ff9f39811d23ea067076d23900aa36e4e705325ceb324265`;
the rulebook MCP digest is
`sha256:2f917c4379c776514caecdc4a00089f6e3512dcd0b07b77b248a649a41e67aae`.
Each production MCP image matches its staging-tested digest. Both MCP services
report their latest revision ready in each environment.
Chat remains on its previously verified digest; this release rebuilt the
reviewer/MCP images and deployed the agent's streaming fix, not the chat image.

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
no extra operator grant was added. Subsequent authenticated production reviewer
readback at `2026-10-20T03:53:42Z` confirmed four persisted synthetic records,
separately from the successful agent-side Cosmos readiness checks.

The deterministic evaluation artifact passed all 13 records. The separate
advisory LLM judge completed as
`evalrun_350161dee4644d13addfac89320ee336` with 0/10 passing items and no
service errors. Its coherence, groundedness and task-adherence results failed
their criteria. The workflow deliberately treats this judge as advisory;
release success must not be presented as a passing semantic-quality judge.

### Previous successful release screenshot

Captured from the actual GitHub Actions release summary at
`2026-10-20T02:46Z`, not a locally rendered mockup. This is the previous
39356610865 release, not the replacement 39411002808 release linked above.

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

### Authenticated production reviewer persistence

The normal Microsoft sign-in flow subsequently completed. The authorized
production reviewer queue displayed `CASE-SYN-001`, `CASE-SYN-002`,
`CASE-SYN-003` and `CASE-SYN-005`, all `PENDING_REVIEW`, revision 1.
The submission times remained visible in the actual queue. No employee
decision, queue clearing or record mutation was performed.

Captured at `2026-10-20T03:55:43Z`, the following actual English queue screenshot
is cropped to synthetic IDs, states and revisions. Account details, preparer
fields and premium columns are excluded; no UI values were altered.

![Authenticated production reviewer queue shows four persisted synthetic cases pending review at revision 1](assets/evidence/production-reviewer-persistence-en.png)

### Authenticated Foundry staging agent

After the human signed in, the actual staging playground showed
`quote-preparation-agent`, version 3, with the running indicator. The following
header capture was taken at `2026-10-20T03:34:42Z` and cropped to exclude account
details. It proves the observed agent/version/status, not a successful chat.

![Authenticated staging Foundry agent header with version 3 and running indicator](assets/evidence/foundry-staging-agent-v3.png)

The earlier v3 `CASE-SYN-001` playground request finished, but its assistant
message displayed no text. That was not a passing portal conversation. Protocol tests
confirmed that the previous stream lacked native text events and used an object
where output text must be a string. The fix sends the final bilingual
map as JSON text, with ordered content/text/completion events; it never streams
intermediate workflow state. Non-streaming responses retain their existing map.
Serialized-event and real-graph regression tests pass. Following human approval,
release 39411002808 deployed the corrected runtime to staging as version 4.
The authenticated playground rendered the complete bounded English/French
response for `CASE-SYN-001`, independently of the direct API tests.

Captured at `2026-10-20T11:07:34Z` from the actual staging playground.
Presentation-only zoom and code wrapping make the response readable; the crop
excludes the account banner and empty margins. No response values were changed.

![Staging Foundry version 4 renders the complete bilingual response](assets/evidence/foundry-staging-playground-v4.png)

### Authenticated production playground

The same approved artifact was promoted through the existing production gate.
The actual production v5 playground also rendered the complete bilingual
`CASE-SYN-001` response. Captured at `2026-10-20T11:17:36Z`, using the same
presentation-only wrapping and account-banner crop as staging.
The SDK-provided version-5 playground link resolved the initially stale v4
portal view; no agent configuration or authentication setting was changed.

![Production Foundry version 5 renders the complete bilingual response](assets/evidence/foundry-production-playground-v5.png)

### Recovered generation jobs in the portal

Captured at `2026-10-20T10:56:21Z` from staging Data generation.
Both recovered-v3 jobs show Succeeded, with 6 and 5 output rows. Historical
failed operations remain visible; they were not relabeled or deleted.

![Actual Foundry generation list with successful replacements and historical failures](assets/evidence/foundry-generation-portal.png)

### Six indexed source files

Captured at `2026-10-20T10:55:59Z` from Knowledge, Indexes,
`showcase-synthetic-native-knowledge:1`. The native File Search vector store
and all six English/French source files show completed status.
This is not a Foundry IQ connection or a hosted quote-agent attachment.

![Actual File Search index contains six completed bilingual source files](assets/evidence/foundry-index-portal.png)

### Project-authored runtime skill

Captured at `2026-10-20T10:57:03Z` from Tools, Skills Preview.
`showcase-synthetic-bilingual-brief` is version 1. It is project-authored,
not a Microsoft built-in skill. Separate operator-runtime evidence establishes
consumption; this list alone establishes registration.

![Actual native project skill registration at version 1](assets/evidence/foundry-skill-portal.png)

### Honest evaluation results

Captured at `2026-10-20T11:01:43Z` from historical run
`evalrun_e2bfaa11b8bb4994a5d89e12c9c9bc7c` against staging v3.
The portal shows coherence 0/10, groundedness 1/10 and task adherence 1/10.
Individual metric passes do not change the overall 0/10 passing-item result.
The Run details panel is collapsed to exclude creator identity.
This capture is not the replacement release's evaluation.

![Actual historical advisory evaluation shows failed criteria, not a quality pass](assets/evidence/foundry-evaluation-portal.png)

### Native trace list

Captured at `2026-10-20T10:58:50Z` from staging agent Traces.
The actual v3 root invocations show Completed. The blank-response playground
request also completed, illustrating why a completed root span alone does not
prove useful output. Token counts are zero and costs are unavailable.
No stage-level visibility or replay success is inferred from this list.

![Actual Foundry root trace list with completed invocations](assets/evidence/foundry-traces-portal.png)

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
