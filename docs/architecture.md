---
layout: default
title: Architecture
description: Deployed Foundry agent, deterministic workflow, employee review, native showcase boundaries and release provenance.
---

[Français](fr/architecture.md) | [Workshop](index.md) | [Current evidence](showcase-evidence.md)

## Current implementation and deployed baseline

The retained customer demo runs a real Microsoft Foundry Responses host:
staging agent **v5**, production **v6**, approved runtime source `01af1fb`,
[release 39424857559](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/runs/39424857559).
The `-poc` Foundry account/project suffix identifies production, not staging.
Both chat apps, both reviewer apps and four MCP apps are deployed. Publication
commits after that release change documentation, not the runtime. The source
trees for `src`, `apps` and `infra` matched merged main `a4b6008`.
Version numbers are a dated observation, not invocation-routing parameters.

All data, rates and outputs are synthetic training material. No actual
insurance quote, delivery, customer policy or automatic approval is represented.
Earlier author-only banners describe approval requirements, not the current
deployment inventory. Future infrastructure changes still require approval.

## Application architecture

<details>
<summary>Rendered image if the Mermaid embed is unavailable</summary>

![Application architecture](assets/architecture/architecture-en-1.png)

</details>

<!-- mermaid-checked: safe labels, quoted subgraphs and edge labels, closed subgraphs, unique ids -->
```mermaid
flowchart TD
    AApplicant["Entra-authenticated pilot browser"]
    AEmployee["Entra-authenticated reviewer browser"]
    subgraph AApps["Azure Container Apps per environment"]
        AChat["React and FastAPI chat"]
        AReview["React and FastAPI reviewer"]
        AMCP["Application and rulebook MCP - read-only"]
    end
    subgraph AFoundry["Microsoft Foundry project per environment"]
        AEndpoint["Native Responses endpoint"]
        AAgent["Hosted LangGraph agent"]
    end
    AStore[("Cosmos DB cases and embedded audit")]
    AMonitor["Application Insights and Log Analytics"]
    AApplicant -->|"Pilot access token"| AChat
    AEmployee -->|"Reviewer access token"| AReview
    AChat -->|"Managed identity"| AEndpoint
    AEndpoint --> AAgent
    AAgent -->|"Direct MCP over HTTPS"| AMCP
    AAgent -->|"Create and submit draft"| AStore
    AReview -->|"Read and employee decisions"| AStore
    AAgent -->|"Payload-free stage spans"| AMonitor
```

### Technology stack and responsibility

| Layer | Technology | Contract or version | Responsibility |
| --- | --- | --- | --- |
| Browser | React frontends | Locked frontend manifests | Separate applicant and employee experiences |
| Web APIs | FastAPI, PyJWT, MSAL browser | Entra access tokens | Tenant, audience and authorization checks |
| Hosted entry point | Agent Server LangGraph adapter | `1.0.0b17`, Responses `2.0.0` | Readiness, request conversion and bounded streaming |
| Orchestration | LangGraph | Deterministic state graph | Intake, reference lookup, composition |
| Tools | FastMCP | Streamable HTTP | Synthetic fixture and pinned rulebook reads |
| Business persistence | Cosmos DB | Database `quote-preparation`, container `cases`, partition `/caseId` | Case state, calculation snapshot and audit |
| Local persistence | SQLite | `CaseStore` contract | Offline workshop and tests, not cross-process hosted state |
| Native demonstrations | Azure AI Projects | SDK `2.6.0` | Separate operator memory/files/skills/evaluations |
| Telemetry | OpenTelemetry and Azure Monitor | SDK-owned hosted pipeline | Sanitized custom stages and native investigation |

No Redis, queue, third-party tracing backend or LLM pricing engine is required
by the deployed quote path. `gpt-4o-mini` is provisioned, but the graph uses
fixed templates and a pure calculator. Having a model/toolbox in the project
does not mean the graph calls a chat model or the Foundry toolbox gateway.

## Component relationships and actual tool routing

<details>
<summary>Rendered image if the Mermaid embed is unavailable</summary>

![Component relationships](assets/architecture/architecture-en-2.png)

</details>

<!-- mermaid-checked: safe labels, quoted subgraphs and edge labels, closed subgraphs, unique ids -->
```mermaid
flowchart LR
    subgraph CProtocol["Responses host"]
        CMain["main.py serve"]
        CBridge["response_bridge.py"]
    end
    subgraph CBusiness["Deterministic workflow"]
        CGraph["graph.py supervisor and stages"]
        CTools["toolbox.py read and draft wrappers"]
        CCalc["calculator.py"]
    end
    subgraph CStorage["Case-store abstraction"]
        CContract["case_store.py"]
        CCosmos["cosmos_case_store.py"]
        CSQLite["sqlite_case_store.py"]
    end
    CRemote["Hosted HTTP MCP client"]
    CLocal["Local in-process MCP functions"]
    CReviewer["Reviewer API decision routes"]
    CMain --> CBridge
    CBridge -->|"Validated case input"| CGraph
    CGraph --> CTools
    CTools --> CCalc
    CTools --> CContract
    CTools -->|"Hosted package"| CRemote
    CTools -->|"Full local checkout"| CLocal
    CReviewer -->|"Never through agent toolbox"| CContract
    CContract -->|"COSMOS_ENDPOINT configured"| CCosmos
    CContract -->|"Local without Cosmos"| CSQLite
```

| Source | Responsibility |
| --- | --- |
| [main.py](../src/quote-preparation-agent/main.py) | Case argument runs locally; no argument starts the host on port 8088 |
| [response_bridge.py](../src/quote-preparation-agent/response_bridge.py) | Converts Responses input into fresh graph state; streams final bilingual JSON only |
| [graph.py](../src/quote-preparation-agent/graph.py) | Fixed routing and applicant-message templates; no model inference |
| [toolbox.py](../src/quote-preparation-agent/toolbox.py) | Local function calls or direct remote MCP; calculator and draft submission only |
| [case_store.py](../src/quote-preparation-agent/case_store.py) | Shared store contract and backend selection |
| [reviewer app](../apps/reviewer-app/app.py) | Authenticated decisions, audit, revision checks and explicitly confirmed synthetic queue clearing |

`azure.yaml` declares `quote-tools` and two remote connections. The current
hosted implementation nevertheless calls `APPLICATION_MCP_URL` and
`RULEBOOK_MCP_URL` directly through MCP sessions. Do not draw the toolbox
gateway as an executed hop. The read-only MCP endpoints expose synthetic data;
they are not the employee authorization boundary. The graph is compiled without
a checkpointer: Foundry conversation IDs do not create durable LangGraph state.

## Request lifecycle and missing-plan example

<details>
<summary>Rendered image if the Mermaid embed is unavailable</summary>

![Request lifecycle](assets/architecture/architecture-en-3.png)

</details>

<!-- mermaid-checked: safe labels, quoted subgraphs and edge labels, closed subgraphs, unique ids -->
```mermaid
flowchart TD
    RInput["Responses case reference"] --> RSupervisor["Supervisor"]
    RSupervisor -->|"First stage"| RIntake["quote.INTAKE"]
    RIntake --> RValidity["Valid case reference"]
    RValidity -->|"Yes"| RLookup["quote.REFERENCE_LOOKUP"]
    RLookup --> RFetch["Read application and pinned rulebook"]
    RFetch --> RCompose["quote.COMPOSITION"]
    RValidity -->|"No - skip lookups"| RReject["Bounded rejection without draft"]
    RCompose --> RCalculate["Pure calculator and status"]
    RCalculate --> RDraft["Create draft and submit for review"]
    RDraft --> RMessage["Bounded EN and FR acknowledgement"]
    RReject --> ROutput["Final applicant output only"]
    RMessage --> ROutput
```

In code, each stage returns to the supervisor, which selects the next
unfinished stage and eventually `END`. The diagram expands the work within
`COMPOSITION`, not additional LangGraph nodes or telemetry stages.
There are exactly three custom stage names. Calculation and persistence are
inside `COMPOSITION`; that stage has no *remote MCP lookup*, but does call
local calculator/store wrappers.

The supplied [CASE-SYN-005 fixture](../data/synthetic/fixtures/case-syn-005-missing-plan.json)
has `input.plan: null`. The calculator returns `INCOMPLETE`,
`amountCents: null`, `issues: ["MISSING_PLAN"]`. The running agent can still
submit a case whose workflow state is `PENDING_REVIEW`, carrying that
calculation status. These are different dimensions, not a contradictory state.
The applicant receives the bilingual missing-information acknowledgement,
never the raw fixture, amount, rulebook or employee audit fields.
The fixture's illustrative `workflow`/`nextCommand` blocks are teaching data,
not instructions to auto-approve a live case.

## Employee approval and persistence boundary

<details>
<summary>Rendered image if the Mermaid embed is unavailable</summary>

![Employee approval states](assets/architecture/architecture-en-4.png)

</details>

<!-- mermaid-checked: safe labels, quoted subgraphs and edge labels, closed subgraphs, unique ids -->
```mermaid
flowchart LR
    SAgent["Agent create draft"] --> SDraft["DRAFT revision N"]
    SDraft -->|"Submit with calculation snapshot"| SPending["PENDING_REVIEW"]
    SPending -->|"Employee approve"| SApproved["APPROVED"]
    SPending -->|"Employee reject"| SRejected["REJECTED"]
    SApproved -->|"Authorized training preview"| SPreview["APPROVED with audit event"]
    SApproved -->|"Revise"| SRevised["DRAFT revision N plus 1"]
    SRejected -->|"Revise"| SRevised
    SPending -->|"Revise"| SRevised
    SDraft -->|"Revise"| SRevised
    SRevised -->|"Resubmit after preparation"| SPending
```

The reviewer API derives actor identity from verified Entra claims, checks
the `Reviewer` role and `Review.Access` delegated scope, and accepts the
revision the employee saw. The stores reject self-approval and invalid
transitions. Cosmos uses ETag-conditional writes and keeps the calculation
snapshot plus audit entries in the case document. This is an application
append-only audit convention, not a claim of immutable regulatory storage.
Revision clears prior approval. Preview is a training-only audited action,
not delivery; the reviewer web API currently exposes decisions and audit,
not an applicant preview/delivery endpoint.

The applicant chat checks pilot membership before server-side managed-identity
invocation. The employee API has a separate registration/role boundary.
Anonymous protected calls return 401; health endpoints alone prove neither
identity authorization nor hosted-agent readiness.

## Isolated native showcase, not hidden production dependencies

<details>
<summary>Rendered image if the Mermaid embed is unavailable</summary>

![Native showcase isolation](assets/architecture/architecture-en-5.png)

</details>

<!-- mermaid-checked: safe labels, quoted subgraphs and edge labels, closed subgraphs, unique ids -->
```mermaid
flowchart TD
    NOperator["Authorized staging operator CLI"]
    NOperator --> NFiles["Files and successful data generation"]
    NOperator --> NSkill["Versioned project-authored skill"]
    NSkill --> NRuntime["Isolated model Responses consumption"]
    NOperator --> NSearch["Native File Search with six source files"]
    NOperator --> NMemory["Synthetic memory store - TTL 3600"]
    NChat["Existing gpt-4o-mini"] --> NMemory
    NEmbedding["Separate approved embedding deployment"] --> NMemory
    NMemory --> NAlice["Alice namespace marker"]
    NMemory --> NBob["Bob namespace marker"]
    NOperator --> NInvoice["Document Intelligence invoice extraction"]
    NOptional["Optional IQ and CU model setup"]
    NOperator -.->|"Not yet accepted"| NOptional
```

Memory recall and cross-scope controls passed; an existing reviewer workload
received memory-list 403 while the authorized operator succeeded.
Namespaces are retrieval partitions, not caller authorization or per-agent ACLs.
User-profile/chat-summary extraction is off; procedural memory is a service
default. No extraction invocation or quote-agent attachment is claimed.
Entries expire in one hour and [Lab 17](labs/lab-17-native-skills-memory.md)
reseeds the existing store instead of recreating it.
The skill is authored by this project, not a prebuilt Microsoft runtime skill.
The verified File Search and invoice paths are separate from optional Foundry
IQ and Content Understanding model setup.

## Telemetry to native evaluation

<details>
<summary>Rendered image if the Mermaid embed is unavailable</summary>

![Telemetry and evaluation lineage](assets/architecture/architecture-en-6.png)

</details>

<!-- mermaid-checked: safe labels, quoted subgraphs and edge labels, closed subgraphs, unique ids -->
```mermaid
flowchart LR
    TGraph["Hosted graph stages"] --> TProvider["One SDK-owned telemetry provider"]
    TProvider --> TInsights["Application Insights dependencies"]
    TInsights --> TWorkspace["Log Analytics operation query"]
    TWorkspace --> TExport["Whitelisted nine-span export"]
    TExport --> TDataset["Synthetic case replay with hashes"]
    TDataset --> TNative["Native evaluation run"]
    TBenchmark["Independent EN and FR acknowledgement facts"]
    TBenchmark --> TCapture["Current endpoint applicant messages"]
    TCapture --> TJudge["Coherence groundedness task adherence"]
```

Custom spans omit applicant text and amounts; failures record sanitized ERROR
status without exception payloads. Platform request roots and application SDK
dependency roots can have different operation IDs. A root-only query cannot
prove custom stages are absent. Export verifies actual ingestion and
unambiguous case/policy lineage before producing a synthetic replay dataset;
it does not recover a private user prompt.

The current applicant benchmark passed five cases in each language on all
three criteria. Scores are advisory; missing, incomplete or errored native
evidence blocks promotion. Historical 0/10 judge and RAG negative-control
failures remain preserved. This is not a same-dataset improvement claim.

## Release and documentation architecture

<details>
<summary>Rendered image if the Mermaid embed is unavailable</summary>

![Release and publication architecture](assets/architecture/architecture-en-7.png)

</details>

<!-- mermaid-checked: safe labels, quoted subgraphs and edge labels, closed subgraphs, unique ids -->
```mermaid
flowchart TD
    DIssue["Issue-linked feature PR"] --> DChecks["Offline tests builds Bicep CodeQL"]
    DApproval["Human approval of exact runtime source"]
    DApproval --> DDispatch["Manual hosted release dispatch"]
    DChecks --> DDispatch
    DDispatch --> DStaging["Staging images and agent deploy"]
    DStaging --> DGate["Cosmos readiness and evaluation evidence"]
    DGate --> DProtected["Protected production approval"]
    DProtected --> DProduction["Production promotion"]
    DChecks --> DMerge["Merge documentation sources to main"]
    DMerge --> DMain["Trusted completed main validation"]
    DMain --> DWiki["Render maintained wiki and preserve live links"]
    DMerge --> DPages["GitHub Pages workshop"]
    DChat["Separate approved chat image update"] --> DProduction
```

Production reuses staging-resolved reviewer/MCP image digests and rebuilds the
approved agent source; it does not copy a running staging agent container.
Chat is deployed out of band. Main frontend image builds do not update live
Container Apps automatically. Memory embedding is an opt-in staging template,
not part of the baseline deployment.

Maintained wiki pages are rendered from repository docs by
[publish_showcase_wiki.py](../scripts/publish_showcase_wiki.py), after the
publication workflow verifies completed main-run provenance. Test trends are
generated from run artifacts; Home deployment links retain the last actual
deployment fragments. No Azure redeployment is needed for documentation.

## Source and evidence map

* [Deployment manifest](../azure.yaml) and [infrastructure](../infra/README.md)
* [Native runbook](native-showcase.md) and [authentic release evidence](showcase-evidence.md)
* [Operations](wiki/operations.md), [workflow inventory](wiki/workflows.md)
  and [evidence interpretation](wiki/release-evidence.md)
* [Microsoft Foundry hosted-agent guidance](https://learn.microsoft.com/azure/ai-foundry/agents/concepts/hosted-agents)
