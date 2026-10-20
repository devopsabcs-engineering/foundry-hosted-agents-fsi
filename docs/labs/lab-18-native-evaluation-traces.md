---
permalink: /labs/lab-18-native-evaluation-traces
title: "Lab 18 - Native Evaluation and Trace Replay"
description: "Compare native evaluator controls, preserve failed grounding gates, and replay only genuinely ingested deterministic workflow traces."
---

[Français](../fr/labs/lab-18-native-evaluation-traces.md) | [Labs](index.md)

## Scope and prerequisites

Allow 50 minutes. Complete [Lab 17](lab-17-native-skills-memory.md) and retain
the File Search evidence from [Lab 16](lab-16-native-search-invoice.md).
Use the existing Python environment, Entra operator access and approved
evaluation/inference budget. Run from the repository root:

```powershell
$endpoint = 'https://aif-desjardins-quote-preparation-staging.services.ai.azure.com/api/projects/proj-desjardins-quote-preparation-staging'
$evidence = Join-Path '.local' ('lab18-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $evidence
$revision = git rev-parse HEAD
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py catalog --endpoint $endpoint --output-dir "$evidence\catalog"
```

All material is synthetic and non-binding, not a real Desjardins product, rate
or policy. Catalog discovery is not an evaluation pass. These exercises do not
deploy agents, change approvals or authorize release. Retain evidence outside
Git with new output paths for every run.

## Exercise 18.1: Measure relevant and irrelevant retrieval controls

```powershell
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py retrieval-compare --endpoint $endpoint --deployment gpt-4o-mini --source-revision $revision --output-dir "$evidence\retrieval"
if ($LASTEXITCODE -ne 0) { throw 'Inspect failed retrieval controls before continuing.' }
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py retrieval-compare --endpoint $endpoint --deployment gpt-4o-mini --source-revision $revision --output-dir "$evidence\retrieval-repeat"
if ($LASTEXITCODE -ne 0) { throw 'Inspect the repeated run before comparison.' }
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py compare-runs --baseline-results "$evidence\retrieval\results.json" --candidate-results "$evidence\retrieval-repeat\results.json" --output-dir "$evidence\comparison"
Get-Content "$evidence\comparison\run-comparison.json"
```

Open each actual native run in Foundry. Record dataset hash, Git revision,
run/evaluation IDs, evaluator version and judge deployment. `builtin.retrieval`
version 15 accepts relevant context at least 3/5 and irrelevant context below
3/5. Inspect the dataset and individual outputs rather than a screenshot alone.
Historically both runs scored 5/1 with zero delta: repeatability, not improvement.
Record your own measured scores without assuming the same result.

The comparison rejects a run compared with itself, failed runs, changed
datasets/evaluator versions/judge deployments, and missing identities or hashes.
As an offline negative check, attempt a self-comparison:

```powershell
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py compare-runs --baseline-results "$evidence\retrieval\results.json" --candidate-results "$evidence\retrieval\results.json" --output-dir "$evidence\self-comparison" 2> "$evidence\self-comparison.stderr.txt"
$selfExit = $LASTEXITCODE
Get-Content "$evidence\self-comparison.stderr.txt"
$selfExit
```

Require nonzero and the specific same-run diagnostic. A missing-file error is
not the intended negative control. This is an evaluator demonstration, not
evidence of hosted-agent RAG or improved production retrieval.

## Exercise 18.2: Preserve the grounding judges' false positives

Obtain retained known-bad and corrected native RAG responses from the evidence
custodian. The bad French answer incorrectly claimed scopes authorize actions.
Do not weaken source/topic checks, edit native responses, or invent a baseline
to regenerate it. If those artifacts are unavailable, mark this reproduction
blocked and analyze the [recorded evidence](../native-showcase.md#preserve-failed-native-grounding-controls).

Inspect both real response artifacts and their native `input_items`: the
original user question must match, not merely the rewritten search queries.
Compare the actually cited context with each answer and privacy version 2.
With those exact retained paths, run both native judges:

```powershell
$badRag = '<retained-known-bad-native-RAG-response.json>'
$fixedRag = '<retained-corrected-native-RAG-response.json>'
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py grounding-compare --endpoint $endpoint --deployment gpt-4o-mini --source-revision $revision --baseline-results $badRag --candidate-results $fixedRag --output-dir "$evidence\grounding"
$groundingExit = $LASTEXITCODE
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py grounding-compare --endpoint $endpoint --grounding-evaluator groundedness_pro --source-revision $revision --baseline-results $badRag --candidate-results $fixedRag --output-dir "$evidence\grounding-pro"
$groundingProExit = $LASTEXITCODE
$groundingExit
$groundingProExit
Get-ChildItem "$evidence\grounding", "$evidence\grounding-pro"
```

Both native judges missed the bad baseline in the recorded runs:

| Judge                       | Bad baseline | Corrected candidate | Negative-control gate |
| --------------------------- | ------------ | ------------------- | --------------------- |
| `builtin.groundedness` v18   | 5/5          | 5/5                 | Failed                |
| `builtin.groundedness_pro` v8 | `true`      | `true`              | Failed                |

Do not claim that grounding comparisons passed or that grounding improved.
The known-bad answer passing makes the CLI exit nonzero deliberately. Inspect
retained native results to distinguish that failure from authentication, timeout
or input validation errors. Preserve all failed outputs and native run IDs;
do not tune controls until they look green or promote on a judge score alone.
The corpus/instruction correction is not a hosted-agent update.

## Exercise 18.3: Check real ingestion before trace export and replay

The graph is deterministic. `AGENT_TASK_INSTRUCTIONS` is evaluation metadata,
not an executed system prompt. Real workflow spans retain stage, validated
synthetic case ID, execution kind and policy hash, not applicant input, amounts,
fabricated model spans or invented token usage.

> [!IMPORTANT]
> Trace replay requires real spans already ingested into the existing
> Application Insights/Log Analytics backend through the authorized telemetry
> provider. The retained release has verified hosted root spans, but custom
> stage fields and deterministic replay remain unverified. Do not deploy or
> change access in this lab.

The isolated local export previously received HTTP 403 for the operator identity
and retained `trace_verified: false`. `force_flush()` and a requested W3C
`traceparent` do not prove ingestion. If publisher authorization or instrumented
deployment is missing, record this exercise blocked. Resolve it through
approved access management; never remove Entra credentials or weaken authentication.

Only with confirmed ingestion and workspace query access, replace the
placeholders with the existing workspace customer ID and the actual
32-character operation ID. Export first and stop if no real spans are found:

```powershell
$workspace = '<existing-Log-Analytics-workspace-customer-ID>'
$traceId = '<actual-32-character-operation-ID>'
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py trace-export --workspace-id $workspace --operation-id $traceId --output-dir "$evidence\trace"
if ($LASTEXITCODE -ne 0) { throw 'No verified trace export; do not create a replay.' }
Get-Content "$evidence\trace\trace.json"
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py trace-dataset --trace-file "$evidence\trace\trace.json" --operation-id $traceId --source-revision $revision --output-dir "$evidence\replay"
if ($LASTEXITCODE -ne 0) { throw 'Trace reconstruction failed; do not evaluate a substitute.' }
Get-Content "$evidence\replay\replay-dataset.json"
```

Verify operation ID, policy hash, source revision, trace-file hash and synthetic
case mapping. Missing spans fail; requested IDs are unverified until the native
query finds them. Replay reconstructs a fixture, not the original private prompt.
Only after that inspection, submit the retained dataset against staging v2:

```powershell
& .venv\Scripts\python.exe eval\run_judge_evaluation.py --endpoint $endpoint --agent quote-preparation-agent --version 2 --deployment gpt-4o-mini --dataset "$evidence\replay\replay-dataset.json" --output-dir "$evidence\replayed-evaluation"
```

Record actual evaluation IDs and failures. If real ingestion is unavailable,
do not create a hand-authored trace and label it live.

## Exercise 18.4: Check the actual playground separately

1. Open the staging project's agent in Foundry and select its currently deployed
   version. Sign in normally; never paste tokens into the browser.
2. In Playground, Chat, submit `CASE-SYN-001`. Wait for the completed response,
   not just a completed trace.
3. Require both nonempty `en-CA` and `fr-CA` fields, employee-review wording and
   the training notice, with no applicant-facing price or reviewer-only fields.
4. Open Traces and distinguish successful root execution from proof of useful
   output or custom stage ingestion. An empty response is a failed UI check.
5. In Evaluations, inspect individual criteria and the overall passing-item
   count. The advisory judge is not the deterministic release gate.

The [actual portal captures](../showcase-evidence.md#authenticated-staging-foundry-agent)
show the earlier blank v3 response investigation and the corrected v4 response.
The [evaluation capture](../showcase-evidence.md#honest-evaluation-results) preserves
failed judge criteria rather than presenting workflow success as a judge pass.
These are reference observations, not substitutes for your own live checks.

## Completion evidence

* Retain two native retrieval runs, their comparison and the self-comparison
  rejection with measured scores and exact identities.
* Retain both grounding control results, including false positives and failed
  gates, or mark reproduction blocked by missing retained artifacts.
* Retain verified trace export, replay provenance and native evaluation only
  if ingestion prerequisites exist; otherwise document the precise block.

Return to [Lab 17](lab-17-native-skills-memory.md), the [labs index](index.md)
or the [native showcase runbook](../native-showcase.md). Leave staging and
production deployed; these exercises do not authorize teardown or release.
