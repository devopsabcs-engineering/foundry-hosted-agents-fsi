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
a hosted LangGraph agent that gathers a quote request and hands it to a
deterministic calculator, and enforce a separately persisted approval step
so an employee, not the model, decides whether a draft can reach the
applicant.

## Learner path

The default path through these labs does not require GitHub Copilot or any
other AI coding assistant. Where workshop authors used AI-assisted tooling
to help draft or review labs, that assistance is disclosed in the affected
file rather than implied as part of the learner experience.

## Labs

The full lab curriculum lives in [Labs](labs/).
