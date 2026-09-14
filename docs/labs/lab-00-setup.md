---
permalink: /labs/lab-00-setup
title: "Lab 00 - Setup"
description: "Create a Python virtual environment, install every component's dependencies, and confirm the existing test suites pass."
---

> 🇫🇷 **[Version française](../fr/labs/lab-00-setup)**

> [!IMPORTANT]
> Every fixture, rulebook, and calculator output in this lab is synthetic and non-binding. Nothing here represents an actual Desjardins product, rate, or policy, and no regulator or insurer has reviewed or endorsed this material.

## Overview

| Item | Value |
| --- | --- |
| **Duration** | 20 minutes |
| **Level** | Beginner |
| **Prerequisites** | None |

## Learning Objectives

By the end of this lab, you will be able to:

* Create a Python virtual environment for this workshop
* Install the dependencies for the calculator, the approval repository, both MCP servers, and the LangGraph agent
* Run the existing pytest suites as a sanity check before touching any code
* Locate the synthetic-only, non-binding disclosure you will see repeated in every lab

## Exercises

### Exercise 0.1: Confirm Python and Clone the Repository

This workshop targets Python 3.11 or newer.

```powershell
python --version
git clone https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi.git
cd foundry-hosted-agents-fsi
```

If you already have the repository open, skip the clone step and confirm you are at the repository root before continuing.

### Exercise 0.2: Create a Virtual Environment and Install Dependencies

Each component keeps its own `requirements.txt`. Install all four so the calculator, both MCP servers, and the agent are available in the same environment.

```powershell
python -m venv .venv
./.venv/Scripts/Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r mcp/application-server/requirements.txt
python -m pip install -r mcp/rulebook-server/requirements.txt
python -m pip install -r src/quote-preparation-agent/requirements.txt
```

The root `requirements.txt` covers `pytest` and `jsonschema`, used by the calculator and approval-repository tests in `apps/workshop/`.

### Exercise 0.3: Run the Existing Test Suites

Before making any change, confirm the repository's own tests pass in your environment.

```powershell
python -m pytest apps/workshop mcp src/quote-preparation-agent -q
```

Expected result: every test passes, with no failures. The exact count grows as later labs and phases add tests; do not compare it against a fixed number.

> [!TIP]
> None of these tests call Azure, a language model, or the network. They run entirely against the fixtures in `data/synthetic/` and a compiled LangGraph state machine, so they are a fast way to confirm your Python environment is correct before Lab 01.

### Exercise 0.4: Find the Disclosure Language

Open [README.md](../../README.md) and [docs/index.md](../index.md). Locate the paragraph that states every fixture, rulebook, and calculator output is synthetic and non-binding, with no regulatory review or endorsement. You will see the same statement, or a close variant of it, at the top of every remaining lab.

## Validation Checklist

* [ ] `python -m venv .venv` completed and the environment activates without error
* [ ] All four `requirements.txt` files installed without error
* [ ] `pytest apps/workshop mcp src/quote-preparation-agent -q` reports zero failures
* [ ] You located the synthetic-only, non-binding disclosure in README.md or docs/index.md

## Knowledge Check

* Why does this workshop keep a separate `requirements.txt` for each MCP server and the agent instead of one shared file?
* Which three top-level directories did the test command in Exercise 0.3 cover?

## Next Steps

Continue to [Lab 01: Fixtures and Schema](lab-01-fixtures-schema.md).
