---
permalink: /labs/lab-16-native-search-invoice
title: "Lab 16 - File Search and Invoice Extraction"
description: "Query the bilingual native File Search corpus, inspect source checks and refusals, and extract a synthetic invoice with Document Intelligence."
---

[Français](../fr/labs/lab-16-native-search-invoice.md) | [Labs](index.md)

## Scope and prerequisites

Allow 45 minutes. Complete [Lab 15](lab-15-native-files-generation.md), or obtain
the same existing Python environment and approved staging operator access.
Use the existing `gpt-4o-mini` deployment. Managed File Search requires neither
a separate Search service nor an embedding deployment. Indexing, storage and
inference incur charges; agree on these before running the live exercises.

All material is synthetic and non-binding, not an actual Desjardins product,
rate or policy. Never send invoice amounts to the applicant response, pricing
workflow or approval record. These operator calls do not change the hosted
quote agent, `quote-tools` or either deployed environment.

From the repository root, prepare a new git-ignored evidence directory:

```powershell
$endpoint = 'https://aif-desjardins-quote-preparation-staging.services.ai.azure.com/api/projects/proj-desjardins-quote-preparation-staging'
$evidence = Join-Path '.local' ('lab16-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $evidence
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py validate-corpus
Get-Content data\showcase\knowledge\provenance.json
```

Identify the six versioned sources and their hashes. Privacy sources are version
2; scope and approval sources remain version 1. If validation fails, do not
weaken hash checks or index altered sources to continue.

## Exercise 16.1: Index and query both languages

```powershell
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py file-search-create --project-endpoint $endpoint --output "$evidence\native-store.json" --poll-timeout 120
if ($LASTEXITCODE -ne 0) { throw 'Inspect the partial indexing evidence before querying.' }
foreach ($language in @('en', 'fr')) {
    foreach ($scenario in @('approval', 'scope', 'privacy', 'out-of-corpus')) {
        & .venv\Scripts\python.exe scripts\native_knowledge_showcase.py file-search-query --project-endpoint $endpoint --store-evidence "$evidence\native-store.json" --model gpt-4o-mini --language $language --scenario $scenario --output "$evidence\rag-$language-$scenario.json"
        if ($LASTEXITCODE -ne 0) { throw 'Native RAG validation failed; retain the response.' }
    }
}
Get-Content "$evidence\rag-fr-privacy.json"
Get-Content "$evidence\rag-en-out-of-corpus.json"
```

Inspect each native response ID, retrieved excerpt, file citation, membership
and source hash. Approval, scope and privacy responses need the correct topic
and language. Privacy must not claim that a memory scope authenticates or
authorizes a caller. Both unsupported questions must return `OUT_OF_CORPUS`;
a plausible invented answer is a failure.

Explain `source_citations_verified`, `store_membership_verified` and
`validation_state`. These are source-attribution checks, not semantic entailment
scores or a native language/access filter. A missing optional store ID in a
result is checked against the independently retrieved membership list, not
invented. Retain a pending response if validation fails.

File Search uses purpose `assistants`, unlike generation's `user_data`. The
store expires seven days after last activity, while uploaded file retention is
separate. This is native File Search in an isolated operator Responses runtime,
not Foundry IQ or proof of hosted-agent consumption.

## Exercise 16.2: Resume a partial index without re-uploading

Do this only if creation failed after all six uploads were journaled. Inspect
the actual journal first. Copy the exact path into `$partialStore`; do not
fabricate a completed journal or a failure. Otherwise mark this exercise not
needed and retain the successful store evidence.

```powershell
$partialStore = '<actual-partial-store-evidence.json>'
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py file-search-index --project-endpoint $endpoint --store-evidence $partialStore --output "$evidence\resumed-store.json" --poll-timeout 120
```

After successful resumption, use `resumed-store.json` as `--store-evidence` for
subsequent queries, with new output filenames. If source versions change,
create a newly indexed corpus instead of reusing mismatched evidence.

## Exercise 16.3: Separate document-service prerequisites from extraction

Read the Content Understanding defaults before attempting analysis:

```powershell
$invoiceEndpoint = 'https://aif-desjardins-quote-preparation-staging.cognitiveservices.azure.com'
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py cu-preflight --cu-endpoint $invoiceEndpoint 1> "$evidence\cu-preflight.json" 2> "$evidence\cu-preflight.stderr.txt"
$cuExit = $LASTEXITCODE
Get-Content "$evidence\cu-preflight.json"
Get-Content "$evidence\cu-preflight.stderr.txt"
$cuExit
```

Current staging reports `DefaultsNotSet`; required compatible model mappings
are not provisioned. This is a prerequisite limit, not extraction evidence.
Do not patch account defaults or substitute an unsupported chat deployment.
Provisioning compatible models is a separate approved change. If that change
has already been completed, the runbook's `analyze` command is the CU path.

Now use the distinct pretrained Document Intelligence service, which needs no
additional generative models:

```powershell
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py invoice-analyze --cu-endpoint $invoiceEndpoint --poll-timeout 120 1> "$evidence\invoice.json" 2> "$evidence\invoice.stderr.txt"
if ($LASTEXITCODE -ne 0) { throw 'Invoice extraction failed; inspect the retained service error.' }
Get-Content "$evidence\invoice.json"
```

The fictional invoice is rendered locally as a PDF; extraction is native
`prebuilt-invoice`, API `2024-11-30`, not local OCR. Inspect document/page count,
invoice ID/date, vendor/customer, items, subtotal, tax and total. Check field
confidence and grounding against the synthetic source, not merely HTTP success.
The earlier verified extraction had 1 page, 1 document and 8 structured fields;
record your actual result rather than copying those historical counts.

## Completion evidence

* Retain corpus provenance, store/membership evidence, and eight EN/FR responses
  or precise failures, including both out-of-corpus checks.
* Explain why verified citations do not prove semantic correctness or access control.
* Retain CU preflight and native invoice evidence separately; do not label
  Document Intelligence success as configured Content Understanding.

Keep evidence outside Git and shared resources available. Continue to
[Lab 17: Runtime Skills and Memory Boundaries](lab-17-native-skills-memory.md).
