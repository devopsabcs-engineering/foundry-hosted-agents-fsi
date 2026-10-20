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
The memory exercise is conditional on separately approved compatible chat and
embedding deployments; current staging has only its chat deployment.

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

## Exercise 17.3: Identify the memory prerequisite limit

Inspect `preflight.json` and list available deployment names. Compare them with
the memory command's required chat and embedding inputs:

```powershell
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint memory-create --help
```

Current staging has no compatible embedding deployment for this path, so native
memory is not live-verified. Record this as blocked by prerequisites, not as a
passing or failing isolation result. Listing models or reading CLI help does
not prove memory operation. Do not substitute a chat model for embeddings.

## Exercise 17.4: Test namespaces only after prerequisites are approved

Skip these live commands unless compatible deployments have already been
approved and provisioned. Replace both placeholders with their exact deployment
names. Use an isolated synthetic store and a one-hour default TTL:

```powershell
$chat = '<supported-memory-chat-deployment>'
$embedding = '<supported-embedding-deployment>'
$store = 'showcase-synthetic-memory'
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\memory-create.json" memory-create --store $store --chat-model $chat --embedding-model $embedding --ttl-seconds 3600
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\alice-seed.json" memory-seed --store $store --scope fixture-alice
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\bob-seed.json" memory-seed --store $store --scope fixture-bob
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\memory-contents.json" memory-list --store $store --scope fixture-alice
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\memory-isolation.json" memory-search --store $store --scope fixture-alice
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

Memory TTL is not Cosmos DB retention. Memory is not the authoritative quote
state or audit trail. Hosted-agent memory attachment needs a separate runtime
compatibility check.

## Completion evidence

* Retain registration and attachment evidence separately from actual consumption.
* Record native response ID, immutable skill version, instruction hash and
  bilingual output checks, or the exact failure.
* Record memory as prerequisite-blocked on current staging. Only if approved
  prerequisites exist, retain both positive and negative retrieval evidence.
* Explain why namespace isolation never grants approval or caller authorization.

Keep evidence under git-ignored `.local`; no teardown is required. Continue to
[Lab 18: Native Evaluation and Trace Replay](lab-18-native-evaluation-traces.md).
