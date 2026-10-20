---
layout: default
title: Operations
description: Safe operation and troubleshooting of the retained synthetic demo environments.
---

[Architecture](../architecture.md) | [Architecture FR](../fr/architecture.md) |
[Native runbook](../native-showcase.md) | [Guide natif FR](../fr/native-showcase.md)

## Retained environment

Release [39424857559](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/runs/39424857559)
is the current verified baseline: staging v5, production v6, source `01af1fb`.
Both environments are retained without teardown. Home contains actual app and
Foundry links; `-poc` identifies production.

Before a customer demo:

1. Open the current Home deployment links and the authenticated Foundry project.
2. Sign into chat as an authorized pilot and the reviewer app as an employee
   with `Reviewer` and `Review.Access`. Keep those identity boundaries distinct.
3. Submit one known synthetic case, then inspect the shared pending-review case.
   Repeated invocation can hit the documented case lifecycle/duplicate guard.
   Do not clear the entire queue merely to obtain a fresh screenshot.
4. Verify the bilingual applicant acknowledgement contains no premium amount.
   The employee view legitimately contains the calculation snapshot.
5. Use [CASE-SYN-005](../../data/synthetic/fixtures/case-syn-005-missing-plan.json)
   to explain missing information: calculation `INCOMPLETE`, null amount,
   `MISSING_PLAN`, stored workflow `PENDING_REVIEW`.
6. For memory recall, run [Lab 17](../labs/lab-17-native-skills-memory.md) with
   the existing `showcase-synthetic-memory` store. Markers expire after one hour.
   Expired markers are not evidence of an application regression.
7. Use [Lab 18](../labs/lab-18-native-evaluation-traces.md) for real trace export
   and synthetic replay. Never invent ingestion when a query is empty.

## Troubleshooting by boundary

| Symptom | Check | Do not infer |
| --- | --- | --- |
| Protected route returns 401 | Entra session, audience, scope, role or pilot group | Health endpoint success proves authorization |
| Chat healthy but no agent answer | Foundry deployment readiness, server identity, Responses request | Frontend build rolls out the agent |
| Agent persistence fails | Actual hosted identity and Cosmos data role; readiness evidence | Provisioning identity equals runtime identity |
| Missing custom stages | SDK dependency operation IDs and ingestion delay | Platform root ID must contain SDK spans |
| Native judge incomplete | All expected cases, three criteria, service errors | Advisory scores allow missing evidence |
| Memory marker absent | Existing store, correct namespace and one-hour TTL | Memory is attached to the quote agent |
| Reviewer conflict | Refresh case revision and respect ETag concurrency | Retry stale approval without reviewing changes |
| Wiki live links unchanged | New release artifacts may be absent | Documentation publication redeployed Azure |

## Safe changes

Use an issue-linked feature branch and required checks. Obtain approval for
the exact runtime source before manual release. Production has its own
protected environment approval. Do not bypass it.

The release workflow builds MCP and reviewer images and promotes their pinned
digests. Chat application updates are separate; image build workflows alone
do not roll out Container Apps. Secretless Azure OIDC avoids persisting Azure
client secrets. Wiki publication still requires a scoped `WIKI_PUSH_TOKEN`;
do not copy any credential into documentation or screenshots.

Full teardown, network rebuild teardown and reviewer teardown workflows are
manual destructive tools, not demo preparation. Reviewer queue clearing is
also destructive and requires typed `CLEAR ALL CASES`. Do not run either
without an explicit operational need and approval.

## Local and native procedures

Use the [root quick start](../../README.md), [infrastructure guide](../../infra/README.md)
and paired [labs](../index.md). Native execution commands remain in the
[English runbook](../native-showcase.md) and [French runbook](../fr/native-showcase.md)
so the wiki does not maintain a divergent copy.
The native SDK platform contract is documented by
[Microsoft](https://learn.microsoft.com/azure/ai-foundry/agents/concepts/hosted-agents).
