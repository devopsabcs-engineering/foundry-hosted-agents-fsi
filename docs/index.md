---
layout: default
title: Home
description: Bilingual hands-on workshop hosting a synthetic auto-insurance quote-preparation agent on Microsoft Foundry Hosted Agents.
nav_order: 0
permalink: /
---

> 🇫🇷 **[Version française](fr/)**

Welcome to the **Foundry Hosted Agents Workshop for Financial Services**, a
bilingual, hands-on workshop adapted from the
[`foundry-hosted-agents`](https://github.com/devopsabcs-engineering/foundry-hosted-agents)
repository. You will build and host a synthetic Ontario auto-insurance
quote-preparation agent on Microsoft Foundry Hosted Agents, backed by
read-only MCP tool servers, a deterministic calculator, and a mandatory
employee-approval gate before any applicant-facing preview.

> [!IMPORTANT]
> Every fixture, rulebook, and calculator output in this workshop is
> synthetic and non-binding. Nothing here represents an actual Desjardins
> product, rate, or policy, and no regulator or insurer has reviewed or
> endorsed this material.

## What you will build

You will provision read-only application and rulebook MCP services, deploy
a hosted LangGraph agent that validates a synthetic case ID and reads its
fixture, then run a deterministic calculator and persist a draft for employee
review. The applicant channel returns bounded bilingual messages without
amounts or reviewer-only fields. The separate bilingual reviewer application
reads calculation snapshots and records authorized employee decisions.

## Architecture and boundaries

Read the [architecture](architecture.md) for the three graph stages, local
versus hosted MCP transport, private Cosmos persistence, and separate chat and
reviewer authorization. Calculation and draft persistence occur inside
`COMPOSITION`, not as extra graph stages. Native File Search, skill and memory
exercises use isolated operator runtimes; they are not automatically attached
to the quote agent.

## Learner path

The default path through these labs does not require GitHub Copilot or any
other AI coding assistant. Where workshop authors used AI-assisted tooling
to help draft or review labs, that assistance is disclosed in the affected
file rather than implied as part of the learner experience.

## Labs

For the retained Azure demo and session-2 follow-ups, see the
[native Foundry showcase](native-showcase.md).

The [release evidence](showcase-evidence.md#current-approved-release) records
the approved staging v6/production v7 release and keeps historical failures
separate from current checks. The full curriculum lives in [Labs](labs/):
local foundations 00–09, controlled pilot surfaces 10–14, and isolated native
exercises 15–18. Keep the retained environments deployed.

Continue with the [evaluation engineering guide](evaluation-guide.md) and
[Lab 19](labs/lab-19-evaluation-engineering.md): ten exercises covering
deterministic versus stochastic testing, the Foundry portal and SDK, independent
datasets, judge calibration, uncertainty and stateful non-regression.
The [34-slide English deck](assets/decks/foundry-evaluation-engineering-en.pptx)
and [French deck](assets/decks/foundry-evaluation-engineering-fr.pptx)
include instructor notes for the 3–4 hour session.
