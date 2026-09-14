<!-- markdownlint-disable-file -->
# Release Changes: Continuous test trends and LLM-judge evaluation parity

**Related Plan**: continuous-test-trends-llm-judge-plan.instructions.md
**Implementation Date**: 2026-09-14

## Summary

Adds real Azure AI Evaluation SDK judge metrics (coherence/groundedness/task_adherence, guarded/inert until deployment gates clear), a `Continuous-Test-Trends.md` wiki page with tables and mermaid charts backed by a `trend-history/` folder, and richer data-driven GitHub Actions job summaries across all four workflows.

## Changes

### Added

* eval/judge-dataset.jsonl - 10 bilingual (en-CA/fr-CA) query/context/expected records for judge evaluation, derived from real golden-dataset scenarios
* eval/convert_judge_dataset.py - CLI converter producing the judge-evaluation dataset envelope with a `--locale` selector
* eval/tests/test_convert_judge_dataset.py - unit tests for the converter's envelope shape and fail-closed locale handling
* eval/judge_gate.py - `METRICS`/`validate_results()` judge-gate module, separate from the deterministic gate
* eval/run_judge_evaluation.py - author-only, gated judge-evaluation harness (`criteria()`, `evaluate()`, guarded `capture()`/`main()`)
* eval/tests/test_run_judge_evaluation.py - unit tests for `criteria()`, `agent_instructions()` AST extraction, and the guard/no-Azure-import behavior
* scripts/ci_results.py - trend-aggregation script: `junit_totals`, `deterministic_gate_totals`, `judge_totals`, `collect`, `publish_history`, `render_trends`, `chart`, `run_label`, CLI (`--context`/`--junit`/`--evidence`/`--wiki`/etc.) (this file already existed from a prior, unrelated plan serving `web-chat-build.yml`'s `--junit` mode; extended in place rather than recreated)
* scripts/tests/test_ci_results.py - unit tests for the above
* eval/judge_gate.py - new sibling module to `evaluation_gate.py`; `METRICS = ("coherence", "groundedness", "task_adherence")` and `validate_results()` ported near-verbatim from the sibling `foundry-hosted-agents` repo's `eval/evaluation_gate.py`
* eval/run_judge_evaluation.py - author-only, gated judge-evaluation harness adapted from the sibling's `eval/run_hosted_evaluation.py`: `criteria()`, `collect_output_items()`, and `evaluate()`'s `AIProjectClient`/`client.evals.create`/`client.evals.runs.create` polling loop ported near-verbatim; `agent_instructions()` adapted to AST-extract `AGENT_TASK_INSTRUCTIONS` from `src/quote-preparation-agent/graph.py`; `capture()` replaced to raise `RuntimeError` immediately (no hosted-invocation harness exists yet); `main()` has a guard that prints the same author-only message and exits 1 before any Azure SDK import or filesystem/network side effect
* eval/tests/test_run_judge_evaluation.py - unit tests for `criteria()`'s per-metric data mapping, `agent_instructions()`'s real AST extraction from `graph.py`, `main()`'s guard exiting 1 without importing `azure.ai.projects`, and `capture()`'s immediate raise

### Modified

* src/quote-preparation-agent/graph.py - added `AGENT_TASK_INSTRUCTIONS` module-level constant (eval-metadata-only, not wired into execution)
* .github/workflows/continuous-validation.yml - split combined `pytest --junitxml=evidence/tests.xml` into three per-suite JUnit files (`agent.xml`, `deterministic.xml`, `reporting.xml`)
* .github/workflows/deploy-and-evaluate.yml - split combined `pytest --junitxml=offline-evidence/tests.xml` in the `lint` job into the same three per-suite JUnit files; added a guarded (`if: false`) LLM-judge step + SDK install to the `evaluate` job; extended the header banner
* .github/workflows/continuous-validation.yml - added a "Stage deterministic gate result alongside JUnit evidence" step and changed the `offline-test-evidence` artifact's `path:` so `eval/results.json` is bundled as a flat `evidence/results.json` (previously nested as `eval/results.json`, which would not have matched `ci_results.py`'s flat-path read after download); replaced the static "Offline test summary" step with `scripts/ci_results.py --junit`; added a deterministic-gate summary step and a `bicep-lint` job summary step
* .github/workflows/publish-test-trends.yml - replaced placeholder body with real provenance verification, evidence-artifact download, `scripts/ci_results.py` invocation, `ci-report` artifact retention, and a `WIKI_PUSH_TOKEN`-gated wiki push (fails loudly if the secret is unset)

Wiki (C:\temp\fsi-wiki, NOT YET PUSHED -- local clone only):

* Continuous-Test-Trends.md - new page, seeded via `scripts/ci_results.py`'s `render_trends([])` (honest empty state; see Planning Log)
* trend-history/ - new, empty folder ready for the first real run
* Home.md, _Sidebar.md - added "Test Trends" navigation links
* Workflows.md - corrected `publish-test-trends.yml`'s table row, the stale "fully deterministic" sentence, and the "Release path" diagram to show the new guarded judge stage

### Removed

## Additional or Deviating Changes

* `eval/run_judge_evaluation.py`'s `main()` guard is placed after argparse parsing (not as the literal first line) so the documented CLI surface stays real/testable while still guaranteeing the guard fires before any Azure import or side effect.
  * Reason: guarding before argparse would make the CLI surface unreachable dead code.
* Sibling's SSE-stream capture helpers (`capture_summary`, `validate_candidate_evidence`, `verified_safety_refusal`, `completed_response`, `runtime_state`, `stream_error`, `CaptureError`) intentionally not ported to `run_judge_evaluation.py`.
  * Reason: they depend on a hosted-agent invocation harness (`scripts/invoke-agent.sh` equivalent) this repo does not have; `capture()` always raises before any of that logic could run.
* `scripts/ci_results.py` dropped the sibling's `evaluation_totals()`/`load_totals()` and the "load" dimension entirely.
  * Reason: this repo has no hosted-agent capture pipeline or load-test harness; keeping them would either dead-code-forever-return-None or fabricate a section.
* `deterministic_gate_totals()`'s lookup in `collect()` checks both `offline-test-evidence/results.json` (continuous-validation.yml's layout) and `evaluation-evidence/results.json` (deploy-and-evaluate.yml's layout), first match wins.
  * Reason: the two workflows bundle `eval/results.json` into different artifacts; this keeps `collect()` correct for both without duplicating the file into two artifacts.
* `publish-test-trends.yml` gained a `run_attempt` dispatch input and a "Resolve source run attempt" step not explicitly specified in the details doc.
  * Reason: the existing file only defined a required `run_id` input; a manual dispatch needs a way to resolve the latest attempt when the caller doesn't know it.
* `Continuous-Test-Trends.md` was seeded empty (`render_trends([])`) rather than from a real historical run.
  * Reason: the only completed `Continuous Validation` runs on `main` predate this plan's JUnit-split/flat-artifact changes (verified by downloading and inspecting run 34861865115's actual artifact: nested `eval/results.json` and a single combined `evidence/tests.xml`). Replaying it through the new `collect()` would either silently miss data or require hand-massaging the download to fake the new layout. Documented as a follow-on instead of fabricating a seed record.

## Release Summary

All 8 implementation phases complete. 71/71 pytest tests pass across `eval`, `scripts`, `src/quote-preparation-agent/tests`, `apps/workshop/tests`, `mcp/application-server/tests`, `mcp/rulebook-server/tests`. All four workflow YAML files parse cleanly. The deterministic evaluation gate (`eval/evaluation_gate.py`) still passes 13/13 on the real golden dataset, unaffected by this work.

**Repository files added**: `eval/judge-dataset.jsonl`, `eval/convert_judge_dataset.py`, `eval/judge_gate.py`, `eval/run_judge_evaluation.py`, `eval/tests/test_convert_judge_dataset.py`, `eval/tests/test_run_judge_evaluation.py`, `scripts/tests/test_ci_results.py`.

**Repository files modified**: `src/quote-preparation-agent/graph.py` (added `AGENT_TASK_INSTRUCTIONS`), `scripts/ci_results.py` (extended in place -- pre-existed from an earlier plan), `.github/workflows/continuous-validation.yml`, `.github/workflows/deploy-and-evaluate.yml`, `.github/workflows/publish-test-trends.yml`.

**No production code paths changed**: `default_model`, `build_graph`, and every node function in `graph.py` are untouched. The new LLM-judge step in `deploy-and-evaluate.yml` is `if: false` (inert). No Azure credentials or network calls are exercised by anything added in this release.

**Wiki (`C:\temp\fsi-wiki`, local clone only -- NOT pushed)**: `Continuous-Test-Trends.md` (new, seeded empty with an honest explanatory note), `trend-history/` (new, empty), `Home.md`/`_Sidebar.md` (navigation links added), `Workflows.md` (corrected stale sentence, table row, and release-path diagram). Pushing these to the live wiki requires explicit user confirmation (live-mutation step, Planning Log Step 7.3) and has not been performed.

**Outstanding manual step**: `WIKI_PUSH_TOKEN` repository secret must be provisioned by a repository admin before `publish-test-trends.yml`'s wiki-push step can succeed (see Planning Log WI-02) -- I cannot create this secret myself.

**Deployment notes**: none of this release deploys anything to Azure; it only adds author-only/gated evaluation tooling and CI reporting. See the Planning Log's Discrepancy Log and Suggested Follow-On Work for full deviation rationale and next steps.
