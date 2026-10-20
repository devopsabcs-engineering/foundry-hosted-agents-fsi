---
permalink: /labs/lab-15-native-files-generation
title: "Lab 15 - Native Files and Generation"
description: "Upload the reviewed synthetic reference, inspect native generation outputs, and diagnose historical failed jobs without a local fallback."
---

[Français](../fr/labs/lab-15-native-files-generation.md) | [Labs](index.md)

## Scope and prerequisites

Allow 40 minutes. Complete [Lab 00](lab-00-setup.md) and obtain approved operator
access to the existing staging project. Use its existing Python environment
with `azure-ai-projects==2.6.0`, Entra credentials and a supported generation
base model. Run PowerShell from the repository root. The operator CLI is not
an end-user API.

All inputs and outputs are synthetic and non-binding, not actual Desjardins
products, rates or policies. Generation consumes service capacity and may incur
charges. Do not deploy, change `quote-tools`, replace restored agents or run
teardown. Approved staging v5 and production v6 remain available.

Create a new evidence directory under the git-ignored `.local` folder. Use a
fresh directory for every attempt; never overwrite earlier evidence.

```powershell
$endpoint = 'https://aif-desjardins-quote-preparation-staging.services.ai.azure.com/api/projects/proj-desjardins-quote-preparation-staging'
$evidence = Join-Path '.local' ('lab15-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $evidence
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\preflight.json"
```

Inspect the returned deployments and warnings. Preflight is read-only, not proof
of generation compatibility. If authentication or service access fails, retain
the error and stop live exercises; do not substitute locally generated output.

## Exercise 15.1: Distinguish the permit from the uploaded reference

```powershell
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint fixture-export --file "$evidence\fixture.json"
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\file.json" file-upload --file "$evidence\fixture.json"
Get-Content "$evidence\file.json"
$fileId = (Get-Content "$evidence\file.json" -Raw | ConvertFrom-Json).result.file.id
```

Read the upload evidence. The JSON is an exact-content safety permit, not the
generation reference sent to the service. The CLI uploads a supported `.txt`
reference including the pinned handbook, hash-verified bilingual corpus and
26 independent standalone lessons from `data\showcase\generation-reference.txt`,
with purpose `user_data`. Record the native file ID and source hashes. A
successful local export alone cannot satisfy this checkpoint.

## Exercise 15.2: Submit, poll and inspect the native output

Generate technical workshop QnA, never applicant profiles or prices. Preserve
the UUID and exact inputs before submission. Reuse them for a submission retry,
but choose a new evidence filename rather than overwriting `submit.json`.

```powershell
$operationId = [guid]::NewGuid().ToString()
$operationId | Set-Content "$evidence\operation-id.txt"
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\submit.json" generation-submit --name showcase-synthetic-demo-qna --file-id $fileId --model gpt-4o-mini --samples 15 --operation-id $operationId
$jobId = (Get-Content "$evidence\submit.json" -Raw | ConvertFrom-Json).result.job_id
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\status.json" generation-status --job-id $jobId --wait-seconds 120 --poll-seconds 5
if ($LASTEXITCODE -ne 0) { throw 'Inspect the native job error before continuing.' }
$job = (Get-Content "$evidence\status.json" -Raw | ConvertFrom-Json).result.job
if ($job.status -ne 'succeeded') { throw 'Download requires a succeeded native job.' }
$outputFileId = ($job.result.outputs | Where-Object type -EQ file | Select-Object -First 1).id
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\download.json" generation-download --job-id $jobId --file-id $outputFileId --download-file "$evidence\generated.jsonl"
Get-FileHash "$evidence\generated.jsonl" -Algorithm SHA256
Get-Content "$evidence\generated.jsonl" | Measure-Object -Line
```

Record the returned status, output ID, hash and actual count; inspect the QnA for
unsupported claims before use. Fifteen is the maximum requested, not a guaranteed
count. The recovered jobs `datagen-a866fd3be0104ae4b6ec4808b76cbec2` and
`datagen-afe38ec64fb744a09e845119139e4064` succeeded with 6 and 5 examples
respectively, each under a requested maximum of 15. Do not report historical
results as your own execution.
Inspect their downloaded output IDs and SHA-256 values in the
[recorded recovery evidence](../showcase-evidence.md#two-failed-generation-jobs-recovered).
These retained results are API/download proofs, distinct from the independently
captured Foundry portal evidence and the approved runtime release. Consult the
[current release](../showcase-evidence.md#current-approved-release) rather than
using a generation result as proof of which agent version is deployed.
The SDK scenario `supervised_finetuning` enables native downloadable outputs;
it does not create a training job, deploy a model or authorize training.

## Exercise 15.3: Diagnose a historical failed job

Read the original failed job `datagen-4e74a27bd5f24a87a08ea35ad788c8cb`
(reference smaller than 1 KB). Then repeat with
`datagen-af8399a33bd7477b8279591b5a408c7a` (insufficient standalone context),
choosing a new stderr filename. Do not invent an ID or intentionally submit a
new bad job. If historical evidence is inaccessible, record this exercise as blocked.

```powershell
$failedJobId = 'datagen-4e74a27bd5f24a87a08ea35ad788c8cb'
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint generation-status --job-id $failedJobId 2> "$evidence\historical-failure.stderr.txt"
$failureExit = $LASTEXITCODE
Get-Content "$evidence\historical-failure.stderr.txt"
$failureExit
```

A failed or cancelled job returns nonzero and a diagnostic with job ID, status
and service error, rather than a successful JSON result. A 404 or permission
error proves only that the job could not be read. Correlate the service error
with the retained submission's reference size and format. Earlier undersized
references failed, including first retries with the old source. Those failures
remain evidence. The recovered reference has 26 standalone lessons and 19,881
bytes. Exceeding a minimum 1 KB input check does not establish sufficient
standalone context for the service to generate usable examples.
Generation accepts text, Markdown or PDF, not JSON filenames. Never count
failures as passes or manufacture a local replacement.

For a new job that is still pending after the wait, keep its UUID/job ID and
resume `generation-status` into a new output path. Do not submit another job
merely because polling timed out.

## Completion evidence

* Retain preflight, native upload, operation UUID, submission, succeeded status,
  downloaded native output and its SHA-256, or the precise blocking error.
* Retain the historical failure's exit code and service diagnosis separately.
* Explain why upload, generation and permission to train are distinct claims.

Keep synthetic evidence outside Git. Do not delete shared resources. Continue
to [Lab 16: File Search and Invoice Extraction](lab-16-native-search-invoice.md).
