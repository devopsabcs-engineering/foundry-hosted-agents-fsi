<!-- markdownlint-disable-file -->
# RPI Validation: Desjardins Bilingual Hosted Agents Workshop — Phase 2

**Plan**: [.copilot-tracking/plans/2026-09-13/desjardins-bilingual-hosted-agents-workshop-plan.instructions.md](../../../plans/2026-09-13/desjardins-bilingual-hosted-agents-workshop-plan.instructions.md)
**Changes Log**: [.copilot-tracking/changes/2026-09-13/desjardins-bilingual-hosted-agents-workshop-changes.md](../../../changes/2026-09-13/desjardins-bilingual-hosted-agents-workshop-changes.md)
**Research**: [.copilot-tracking/research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md](../../../research/2026-09-13/desjardins-bilingual-hosted-agents-workshop-research.md)
**Details**: [.copilot-tracking/details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md](../../../details/2026-09-13/desjardins-bilingual-hosted-agents-workshop-details.md)
**Planning Log**: [.copilot-tracking/plans/logs/2026-09-13/desjardins-bilingual-hosted-agents-workshop-log.md](../../../plans/logs/2026-09-13/desjardins-bilingual-hosted-agents-workshop-log.md)
**Phase Validated**: `### [x] Implementation Phase 2: Synthetic Fixtures, JSON Schema, and Deterministic Calculator`
**Validation Date**: 2026-09-13

## Scope

Phase 2 has three checklist items:

* Step 2.1: Author the synthetic fixture set and JSON Schema (draft-07) for the quote-preparation contract.
* Step 2.2: Implement the pure deterministic calculator and its unit tests.
* Step 2.3: Validate phase changes (run calculator unit tests; validate every fixture against the JSON Schema).

## Plan Item vs. Changes Log Comparison

| Plan item | Changes log evidence | Match |
| --- | --- | --- |
| Step 2.1 — fixture set + draft-07 schema | "Added" section: `data/synthetic/quote-contract.schema.json`, `data/synthetic/rulebook.json`, 5 fixtures under `data/synthetic/fixtures/` | Yes |
| Step 2.2 — pure calculator + unit tests | "Added" section: `apps/workshop/calculator.py`, `apps/workshop/__init__.py`, `apps/workshop/tests/__init__.py`, `apps/workshop/tests/test_calculator.py`, `requirements.txt` | Yes |
| Step 2.3 — validate phase changes | Release Summary: "pytest ... → 49 passed" (aggregate, includes Phase 2); no phase-2-specific validation output recorded in the changes log itself | Partially — see Minor-1 |

## File-Level Verification

All files below were opened directly and checked against the plan/details/research intent.

### Schema — [data/synthetic/quote-contract.schema.json](../../../../data/synthetic/quote-contract.schema.json)

* Byte-for-byte match (modulo whitespace normalization) against the draft-07 schema in [platform-and-scenario-decision-research.md](../../../research/subagents/2026-09-13/platform-and-scenario-decision-research.md) (lines ~193-368), including the `calculation.if/then/else` (READY requires non-null `amountCents`, 3 `ruleIds`, empty `issues`; all other states require null `amountCents` and ≥1 issue) and `workflow.if/then/else` (APPROVED requires non-null `approvedRevision`).
* `$schema` is `http://json-schema.org/draft-07/schema#` as required. Confirmed schema-of-schema valid via `Draft7Validator.check_schema(...)` (ran clean, no exception).
* Satisfies details Step 2.1 success criterion "Every fixture validates against quote-contract.schema.json" — verified by direct execution (see Test Execution Results below): all 5 fixtures pass.

### Rulebook — [data/synthetic/rulebook.json](../../../../data/synthetic/rulebook.json)

* Matches the research's illustrative rulebook exactly: `baseCents: {COMPACT: 80000, SEDAN: 90000}`, `planAddOnCents: {TRAINING_BASIC: 0, TRAINING_EXTENDED: 20000}`, `authority: WORKSHOP_AUTHORS_ONLY`, three rules (BASE_LOOKUP/PLAN_LOOKUP/EMPLOYEE_GATE).
* Bilingual `notice` field present (en-CA/fr-CA), matching the research's "Synthetic arithmetic" notice text verbatim.

### Fixtures — [data/synthetic/fixtures/](../../../../data/synthetic/fixtures)

| Fixture | Case covered | Expected result | Verified |
| --- | --- | --- | --- |
| case-syn-001.json | COMPACT + TRAINING_EXTENDED, ON | READY, 100000 cents (80000+20000) | Matches research's canonical CASE-SYN-001 exactly; arithmetic correct |
| case-syn-002-sedan.json | SEDAN + TRAINING_BASIC, ON | READY, 90000 cents (90000+0) | Correct; covers plan's "SEDAN, TRAINING_BASIC" requirement (combined per changes log Additional/Deviating note) |
| case-syn-003-unsupported.json | vehicleClass=UNKNOWN | UNSUPPORTED, null amount, `UNSUPPORTED_INPUT` | Correct; satisfies Step 2.1's "at least one fixture exercises the UNSUPPORTED path" |
| case-syn-004-revision.json | SEDAN + TRAINING_EXTENDED, APPROVED then REVISE | workflow.state=DRAFT, approvedRevision=null after revise; calculation READY 110000 cents (90000+20000) | Correct; satisfies "one exercises revision invalidation"; audit trail shows CREATE_DRAFT→SUBMIT→APPROVE→REVISE with draftRevision incrementing 1→2 |
| case-syn-005-missing-plan.json | plan=null | INCOMPLETE, null amount, `MISSING_PLAN` | Correct; additional coverage beyond the plan's minimum, within the details file's "1-2 more for coverage" allowance (documented in changes log) |

All 5 fixtures re-validated directly against the schema in this session (see Test Execution Results) — 5/5 valid, 0 errors.

### Calculator — [apps/workshop/calculator.py](../../../../apps/workshop/calculator.py)

* Pure function `calculate_quote(input_data, rulebook, *, expected_rulebook_version=None)`: no I/O, no LLM calls, no imports beyond stdlib typing — matches the plan/research constraint "pure calculator... no I/O, no LLM."
* Precedence order implemented: (1) `rulebook is None` → `EVIDENCE_UNAVAILABLE`; (2) rulebook version mismatch → `EVIDENCE_UNAVAILABLE`/`RULE_VERSION_MISMATCH`; (3) missing `jurisdiction`/`vehicleClass`/`plan` → `INCOMPLETE` with corresponding `MISSING_*` issue(s); (4) jurisdiction ≠ `ON` or class/plan not in rulebook tables → `UNSUPPORTED`/`UNSUPPORTED_INPUT`; (5) otherwise `READY` with `amountCents = baseCents[vehicleClass] + planAddOnCents[plan]`. This matches the research's stated precedence: "Missing fields take precedence over unsupported values; evidence retrieval failure takes precedence over calculation; all non-READY outcomes have null amounts" (verified directly in the platform subagent research, line ~182).
* Never returns a non-null `amountCents` for a non-`READY` status — enforced structurally by `_result()` defaulting `amount_cents=None` unless explicitly passed, and only the `READY` branch passes a value.
* Issue-code enum used (`MISSING_JURISDICTION`, `MISSING_VEHICLE_CLASS`, `MISSING_PLAN`, `UNSUPPORTED_INPUT`, `EVIDENCE_UNAVAILABLE`, `RULE_VERSION_MISMATCH`) matches the schema's `calculation.issues` enum exactly. The plan's illustrative names (for example `UNSUPPORTED_VEHICLE_CLASS`) were not used; this is explicitly logged in the changes log's "Additional or Deviating Changes" section as an intentional alignment with the authoritative schema — correctly flagged, not a silent deviation.

### Calculator tests — [apps/workshop/tests/test_calculator.py](../../../../apps/workshop/tests/test_calculator.py)

* Parametrized over every fixture file in `data/synthetic/fixtures/` (`test_calculator_matches_expected_calculation_for_every_fixture`), directly satisfying the details file's "test_calculator.py passes for every fixture in data/synthetic/."
* Dedicated tests for the exact 100000-cent case, the UNSUPPORTED path, the MISSING_PLAN path, the revision-invalidation fixture, and a rulebook-unavailable case (`EVIDENCE_UNAVAILABLE`) — covers every state referenced in the phase's success criteria.
* No network, database, or LLM calls anywhere in the test file (self-documented in the module docstring and confirmed by inspection — only `json`, `sys`, `pathlib`, and the calculator module are imported).

### Supporting files

* `apps/workshop/__init__.py` and `apps/workshop/tests/__init__.py` exist (both intentionally empty, standard Python package markers) — matches changes log claim.
* `requirements.txt` (repo root) contains `pytest>=8.0` and `jsonschema>=4.21`, matching the changes log's claim that this file is new and provides exactly the two packages Phase 2 needs.

## Test Execution Results (this validation session)

Executed directly against `.venv\Scripts\python.exe`, not taken from the changes log's prior claims:

* `pytest apps/workshop/tests/test_calculator.py -v --no-header -p no:cacheprovider` → **11 passed, 0 failed** (test count matches the changes log's "11 tests" claim for Phase 2).
* Direct `Draft7Validator` schema validation of all 5 files in `data/synthetic/fixtures/*.json` against `data/synthetic/quote-contract.schema.json` → **5/5 valid, 0 errors**.

Both results corroborate the aggregate "49 passed" figure reported in the changes log's Release Summary (Phase 9 sweep) and directly satisfy Step 2.3's two validation commands from the details file.

## Cross-Check Against Research Guidance

* Arithmetic constant (COMPACT + TRAINING_EXTENDED = 100000 CAD cents) — matches research verbatim, confirmed by direct calculation and test execution.
* "Missing fields take precedence over unsupported values; evidence retrieval failure takes precedence over calculation; all non-READY outcomes have null amounts" (research subagent report line ~182) — matches calculator's implemented precedence order.
* "No coercion of strings, fractions or negative cents is permitted" — the calculator performs no type coercion (uses input values as-is for dict lookups); the schema's `cents` definition (`type: integer, minimum: 0`) independently rejects non-integer/negative values at the fixture level. No dedicated calculator-level coercion-rejection test exists in Phase 2, but this is a schema-layer concern (V02 in the research's acceptance table) rather than a calculator-function concern, and is out of Phase 2's stated scope (Step 2.2 details reference only the exact/unsupported cases).
* V04/V05/V08-style calculator-boundary tests (research acceptance table) are represented: V04 (MISSING_PLAN) ≈ case-syn-005; V05 (UNSUPPORTED_INPUT) ≈ case-syn-003; V08 (EVIDENCE_UNAVAILABLE) ≈ `test_missing_evidence_never_invents_an_amount`.

## Planning Log Cross-Check

Reviewed all Discrepancy Log (DR-01, DR-02, DR-03) and Plan Deviation (DD-01) entries in the planning log: **none reference Phase 2**. DR-01/DR-02/DR-03 concern gate numbering, PDF timing conflicts, and unexpanded acronyms (none touch fixtures/schema/calculator). DD-01 concerns the ten-vs-nine lab count (Phase 6). No planning-log-flagged discrepancy applies to this phase.

The changes log's own "Additional or Deviating Changes" section documents two Phase-2-specific deviations, both already cross-checked above and found to be non-blocking, correctly disclosed adaptations:

1. Issue-code enum alignment to the schema instead of the plan's illustrative names (see Calculator section above) — verified correct and necessary for schema conformance.
2. Fixture consolidation (SEDAN+TRAINING_BASIC combined into one file) plus an added fifth fixture for MISSING_PLAN coverage, within the plan's stated "1-2 more for coverage" allowance — verified as compliant, not a gap.

## Findings

### Critical

None.

### Major

None.

### Minor

* **Minor-1**: The changes log's per-file "Added" entries for Phase 2 do not include a phase-scoped validation-command transcript (only the aggregate Phase 9 "49 passed" figure is recorded in the Release Summary). This validation session independently re-ran both Step 2.3 validation commands and confirmed they pass (11/11 calculator tests; 5/5 fixtures schema-valid), so there is no functional gap — only a documentation completeness note for future phase sign-offs.
  * Evidence: [desjardins-bilingual-hosted-agents-workshop-changes.md](../../../changes/2026-09-13/desjardins-bilingual-hosted-agents-workshop-changes.md) (Release Summary paragraph, "Test results (final Phase 9 sweep)") has no equivalent phase-by-phase breakdown for Phase 2 specifically.
* **Minor-2**: No calculator-level test explicitly asserts rejection/non-coercion of malformed `amountCents`-adjacent inputs (research's V02: strings, negative numbers, fractional cents) at the calculator function boundary — this protection currently exists only at the schema layer (`cents` definition: `type: integer, minimum: 0`), and Phase 2's own scope (details file Step 2.2) does not list this as a required test. Not a defect against Phase 2's stated success criteria, but worth tracking if a future phase relies on the calculator itself (rather than schema validation) to reject malformed numeric input.
  * Evidence: [apps/workshop/tests/test_calculator.py](../../../../apps/workshop/tests/test_calculator.py) (lines 1-95, full file) — no such test present; [data/synthetic/quote-contract.schema.json](../../../../data/synthetic/quote-contract.schema.json) `"cents"` definition provides the only enforcement.

## Coverage Assessment

Phase 2 is **fully implemented** against its plan checklist, details file, and the research's schema/fixture/arithmetic guidance. Both Step 2.3 validation commands were independently re-executed in this session (not merely trusted from the changes log) and passed cleanly. The two minor findings are documentation/defense-in-depth notes, not functional gaps — neither blocks Phase 2 sign-off.

## Clarifying Questions

None. All evidence needed to validate this phase was available in the plan, details file, research documents, planning log, and the actual repository files/tests.
