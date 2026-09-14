---
title: Foundry Hosted Agents Workshop - Financial Services (FSI)
description: Bilingual hands-on workshop adapting Microsoft Foundry hosted agents to a synthetic Ontario auto-insurance quote-preparation scenario with a deterministic calculator and a mandatory employee-approval gate.
---

## Overview

This repository is a bilingual (English/French) hands-on workshop adapted
from the sibling
[`foundry-hosted-agents`](https://github.com/devopsabcs-engineering/foundry-hosted-agents)
repository. It replaces that repository's airline threat-assessment
scenario with a financial-services scenario: a synthetic Ontario
auto-insurance quote-preparation agent, backed by a deterministic
calculator and a mandatory, separately persisted employee-approval gate
before any applicant-facing preview.

> [!IMPORTANT]
> Every fixture, rulebook, and calculator output in this repository is
> synthetic and non-binding. Nothing here represents an actual Desjardins
> product, rate, or policy, and no regulator or insurer has reviewed or
> endorsed this workshop.

## Learner path

The default path through these labs does not require GitHub Copilot or any
other AI coding assistant. Where workshop authors used AI-assisted tooling
to help draft or review content, that assistance is disclosed in the
affected lab or file rather than implied as part of the learner
experience.

## Repository layout

* `docs/` holds the English workshop site (Jekyll, Just the Docs theme);
  start at [docs/index.md](docs/index.md).
* `docs/fr/` holds the French workshop site, structurally paired with
  `docs/`; start at [docs/fr/index.md](docs/fr/index.md).
* `src/quote-preparation-agent/` will hold the hosted LangGraph
  quote-preparation agent.
* `mcp/application-server/` will hold a read-only MCP service exposing
  synthetic application data.
* `mcp/rulebook-server/` will hold a read-only MCP service exposing
  synthetic rulebook data.
* `apps/workshop/` will hold the deterministic calculator, approval
  repository, and applicant/reviewer views.
* `data/synthetic/` will hold the synthetic fixtures and JSON Schema for
  the quote-preparation contract.
* `eval/` will hold the evaluation harness for arithmetic, approval,
  injection, and bilingual-parity checks.
* `infra/` will hold Bicep infrastructure modules, author-only until
  platform and regulatory review gates clear.
* `scripts/` will hold shared helpers, including the bilingual
  workshop-deck generator.

## Getting started

Start at the workshop landing page: [docs/index.md](docs/index.md) in
English, or [docs/fr/index.md](docs/fr/index.md) in French.