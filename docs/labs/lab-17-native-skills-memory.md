---
permalink: /labs/lab-17-native-skills-memory
title: "Lab 17 - Runtime Skills and Memory Boundaries"
description: "Register and consume the project-authored skill in an isolated runtime, then distinguish memory namespace checks from authorization."
---

[Français](../fr/labs/lab-17-native-skills-memory.md) | [Labs](index.md)

## Scope and prerequisites

Allow 40 minutes. Complete [Lab 16](lab-16-native-search-invoice.md), or obtain
the same Python environment and approved staging operator access. The skill
exercise uses the existing `gpt-4o-mini` deployment and incurs inference charges.
The memory exercise reuses the separately approved staging chat and embedding
deployments and the existing isolated `showcase-synthetic-memory` store.

All content is synthetic and non-binding, not a real Desjardins product, rate
or policy. Do not change the hosted quote agent, `quote-tools`, Cosmos DB
business state or employee-only approval. Do not deploy new models to unblock
an exercise. Start in PowerShell at the repository root:

```powershell
$endpoint = 'https://aif-desjardins-quote-preparation-staging.services.ai.azure.com/api/projects/proj-desjardins-quote-preparation-staging'
$evidence = Join-Path '.local' ('lab17-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $evidence
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\preflight.json"
Get-Content data\showcase\runtime-skill\SKILL.md
```

The skill is authored by this project. It is not a Microsoft-provided runtime
skill; the historical Azure Kusto developer/Copilot skill is a different artifact.
Read its output constraints before sending any inference request.

## Exercise 17.1: Register and attach without claiming consumption

```powershell
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\skill.json" skill-register --name showcase-synthetic-bilingual-brief --file data\showcase\runtime-skill\SKILL.md
$skillVersion = (Get-Content "$evidence\skill.json" -Raw | ConvertFrom-Json).result.skill.version
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\skill-toolbox.json" skill-attach --name showcase-synthetic-bilingual-brief --version $skillVersion --toolbox showcase-synthetic-runtime-skills
Get-Content "$evidence\skill-toolbox.json"
```

Record native ID/version and the separate toolbox name. Evidence should still
report `consumed: false`: a catalog entry or toolbox attachment is not a runtime
invocation. The separate toolbox contains no production tools and changes
neither `quote-tools` nor the running agent. Keep all output paths new.

## Exercise 17.2: Prove consumption by the isolated operator runtime

```powershell
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\skill-consumed.json" skill-consume --name showcase-synthetic-bilingual-brief --version $skillVersion --model gpt-4o-mini --scope fixture-alice
if ($LASTEXITCODE -ne 0) { throw 'Skill consumption failed; retain the native error.' }
Get-Content "$evidence\skill-consumed.json"
```

Trace the evidence from native discovery to immutable-version download to the
completed Responses call. The CLI verifies downloaded instructions against the
reviewed repository file and sends them to the existing model with no tools.
Verify instruction SHA-256, native response ID and exact skill ID/version
metadata, rather than inferring consumption from registration.

Inspect the actual bilingual result: preferred language first, synthetic
designation, `approved: false`, and no monetary amount. The successful runtime
evidence reports `consumed: true`; the earlier attachment remains false. A
failed output validation must remain a failure.

Write down which runtime executed: the isolated operator Responses runtime,
not the hosted quote agent, toolbox MCP client or Agent Framework skills
provider. No deployment or business approval changed.

## Exercise 17.3: Verify the approved memory prerequisites

Inspect `preflight.json` and list available deployment names. Compare them with
the memory command's required chat and embedding inputs:

```powershell
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint memory-create --help
```

Staging now has `gpt-4o-mini` and the approved `showcase-memory-embedding`
(`text-embedding-3-small`, version `1`). The isolated store was created with
a 3600-second default TTL, with user-profile and chat-summary extraction
disabled. Native seed,
list and search passed, unlike the earlier prerequisite-blocked state.
Listing models alone does not prove operation. Do not substitute a chat model
for embeddings or redeploy the baseline infrastructure.

## Exercise 17.4: Test namespaces only after prerequisites are approved

Reuse the existing approved staging store; do not recreate it (HTTP 409).
For a different approved target only, create a new isolated store using the
deployment names above and `--ttl-seconds 3600`. The following commands reseed
expired one-hour fixtures and retain new evidence without changing store setup:

```powershell
$store = 'showcase-synthetic-memory'
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\alice-seed.json" memory-seed --store $store --scope fixture-alice
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\bob-seed.json" memory-seed --store $store --scope fixture-bob
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\memory-contents.json" memory-list --store $store --scope fixture-alice
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\memory-isolation.json" memory-search --store $store --scope fixture-alice
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\bob-isolation.json" memory-search --store $store --scope fixture-bob
Get-Content "$evidence\memory-isolation.json"
```

Stop on any failed operation. Inspect `positive`, `negative`, `scope`,
`negative_scope` and `scope_negative_check`. Alice's marker must be found in
Alice's scope and absent in Bob's. An empty positive result fails; wait for
indexing and retry search into a fresh evidence path rather than declaring an
empty store isolated. Sequential seed retries reuse matching content, but
concurrent seeds are not atomic.

Even a successful test establishes a retrieval partition, not authorization.
A sufficiently privileged project caller can choose another namespace. Bind
scope selection to authenticated application identity, restrict project roles
and consider separate project/store boundaries for stronger isolation. Never
accept an arbitrary scope string from a chatbot. Sharing a scope is not a
per-agent access-control list.

The recorded authorization control used the existing staging reviewer workload
identity: token acquisition succeeded, but memory list returned HTTP 403.
An authorized operator read the seeded entry as the positive control.
This is caller/project-role denial, not per-agent ACL enforcement.
Do not change RBAC or expose workload tokens to repeat it. Inspect the
[recorded evidence](../showcase-evidence.md#verified-isolated-memory) instead.

Memory TTL is not Cosmos DB retention. Memory is not the authoritative quote
state or audit trail. Hosted-agent memory attachment needs a separate runtime
compatibility check.

## Completion evidence

* Retain registration and attachment evidence separately from actual consumption.
* Record native response ID, immutable skill version, instruction hash and
  bilingual output checks, or the exact failure.
* Retain positive and cross-scope negative results in both directions.
* Distinguish the recorded caller-role 403 from scope partitioning and note
  the one-hour expiry; reseed before a live demo.
* Explain why namespace isolation never grants approval or caller authorization.

Keep evidence under git-ignored `.local`; no teardown is required. Continue to
[Lab 18: Native Evaluation and Trace Replay](lab-18-native-evaluation-traces.md).
