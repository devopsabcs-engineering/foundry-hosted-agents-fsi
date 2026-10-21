---
layout: default
title: Release evidence
description: Verified release outcomes and explicit limits on native showcase evidence.
---

[Current screenshots](../showcase-evidence.md) | [Captures françaises](../fr/showcase-evidence.md) |
[Native runbook](../native-showcase.md) | [Architecture](../architecture.md)

## Current approved production release

[Release 39527950931, attempt 2](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/runs/39527950931)
succeeded at approved source `2c3f13b`: staging agent v6 and production v7.
Production used the protected reviewer gate and the exact evaluated staging
reviewer/MCP digests. Chat retains its prior image. All environments remain deployed.

The [authentic bilingual production captures](../showcase-evidence.md) show
isolated `CASE-SYN-004` revision 2, corrected `TRAINING_BASIC`, current audit,
native response `resp_x17dKvgjXUeG5WiGayxga6LUnpIjYR2W6bAvDx194iEbUUHngH`,
`PENDING_REVIEW`, `READY` and `90000` cents. The returned draft stayed visible
in active and draft-filtered queues. Self-approval returned 403 `SELF_APPROVAL`.
Both actual reviewer identities passed invocation200/memory403, first attempt.
No queue was cleared and benchmark cases were not corrected.

Release checks passed 565 offline tests with 50 conditional skips and the
13/13 deterministic gate. Both native locale runs completed all five cases
with 100% on all three criteria and no errors:

* English: `evalrun_985de95ac8e742be88c6172d8a4098d6`
* French: `evalrun_db159f558fd847668d7bba275ba1a353`

Attempt 1 had native service errors with no scored items; those remain failed
evidence. Retrying only the failed evaluation job at the same source succeeded
before promotion. This is neither a weakened gate nor a same-dataset claim
against the historical 0/10 benchmark.

## Earlier revision workflow staging proof

Authenticated [English and French captures](../showcase-evidence.md) show
`CASE-SYN-004` revision 2 after a genuine native-agent preparation:
`TRAINING_BASIC`, `READY`, `90000` cents and `PENDING_REVIEW`, with current
corrections, response ID and audit. The case remained visible when returned
to draft. Self-approval returned 403; the real reviewer identity returned
invocation 200 and memory denial 403 under `Foundry Agent Consumer`.

Source `cf2d003` supplied this live business-flow proof. PR #34 makes the
working role declarative and gates both environments on workload identity
controls. Release 39523315263 reached healthy staging but stopped on a Linux
CLI terminal requirement; PR #36 corrects that CI-only problem.
These earlier observations alone did not establish production promotion;
the successful corrected release is recorded above.

## Historical full-release checkpoint

| Evidence | Verified result | Boundary |
| --- | --- | --- |
| [Release 39424857559](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/runs/39424857559) | Successful staging v5 and protected production v6 | Exact approved runtime source `01af1fb` |
| Live applicant benchmark | Five English and five French cases, all three criteria, no service errors | Bounded current messages; not historical same-dataset remediation |
| Independent endpoint regression | Four bilingual/no-amount cases per environment | Staging and production exercised separately |
| App checks | Both chat and reviewer health/config/anonymous protected routes | Does not replace authenticated business-flow evidence |
| Native memory | Create, seed, list/search, cross-namespace controls | Isolated operator store, one-hour TTL |
| Memory authorization | Existing reviewer identity receives HTTP 403 | Namespace separation is not an authorization test |
| Custom trace export | Nine actual SDK spans across three expected stages | Sanitized dependency spans, not fabricated portal rows |
| Native synthetic replay | One trace-derived case passes three criteria | Synthetic case replay with provenance, not raw prompt recovery |
| Main after PR #21 | 480 tests passed, 36 conditional skips; deterministic 13/13 | Offline CI, not live availability |
| Documentation publication | Four original native pages and 18 PNG assets verified against wiki | Subsequent docs expand maintained publication |

## Read the evidence in order

1. Open the release run and inspect the staging evaluation and production jobs.
2. Use [Home](home.md) for deployment links generated from actual artifacts.
3. Compare [current authenticated playground captures](../showcase-evidence.md)
   with the displayed agent versions. Historical v3/v4/v5 images are retained
   and labeled, not silently relabeled as the latest production.
4. Consult [Lab 11](../labs/lab-11-web-chat.md) for authenticated chat and
   [Lab 18](../labs/lab-18-native-evaluation-traces.md) for benchmark provenance.
   [Labs 15-18](../index.md) cover isolated native functionality.
5. Treat current memory marker absence after TTL as expected expiry. Reseed
   the existing store rather than recreating it.
6. Distinguish an empty trace query from proof of no telemetry. The SDK stage
   operation and platform request operation can differ.

## Claims intentionally not made

Historical native RAG negative controls failed and remain failed evidence.
The older judge 0/10 run is retained; the newer applicant-specific benchmark
does not prove a same-dataset quality improvement.
Foundry IQ, optional Content Understanding model setup and a completed
red-team execution are not implied by successful File Search, Document
Intelligence extraction or prepared red-team fixtures.

The quote graph does not call a generative model for pricing, automatically
consume the project-authored skill, attach the memory store or invoke the
Foundry toolbox gateway. A successful operator demonstration is not an
automatic runtime integration.

Screenshots are authentic observations, not continuous monitoring. Docs and
wiki publication cannot establish current service health without a live check.
See [Microsoft Foundry](https://learn.microsoft.com/azure/ai-foundry/agents/concepts/hosted-agents)
for the hosted platform contract.
