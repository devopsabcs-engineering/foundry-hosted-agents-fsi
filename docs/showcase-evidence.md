---
layout: default
title: Native showcase evidence
description: Recorded native generation recovery, running demo versions and authentic application screenshots.
---

[Français](fr/showcase-evidence.md) | [Native runbook](native-showcase.md) | [Labs](labs/index.md)

## Release status

Evidence collected on 2026-10-20 UTC. The environments remain deployed.
The latest merged source is `349f6ed3abe783c99f457c8f6d5d5b56b3122726`.
Its image-publication workflows succeeded, but this is not proof of runtime
deployment. Direct project SDK queries still return staging agent version 2
and production agent version 3. The last verified full deployment is
[39293980605, attempt 2](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/runs/39293980605).
The latest source has **not** been verified as deployed.

| Runtime | Running image digest | Ready revision |
| --- | --- | --- |
| Staging chat | `sha256:ccfab1bc368463602c5b5f85cc6b93cde242e9a03c7b3000a6cf8cee007fce70` | `foundry-quote-chat-staging--p5occpg` |
| Production chat | Same chat digest | `foundry-quote-chat--zdpiuid` |
| Staging reviewer | `sha256:5882f2e3ef0ff0884b53387e10a981d7f5591e7c23a8229bc038afad151d1b01` | `foundry-quote-reviewer-staging--0000002` |
| Production reviewer | Same reviewer digest | `foundry-quote-reviewer--k1qw0tn` |

The remaining rollout needs recorded release approvals and the unchanged
GitHub production review gate. No role grant, authentication bypass, new Search
service, embedding deployment or environment teardown was performed.

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

These captures show the deployed, signed-out application boundaries, not an
authenticated conversation, reviewer action or latest-source rollout.
They contain no applicant data or tokens.

### Staging applicant chat

Captured at `2026-10-20T01:22Z` from the
[live staging chat](https://foundry-quote-chat-staging.victorioussand-be863134.eastus2.azurecontainerapps.io).

![Deployed staging chat requires Microsoft sign-in and disables message input before authentication](assets/evidence/staging-chat-en.png)

### Production employee reviewer

Captured at `2026-10-20T01:22Z` from the
[live production reviewer](https://foundry-quote-reviewer.gentleplant-e170129b.eastus2.azurecontainerapps.io).

![Deployed production reviewer requires Microsoft sign-in before employee actions](assets/evidence/production-reviewer-en.png)

### Foundry portal screenshots still pending

The integrated browser is signed out of Foundry. API evidence above is genuine,
but it must not be presented as a portal screenshot. Share an authenticated
project tab to capture generation jobs, indexed files, skill versions,
evaluation runs and traces without exposing account details.

## Native quality boundaries

The native File Search demonstration verified six cited answers and two exact
`OUT_OF_CORPUS` refusals. It uses the reviewed EN/FR corpus, not Foundry IQ and
not a new hosted-agent attachment. The runtime skill was actually consumed by
an isolated operator runtime in both language orders.

The retrieval evaluator distinguished relevant and irrelevant controls, 5/1.
Groundedness v18 and groundedness_pro v8 accepted a known bad scope/authorization
answer; their negative-control comparison gates therefore failed. These are
documented judge limitations, not an optimization success. Local trace export
received HTTP 403; exporter flush was not treated as ingestion evidence.

See the [native runbook](native-showcase.md) and
[Microsoft Foundry documentation](https://learn.microsoft.com/azure/ai-foundry/)
for the capability boundaries and reproducible commands.
