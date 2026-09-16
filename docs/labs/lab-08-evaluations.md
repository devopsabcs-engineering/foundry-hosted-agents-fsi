---
permalink: /labs/lab-08-evaluations
title: "Lab 08 - Evaluation Suite"
description: "Explore the golden dataset and deterministic checks that gate arithmetic, approval, and language-parity behavior."
---

> 🇫🇷 **[Version française](../fr/labs/lab-08-evaluations)**

> [!IMPORTANT]
> Every fixture, rulebook, and calculator output in this lab is synthetic and non-binding. Nothing here represents an actual Desjardins product, rate, or policy, and no regulator or insurer has reviewed or endorsed this material.

## Overview

| Item | Value |
| --- | --- |
| **Duration** | 30 minutes |
| **Level** | Intermediate |
| **Prerequisites** | [Lab 02](lab-02-calculator.md) |

## Learning Objectives

By the end of this lab, you will be able to:

* Locate the paired English/French golden dataset and the deterministic evaluation gate
* Name the categories the evaluation gate is designed to check: arithmetic, evidence, approval-state correctness, injection resistance, missing-data handling, case isolation, and language parity
* Run the evaluation gate against this repository's implementation
* Write your own small deterministic check that mirrors the arithmetic category, scoped to what you built in Labs 01-02

## Exercises

### Exercise 8.1: Locate the Evaluation Artifacts

```powershell
Test-Path eval/golden-dataset.jsonl
Test-Path eval/evaluation_gate.py
```

Expected result: both paths return `True`. `eval/` holds the paired EN/FR golden dataset and the evaluation gate that checks it against this project's calculator, approval repository, and MCP servers.

### Exercise 8.2: Run the Evaluation Gate

```powershell
python eval/evaluation_gate.py
```

Expected result: the gate reports every required check passing and writes a machine-readable copy of the same report to `eval/results.json`. The gate takes no command-line arguments; the dataset path (`eval/golden-dataset.jsonl`) is fixed in `eval/deterministic-tests/checks.py`. The gate is designed so a quality judge can never override an arithmetic or approval-state failure; a missing or skipped required case fails the run outright.

### Exercise 8.3 (Hands-on): Write Your Own Arithmetic Check

You can write the same kind of check the evaluation gate performs for arithmetic, scoped to the fixtures from Lab 01.

```powershell
python -c "
import json, pathlib, sys
sys.path.insert(0, 'apps/workshop')
from calculator import calculate_quote

failures = []
for path in sorted(pathlib.Path('data/synthetic/fixtures').glob('*.json')):
    fixture = json.loads(path.read_text())
    actual = calculate_quote(fixture['input'], fixture['rulebook'])
    expected = fixture['expectedCalculation']
    if actual != expected:
        failures.append((path.name, actual, expected))

if failures:
    for name, actual, expected in failures:
        print(f'MISMATCH {name}: actual={actual} expected={expected}')
else:
    print(f'All fixtures matched their expectedCalculation.')
"
```

Expected result: every fixture matches its `expectedCalculation` exactly, printing a single confirmation line.

## Validation Checklist

* [ ] You located `eval/golden-dataset.jsonl` and `eval/evaluation_gate.py`
* [ ] `python eval/evaluation_gate.py` reported every required check passing
* [ ] Your Exercise 8.3 check confirms `calculate_quote` matches `expectedCalculation` for every fixture
* [ ] You can name the seven categories the full evaluation gate is designed to cover

## Knowledge Check

* Why must a quality judge never be allowed to override an arithmetic or approval-state failure in this gate?
* Which fault categories, beyond arithmetic, does the golden dataset need at minimum to cover missing data and an unauthorized approval attempt?

## Next Steps

Continue to [Lab 09: Teardown](lab-09-teardown.md).
