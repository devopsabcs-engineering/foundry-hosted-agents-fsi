---
layout: default
title: Native Foundry showcase
description: Session-2 native-first demonstrations, reproducible evidence, governance limits and retained demo environments.
nav_order: 20
---

[Français](fr/native-showcase.md) | [Workshop home](index.md) | [Root README](../README.md)

[Deployed architecture and native isolation diagrams](architecture.md)

[Current release and generation-recovery evidence, with authentic screenshots](showcase-evidence.md).

The deployment workflow explicitly selects native azd authentication before each
GitHub OIDC login. Provisioning may use delegated Azure CLI authentication, but
newer azd versions reject `azd auth login` while that delegated mode is active.
Both staging and production switch back before refreshing the native credential.

## Keep the restored customer demo available

The current verified staging agent is version 6; production is version 7.
[Release 39527950931, attempt 2](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/runs/39527950931)
deployed approved runtime source `2c3f13b`, with independently verified,
matching reviewer and MCP digests in both environments. Chat retains its
previous verified image. The production revision/correction flow and both
reviewer identities' invocation200/memory403 controls passed. The earlier
[release 39293980605, attempt 2](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/runs/39293980605)
restored the v2/v3 baseline. Both environments remain deployed. Do not run teardown,
replace agent identities, change `quote-tools`, or infer production from the
historical `-poc` suffix. Use the [deployment links](../README.md#deployment-links).

This guide addresses the [session-2 follow-ups](../assets/session2.md).
The additional showcase is isolated from the running quote workflow. Authored
code, successful native registration, and actual runtime consumption are three
different claims. Only recorded live evidence establishes the last claim.

## What is native and what remains external

| Capability | Implementation | Verification boundary |
| --- | --- | --- |
| Hosted agents | Foundry project, version, managed identity and Responses endpoint | Restored staging and production passed live checks |
| Files | Native project OpenAI Files, `user_data`, synthetic text | Native upload verified; generation accepts text, Markdown or PDF, not JSON filenames |
| Synthetic data | Native generation job, explicit operation UUID, status and output download | Two recovered jobs succeeded with 6 and 5 downloaded rows; maximum requested 15 per job, no local fallback |
| Memory | Native memory store, explicit TTL, list, seed, search and cross-scope negative test | Staging store verified with approved embedding; caller-role negative returned 403, not a per-agent ACL |
| Runtime skill | Versioned project-authored native skill | Version 1 discovered, downloaded and consumed by an isolated operator Responses runtime; not attached to the hosted quote agent |
| Managed RAG | Native File Search vector store and Responses tool | Six versioned files indexed; three EN/FR questions each have native citations; both out-of-corpus questions decline |
| Knowledge | Azure AI Search GA source, knowledge base and extractive retrieve | Optional isolated Search deployment; an index alone is not Foundry IQ |
| Document service | Content Understanding GA invoice analyzer and grounded fields | Prebuilt analyzer is reachable; account defaults are unset and required model mappings are not provisioned |
| Pretrained document service | Native Document Intelligence `prebuilt-invoice`, GA `2024-11-30` | Live extraction succeeded: 1 page, 1 document, 8 structured fields with grounding; no new models |
| Built-in evaluator | `builtin.retrieval`, version 15 | Live staging relevant control scored 5/5; irrelevant control scored 1/5 |
| Grounding controls | `builtin.groundedness` v18 and `builtin.groundedness_pro` v8 | Both missed a known erroneous French baseline; negative-control gate fails, not an improvement claim |
| Red team | Native taxonomy and bounded agent-targeted evaluation | Taxonomy created for staging v2; inspect and approve exact categories before attacks |
| Traces | Deterministic instrumentation, native Log Analytics query and replay fixture | Nine actual spans exported, three custom stages verified, trace-derived native replay passed 1/1; not original-prompt recovery |
| Business state | Cosmos DB and employee-only approval | Independent of native memory; never approve a quote from the agent |

The web applications and read-only MCP servers run in Azure Container Apps.
They are Azure-hosted, but not inside the Foundry project. Search is a separate
Azure service underpinning the knowledge demonstration. Application Insights and
Log Analytics provide the existing Azure observability backend.

## Applicant-message judge contract

The historical 10-row judge run remains a failure: its generic queries asked
for a quote and hidden workflow execution, while the captured answer contained
only the English applicant acknowledgement. Do not reinterpret that evidence
as a passing run or claim a same-dataset quality improvement.

The separate `eval/applicant-message-dataset.jsonl` benchmark contains five
synthetic cases with independently authored facts. It evaluates only the
selected-locale acknowledgement, not hidden calculations, persistence or
authorization. On the retained staging version 4, all five English and all
five French cases passed coherence, groundedness and task adherence, with
zero evaluator errors:

* English: `evalrun_7556a65eb27544b7be68fd918979df8d`
* French: `evalrun_2a731e4ec7d14e8aa03bb300dba6b6fd`

Separate calibration run `evalrun_9c0960204b0945e8aa1d713b09f95211` rejected
both deliberate falsehoods on every criterion: invented approval with a price,
and successful submission for an invalid reference. No threshold was reduced.
These controls do not erase the earlier RAG grounding false positives below.
The release workflow now evaluates both locales and retains full native
results and capture provenance. Scores remain advisory, but missing, errored
or incomplete native evidence blocks promotion.

The invocation URL targets the current deployment; `--version` records the
operator-observed version, not a routing pin. Confirm the deployment before
running [Lab 18](labs/lab-18-native-evaluation-traces.md#exercise-185-judge-observable-applicant-messages).

## Setup and read-only checks

Use the existing Python environment. The root dependency manifest pins the
native SDK to `azure-ai-projects==2.6.0`; 2.3.0 has a different generation
submission method. Do not mix interpreters between commands.

```powershell
& .venv\Scripts\python.exe -m pip install -r requirements.txt
az login
$endpoint = 'https://aif-desjardins-quote-preparation-staging.services.ai.azure.com/api/projects/proj-desjardins-quote-preparation-staging'
$evidence = Join-Path $env:TEMP ('foundry-showcase-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $evidence
$revision = git rev-parse HEAD
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\preflight.json"
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py validate-corpus
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py catalog --endpoint $endpoint --output-dir "$evidence\catalog"
```

Evidence paths must be new. Native operation failures return nonzero and must
not be presented as successful screenshots. Authentication uses Entra tokens,
not checked-in secrets. Never expose the operator CLIs as end-user APIs.

### Isolated memory embedding prerequisite

Approved staging deployment `issue20-isolated-memory` succeeded.
`infra/memory-showcase.bicep` provisions only the separate
`showcase-memory-embedding` deployment on an existing account:
`text-embedding-3-small`, version `1`, regional `Standard`, capacity `1`,
with automatic version upgrades disabled. Reuse the existing deployment for
the demo. Recheck availability and quota before provisioning another target.

This opt-in template is outside `main.bicep` and `azure.yaml`, like the existing
isolated showcase template. It does not rewrite the account, existing chat
deployment, agent, RBAC, network, storage or production. Do not reprovision the
primary environment to add embeddings. Obtain exact-artifact and staging-target
approval, preview this template in incremental mode, and require only the one
new embedding resource before applying it. Compilation is not deployment.

The isolated `showcase-synthetic-memory` store was tested with existing
`gpt-4o-mini`, this embedding deployment and a 3600-second default TTL using
[Lab 17](labs/lab-17-native-skills-memory.md). Seed/list/search and both
cross-scope negative checks passed. Retain any explicit service rejection; do not
replace the working chat model or attach memory to the hosted quote agent to
hide a failure. The existing reviewer workload's memory-list request returned
403, with an operator positive control. This proves caller-role denial, not
per-agent isolation or authorization by scope.

## Demonstrate native files and generated data

The exported JSON is an exact-content safety permit, not the reference uploaded
to the generation service. The upload combines the pinned synthetic handbook
and hash-verified bilingual corpus into a supported `.txt` file with purpose
`user_data`. The job generates technical QnA, not applicant profiles or prices.

```powershell
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint fixture-export --file "$evidence\fixture.json"
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\file.json" file-upload --file "$evidence\fixture.json"
$fileId = (Get-Content "$evidence\file.json" -Raw | ConvertFrom-Json).result.file.id
$operationId = [guid]::NewGuid().ToString()
# Preserve this UUID with the exact inputs; reuse it for submission retries.
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\submit.json" generation-submit --name showcase-synthetic-demo-qna --file-id $fileId --model gpt-4o-mini --samples 15 --operation-id $operationId
$jobId = (Get-Content "$evidence\submit.json" -Raw | ConvertFrom-Json).result.job_id
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\status.json" generation-status --job-id $jobId --wait-seconds 120 --poll-seconds 5
$job = (Get-Content "$evidence\status.json" -Raw | ConvertFrom-Json).result.job
$outputFileId = ($job.result.outputs | Where-Object type -EQ file | Select-Object -First 1).id
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\download.json" generation-download --job-id $jobId --file-id $outputFileId --download-file "$evidence\generated.jsonl"
```

The generation scenario is named `supervised_finetuning` in this SDK because it
produces downloadable native file outputs. No training job, model deployment,
or permission to train on the result is created. Review generated content before
use. A succeeded native job and its actual output files, not an exported local
fixture, establish generation acceptance.

The verified staging job is `datagen-6424fd4d37904cebac2a1bbe9459df86`.
It generated 8 examples under a maximum of 15. Its downloaded native output
has SHA-256 `dc10f004c929303f1485b33eaf97e83688fc59d47f9d3ca047fe1f4bbe204e48`.
The service required a sufficiently comprehensive standalone reference;
the earlier undersized examples failed explicitly and were not counted as passes.

## Inspect real memory and test its limits

Reuse the approved existing staging store. Do not run `memory-create` again
against that name (HTTP 409). For a separately approved new store, use
`gpt-4o-mini`, `showcase-memory-embedding` and a 3600-second TTL.
Entries expire after one hour; reseed before the demo with fresh evidence paths:

```powershell
$store = 'showcase-synthetic-memory'
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\alice-seed.json" memory-seed --store $store --scope fixture-alice
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\bob-seed.json" memory-seed --store $store --scope fixture-bob
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\memory-contents.json" memory-list --store $store --scope fixture-alice
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\memory-isolation.json" memory-search --store $store --scope fixture-alice
```

The search must find Alice's marker in Alice's scope and not find it in Bob's.
An empty positive result fails the check. This proves a retrieval partition,
not caller authorization: a sufficiently privileged project caller can choose
another scope. Bind scope selection to authenticated application identity,
restrict project roles and consider separate project/store boundaries for
stronger isolation. Do not expose arbitrary scope strings to a chatbot.

Memory is not the authoritative quote state, audit trail or Cosmos DB retention
policy. Sharing a scope between agents is not a per-agent access-control list.
Hosted-agent runtime memory attachment remains a separate compatibility check.

## Explain the runtime skill accurately

[The runtime skill](../data/showcase/runtime-skill/SKILL.md) produces a synthetic
bilingual workshop briefing. It is authored by this project. The historical
Azure Kusto developer/Copilot skill is not evidence of a Microsoft-provided
Foundry runtime skill.

```powershell
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\skill.json" skill-register --name showcase-synthetic-bilingual-brief --file data\showcase\runtime-skill\SKILL.md
$skillVersion = (Get-Content "$evidence\skill.json" -Raw | ConvertFrom-Json).result.skill.version
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\skill-toolbox.json" skill-attach --name showcase-synthetic-bilingual-brief --version $skillVersion --toolbox showcase-synthetic-runtime-skills
```

The separate toolbox contains no production tools and does not alter the
running agent or `quote-tools`. Evidence intentionally reports `consumed: false`.

You can demonstrate real consumption without deploying another agent:

```powershell
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\skill-consumed.json" skill-consume --name showcase-synthetic-bilingual-brief --version $skillVersion --model gpt-4o-mini --scope fixture-alice
```

This isolated operator runtime discovers the native catalog entry and downloads
its immutable version. It accepts only the reviewed single-file skill, verifies
its instructions against the repository, and sends those downloaded instructions
to the existing model through native Responses with no tools. The completed
native response must retain the exact skill ID/version in its metadata.
The bilingual result must put the configured preferred language first,
mark the example synthetic, keep `approved: false`, and contain no monetary amount.

Live staging response
`resp_0fe8c263eaea766a006ad690cce8a08190ba6eb665618a7d3e`
passed these checks with skill version 1 and instruction SHA-256
`65c5c61f21d1c75f5f82a15b280392d8d20e69cdf57bbac679fec2c2106073df`.
This proves consumption by the operator Responses runtime, not by the hosted
quote agent, a toolbox MCP client, or the Agent Framework skills provider.
No hosted-agent deployment or approval state changes occur. Model inference
uses the existing deployment and incurs its normal usage charges.

## Retrieve grounded bilingual knowledge

### Start with managed native File Search

The verified managed path needs no separate Search service, embedding deployment
or companion agent. It uses the existing model and the reviewed six-file
[synthetic corpus](../data/showcase/knowledge/provenance.json).
Privacy sources are now version 2: memory scope keys partition records, but
neither authenticate nor authorize. Scope and review sources remain version 1.

```powershell
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py file-search-create --project-endpoint $endpoint --output "$evidence\native-store.json" --poll-timeout 120
foreach ($language in @('en', 'fr')) {
    foreach ($scenario in @('approval', 'scope', 'privacy', 'out-of-corpus')) {
        & .venv\Scripts\python.exe scripts\native_knowledge_showcase.py file-search-query --project-endpoint $endpoint --store-evidence "$evidence\native-store.json" --model gpt-4o-mini --language $language --scenario $scenario --output "$evidence\rag-$language-$scenario.json"
        if ($LASTEXITCODE -ne 0) { throw "Native RAG validation failed" }
    }
}
```

The live versioned store is `vs_035lJB6UtY795UZ6oOXOuDi9`. Six real answers
carry native citations and both unsupported questions return `OUT_OF_CORPUS`.
French privacy response `resp_0e7dd0761517e6d8006ad6b1bd347081968f41a01de565afcc`
cites `FSI-PRIVACY-FR` and explicitly denies scope-key authentication and authorization.
The operator runtime is not the hosted quote agent and this is not Foundry IQ.

Files use the native `assistants` purpose, distinct from generation's `user_data`.
Store membership, exact source hashes, retrieved excerpts, citation topic and
citation language are checked. Language validation is not a native filter or an
authorization boundary. Missing optional result-store IDs are checked against
the independently retrieved native membership list, never invented.
`source_citations_verified` does not mean semantic entailment has been scored.

The store has explicit seven-day expiry after last activity; uploaded file
retention is separate. Managed indexing, storage and inference incur charges.
No environment, deployed agent or application approval state is deleted or changed.
New evidence never overwrites an existing output. Partial resource IDs are
journaled before subsequent operations. To resume indexing after all six
uploads have been journaled:

```powershell
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py file-search-index --project-endpoint $endpoint --store-evidence "$evidence\partial-store.json" --output "$evidence\resumed-store.json" --poll-timeout 120
```

Reuse the resumed evidence for queries. Do not re-upload the corpus just to
retry indexing. Changed source versions require a newly indexed corpus;
the prior successful generation reference remains accepted by its exact pinned hash.

### Optional Search knowledge base

[The optional Bicep template](../infra/showcase.bicep) provisions a new Basic
Search service with Entra-only authentication, semantic ranking, a managed
identity and explicit operator/ingestion/query roles. It is not included by the
baseline template. It adds ongoing cost and requires regional, quota and
authorization approval before deployment.

Use the exact new Search resource ID, endpoint and operator principal:

```powershell
$search = 'https://<new-search-service>.search.windows.net'
$searchId = '/subscriptions/<subscription>/resourceGroups/<group>/providers/Microsoft.Search/searchServices/<new-search-service>'
$principal = '<operator-object-id>'
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py preflight --search-endpoint $search --search-resource-id $searchId --principal-id $principal --for-operation upsert
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py upsert --search-endpoint $search --search-resource-id $searchId --principal-id $principal
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py ingest --search-endpoint $search --search-resource-id $searchId --principal-id $principal
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py query --search-endpoint $search --question 'Who can approve the synthetic quote?' --language en
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py query --search-endpoint $search --question 'Qui peut approuver la soumission synthétique ?' --language fr
```

Inspect the actual source, base, retrieval activity and citations. Unknown source
IDs, changed hashes, wrong-language references, missing citations and unsupported
excerpts fail explicitly. GA `2026-04-01` extractive retrieval does not require a
new retrieval LLM. This CLI does not automatically create a Foundry project
connection or attach knowledge to the running hosted agent.

## Use a real document service

The invoice is fictional and rendered to a minimal PDF locally; its extraction
is performed by native Content Understanding, not a local OCR substitute.
The analyzer must return structured fields and inspectable grounding.

```powershell
$cu = '<Content Understanding resource endpoint>'
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py cu-preflight --cu-endpoint $cu
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py analyze --cu-endpoint $cu --poll-timeout 120
```

Current staging returns `DefaultsNotSet` for its GA defaults resource.
Do not overwrite account defaults or substitute the existing chat deployment
for an unsupported analyzer model. Provisioning compatible models is a separate
approved change. The CLI reports the missing prerequisite rather than
fabricating document fields.

For a working native pretrained service without those additional generative
models, use the existing account's Document Intelligence invoice analyzer:

```powershell
$invoiceEndpoint = 'https://aif-desjardins-quote-preparation-staging.cognitiveservices.azure.com'
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py invoice-analyze --cu-endpoint $invoiceEndpoint --poll-timeout 120
```

This is a distinct first-party Azure AI service, not a claim that Content
Understanding was configured. The verified native extraction contains invoice
ID/date, vendor/customer names, items, subtotal, tax and total, with confidence
and document grounding. These are synthetic invoice observations only; no
amount enters the applicant response, pricing workflow or approval record.

## Evaluate, investigate and replay

```powershell
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py retrieval-compare --endpoint $endpoint --deployment gpt-4o-mini --source-revision $revision --output-dir "$evidence\retrieval"
```

Inspect the native run in Foundry and the retained dataset, results, identity
and comparison files. Acceptance requires relevant context at least 3/5 and
irrelevant context below 3/5. The live staging run measured 5 and 1. This is
a controlled evaluator demonstration, not proof that the hosted agent is a RAG
or that its production retrieval has improved.

Repeat the retrieval command into a second new output directory, then compare
the two completed native runs:

```powershell
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py retrieval-compare --endpoint $endpoint --deployment gpt-4o-mini --source-revision $revision --output-dir "$evidence\retrieval-repeat"
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py compare-runs --baseline-results "$evidence\retrieval\results.json" --candidate-results "$evidence\retrieval-repeat\results.json" --output-dir "$evidence\comparison"
```

The comparison rejects different datasets, evaluator versions, judge
deployments, failed runs, missing identities/hashes and the same run compared
with itself. Two verified native runs both scored 5/1, with zero score delta.
That demonstrates measured repeatability, not an optimization gain.

### Preserve failed native grounding controls

An earlier French answer incorrectly said scope keys authorize actions and
cited the scope source. Privacy version 2 and explicit source/topic guards
corrected the real response; both current EN/FR privacy answers were inspected
against that source. This is a corpus/instruction correction, not a hosted-agent update.

Both native grounding judges nevertheless accepted the known bad baseline:

| Native evaluator | Bad baseline | Corrected candidate | Negative-control gate |
|------------------|--------------|---------------------|-----------------------|
| `builtin.groundedness` v18, existing `gpt-4o-mini` | 5/5 | 5/5 | Failed |
| `builtin.groundedness_pro` v8, managed service | `true` | `true` | Failed |

Native runs are `evalrun_90768c55e09946809a97eac233d7c4bb` and
`evalrun_8683ff9a323a40de87cbeed5d752def2`. Their original native `input_items`
confirm identical user questions; search rewrites alone were not identical.
Contexts are the actually cited excerpts, not invented reference answers.
No grounding improvement or passing quality gate is claimed.

To reproduce using the retained erroneous and corrected native response artifacts:

```powershell
$badRag = '<retained-known-bad-native-RAG-response.json>'
$fixedRag = '<retained-corrected-native-RAG-response.json>'
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py grounding-compare --endpoint $endpoint --deployment gpt-4o-mini --source-revision $revision --baseline-results $badRag --candidate-results $fixedRag --output-dir "$evidence\grounding"
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py grounding-compare --endpoint $endpoint --grounding-evaluator groundedness_pro --source-revision $revision --baseline-results $badRag --candidate-results $fixedRag --output-dir "$evidence\grounding-pro"
```

These comparisons deliberately exit nonzero when the bad answer passes.
Preserve the failed outputs. Do not change controls until they look green,
weaken source checks to regenerate a bad baseline, or promote on a judge score alone.

### Verify actual trace ingestion

The quote graph is deterministic. `AGENT_TASK_INSTRUCTIONS` is evaluation
metadata, not an executed system prompt. Its real stage spans record stage,
validated synthetic case ID, execution kind and policy hash. They intentionally
omit applicant input, amounts, fabricated model spans and invented token costs.
The existing agent-server telemetry provider must export them after deployment.

An isolated local export to existing staging Application Insights was rejected
with HTTP 403 for the operator credential. Exporter `force_flush()` is not
proof of ingestion: the retained record explicitly says `trace_verified: false`.
Resolve the publisher authorization through approved access management.
Do not omit Entra credentials or weaken authentication to bypass the rejection.

The approved staging v5 runtime exported nine actual spans for operation
`f63bbcfefd1b3b252a4c343bdc99fd2b`, including `quote.INTAKE`,
`quote.REFERENCE_LOOKUP` and `quote.COMPOSITION`, with parent/status/policy
lineage. Calculation and persistence execute inside `COMPOSITION`.
Search SDK dependencies independently from platform request roots: their
operation IDs can differ. A root-only query is not proof of missing stages.
The trace-derived native replay passed 1/1 on all three criteria.
See [current evidence](showcase-evidence.md#verified-custom-trace-and-native-replay).
Do not feed a root-only invocation into `trace-dataset`.

```powershell
$workspace = '<existing-Log-Analytics-workspace-customer-ID>'
$traceId = '<actual-32-character-operation-ID>'
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py trace-export --workspace-id $workspace --operation-id $traceId --output-dir "$evidence\trace"
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py trace-dataset --trace-file "$evidence\trace\trace.json" --operation-id $traceId --source-revision $revision --output-dir "$evidence\replay"
& .venv\Scripts\python.exe eval\run_judge_evaluation.py --endpoint $endpoint --agent quote-preparation-agent --version 5 --deployment gpt-4o-mini --dataset "$evidence\replay\replay-dataset.json" --output-dir "$evidence\replayed-evaluation"
```

Missing spans fail. A requested `traceparent` is marked unverified until the
native query finds it. Replay reconstructs a synthetic case, not the original
private user prompt. The dataset retains operation ID, policy hash, source
revision and trace-file hash; the native evaluation adds run identities.

## Safe native red teaming

```powershell
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py taxonomy-create --endpoint $endpoint --agent quote-preparation-agent --agent-version 2 --taxonomy showcase-synthetic-prohibited-actions --output-dir "$evidence\taxonomy"
```

Inspect the complete native taxonomy. The service may generate broad universal
categories beyond this workshop's intended no-amount/no-approval policy.
Do not launch attacks merely because taxonomy generation succeeded.
After human review, use the exact hash, a pinned synthetic target and one turn:

```powershell
$approvedHash = '<SHA-256 of the exact reviewed native taxonomy>'
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py red-team --endpoint $endpoint --agent quote-preparation-agent --agent-version 2 --taxonomy showcase-synthetic-prohibited-actions --approved-taxonomy-sha256 $approvedHash --source-revision $revision --turns 1 --output-dir "$evidence\redteam"
```

Only `ProhibitedActions` is accepted. No harmful-content risk categories are
requested. Native results and failures are retained; timeout requests
cancellation. Successful scan execution is not a clean security sign-off.

## Experiment tracking and architecture recommendation

Start with native evaluation comparisons and actual Azure traces. Retain source
revision, runner hash, evaluator version, model deployment, dataset hash,
parameters, native run IDs and any verified trace IDs. Compare the same dataset
and evaluator configuration when changing a prompt, retrieval setting or model.

Foundry evaluations are not simply a renamed MLflow experiment service.
Azure ML supplies an MLflow-compatible tracking backend; that does not establish
an equivalent native Foundry Experiments blade. Add Langfuse, Phoenix or MLflow
only when a measured unmet need justifies another platform, its operational
cost, access model, retention and approved data boundary. No external tracing
platform is installed by this showcase.

## Validation and publication

```powershell
& .venv\Scripts\python.exe -m pytest eval src\quote-preparation-agent\tests -q
az bicep build --file infra\showcase.bicep --stdout
npm run build-workshop-deck
```

The [English deck](assets/decks/foundry-hosted-agents-workshop-fsi-en.pptx)
and [French deck](assets/decks/foundry-hosted-agents-workshop-fsi-fr.pptx)
use the same slide structure and distinguish local exercises from the restored
Azure demo. Existing CI collects unit/evaluation results. Wiki publication keeps
its main-branch provenance guard; feature-branch evidence must not bypass it.
Enhancement release requires Product Owner, Security Team and Tech Lead
sign-off. Both web apps now pin PyJWT 2.15.1 rather than the vulnerable 2.12.1.
Authentication regression tests and a package-advisory recheck validate that
source change, not the unchanged deployed images. Existing dependency alerts
must be rechecked after publication and rebuilding.

GitHub CodeQL default setup is configured, but its last observed analysis
targets main commit `b4ceba0`, not this unpublished feature. No local SAST or
secret scanner is installed. A historical scan does not clear the new source;
run the configured checks on the exact published feature before release.

## Primary references

* [Native runtime skills](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/skills)
* [Native memory usage](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/memory-usage)
* [Search knowledge bases](https://learn.microsoft.com/en-us/azure/search/agentic-retrieval-how-to-create-knowledge-base)
* [Content Understanding](https://learn.microsoft.com/en-us/azure/ai-services/content-understanding/overview)
* [Native synthetic evaluation data](https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/evaluation-dataset-synthetic)
* [Cloud red teaming](https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/run-ai-red-teaming-cloud)
* [Azure ML and MLflow](https://learn.microsoft.com/en-us/azure/machine-learning/concept-mlflow?view=azureml-api-2)
