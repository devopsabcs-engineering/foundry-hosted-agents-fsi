---
permalink: /labs/lab-01-fixtures-schema
title: "Lab 01 - Fixtures and Schema"
description: "Explore the synthetic quote-preparation fixtures and the draft-07 JSON Schema that binds their calculation and workflow shapes."
---

> 🇫🇷 **[Version française](../fr/labs/lab-01-fixtures-schema)**

> [!IMPORTANT]
> Every fixture, rulebook, and calculator output in this lab is synthetic and non-binding. Nothing here represents an actual Desjardins product, rate, or policy, and no regulator or insurer has reviewed or endorsed this material.

## Overview

| Item | Value |
| --- | --- |
| **Duration** | 20 minutes |
| **Level** | Beginner |
| **Prerequisites** | [Lab 00](lab-00-setup.md) |

## Learning Objectives

By the end of this lab, you will be able to:

* Describe the five synthetic fixtures in `data/synthetic/fixtures/` and the calculation status each one produces
* Explain how `data/synthetic/quote-contract.schema.json` uses `if`/`then`/`else` to tie a calculation's status to its `amountCents` and `issues` fields
* Explain how the schema ties a case's workflow state to its `approvedRevision` field
* Validate every fixture against the schema yourself

## Exercises

### Exercise 1.1: Read the Fixture Set

Open each file in `data/synthetic/fixtures/` and note its `fixtureId`, `input`, and `expectedCalculation.status`:

| Fixture | Vehicle class | Plan | Expected status |
| --- | --- | --- | --- |
| case-syn-001.json | COMPACT | TRAINING_EXTENDED | READY (100000 cents) |
| case-syn-002-sedan.json | SEDAN | TRAINING_BASIC | READY |
| case-syn-003-unsupported.json | UNKNOWN | TRAINING_BASIC | UNSUPPORTED |
| case-syn-004-revision.json | SEDAN | TRAINING_EXTENDED | READY (draftRevision 2) |
| case-syn-005-missing-plan.json | COMPACT | null | INCOMPLETE |

Every fixture carries `"dataClass": "SYNTHETIC_ONLY"` and the same `RULEBOOK-SYN-ON` rulebook, pinned at `"authority": "WORKSHOP_AUTHORS_ONLY"`.

### Exercise 1.2: Read the Schema's Conditional Logic

Open `data/synthetic/quote-contract.schema.json` and find the `calculation` definition's `if`/`then`/`else` block. When `status` is `READY`, the schema requires a populated `amountCents`, exactly three `ruleIds`, and zero `issues`. For any other status, it requires a null `amountCents` and at least one issue code. Find the equivalent rule for `workflow`: an `APPROVED` state requires a non-null `approvedRevision`, while every other state requires it to be null.

### Exercise 1.3: Validate the Fixtures Against the Schema

```powershell
python -c "
import json, pathlib
from jsonschema import validate

schema = json.loads(pathlib.Path('data/synthetic/quote-contract.schema.json').read_text())
for path in sorted(pathlib.Path('data/synthetic/fixtures').glob('*.json')):
    fixture = json.loads(path.read_text())
    validate(instance=fixture, schema=schema)
    print(f'{path.name}: OK')
"
```

Expected result: every fixture prints `OK`, with no `ValidationError` raised.

### Exercise 1.4 (Hands-on): Explain the Unsupported and Revision Cases

Answer, in your own words, using only the fixture content and the schema:

1. Why does `case-syn-003-unsupported.json` produce `UNSUPPORTED` instead of `INCOMPLETE`, even though every input field is present?
2. `case-syn-004-revision.json` has `draftRevision: 2`. What does that tell you about this case's history, and why would the schema reject `draftRevision: 2` paired with `approvedRevision: null` if the workflow state were `APPROVED`?

## Validation Checklist

* [ ] You can name all five fixtures and the calculation status each is expected to produce
* [ ] The Exercise 1.3 script prints `OK` for every fixture with no validation error
* [ ] You can explain why an unknown vehicle class produces `UNSUPPORTED` rather than a missing-field issue
* [ ] You can explain the schema's `APPROVED` requires `approvedRevision` rule from Exercise 1.2

## Knowledge Check

* Which fixture is designed to exercise revision invalidation, and which field number changed to signal it?
* What value does `rulebook.authority` carry on every fixture, and why does that matter for a learner reading this data?

## Next Steps

Continue to [Lab 02: The Deterministic Calculator](lab-02-calculator.md).
