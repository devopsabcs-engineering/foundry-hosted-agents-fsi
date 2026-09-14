---
permalink: /labs/lab-02-calculator
title: "Lab 02 - The Deterministic Calculator"
description: "Trace the pure calculate_quote function and prove it never invents an amount for input it cannot resolve."
---

> 🇫🇷 **[Version française](../fr/labs/lab-02-calculator)**

> [!IMPORTANT]
> Every fixture, rulebook, and calculator output in this lab is synthetic and non-binding. Nothing here represents an actual Desjardins product, rate, or policy, and no regulator or insurer has reviewed or endorsed this material.

## Overview

| Item | Value |
| --- | --- |
| **Duration** | 30 minutes |
| **Level** | Intermediate |
| **Prerequisites** | [Lab 01](lab-01-fixtures-schema.md) |

## Learning Objectives

By the end of this lab, you will be able to:

* Trace `calculate_quote`'s resolution order in `apps/workshop/calculator.py`: unavailable rulebook, version mismatch, missing fields, unsupported values, then a ready result
* State the four calculation statuses the calculator can return
* Add a new test case and confirm it passes
* Prove that a rulebook lookup miss produces an issue code, never an invented amount

## Exercises

### Exercise 2.1: Read the Resolution Order

Open `apps/workshop/calculator.py` and read `calculate_quote` top to bottom. Note the order the function checks conditions in:

1. `rulebook is None` returns `EVIDENCE_UNAVAILABLE`
2. A rulebook version mismatch (when `expected_rulebook_version` is supplied) returns `EVIDENCE_UNAVAILABLE` with `RULE_VERSION_MISMATCH`
3. Any missing `jurisdiction`, `vehicleClass`, or `plan` returns `INCOMPLETE` with one issue per missing field
4. A jurisdiction other than `ON`, or a `vehicleClass`/`plan` absent from the rulebook's `baseCents`/`planAddOnCents` tables, returns `UNSUPPORTED`
5. Otherwise, the function sums `baseCents[vehicleClass] + planAddOnCents[plan]` and returns `READY`

### Exercise 2.2: Run the Existing Tests

```powershell
python -m pytest apps/workshop/tests/test_calculator.py -v
```

Expected result: every test passes, including one asserting `case-syn-001`'s exact 100000-cent result.

### Exercise 2.3 (Hands-on): Add a New Test Case

Add a test to `apps/workshop/tests/test_calculator.py` asserting that a `SEDAN` vehicle with the `TRAINING_BASIC` plan resolves to exactly 90000 cents, using the same rulebook shape as the existing tests. Run the file again and confirm your new test passes alongside the existing ones.

### Exercise 2.4 (Hands-on): Prove the No-Invented-Amount Rule

In a Python shell, build a rulebook dictionary copied from `data/synthetic/rulebook.json`, remove the `"SEDAN"` key from `baseCents`, then call `calculate_quote` with a `SEDAN` input against that modified rulebook.

```powershell
python -c "
import json, pathlib, sys
sys.path.insert(0, 'apps/workshop')
from calculator import calculate_quote

rulebook = json.loads(pathlib.Path('data/synthetic/rulebook.json').read_text())
del rulebook['baseCents']['SEDAN']
result = calculate_quote({'jurisdiction': 'ON', 'vehicleClass': 'SEDAN', 'plan': 'TRAINING_BASIC'}, rulebook)
print(result)
"
```

Expected result: `status` is `UNSUPPORTED`, `amountCents` is `null`, and `issues` contains `UNSUPPORTED_INPUT`. No amount is returned, even though `TRAINING_BASIC` is a recognized plan.

## Validation Checklist

* [ ] `pytest apps/workshop/tests/test_calculator.py -v` passes, including your Exercise 2.3 test
* [ ] You can list the four calculation statuses from memory
* [ ] Exercise 2.4 confirms a missing rulebook entry returns `UNSUPPORTED_INPUT`, never an amount
* [ ] You can explain, without looking at the code, why the rulebook-availability check runs before the missing-field check

## Knowledge Check

* Why does the calculator check for a missing rulebook before it checks for missing input fields?
* What currency and period does every `READY` result carry, and where do those values come from?

## Next Steps

Continue to [Lab 03: Approval Repository and State Machine](lab-03-approval-repository.md).
